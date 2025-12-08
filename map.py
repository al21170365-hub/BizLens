import streamlit as st
import pandas as pd
import requests
import pydeck as pdk  # Added for better map visualization

# Initialize session state for page tracking and data caching
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'current_data' not in st.session_state:
    st.session_state.current_data = None
if 'search_params' not in st.session_state:
    st.session_state.search_params = {}

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

def create_map_dataframe(lat, lon, names, activities):
    """Create DataFrame for Streamlit map visualization."""
    if not lat or not lon:
        return pd.DataFrame()
    
    # Create DataFrame for map
    data = {
        'lat': lat,
        'lon': lon,
        'name': names,
        'activity': activities,
        'size': [15] * len(lat)  # Fixed size for all markers
    }
    
    return pd.DataFrame(data)

def create_pydeck_layer(df):
    """Create a PyDeck layer for more advanced visualization."""
    if df.empty:
        return None
    
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=df,
        get_position=['lon', 'lat'],
        get_color='[200, 30, 0, 160]',  # RGBA color
        get_radius=50,
        pickable=True,
        auto_highlight=True
    )
    
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(),
        longitude=df['lon'].mean(),
        zoom=11,
        pitch=0
    )
    
    tooltip = {
        "html": "<b>Business:</b> {name}<br/><b>Activity:</b> {activity}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip
    )

# Streamlit UI Configuration
st.set_page_config(
    page_title="BizLens - Business Locator",
    page_icon="📍",
    layout="wide"
)

# Sidebar for search controls
with st.sidebar:
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
st.title("📍 BizLens Business Locator (Beta)")
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
                # Display map
                st.subheader("📍 Business Locations on Map")
                
                # Option 1: Simple Streamlit map
                tab1, tab2 = st.tabs(["Simple Map", "Advanced Map"])
                
                with tab1:
                    map_df = create_map_dataframe(lat, lon, names, activities)
                    if not map_df.empty:
                        st.map(map_df, use_container_width=True)
                    else:
                        st.warning("No valid coordinates found for mapping.")
                
                with tab2:
                    if not map_df.empty:
                        deck = create_pydeck_layer(map_df)
                        if deck:
                            st.pydeck_chart(deck, use_container_width=True)
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

**Features:**
- Search businesses by name keyword
- Filter by registration date
- Visualize locations on interactive maps
- View detailed business information including postal codes
- Download results as CSV

**Note:** This is a beta version. Ensure the Flask API server is running on `127.0.0.1:5000`.
""")
