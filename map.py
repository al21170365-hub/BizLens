import streamlit as st
import pandas as pd
import requests
import pydeck as pdk  # Added for better map visualization
import random
import jwt

def register_user(username):
    """Registra un nuevo usuario"""
    url = "http://127.0.0.1:5000/api/auth/register"
    try:
        response = requests.post(url, json={'username': username}, timeout=10)
        if response.status_code == 201:
            data = response.json()
            if data['success']:
                return data['token'], data['user'], None
        return None, None, f"Error: {response.json().get('message', 'Unknown error')}"
    except Exception as e:
        return None, None, f"Error de conexión: {str(e)}"

def login_user(username):
    """Inicia sesión con un usuario"""
    url = "http://127.0.0.1:5000/api/auth/login"
    try:
        response = requests.post(url, json={'username': username}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                return data['token'], data['user'], data.get('usage'), None
        return None, None, None, f"Error: {response.json().get('message', 'Unknown error')}"
    except Exception as e:
        return None, None, None, f"Error de conexión: {str(e)}"


def get_usage_info(token):
    """Obtiene información de uso actual"""
    if not token:
        return None
    
    url = "http://127.0.0.1:5000/api/auth/usage"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                return data['usage']
    except:
        pass
    return None

def check_auth_status(token):
    """Verifica si el token es válido"""
    if not token:
        return False
    
    url = "http://127.0.0.1:5000/api/auth/status"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def decode_token_info(token):
    """Decodifica el token para mostrar información (solo lectura)"""
    try:
        # Decodificar sin verificar firma (solo para mostrar info)
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except:
        return None

# Initialize session state for page tracking and data caching
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'current_data' not in st.session_state:
    st.session_state.current_data = None
if 'search_params' not in st.session_state:
    st.session_state.search_params = {}
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'usage_info' not in st.session_state:
    st.session_state.usage_info = None

# Función para generar colores únicos basados en códigos postales
def generate_colors_for_postal_codes(postal_codes):
    """
    Genera un color único para cada código postal diferente.
    
    Args:
        postal_codes: Lista de códigos postales
    
    Returns:
        Dict: Mapeo de código postal a color [R, G, B, A]
    """
    unique_codes = sorted(list(set(postal_codes)))
    color_map = {}
    
    # Colores predefinidos para mejor visibilidad
    predefined_colors = [
        [255, 0, 0, 160],    # Rojo
        [0, 255, 0, 160],    # Verde
        [0, 0, 255, 160],    # Azul
        [255, 255, 0, 160],  # Amarillo
        [255, 0, 255, 160],  # Magenta
        [0, 255, 255, 160],  # Cian
        [255, 165, 0, 160],  # Naranja
        [128, 0, 128, 160],  # Púrpura
        [165, 42, 42, 160],  # Marrón
        [0, 128, 0, 160],    # Verde oscuro
        [128, 128, 0, 160],  # Oliva
        [0, 128, 128, 160],  # Verde azulado
        [128, 0, 0, 160],    # Rojo oscuro
        [0, 0, 128, 160],    # Azul marino
        [128, 128, 128, 160], # Gris
    ]
    
    # Asignar colores predefinidos primero, luego generar aleatorios si hay más
    for i, code in enumerate(unique_codes):
        if i < len(predefined_colors):
            color_map[code] = predefined_colors[i]
        else:
            # Generar color aleatorio pero evitando colores muy claros
            color_map[code] = [
                random.randint(30, 225),  # R
                random.randint(30, 225),  # G
                random.randint(30, 225),  # B
                160  # Alpha (transparencia)
            ]
    
    return color_map

def get_negocio(municipio, word, fecha, page):
    """
    Fetch business data from API with fallback to SQLite endpoint.
    
    Args:
        municipio: Municipality parameter
        word: Search word parameter
        fecha: Date parameter
        page: Page number for pagination
    
    Returns:
        JSON response data or None if all requests fail
    """
    if not token:
        st.error("No estás autenticado. Por favor inicia sesión.")
        return None
    
    headers = {'Authorization': f'Bearer {token}'}

    excel_url = f"http://127.0.0.1:5000/api/excel/negocio?municipio={municipio}&word={word}&date={fecha}&page={page}&per_page=50"
    sqlite_url = f"http://127.0.0.1:5000/api/sqlite/negocio?municipio={municipio}&word={word}&date={fecha}&page={page}&per_page=50"
    
    endpoints = [
        ("Excel API", excel_url),
        ("SQLite API", sqlite_url)
    ]
    
    for endpoint_name, url in endpoints:
        try:
            st.info(f"Trying {endpoint_name}...")
            print(url)
            response = requests.get(url, timeout=15)
            
            # Manejar límite de uso
            if response.status_code == 429:
                error_data = response.json()
                st.error(f"⛔ {error_data.get('message', 'Límite diario alcanzado')}")
                return None
            # Manejar token inválido
            if response.status_code == 401:
                error_data = response.json()
                st.error(f"🔑 {error_data.get('message', 'Token inválido o expirado')}")
                return None
            # Handle specific status codes
            if response.status_code == 400:
                error_data = response.json()
                st.error(f"Bad Request: {error_data.get('message', 'Invalid parameters')}")
                return None
            
            if response.status_code == 404:
                error_data = response.json()
                st.warning(f"Not Found: {error_data.get('message', 'No data found')}")
                return None

            if response.status_code == 500:
                error_data = response.json()
                st.error(f"Server Error: {error_data.get('message', 'Internal server error')}")
                continue  # Try next endpoint

            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                st.success(f"Data retrieved successfully from {endpoint_name}")
                return data
            else:
                st.warning(f"{endpoint_name} returned unsuccessful: {data.get('message')}")
                continue
                
        except requests.exceptions.ConnectionError:
            st.error(f"Cannot connect to {endpoint_name}. Make sure the Flask server is running on 127.0.0.1:5000")
            continue
        except requests.exceptions.Timeout:
            st.warning(f"{endpoint_name} timeout. Trying next endpoint...")
            continue
        except requests.exceptions.RequestException as e:
            st.error(f"{endpoint_name} error: {str(e)}")
            continue
    
    st.error("All API endpoints failed. Please check your Flask server.")
    return None

def get_cords(data):
    """
    Extract coordinates and additional business info from API response.
    
    Returns:
        lat: List of latitudes
        lon: List of longitudes
        names: List of business names
        activities: List of business activities
        postal_codes: List of postal codes
        df_data: DataFrame with complete business info
    """
    lat = []
    lon = []
    names = []
    activities = []
    postal_codes = []
    df_data = []
    
    if data and 'data' in data and 'results' in data['data']:
        for business in data['data']['results']:
            lati = business.get('latitud')
            long = business.get('longitud')
            name = business.get('nom_estab', 'Unknown')
            activity = business.get('nombre_act', 'Unknown')
            postal_code = business.get('cod_postal', 'Unknown')
            
            # Only add if coordinates are valid
            if lati is not None and long is not None:
                lat.append(lati)
                lon.append(long)
                names.append(name)
                activities.append(activity)
                postal_codes.append(postal_code)
                
                # Store complete business info
                df_data.append({
                    'Business Name': name,
                    'Activity': activity,
                    'Postal Code': postal_code,
                    'Latitude': lati,
                    'Longitude': long,
                    'Date Registered': business.get('fecha_alta', 'Unknown')
                })
    
    return lat, lon, names, activities, postal_codes, pd.DataFrame(df_data)

def create_map_dataframe(lat, lon, names, activities, postal_codes):
    """Create DataFrame for Streamlit map visualization."""
    if not lat or not lon:
        return pd.DataFrame()
    
    # Generate color mapping for postal codes
    color_map = generate_colors_for_postal_codes(postal_codes)
    
    # Create DataFrame for map with colors
    data = {
        'lat': lat,
        'lon': lon,
        'name': names,
        'activity': activities,
        'postal_code': postal_codes,
        'color': [color_map.get(code, [200, 30, 0, 160]) for code in postal_codes],
        'size': [15] * len(lat)  # Fixed size for all markers
    }
    
    return pd.DataFrame(data), color_map

def create_pydeck_layer(df, color_map):
    """Create a PyDeck layer for more advanced visualization with colored points."""
    if df.empty:
        return None
    
    # Create a layer with colors based on postal code
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=df,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius=50,  # Este valor es el tamaño base
        radius_min_pixels=3,     # Tamaño mínimo en píxeles (siempre visible)
        radius_max_pixels=3,   # Tamaño máximo en píxeles
        radius_scale=1,          # Escala del radio
        pickable=True,
        auto_highlight=True,
        filled=True,
        stroked=True,
        line_width_min_pixels=1,
        line_width_max_pixels=3,
        # Ajustar la escala según el zoom
        radius_units='pixels'  # Usar píxeles en lugar de metros
    )
    
    # Calculate center of the map
    if not df.empty:
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
    else:
        center_lat, center_lon = 32.5333, -117.0167  # Default center (Tijuana)
    
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=11,
        pitch=0
    )
    
    # Create tooltip with postal code information
    tooltip = {
        "html": """
        <div style="padding: 10px; background-color: #2E2E2E; color: white; border-radius: 5px;">
            <b>Business:</b> {name}<br/>
            <b>Activity:</b> {activity}<br/>
            <b>Postal Code:</b> {postal_code}
        </div>
        """,
        "style": {
            "backgroundColor": "#2E2E2E",
            "color": "white",
            "fontFamily": "Arial, sans-serif"
        }
    }
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style='light'  # Estilo de mapa más simple que debería funcionar
    )

# Streamlit UI Configuration
st.set_page_config(
    page_title="BizLens - Business Locator",
    page_icon="📍",
    layout="wide"
)

# Sidebar for search controls
with st.sidebar:
    st.title("🔐 Autenticación")
    
    # Sección de login/registro si no hay token
    if not st.session_state.token:
        auth_tab1, auth_tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
        
        with auth_tab1:
            login_username = st.text_input("Nombre de usuario:", key="login_username")
            if st.button("🎯 Iniciar Sesión", key="login_button", use_container_width=True):
                if login_username:
                    with st.spinner("Iniciando sesión..."):
                        token, user, usage, error = login_user(login_username)
                        if token:
                            st.session_state.token = token
                            st.session_state.user_info = user
                            st.session_state.usage_info = usage
                            st.success(f"✅ ¡Bienvenido, {user['username']}!")
                            st.rerun()
                        else:
                            st.error(f"❌ {error}")
                else:
                    st.warning("⚠️ Por favor ingresa un nombre de usuario")
        
        with auth_tab2:
            reg_username = st.text_input("Nuevo usuario:", key="reg_username")
            if st.button("📝 Registrarse", key="reg_button", use_container_width=True):
                if reg_username:
                    with st.spinner("Registrando usuario..."):
                        token, user, error = register_user(reg_username)
                        if token:
                            st.session_state.token = token
                            st.session_state.user_info = user
                            st.success(f"✅ ¡Usuario {user['username']} registrado!")
                            st.rerun()
                        else:
                            st.error(f"❌ {error}")
                else:
                    st.warning("⚠️ Por favor ingresa un nombre de usuario")
        
        st.markdown("---")
        st.info("ℹ️ Debes iniciar sesión para usar las funciones de búsqueda.")
        
    else:
        # Usuario autenticado - mostrar información
        st.success(f"✅ Conectado como: **{st.session_state.user_info['username']}**")
        
        # Mostrar información de uso
        if st.session_state.usage_info:
            usage = st.session_state.usage_info
        else:
            # Obtener uso actual si no está en session state
            usage = get_usage_info(st.session_state.token)
            if usage:
                st.session_state.usage_info = usage
        
        if usage:
            used = usage.get('today', 0)
            limit = usage.get('limit', 100)
            remaining = usage.get('remaining', 100 - used)
            percentage = (used / limit) * 100
            
            # Barra de progreso
            st.progress(percentage / 100)
            
            # Métricas de uso
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Usados hoy", f"{used}/{limit}")
            with col2:
                st.metric("Disponibles", remaining)
            
            # Advertencia si está cerca del límite
            if used >= 90:
                st.warning(f"⚠️ Te quedan solo {remaining} usos hoy")
            elif used >= 75:
                st.info(f"ℹ️ Has usado {used} de {limit} usos")
        
        # Botón para actualizar uso
        if st.button("🔄 Actualizar uso", use_container_width=True):
            usage = get_usage_info(st.session_state.token)
            if usage:
                st.session_state.usage_info = usage
                st.rerun()
        
        # Botón de cerrar sesión
        if st.button("🚪 Cerrar Sesión", type="secondary", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_info = None
            st.session_state.usage_info = None
            st.session_state.search_params = {}
            st.session_state.current_data = None
            st.success("✅ Sesión cerrada exitosamente")
            st.rerun()
        
        st.markdown("---")
    st.title("🔍 Search Filters")
    
    municipio = st.text_input("Municipality/City:", 
                             help="Enter municipality name (e.g., Tijuana, Ensenada)")
    
    word = st.text_input("Search Keyword (min 4 chars):", 
                        help="Search for business names containing this word")
    
    fecha = st.text_input("Start Date (YYYY/MM/DD):", 
                         help="Optional: Filter businesses registered after this date")
    
    per_page = st.slider("Results per page:", 
                        min_value=10, max_value=100, value=50, step=10)
    
    search_button = st.button("Search Businesses", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### ℹ️ Instructions")
    st.markdown("""
    1. Enter a municipality (e.g., Tijuana)
    2. Enter a search word (min 4 characters)
    3. Optional: Add a date filter
    4. Click 'Search Businesses'
    5. View results on the map and table
    6. Different colors represent different postal codes
    """)
    
    st.markdown("### 📊 API Status")
    # Simple API status check
    try:
        status_response = requests.get("http://127.0.0.1:5000/api", timeout=5)
        if status_response.status_code == 200:
            st.success("✅ Flask API is running")
        else:
            st.error("❌ Flask API not responding properly")
    except:
        st.error("❌ Cannot connect to Flask API")

# Main content area
st.title("📍 BizLens Business Locator - Colored by Postal Code")
st.markdown("---")

# Store search parameters when button is clicked
if search_button:
    if municipio and word and len(word) >= 4:
        st.session_state.search_params = {
            'municipio': municipio,
            'word': word,
            'fecha': fecha if fecha else None,
            'per_page': per_page
        }
        st.session_state.page = 1  # Reset to first page on new search
        st.session_state.current_data = None  # Clear previous data
    elif not municipio or not word:
        st.error("Please enter both municipality and search word.")
    elif len(word) < 4:
        st.error("Search word must be at least 4 characters long.")

# Perform search if we have valid parameters
if st.session_state.search_params:
    params = st.session_state.search_params
    
    # Show current search criteria
    with st.expander("Current Search Criteria", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Municipality", params['municipio'])
        with col2:
            st.metric("Search Word", params['word'])
        with col3:
            st.metric("Date Filter", params['fecha'] or "None")
    
    # Fetch data
    with st.spinner(f"Searching for '{params['word']}' in {params['municipio']}..."):
        data = get_negocio(
            params['municipio'],
            params['word'],
            params['fecha'],
            st.session_state.page
        )
        
        if data and data.get('success'):
            st.session_state.current_data = data
            
            # Display results
            data_info = data['data']
            
            # Results summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Businesses", data_info['total_items'])
            with col2:
                st.metric("Total Pages", data_info['total_pages'])
            with col3:
                st.metric("Current Page", data_info['page'])
            with col4:
                st.metric("Results per Page", data_info['per_page'])
            
            # Extract coordinates and business info
            lat, lon, names, activities, postal_codes, business_df = get_cords(data)
            
            if not business_df.empty:
                # Create map dataframe with colors
                map_df, color_map = create_map_dataframe(lat, lon, names, activities, postal_codes)
                
                # Display color legend
                st.subheader("🎨 Postal Code Color Legend")
                if color_map:
                    # Create a legend with colors
                    unique_codes = sorted(list(set(postal_codes)))
                    cols = st.columns(min(5, len(unique_codes)))
                    
                    for idx, code in enumerate(unique_codes):
                        col_idx = idx % 5
                        with cols[col_idx]:
                            color = color_map[code]
                            # Create a colored box using HTML/CSS
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                                <div style="width: 20px; height: 20px; background-color: rgba({color[0]}, {color[1]}, {color[2]}, {color[3]/255}); 
                                            border-radius: 3px; margin-right: 10px;"></div>
                                <span>CP: {code}</span>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Display map
                st.subheader("📍 Business Locations on Map")
                
                # Option 1: Simple Streamlit map (no colors diferenciados)
                tab1, tab2 = st.tabs(["Simple Map", "Colored Map by Postal Code"])
                
                with tab1:
                    # Simple map without colors
                    simple_map_df = pd.DataFrame({
                        'lat': lat,
                        'lon': lon,
                        'name': names,
                        'activity': activities
                    })
                    if not simple_map_df.empty:
                        st.map(simple_map_df, use_container_width=True)
                    else:
                        st.warning("No valid coordinates found for mapping.")
                
                with tab2:
                    if not map_df.empty:
                        deck = create_pydeck_layer(map_df, color_map)
                        if deck:
                            st.pydeck_chart(deck, use_container_width=True)
                        else:
                            st.error("Could not create the colored map.")
                    else:
                        st.info("Try the Simple Map tab for basic visualization.")
                
                # Display business data table
                st.subheader("📋 Business Details")
                st.dataframe(
                    business_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Business Name": st.column_config.TextColumn(width="large"),
                        "Activity": st.column_config.TextColumn(width="medium"),
                        "Postal Code": st.column_config.TextColumn(width="small"),
                        "Latitude": st.column_config.NumberColumn(format="%.6f"),
                        "Longitude": st.column_config.NumberColumn(format="%.6f"),
                        "Date Registered": st.column_config.DateColumn(format="YYYY/MM/DD")
                    }
                )
                
                # Download button for the data
                csv = business_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"businesses_{params['municipio']}_{params['word']}_page_{st.session_state.page}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Pagination controls
                st.markdown("---")
                st.subheader("📄 Pagination")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    if st.button("⏮️ Previous Page", disabled=not data_info.get('has_prev', False)):
                        if data_info.get('has_prev', False):
                            st.session_state.page -= 1
                            st.rerun()
                
                with col2:
                    st.markdown(f"**Page {data_info['page']} of {data_info['total_pages']}**", 
                               help="Use buttons to navigate between pages")
                
                with col3:
                    if st.button("Next Page ⏭️", disabled=not data_info.get('has_next', False)):
                        if data_info.get('has_next', False):
                            st.session_state.page += 1
                            st.rerun()
                
                # Page jump
                col1, col2 = st.columns([1, 3])
                with col1:
                    new_page = st.number_input("Go to page:", 
                                              min_value=1, 
                                              max_value=data_info['total_pages'], 
                                              value=data_info['page'])
                with col2:
                    if st.button("Jump to Page", use_container_width=True):
                        if new_page != data_info['page']:
                            st.session_state.page = new_page
                            st.rerun()
            
            else:
                st.warning("No businesses with valid location data found.")
        
        elif data and not data.get('success'):
            st.error(f"Search failed: {data.get('message', 'Unknown error')}")
    
    # Clear search button
    if st.button("Clear Search", type="secondary"):
        st.session_state.search_params = {}
        st.session_state.current_data = None
        st.session_state.page = 1
        st.rerun()

else:
    # Welcome/placeholder content
    st.info("👈 Use the sidebar to start searching for businesses.")
    
    # Example searches
    st.markdown("### 💡 Try these example searches:")
    
    examples = [
        {"municipio": "Tijuana", "word": "restaurante"},
        {"municipio": "Ensenada", "word": "hotel"},
        {"municipio": "Mexicali", "word": "tienda"},
    ]
    
    for example in examples:
        if st.button(f"Search: '{example['word']}' in {example['municipio']}", 
                    key=f"example_{example['municipio']}"):
            st.session_state.search_params = {
                'municipio': example['municipio'],
                'word': example['word'],
                'fecha': None,
                'per_page': 50
            }
            st.session_state.page = 1
            st.rerun()

# Footer
st.markdown("---")
st.markdown("### ℹ️ About BizLens")
st.markdown("""
BizLens is a business location visualization tool that helps you find 
and map businesses across municipalities in Baja California.

**New Feature:** Postal Code Color Coding
- Each postal code has a unique color on the map
- Easily identify geographic distribution patterns
- Legend shows color assignments

**Features:**
- Search businesses by name keyword
- Filter by registration date
- Visualize locations on interactive maps with color coding
- View detailed business information including postal codes
- Download results as CSV

**Note:** This is a beta version. Ensure the Flask API server is running on `127.0.0.1:5000`.
""")
