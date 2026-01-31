import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestor Pólizas Inbursa", layout="centered")

# --- 1. GESTIÓN DE API KEY ---
# Busca la clave en secrets o pídela manual
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    # Si no estás en local, pon tu clave aquí entre comillas para probar rápido:
    # api_key = "TU_CLAVE_AIzaSyD..." 
    api_key = st.sidebar.text_input("Tu API Key", type="password")

if not api_key:
    st.warning("⚠️ Ingresa tu API Key en la barra lateral para comenzar.")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. FUNCIONES ---

def clean_json_text(text):
    """Limpia bloques de código markdown si la IA los incluye"""
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def extract_data_with_gemini(uploaded_file):
    """Extrae datos usando el modelo confirmado gemini-2.5-flash"""
    
    # NOMBRE DEL MODELO QUE YA CONFIRMAMOS QUE FUNCIONA:
    model_name = 'models/gemini-2.5-flash'
    
    prompt = """
    Actúa como experto en seguros. Analiza este documento.
    Extrae la siguiente información en formato JSON estricto.
    
    Si no encuentras un dato, usa null. NO inventes información.
    
    Claves del JSON:
    - nombre_asegurado (String)
    - fecha_renovacion (Formato YYYY-MM-DD)
    - tipo_poliza (Ej: Autos, Vida, GMM)
    - costo_informativo (String con moneda)
    - telefono_contacto (String)
    - aseguradora (String, por defecto Inbursa si no se especifica)
    """

    try:
        model = genai.GenerativeModel(model_name)
        
        # Procesar archivo
        bytes_data = uploaded_file.getvalue()
        mime_type = uploaded_file.type

        response = model.generate_content([
            {'mime_type': mime_type, 'data': bytes_data},
            prompt
        ])
        
        text_clean = clean_json_text(response.text)
        return json.loads(text_clean)

    except Exception as e:
        st.error(f"Error detallado: {e}")
        return None

# --- 3. INTERFAZ ---

st.title("🛡️ Extractor Inbursa (MVP)")
st.markdown("Sube una póliza para extraer datos y generar el registro.")

if 'datos_actuales' not in st.session_state:
    st.session_state['datos_actuales'] = {}

uploaded_file = st.file_uploader("Arrastra tu PDF o Imagen aquí", type=['pdf', 'jpg', 'png', 'jpeg'])

if uploaded_file:
    # Botón para procesar (así no gasta saldo cada vez que se recarga la página)
    if st.button("🔍 Analizar Documento con IA"):
        with st.spinner('Procesando con Gemini 2.5 Flash...'):
            data = extract_data_with_gemini(uploaded_file)
            if data:
                st.session_state['datos_actuales'] = data
                st.toast("¡Datos extraídos con éxito!")
            else:
                st.error("No se pudo extraer información.")

    # Si hay datos extraídos, mostramos el formulario
    if st.session_state['datos_actuales']:
        data = st.session_state['datos_actuales']
        
        st.divider()
        st.subheader("📝 Verifica y Edita")
        
        with st.form("form_final"):
            c1, c2 = st.columns(2)
            
            # Campos editables
            nombre = c1.text_input("Asegurado", value=data.get('nombre_asegurado'))
            fecha = c2.text_input("Renovación (YYYY-MM-DD)", value=data.get('fecha_renovacion'))
            tipo = c1.text_input("Tipo Póliza", value=data.get('tipo_poliza'))
            costo = c2.text_input("Costo Informativo", value=data.get('costo_informativo'))
            tel_cliente = c1.text_input("Tel. Cliente", value=data.get('telefono_contacto'))
            aseguradora = c2.text_input("Aseguradora", value=data.get('aseguradora'))
            
            # Datos del asesor (puedes dejarlos fijos o configurables)
