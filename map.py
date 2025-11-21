import streamlit as st
import pandas as pd
import requests

# Initialize session state for page tracking
if 'page' not in st.session_state:
    st.session_state.page = 1

def get_negocio(municipio, word, fecha, page):
    try:
        response = requests.get(f"http://127.0.0.1:5000/api/exel/negocio?municipio={municipio}&word={word}&date={fecha}&page={page}")
        if response.status_code == 400:
            error_data = response.json()
            st.info(f"{error_data.get('message', 'Invalid date format')}")
            return None
        
        if response.status_code == 404:
            error_data = response.json()
            st.info(f"{error_data.get('message', 'Data not found')}")
            return None

        if response.status_code == 500:
            error_data = response.json()
            st.info(f"{error_data.get('message', 'Data not found')}")
            return None

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

def get_cords(data):
    lat = []
    lon = []
    size = []
    color = []
    if data and 'data' in data and 'results' in data['data']:
        for cords in data['data']['results']:
            lati = cords.get('latitud')
            long = cords.get('longitud')
            
            # Only add if coordinates are valid
            if lati is not None and long is not None:
                lat.append(lati)
                lon.append(long)
                size.append(1)
                color.append('#FF0000')
    return lat, lon, size, color

# Streamlit UI
st.title("BizLens")

# Use Streamlit input widgets instead of input()
municipio = st.text_input("Input city:", value="")
word = st.text_input("Input word(minimum: 4 letters):", value="")
fecha = st.text_input("Input date YYYY/MM/DD (OPTIONAL):", value="")

if municipio and word:
    data = get_negocio(municipio, word, fecha,  st.session_state.page)
    
    if data and 'data' in data:
        st.write(f"Total items: {data['data'].get('total_items', 0)}")
        st.write(f"Total pages: {data['data'].get('total_pages', 0)}")
        st.write(f"Page: {data['data'].get('page', 0)}")
        
        lat, lon, size, color = get_cords(data)
        
        if lat and lon:  # Only show map if we have coordinates
            data_df = {
                'lat': lat,
                'lon': lon,
                'size': size,
                'color': color
            }
            df = pd.DataFrame(data_df)
            st.map(df, size='size', color='color')
        else:
            st.warning("No location data found for the given criteria.")
        
        # Pagination controls
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Previous", use_container_width=True):
                if data['data'].get('has_prev', False):
                    st.session_state.page -= 1
                    st.rerun()
                else:
                    st.warning("There is no previous page")
        
        with col2:
            if st.button("Next", use_container_width=True):
                if data['data'].get('has_next', False):
                    st.session_state.page += 1
                    st.rerun()
                else:
                    st.warning("There is no next page")
    #else:
    #    st.error("No data received from the API")
else:
    st.info("Please enter both city and word to search for businesses.")
