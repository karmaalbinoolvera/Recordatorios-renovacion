import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime
# ### NUEVO: Importamos la librería de conexión a Sheets ###
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestor Pólizas Inbursa", layout="centered")

# --- 1. GESTIÓN DE API KEY (IA) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.sidebar.text_input("Tu API Key", type="password")

if not api_key:
    st.warning("⚠️ Ingresa tu API Key para comenzar.")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. FUNCIONES ---

def clean_json_text(text):
    """Limpia la respuesta de la IA"""
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def extract_data_with_gemini(uploaded_file):
    """Extrae datos usando Gemini 2.5 Flash"""
    model_name = 'models/gemini-2.5-flash'
    
    prompt = """
    Actúa como experto en seguros. Analiza este documento.
    Extrae la siguiente información en formato JSON estricto.
    Si no encuentras un dato, usa null.
    
    Claves del JSON:
    - nombre_asegurado (String)
    - fecha_renovacion (Formato YYYY-MM-DD)
    - tipo_poliza (Ej: Autos, Vida, GMM)
    - costo_informativo (String con moneda)
    - telefono_contacto (String)
    - aseguradora (String, por defecto Inbursa)
    """

    try:
        model = genai.GenerativeModel(model_name)
        bytes_data = uploaded_file.getvalue()
        mime_type = uploaded_file.type

        response = model.generate_content([
            {'mime_type': mime_type, 'data': bytes_data},
            prompt
        ])
        
        text_clean = clean_json_text(response.text)
        return json.loads(text_clean)

    except Exception as e:
        st.error(f"Error en lectura IA: {e}")
        return None

# --- 3. INTERFAZ ---

st.title("🛡️ Extractor Inbursa + Nube")
st.markdown("Sube una póliza. Al guardar, se enviará a la **Base de Datos en Google Sheets**.")

if 'datos_actuales' not in st.session_state:
    st.session_state['datos_actuales'] = {}

uploaded_file = st.file_uploader("Arrastra tu PDF aquí", type=['pdf', 'jpg', 'png'])

if uploaded_file:
    if st.button("🔍 Analizar Documento con IA"):
        with st.spinner('Leyendo...'):
            data = extract_data_with_gemini(uploaded_file)
            if data:
                st.session_state['datos_actuales'] = data
                st.toast("Datos leídos")
            else:
                st.error("No se pudo leer.")

    # Formulario de revisión
    if st.session_state['datos_actuales']:
        data = st.session_state['datos_actuales']
        
        st.divider()
        st.subheader("📝 Verifica antes de Guardar")
        
        with st.form("form_final"):
            c1, c2 = st.columns(2)
            
            # Inputs editables
            nombre = c1.text_input("Asegurado", value=data.get('nombre_asegurado'))
            fecha = c2.text_input("Renovación (YYYY-MM-DD)", value=data.get('fecha_renovacion'))
            tipo = c1.text_input("Tipo Póliza", value=data.get('tipo_poliza'))
            costo = c2.text_input("Costo", value=data.get('costo_informativo'))
            tel_cliente = c1.text_input("Tel. Cliente", value=data.get('telefono_contacto'))
            aseguradora = c2.text_input("Aseguradora", value=data.get('aseguradora'))
            
            cel_asesor = st.text_input("WhatsApp Asesor (Recordatorio)", value="521...")
            
            # Botón de envío
            submitted = st.form_submit_button("💾 Guardar en Base de Datos")
            
            if submitted:
                # 1. Empaquetamos los datos en un formato que entiende Pandas (DataFrame)
                nuevo_registro = pd.DataFrame([{
                    "Nombre": nombre,
                    "Renovacion": fecha,
                    "Tipo": tipo,
                    "Costo": costo,
                    "Tel Cliente": tel_cliente,
                    "Aseguradora": aseguradora,
                    "Cel Asesor": cel_asesor,
                    "Fecha Registro": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                
                # ### NUEVO: Lógica de conexión a Google Sheets ###
                try:
                    # a) Establecemos conexión usando los secretos
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    
                    # b) Leemos lo que ya existe en la hoja (para no borrarlo)
                    # ttl=0 significa "no uses memoria caché, lee los datos frescos ahora mismo"
                    datos_existentes = conn.read(ttl=0)
                    
                    # c) Pegamos el dato nuevo al final de los existentes
                    # dropna evita filas vacías fantasma
                    datos_actualizados = pd.concat([datos_existentes, nuevo_registro], ignore_index=True).dropna(how="all")
                    
                    # d) Escribimos todo de vuelta a la hoja
                    conn.update(data=datos_actualizados)
                    
                    st.success(f"✅ ¡Guardado Exitoso! {nombre} ya está en la nube.")
                    st.balloons()
                    
                    # Limpiamos para el siguiente
                    st.session_state['datos_actuales'] = {}
                    
                except Exception as e:
                    st.error("❌ Error conectando a Google Sheets:")
                    st.write(e)
                    st.info("Revisa que hayas compartido la hoja con el email del robot (client_email) en tu JSON.")
