import streamlit as st
import requests
import folium
import os
from dotenv import load_dotenv
from streamlit_folium import folium_static
from urllib.parse import quote
import re
from bs4 import BeautifulSoup

# st.write(st.get_option("theme.primaryColor"))
# st.write(st.get_option("theme.backgroundColor"))
# Intenta cargar las variables del archivo .env (desarrollo local)
load_dotenv()

# Configuración de la página
st.set_page_config(page_title="Extractor de Información de Negocios", layout="wide")

# Título de la aplicación
st.title("Extractor de Información de Negocios")

# Función para obtener la clave de API
def get_api_key():
    try:
    # Primero, intenta obtener la clave de Streamlit Secrets
        api_key = st.secrets.get("GOOGLE_API_KEY")    
        return api_key
    
    except (KeyError, FileNotFoundError):
    # Si no está en Streamlit Secrets, intenta obtenerla de las variables de entorno
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key is not None:
            return api_key
    
    # Si no se encuentra la clave, lanza un error
        raise ValueError("No se encontró la clave de API de Google. Por favor, configura la variable de entorno GOOGLE_API_KEY.")

# Función para crear el mapa
def create_map(lat, lon, zoom=12):
    m = folium.Map(location=[lat, lon], zoom_start=zoom)
    return m

# Función para buscar correos electrónicos en una página web
def find_emails(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_regex, soup.get_text())
            return list(set(emails))  # Eliminar duplicados
    except:
        pass
    return []

# Controles de entrada
col1, col2, col3 = st.columns(3)
with col1:
    city = st.text_input("Ciudad:", "Barcelona")
with col2:
    type_of_business = st.text_input("Tipo de Negocio:", "Restaurante")
with col3:
    radius = st.number_input("Radio (metros):", value=500, min_value=100, max_value=5000)

# Obtener la API Key
try:
    api_key = get_api_key()
except ValueError as e:
    st.error(str(e))
    st.stop()

# Botones
if st.button("Buscar"):
    if not type_of_business:
        st.warning("Por favor, ingrese un tipo de negocio.")
    else:
        # Codificar la ciudad para la URL
        encoded_city = quote(city)
        
        # Lógica para buscar lugares
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_city}&key={api_key}"
        geocode_response = requests.get(geocode_url).json()
        
        if geocode_response['status'] == 'OK':
            location = geocode_response['results'][0]['geometry']['location']
            lat, lng = location['lat'], location['lng']
            
            # Crear y mostrar el mapa
            m = create_map(lat, lng)
            folium_static(m)
            
            places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius={radius}&keyword={quote(type_of_business)}&key={api_key}"
            places_response = requests.get(places_url).json()
            
            if places_response['status'] == 'OK':
                for place in places_response['results']:
                    place_id = place['place_id']
                    details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key={api_key}"
                    details_response = requests.get(details_url).json()
                    
                    if details_response['status'] == 'OK':
                        place_details = details_response['result']
                        with st.expander(f"{place_details.get('name', 'Negocio sin nombre')}"):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**Dirección:** {place_details.get('vicinity', 'N/A')}")
                                st.write(f"**Valoración:** {place_details.get('rating', 'N/A')}")
                                website = place_details.get('website', 'N/A')
                                st.write(f"**Sitio Web:** {website}")
                                
                                # Buscar correos electrónicos si hay un sitio web disponible
                                if website != 'N/A':
                                    emails = find_emails(website)
                                    if emails:
                                        st.write(f"**Correos encontrados:** {', '.join(emails)}")
                                    else:
                                        st.write("**Correos encontrados:** Ninguno")
                                else:
                                    st.write("**Correos encontrados:** No se pudo buscar (sitio web no disponible)")
                            
                            with col2:
                                if place_details.get('photos'):
                                    photo_reference = place_details['photos'][0]['photo_reference']
                                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={api_key}"
                                    st.image(photo_url, width=150)
                        
                        # Añadir marcador al mapa
                        folium.Marker(
                            [place_details['geometry']['location']['lat'], place_details['geometry']['location']['lng']],
                            popup=place_details.get('name', 'Negocio sin nombre')
                        ).add_to(m)
                
                # Actualizar el mapa con los marcadores
                folium_static(m)
            else:
                st.error("No se encontraron resultados,.")
        else:
            st.error(f"Ciudad no encontrada. Status: {geocode_response['status']}")

if st.button("Limpiar Resultados"):
    st.experimental_rerun()