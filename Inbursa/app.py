import streamlit as st
import google.generativeai as genai
import json
import time

# Configuración de la página
st.set_page_config(page_title="Gestor Pólizas Inbursa", layout="centered")

# --- 1. CONFIGURACIÓN DE API ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.sidebar.text_input("AIzaSyCEXc9iwb4_R6VXqvDebu93XiIWQLeE2L0", type="password")

if not api_key:
    st.error("⚠️ Falta la API Key. Configúrala en secrets.toml o en la barra lateral.")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. FUNCIONES ---

def clean_json_text(text):
    """Limpia la respuesta para obtener solo el JSON"""
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def extract_data_with_gemini(uploaded_file):
    """
    Intenta extraer datos probando varios modelos automáticamente 
    hasta que uno funcione.
    """
    
    # Lista de modelos a probar en orden de prioridad
    # Si el primero da error 404, el código saltará al siguiente automáticamente.
    modelos_a_probar = [
        'gemini-1.5-flash',       # Opción A: Estándar
        'gemini-1.5-flash-001',   # Opción B: Versión específica (muy estable)
        'gemini-1.5-pro',         # Opción C: Más potente (si Flash falla)
        'gemini-1.5-flash-latest' # Opción D: Última versión
    ]

    prompt = """
    Eres un experto en seguros. Extrae la información de este documento.
    Responde ÚNICAMENTE con un JSON válido.
    
    Claves requeridas (usa null si no encuentras el dato):
    - nombre_asegurado
    - fecha_renovacion (YYYY-MM-DD)
    - tipo_poliza (Ej: Auto, GMM, Vida)
    - costo_informativo
    - telefono_contacto
    - aseguradora
    """

    bytes_data = uploaded_file.getvalue()
    mime_type = uploaded_file.type

    # Bucle de intentos
    for modelo in modelos_a_probar:
        try:
            # Intentamos configurar el modelo actual
            model = genai.GenerativeModel(modelo)
            
            # Intentamos generar el contenido
            response = model.generate_content([
                {'mime_type': mime_type, 'data': bytes_data},
                prompt
            ])
            
            # Si llegamos aquí, funcionó. Procesamos y salimos.
            st.toast(f"✅ Éxito usando el modelo: {modelo}") # Aviso visual de cuál funcionó
            clean_text = clean_json_text(response.text)
            return json.loads(clean_text)

        except Exception as e:
            # Si falla, imprimimos un aviso pequeño y probamos el siguiente
            print(f"Fallo con {modelo}: {e}")
            continue # Pasa al siguiente modelo de la lista
            
    # Si terminamos el bucle y ninguno funcionó:
    st.error("❌ Todos los modelos fallaron. Verifica que tu API Key tenga permisos para 'Generative Language API'.")
    return None

# --- 3. INTERFAZ ---

st.title("🛡️ Extractor de Pólizas Inbursa")
st.info("Sistema MVP - Versión Multi-Modelo")

uploaded_file = st.file_uploader("Sube póliza (PDF/Imagen)", type=['pdf', 'jpg', 'png', 'jpeg'])

if uploaded_file:
    # Lógica para no reprocesar el mismo archivo si ya se extrajo
    if 'datos_extraidos' not in st.session_state or st.session_state.get('file_name') != uploaded_file.name:
        
        with st.spinner('Analizando documento (probando modelos de IA)...'):
            data = extract_data_with_gemini(uploaded_file)
            
            if data:
                st.session_state['datos_extraidos'] = data
                st.session_state['file_name'] = uploaded_file.name
            else:
                st.error("No se pudo leer el documento con ningún modelo.")

    # Mostrar resultados si existen
    if 'datos_extraidos' in st.session_state:
        data = st.session_state['datos_extraidos']
        
        with st.form("revision"):
            st.subheader("Verifica los Datos")
            c1, c2 = st.columns(2)
            
            nombre = c1.text_input("Asegurado", value=data.get('nombre_asegurado'))
            fecha = c2.text_input("Renovación", value=data.get('fecha_renovacion'))
            tipo = c1.text_input("Tipo", value=data.get('tipo_poliza'))
            costo = c2.text_input("Costo", value=data.get('costo_informativo'))
            tel = c1.text_input("Tel. Cliente", value=data.get('telefono_contacto'))
            
            st.divider()
            asesor = st.text_input("WhatsApp Asesor", value="521...")
            
            if st.form_submit_button("💾 Guardar"):
                st.success("Guardado correctamente (Simulación)")
                st.json(data)

