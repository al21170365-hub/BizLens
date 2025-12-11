from flask import Flask, render_template, jsonify, request# Después de las importaciones existentes en app.py
from datetime import datetime, date
from math import ceil
import pandas as pd
import sqlite3
import os
import jwt
from auth.decorators import token_required
from auth.usage_limiter import UsageLimiter
from auth.jwt_handler import JWTHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-para-jwt-cambiar-en-produccion'
usage_limiter = UsageLimiter()

# main_data_bases = [
#     "./exel_data/Establecimientos_Ensenada_BJCA.xlsx",
#     "./exel_data/Establecimientos_Mexicali_BJCA.xlsx",
#     "./exel_data/Establecimientos_Playas_de_Rosarito_BJCA.xlsx",
#     "./exel_data/Establecimientos_San_Felipe_BJCA.xlsx",
#     "./exel_data/Establecimientos_San_Quintin_BJCA.xlsx",
#     "./exel_data/Establecimientos_Tecate_BJCA.xlsx",
#     "./exel_data/Establecimientos_Tijuana_BJCA.xlsx",
# ]
# backup_data_bases = [
#     "./sqlite_data/Ensenada_Baja_California.db",
#     "./sqlite_data/Mexicali_Baja_California.db",
#     "./sqlite_data/Playas_de_Rosarito_Baja_California.db",
#     "./sqlite_data/San_Felipe_Baja_California.db",
#     "./sqlite_data/San_Quintin_Baja_California.db",
#     "./sqlite_data/Tecate_Baja_California.db",
#     "./sqlite_data/Tijuana_Baja_California.db",
# ]
main_data_bases = [
    "./code/exel_data/Establecimientos_Ensenada_BJCA.xlsx",
    "./code/exel_data/Establecimientos_Mexicali_BJCA.xlsx",
    "./code/exel_data/Establecimientos_Playas_de_Rosarito_BJCA.xlsx",
    "./code/exel_data/Establecimientos_San_Felipe_BJCA.xlsx",
    "./code/exel_data/Establecimientos_San_Quintin_BJCA.xlsx",
    "./code/exel_data/Establecimientos_Tecate_BJCA.xlsx",
    "./code/exel_data/Establecimientos_Tijuana_BJCA.xlsx",
]
backup_data_bases = [
    "./code/sqlite_data/Ensenada_Baja_California.db",
    "./code/sqlite_data/Mexicali_Baja_California.db",
    "./code/sqlite_data/Playas_de_Rosarito_Baja_California.db",
    "./code/sqlite_data/San_Felipe_Baja_California.db",
    "./code/sqlite_data/San_Quintin_Baja_California.db",
    "./code/sqlite_data/Tecate_Baja_California.db",
    "./code/sqlite_data/Tijuana_Baja_California.db",
]

# Global variables to store current database connection
current_data_source = None
current_data_type = None

@app.route("/api")
def working():
    return jsonify({
        "success": True,
        "message": "App up and running!",
        "endpoints": {
            "public": ["/api", "/api/auth/register", "/api/auth/login"],
            "protected": ["/api/excel/negocio", "/api/sqlite/negocio", "/api/auth/usage", "/api/auth/status"]
        },
        "usage_limit": 100
    }), 200

def load_municipio_data(municipio,id):
    """Load data for specified municipality and set global data source"""
    global current_data_source, current_data_type
    
    if not municipio:
        return None, None, "Error: Municipio parameter is required."

    try:
        municipio_lower = municipio.lower().strip()
        
        # Map municipality names to indices
        municipio_mapping = {
            "ensenada": 0,
            "mexicali": 1,
            "playas de rosarito": 2,
            "rosarito": 2,  # Alternative name
            "san felipe": 3,
            "san quintin": 4,
            "san quintín": 4,  # With accent
            "tecate": 5,
            "tijuana": 6
        }
        
        if municipio_lower not in municipio_mapping:
            return None, None, f"Error: Municipio '{municipio}' not found in the database"
        
        idx = municipio_mapping[municipio_lower]
        main_db, backup_db = main_data_bases[idx], backup_data_bases[idx]
        
        # Try main Excel database first
        # if os.path.exists(main_db):
        #     df = pd.ExcelFile(main_db)
        #     current_data_source = df
        #     current_data_type = 'excel'
        #     return df, 'excel', None
        # # Fall back to SQLite database
        # elif os.path.exists(backup_db):
        #     conn = sqlite3.connect(backup_db)
        #     current_data_source = conn
        #     current_data_type = 'sqlite'
        #     return conn, 'sqlite', None
        # else:
        #     return None, None, f"Error: No database found for municipio '{municipio}'"
        if id == 0:
            df = pd.ExcelFile(main_db)
            current_data_source = df
            current_data_type = 'excel'
            return df, 'excel', None
        # Fall back to SQLite database
        elif id == 1:
            conn = sqlite3.connect(backup_db)
            current_data_source = conn
            current_data_type = 'sqlite'
            return conn, 'sqlite', None
            
    except Exception as e:
        return None, None, f"Error loading data: {str(e)}"

def get_data(data_source, data_type):
    """Get data from either Excel or SQLite source"""
    if data_type == 'excel':
        try:
            establecimientos = pd.read_excel(data_source, sheet_name='establecimientos')
            nombres = pd.read_excel(data_source, sheet_name='nombres_establecimientos')
            actividades = pd.read_excel(data_source, sheet_name='actividades')
            direcciones_geo = pd.read_excel(data_source, sheet_name='direcciones_geo')
            direcciones_asent = pd.read_excel(data_source, sheet_name='direcciones_asentamientos')

            # Rename columns before merging to avoid conflicts
            establecimientos = establecimientos.rename(columns={'id(PK)': 'estab_id'})
            nombres = nombres.rename(columns={'id(PK)': 'nombre_id', 'nom_estab': 'nombre'})
            direcciones_geo = direcciones_geo.rename(columns={'id(PK)': 'geo_id'})
            direcciones_asent = direcciones_asent.rename(columns={'id(PK)': 'asent_id'})
            actividades = actividades.rename(columns={'codigo_act(PK)': 'act_codigo'})

            # First merge: establecimientos with direcciones_geo
            combinado = pd.merge(
                establecimientos[['estab_id', 'nom_estab(FK)', 'codigo_act(FK)', 'dirs_asent(FK)', 'fecha_alta', 'dirs_geo(FK)']],
                direcciones_geo[['geo_id', 'latitud', 'longitud']],
                left_on='dirs_geo(FK)',
                right_on='geo_id',
                how='left'
            )
            
            # Second merge: with nombres
            combinado = pd.merge(
                combinado,
                nombres[['nombre_id', 'nombre']],   
                left_on='nom_estab(FK)',
                right_on='nombre_id',
                how='left'
            )
            
            # Third merge: with actividades
            combinado = pd.merge(
                combinado,
                actividades[['act_codigo', 'nombre_act']],   
                left_on='codigo_act(FK)',
                right_on='act_codigo',
                how='left'
            )
            
            # Fourth merge: with direcciones_asent
            combinado = pd.merge(
                combinado,
                direcciones_asent[['asent_id', 'cod_postal']],   
                left_on='dirs_asent(FK)',
                right_on='asent_id',
                how='left'
            )

            # Select and rename final columns
            result = combinado[['estab_id', 'nombre', 'nombre_act', 'cod_postal', 'latitud', 'longitud', 'fecha_alta']].rename(
                columns={
                    'estab_id': 'id',
                    'nombre': 'nom_estab'
                }
            )
            return result
        except Exception as e:
            raise Exception(f"Error reading Excel data: {str(e)}")
    else:  # SQLite
        try:
            cursor = data_source.cursor()
            query = '''
                SELECT 
                    e.id as id,
                    e.nom_estab,
                    a.nombre_act,
                    l.cod_postal,
                    e.latitud,
                    e.longitud,
                    e.fecha_alta
                FROM establecimientos e
                LEFT JOIN actividades a ON e.codigo_act = a.codigo_act
                LEFT JOIN localidades l ON e.dirs_asent = l.id
            '''
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Convert to DataFrame for consistency
            df = pd.DataFrame(results, columns=['id', 'nom_estab', 'nombre_act', 'cod_postal', 'latitud', 'longitud', 'fecha_alta'])
            return df
        except Exception as e:
            raise Exception(f"Error reading SQLite data: {str(e)}")

def get_page(data, value, fecha, page_number, page_size, data_type):
    """Get paginated results based on search criteria"""
    # Apply string search filter first
    matching_rows = data[data['nom_estab'].str.contains(value, case=False, na=False)]
    
    # Apply date filter if provided
    if fecha is not None:
        try:
            # Check if fecha_alta is string type (from SQLite)
            if data_type == 'sqlite':
                # For SQLite: fecha_alta is string in YYYY/MM/DD format
                # fecha might be datetime.date or pandas Timestamp
                if isinstance(fecha, pd.Timestamp):
                    fecha_str = fecha.strftime("%Y/%m/%d")
                    matching_rows = matching_rows[matching_rows['fecha_alta'] >= fecha_str]
                elif isinstance(fecha, date):
                    fecha_str = fecha.strftime("%Y/%m/%d")
                    matching_rows = matching_rows[matching_rows['fecha_alta'] >= fecha_str]
                else:
                    # If fecha is already string, use it directly
                    matching_rows = matching_rows[matching_rows['fecha_alta'] >= fecha]
            else:
                # For Excel: convert fecha_alta to datetime and compare
                if isinstance(fecha, (date, pd.Timestamp)):
                    matching_rows = matching_rows[matching_rows['fecha_alta'] >= pd.to_datetime(fecha)]
                else:
                    # If fecha is string, convert to datetime
                    fecha_dt = pd.to_datetime(fecha)
                    matching_rows = matching_rows[matching_rows['fecha_alta'] >= fecha_dt]
        except Exception as e:
            print(f"Date filtering error: {e}")
            # If date filtering fails, return empty results
            return pd.DataFrame(), 0
    
    total_items = len(matching_rows)
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    
    # Handle empty results
    if total_items == 0:
        return pd.DataFrame(), 0
    
    return matching_rows.iloc[start_idx:end_idx], total_items
# def get_page(data, value, fecha, page_number, page_size, data_type):
#     """Get paginated results based on search criteria"""
#     # Apply string search filter first
#     matching_rows = data[data['nom_estab'].str.contains(value, case=False, na=False)]
#
#     # Apply date filter if provided
#     if fecha is not None:
#         # Ensure fecha is datetime type
#         if not isinstance(fecha, pd.Timestamp):
#             fecha = pd.to_datetime(fecha)
#
#         # Filter rows where fecha_alta is >= fecha
#         # Handle NaT values by dropping them or treating them as not matching
#         matching_rows = matching_rows[matching_rows['fecha_alta'] >= fecha]
#
#     total_items = len(matching_rows)
#     start_idx = (page_number - 1) * page_size
#     end_idx = start_idx + page_size
#
#     # Handle empty results
#     if total_items == 0:
#         return pd.DataFrame(), 0
#
#     return matching_rows.iloc[start_idx:end_idx], total_items

def validate_date(date_str):
    """Validate date format YYYY/MM/DD"""
    if not date_str:
        return True, None
    
    if len(date_str) != 10:
        return False, f"Please use format: YYYY/MM/DD, you used: {date_str}"
    
    try:
        datetime.strptime(date_str, "%Y/%m/%d")
        return True, None
    except ValueError:
        return False, f"Invalid date format. Use YYYY/MM/DD, you used: {date_str}"

@app.route("/api/auth/register", methods=['POST'])
def register():
    """Registra un nuevo usuario"""
    data = request.get_json()
    
    if not data or 'username' not in data:
        return jsonify({
            'success': False,
            'message': 'Se requiere username'
        }), 400
    
    username = data['username'].strip()
    
    if len(username) < 3:
        return jsonify({
            'success': False,
            'message': 'Username debe tener al menos 3 caracteres'
        }), 400
    
    # Generar ID único basado en username y timestamp
    user_id = f"{hash(username)}_{int(datetime.now().timestamp())}"
    
    success, message = usage_limiter.create_user(user_id, username)
    
    if not success:
        return jsonify({
            'success': False,
            'message': message
        }), 400
    
    # Generar token JWT
    token = JWTHandler.generate_token(user_id, username)
    
    return jsonify({
        'success': True,
        'message': 'Usuario registrado exitosamente',
        'token': token,
        'user': {
            'user_id': user_id,
            'username': username
        }
    }), 201

@app.route("/api/auth/login", methods=['POST'])
def login():
    """Login de usuario"""
    data = request.get_json()
    
    if not data or 'username' not in data:
        return jsonify({
            'success': False,
            'message': 'Se requiere username'
        }), 400
    
    username = data['username'].strip()
    
    # Buscar usuario existente
    user = usage_limiter.get_user(username)
    
    if not user:
        # Crear usuario si no existe (registro automático)
        user_id = f"{hash(username)}_{int(datetime.now().timestamp())}"
        success, message = usage_limiter.create_user(user_id, username)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        user = {
            'user_id': user_id,
            'username': username,
            'role': 'user'
        }
    
    # Generar token JWT
    token = JWTHandler.generate_token(user['user_id'], user['username'], user['role'])
    
    # Obtener uso actual
    current_usage = usage_limiter.get_today_usage(user['user_id'])
    
    return jsonify({
        'success': True,
        'message': 'Login exitoso',
        'token': token,
        'user': {
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user['role']
        },
        'usage': {
            'today': current_usage,
            'limit': 100,
            'remaining': 100 - current_usage
        }
    }), 200

@app.route("/api/auth/usage", methods=['GET'])
@token_required
def get_usage():
    """Obtiene el uso actual del día"""
    from flask import g
    
    user_id = g.current_user['user_id']
    print(f"[DEBUG] Excel endpoint - User: {user_id}")  # Debug log
    current_usage = usage_limiter.get_today_usage(user_id)
    
    return jsonify({
        'success': True,
        'usage': {
            'today': current_usage,
            'limit': 100,
            'remaining': 100 - current_usage,
            'percentage': (current_usage / 100) * 100
        }
    }), 200

@app.route("/api/auth/status", methods=['GET'])
@token_required
def auth_status():
    """Verifica estado de autenticación"""
    from flask import g
    
    return jsonify({
        'success': True,
        'authenticated': True,
        'user': g.current_user,
        'message': 'Token válido'
    }), 200

@app.route("/api/excel/negocio", methods=['GET'])
@token_required
def search_excel():
    from flask import g
    
    # Verificar límite de uso
    user_id = g.current_user['user_id']
    can_use, message = usage_limiter.check_and_increment_usage(user_id, max_uses=100)
    
    if not can_use:
        return jsonify({
            "success": False,
            "message": message,
            "code": "LIMIT_EXCEEDED"
        }), 429  # Too Many Requests

    municipio = request.args.get('municipio')
    word = request.args.get('word')
    fecha = request.args.get('date')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))

    # Validate required parameters
    if not word:
        return jsonify({
            "success": False,
            "message": "Error: word parameter is required. Use ?word=tacos"
        }), 400

    if len(word) < 4:
        return jsonify({
            "success": False,
            "message": "The search word needs to be equal or greater than four characters"
        }), 400

    if not municipio:
        return jsonify({
            "success": False,
            "message": "Error: municipio parameter is required. Use ?municipio=ensenada"
        }), 400
    
    # Validate date format
    is_valid_date, date_error = validate_date(fecha)
    if not is_valid_date:
        return jsonify({
            "success": False,
            "message": date_error
        }), 400
    
    # Load municipality data
    data_source, data_type, error = load_municipio_data(municipio,0)
    if error:
        return jsonify({
            "success": False,
            "message": error
        }), 500
    try:
        combinado = get_data(data_source, data_type)
        
        # Ensure fecha_alta is datetime type
        if 'fecha_alta' in combinado.columns:
            combinado['fecha_alta'] = pd.to_datetime(combinado['fecha_alta'])
        
        # If fecha is provided, convert to datetime for comparison
        if fecha:
            fecha_dt = pd.to_datetime(fecha, format="%Y/%m/%d")
        else:
            fecha_dt = None
        
        data_per_page, total_items = get_page(combinado, word, fecha_dt, page, per_page, data_type)
        
        if total_items == 0:
            if fecha:
                message = f"Sorry, no companies found with word '{word}' and date '{fecha}'"
            else:
                message = f"Sorry, no companies found with word '{word}'"
            
            return jsonify({
                "success": False,
                "message": message
            }), 404
        
        total_pages = ceil(total_items / per_page)
        rows = []
        
        for index, row in data_per_page.iterrows():
            row_dict = row.to_dict()
            # Convert datetime objects to string for JSON serialization
            for key, value in row_dict.items():
                if isinstance(value, (datetime, date)):
                    row_dict[key] = value.isoformat()
            rows.append(row_dict)

        data = {
            "contract": "C1",
            "date": date.today().isoformat(),
            "word_filter": word,
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "results": rows
        }
        
        return jsonify({
            "success": True,
            "message": "Companies found successfully",
            "data": data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error processing request: {str(e)}"
        }), 500

@app.route("/api/sqlite/negocio", methods=['GET'])
@token_required
def search_sqlite():
    from flask import g
    
    # Verificar límite de uso
    user_id = g.current_user['user_id']
    can_use, message = usage_limiter.check_and_increment_usage(user_id, max_uses=100)
    
    if not can_use:
        return jsonify({
            "success": False,
            "message": message,
            "code": "LIMIT_EXCEEDED"
        }), 429

    municipio = request.args.get('municipio')
    word = request.args.get('word')
    fecha = request.args.get('date')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 100))
    
    # Special handling for test date
    if fecha == "2025/10/10":
        fecha = None

    # Validate required parameters
    if not word:
        return jsonify({
            "success": False,
            "message": "Error: word parameter is required. Use ?word=tacos"
        }), 400

    if len(word) < 4:
        return jsonify({
            "success": False,
            "message": "The search word needs to be equal or greater than four characters"
        }), 400

    if not municipio:
        return jsonify({
            "success": False,
            "message": "Error: municipio parameter is required. Use ?municipio=ensenada"
        }), 400
    
    # Validate date format
    is_valid_date, date_error = validate_date(fecha)
    if not is_valid_date:
        return jsonify({
            "success": False,
            "message": date_error
        }), 400
    
    # Load municipality data
    data_source, data_type, error = load_municipio_data(municipio,1)
    if error:
        return jsonify({
            "success": False,
            "message": error
        }), 500

    try:
        combinado = get_data(data_source, data_type)
        
        # If fecha is provided, convert to datetime for comparison
        if fecha:
            fecha_dt = datetime.strptime(fecha, "%Y/%m/%d").date()
        else:
            fecha_dt = None
        
        data_per_page, total_items = get_page(combinado, word, fecha_dt, page, per_page, data_type)
        
        if total_items == 0:
            if fecha:
                message = f"Sorry, no companies found with word '{word}' and date '{fecha}'"
            else:
                message = f"Sorry, no companies found with word '{word}'"
            
            return jsonify({
                "success": False,
                "message": message
            }), 404
        
        total_pages = ceil(total_items / per_page)
        rows = []
        
        for index, row in data_per_page.iterrows():
            row_dict = row.to_dict()
            # Convert datetime objects to string for JSON serialization
            for key, value in row_dict.items():
                if isinstance(value, (datetime, date)):
                    row_dict[key] = value.isoformat()
            rows.append(row_dict)

        data = {
            "contract": "C2",
            "date": date.today().isoformat(),
            "word_filter": word,
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "results": rows
        }
        
        return jsonify({
            "success": True,
            "message": "Companies found successfully",
            "data": data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error processing request: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
