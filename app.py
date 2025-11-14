from flask import Flask, render_template, jsonify, request
from datetime import datetime, date
from math import ceil
import pandas as pd
import sqlite3
import os

app = Flask(__name__)

main_data_bases = [
    "./exel_data/Establecimientos_Ensenada_BJCA.xlsx",
    "./exel_data/Establecimientos_Mexicali_BJCA.xlsx",
    "./exel_data/Establecimientos_Playas_de_Rosarito_BJCA.xlsx",
    "./exel_data/Establecimientos_San_Felipe_BJCA.xlsx",
    "./exel_data/Establecimientos_San_Quintin_BJCA.xlsx",
    "./exel_data/Establecimientos_Tecate_BJCA.xlsx",
    "./exel_data/Establecimientos_Tijuana_BJCA.xlsx",
]
backup_data_bases = [
    "./sqlite_data/Ensenada_Baja_California.db",
    "./sqlite_data/Mexicali_Baja_California.db",
    "./sqlite_data/Playas_de_Rosarito_Baja_California.db",
    "./sqlite_data/San_Felipe_Baja_California.db",
    "./sqlite_data/San_Quintin_Baja_California.db",
    "./sqlite_data/Tecate_Baja_California.db",
    "./sqlite_data/Tijuana_Baja_California.db",
]

# Global variables to store current database connection
current_data_source = None
current_data_type = None

@app.route("/")
def working():
    return jsonify({
        "success": True,
        "message": "App up and runing!"
    }), 200

def load_municipio_data(municipio):
    """Load data for specified municipality and set global data source"""
    global current_data_source, current_data_type
    
    if not municipio:
        return None, "Error: Municipio parameter is required."

    try:
        municipio_lower = municipio.lower()
        
        if municipio_lower == "ensenada":
            main_db, backup_db = main_data_bases[0], backup_data_bases[0]
        elif municipio_lower == "mexicali":
            main_db, backup_db = main_data_bases[1], backup_data_bases[1]
        elif municipio_lower in ["playas de rosarito", "plays de rosarito"]:
            main_db, backup_db = main_data_bases[2], backup_data_bases[2]
        elif municipio_lower in ["san felipe", "san felige"]:
            main_db, backup_db = main_data_bases[3], backup_data_bases[3]
        elif municipio_lower == "san quintin":
            main_db, backup_db = main_data_bases[4], backup_data_bases[4]
        elif municipio_lower == "tecate":
            main_db, backup_db = main_data_bases[5], backup_data_bases[5]
        elif municipio_lower == "tijuana":
            main_db, backup_db = main_data_bases[6], backup_data_bases[6]
        else:
            return None, f"Error: Municipio '{municipio}' not found"
        
        # Try main Excel database first
        if os.path.exists(main_db):
            df = pd.ExcelFile(main_db)
            current_data_source = df
            current_data_type = 'excel'
            return df, None
        # Fall back to SQLite database
        elif os.path.exists(backup_db):
            conn = sqlite3.connect(backup_db)
            current_data_source = conn
            current_data_type = 'sqlite'
            return conn, None
        else:
            return None, f"Error: No database found for municipio '{municipio}'"
            
    except Exception as e:
        return None, f"Error loading data: {str(e)}"

def get_data(data_source):
    establecimientos = pd.read_excel(data_source, sheet_name='establecimientos')
    nombres = pd.read_excel(data_source, sheet_name='nombres_establecimientos')
    actividades = pd.read_excel(data_source, sheet_name='actividades')
    direcciones = pd.read_excel(data_source, sheet_name='direcciones_geo')

    combinado = pd.merge(
        establecimientos[['id(PK)','nom_estab(FK)', 'codigo_act(FK)', 'fecha_alta', 'dirs_geo(FK)']],
        direcciones[['id(PK)', 'latitud', 'longitud']],
        left_on='dirs_geo(FK)',
        right_on='id(PK)',
        how='left'
    )
    combinado = pd.merge(
        combinado,
        nombres[['id(PK)', 'nom_estab']],   
        left_on='nom_estab(FK)',
        right_on='id(PK)',
        how='left'
    )
    combinado = pd.merge(
        combinado,
        actividades[['codigo_act(PK)', 'nombre_act']],   
        left_on='codigo_act(FK)',
        right_on='codigo_act(PK)',
        how='left'
    )

    return combinado[['id(PK)_x','nom_estab', 'nombre_act', 'latitud', 'longitud', 'fecha_alta']].rename(
        columns={'id(PK)_x': 'id'}
    )

def get_page(data_source,value,page_number=1, page_size=10,type=True):
    if type:
        matching_rows = data_source[data_source['nom_estab'].str.contains(value, case = False)]
    else:
        matching_rows = data_source[data_source['fecha_alta'] == value]
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    return matching_rows.iloc[start_idx:end_idx]

@app.route("/api/exel/negocio", methods=['GET'])
def search():
    word = request.args.get('word')
    municipio = request.args.get('municipio')
    page = int(request.args.get('page',1))
    per_page = int(request.args.get('per_page',10))

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

    # Load municipality data
    data_source, error = load_municipio_data(municipio)
    if error:
        return jsonify({
            "success": False,
            "message": error
        }), 400

    combinado = get_data(data_source)
    
    matching_rows = get_page(combinado,word,page,per_page)
    total_items = len(combinado)
    total_pages = ceil(total_items/per_page)
    rows = []
    for index, row in matching_rows.iterrows():
        row_dict = row.to_dict()
        rows.append(row_dict)

    data = {
        "contract": "C1",
        "date": date.today(),
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

@app.route("/api/exel/negocio/fecha", methods=['GET'])
def filter_search():
    fecha = request.args.get('date')
    municipio = request.args.get('municipio')
    page = int(request.args.get('page',1))
    per_page = int(request.args.get('per_page',10))

    if not fecha:
        return jsonify({
            "success": False,
            "message": "Error: Date parameter is required. Use ?date=YYYY/MM/DD"
        }), 400

    if len(fecha) != 10 or fecha.count('/') != 2:
        return jsonify({
            "success": False,
            "message": "Error: Date format: YYYY/MM/DD"
        }), 400

    if not municipio:
        return jsonify({
            "success": False,
            "message": "Error: municipio parameter is required. Use ?municipio=ensenada"
        }), 400

    # Load municipality data
    data_source, error = load_municipio_data(municipio)
    if error:
        return jsonify({
            "success": False,
            "message": error
        }), 400
    
    combinado = get_data(data_source)

    matching_rows = get_page(combinado,fecha,page,per_page,False)
    total_items = len(combinado)
    total_pages = ceil(total_items/per_page)
    rows = []
    for index, row in matching_rows.iterrows():
        row_dict = row.to_dict()
        rows.append(row_dict)

    data = {
        "contract": "C2",
        "date": date.today(),
        "date_filter": fecha,
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
        "message": "Companies found successfully by date filter",
        "data": data
    }), 200

