import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Gestor de Pólizas Inbursa", layout="centered")

# --- CONFIGURACIÓN ---
# En Streamlit Cloud, esto se configura en "Secrets", no en el código directo por seguridad.
# Por ahora, para probar local, puedes poner tu key aquí, pero bórrala antes de subir a GitHub.
api_key = st.secrets["GEMINI_API_KEY"] 
genai.configure(api_key=api_key)

def extract_data_with_gemini(uploaded_file):
    # Usamos Gemini 1.5 Flash por velocidad
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = """
    Actúa como un experto administrativo de seguros. Analiza este documento (PDF/Imagen) y extrae la siguiente información en formato JSON estricto.
    Si un dato no está claro, usa null.
    
    Campos requeridos:
    - nombre_asegurado (String)
    - fecha_renovacion (Formato YYYY-MM-DD)
    - tipo_poliza (Ej: Vida, Autos, Gastos Médicos)
    - costo_informativo (String con moneda, Ej: $5,000 MXN)
    - telefono_contacto (String)
    - aseguradora (String)

    Responde SOLO con el JSON, sin texto adicional ni bloques de código markdown.
    """
    
    # Procesar archivo (Streamlit sube bytes, Gemini necesita el mime_type)
    bytes_data = uploaded_file.getvalue()
    mime_type = uploaded_file.type
    
    try:
        response = model.generate_content([
            {'mime_type': mime_type, 'data': bytes_data},
            prompt
        ])
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Error al leer con IA: {e}")
        return None

# --- INTERFAZ ---
st.title("📂 Carga de Pólizas - MVP")
st.markdown("Sube la póliza (PDF o Imagen) para programar los recordatorios.")

uploaded_file = st.file_uploader("Arrastra la póliza aquí", type=['pdf', 'jpg', 'png'])

if uploaded_file:
    with st.spinner('Analizando documento con IA...'):
        if 'datos_extraidos' not in st.session_state:
            data = extract_data_with_gemini(uploaded_file)
            st.session_state['datos_extraidos'] = data
        
        if st.session_state['datos_extraidos']:
            st.success("¡Datos extraídos!")
            
            # Formulario para verificar/editar lo que la IA encontró
            with st.form("verificacion"):
                col1, col2 = st.columns(2)
                data = st.session_state['datos_extraidos']
                
                nombre = col1.text_input("Asegurado", value=data.get('nombre_asegurado'))
                fecha = col2.text_input("Fecha Renovación (YYYY-MM-DD)", value=data.get('fecha_renovacion'))
                tipo = col1.text_input("Tipo Póliza", value=data.get('tipo_poliza'))
                costo = col2.text_input("Costo (Informativo)", value=data.get('costo_informativo'))
                tel = col1.text_input("Tel. Cliente", value=data.get('telefono_contacto'))
                
                # Configuración de recordatorios
                st.divider()
                st.subheader("Configuración de Alertas")
                advisor_phone = st.text_input("WhatsApp del Asesor (para notificaciones)", value="521...")
                
                submitted = st.form_submit_button("✅ Guardar y Programar Alertas")
                
                if submitted:
                    # AQUÍ CONECTAREMOS CON GOOGLE SHEETS
                    nuevo_registro = {
                        "Nombre": nombre,
                        "Fecha Vencimiento": fecha,
                        "Tipo": tipo,
                        "Costo": costo,
                        "Asesor Phone": advisor_phone,
                        "Status": "Activo",
                        "Creado": datetime.now().strftime("%Y-%m-%d")
                    }
                    st.write("JSON a enviar a Base de Datos:", nuevo_registro)
                    st.toast("Guardado exitosamente (Simulación)")
                    # Limpiar estado para siguiente subida

                    del st.session_state['datos_extraidos']
