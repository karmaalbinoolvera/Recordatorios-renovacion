import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Gestor Pólizas Inbursa", layout="centered")

# --- 1. CONFIGURACIÓN DE API ---
# Intenta obtener la clave de los secretos de Streamlit, si no, pide input manual (para pruebas locales)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    # Esto es solo por si lo corres en tu compu sin secrets.toml
    api_key = st.sidebar.text_input("Ingresa tu Gemini API Key", type="password")

if not api_key:
    st.error("Por favor configura la API Key en los 'Secrets' de Streamlit o en la barra lateral.")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. FUNCIONES ---

def clean_json_text(text):
    """Limpia la respuesta de la IA por si incluye bloques de código markdown"""
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def extract_data_with_gemini(uploaded_file):
    """Envía el archivo a Gemini y retorna un diccionario JSON"""
    
    # Intentamos usar el modelo Flash, si falla, usamos Pro.
    # El nombre 'gemini-1.5-flash' es el estándar actual.
    model_name = 'gemini-1.5-flash' 
    
    try:
        model = genai.GenerativeModel(model_name)
        
        prompt = """
        Eres un asistente experto en seguros. Extrae la siguiente información de la póliza adjunta.
        Devuelve SOLO un objeto JSON válido. Si un campo no se encuentra, usa null.
        
        Claves del JSON:
        - nombre_asegurado (Texto)
        - fecha_renovacion (Formato YYYY-MM-DD)
        - tipo_poliza (Ej: Automóvil, Vida, GMM)
        - costo_informativo (Texto con moneda)
        - telefono_contacto (Texto)
        - aseguradora (Texto, ej: Inbursa)
        """

        # Preparamos los datos
        bytes_data = uploaded_file.getvalue()
        mime_type = uploaded_file.type

        # Llamada a la API
        response = model.generate_content([
            {'mime_type': mime_type, 'data': bytes_data},
            prompt
        ])

        # Limpiamos y convertimos a JSON
        clean_text = clean_json_text(response.text)
        return json.loads(clean_text)

    except Exception as e:
        st.error(f"Error procesando el documento: {e}")
        return None

# --- 3. INTERFAZ DE USUARIO (FRONTEND) ---

st.title("🛡️ Extractor de Pólizas Inbursa")
st.write("Sube tu PDF para extraer los datos y programar recordatorios.")

# Subida de archivo
uploaded_file = st.file_uploader("Sube la póliza (PDF, JPG, PNG)", type=['pdf', 'jpg', 'png', 'jpeg'])

if uploaded_file:
    # Solo procesamos si no lo hemos hecho ya para este archivo
    if 'datos_extraidos' not in st.session_state or st.session_state.get('file_name') != uploaded_file.name:
        with st.spinner('Leyendo documento con IA...'):
            data = extract_data_with_gemini(uploaded_file)
            if data:
                st.session_state['datos_extraidos'] = data
                st.session_state['file_name'] = uploaded_file.name
            else:
                st.warning("No se pudieron extraer datos. Intenta con otra imagen.")

    # Mostrar formulario si hay datos
    if 'datos_extraidos' in st.session_state:
        data = st.session_state['datos_extraidos']
        
        st.success("✅ Datos extraídos. Verifica antes de guardar.")
        
        with st.form("form_poliza"):
            col1, col2 = st.columns(2)
            
            nombre = col1.text_input("Nombre Asegurado", value=data.get('nombre_asegurado'))
            fecha = col2.text_input("Fecha Renovación (YYYY-MM-DD)", value=data.get('fecha_renovacion'))
            tipo = col1.text_input("Tipo de Póliza", value=data.get('tipo_poliza'))
            costo = col2.text_input("Costo (Informativo)", value=data.get('costo_informativo'))
            tel_cliente = col1.text_input("Teléfono Cliente", value=data.get('telefono_contacto'))
            aseguradora = col2.text_input("Aseguradora", value=data.get('aseguradora'))

            st.divider()
            st.caption("Configuración para el Asesor")
            tel_asesor = st.text_input("WhatsApp del Asesor (para recibir la alerta)", value="521...")
            
            submitted = st.form_submit_button("💾 Guardar y Programar Recordatorio")
            
            if submitted:
                # AQUÍ IRÁ LA CONEXIÓN A GOOGLE SHEETS DESPUÉS
                st.balloons()
                st.info(f"Simulación: Se guardó recordatorio para {nombre} el día {fecha}.")
                st.json({
                    "cliente": nombre,
                    "renovacion": fecha,
                    "notificar_a": tel_asesor,
                    "estado": "Pendiente"
                })
