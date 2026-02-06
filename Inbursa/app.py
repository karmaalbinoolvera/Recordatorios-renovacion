import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from cryptography.fernet import Fernet

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestor Inbursa Seguro", layout="centered")

# Recuperar claves
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    enc_key = st.secrets["ENCRYPTION_KEY"]
except:
    st.error("⚠️ Faltan claves en Secrets (GEMINI_API_KEY o ENCRYPTION_KEY).")
    st.stop()

genai.configure(api_key=api_key)
cipher_suite = Fernet(enc_key)

# --- FUNCIONES DE SEGURIDAD ---

def encrypt_data(text):
    """Encripta un texto (ej: Nombre Cliente)"""
    if not text: return None
    return cipher_suite.encrypt(text.encode()).decode()

def decrypt_data(text_encrypted):
    """(Opcional) Para que el asesor pueda ver el dato desencriptado si lo necesita"""
    try:
        return cipher_suite.decrypt(text_encrypted.encode()).decode()
    except:
        return "Error desencriptando"

# --- FUNCIONES DE IA ---

def clean_json_text(text):
    return text.replace("```json", "").replace("```", "").strip()

def extract_data_with_gemini(uploaded_file):
    model_name = 'models/gemini-2.5-flash'
    
    prompt = """
    Actúa como experto en seguros Inbursa. Extrae datos de la póliza.
    Devuelve un JSON estricto. Si no encuentras un dato, usa null.
    
    REGLAS DE FECHAS:
    - Busca fecha y HORA. Formato: 'YYYY-MM-DD HH:MM'.
    - Si la póliza dice solo fecha sin hora, asume '00:00'.
    - Ejemplo: "2025-05-20 12:00"
    
    CAMPOS A EXTRAER:
    - CLIENTE (Nombre del asegurado)
    - POLIZA (Número de póliza)
    - CIS (Código de Identificación, suele estar cerca de la póliza)
    - VIGENCIA_FIN (Fecha y hora exacta de vencimiento)
    - FECHA_CONTRATACION (Fecha y hora de inicio/emisión)
    """

    try:
        model = genai.GenerativeModel(model_name)
        bytes_data = uploaded_file.getvalue()
        response = model.generate_content([{'mime_type': uploaded_file.type, 'data': bytes_data}, prompt])
        return json.loads(clean_json_text(response.text))
    except Exception as e:
        st.error(f"Error IA: {e}")
        return None

# --- GESTIÓN DE SESIÓN (LOGIN) ---
if 'usuario_validado' not in st.session_state:
    st.session_state['usuario_validado'] = False

# --- INTERFAZ: LOGIN / REGISTRO ---
if not st.session_state['usuario_validado']:
    st.title("🔐 Acceso Asesores")
    
    with st.form("login_form"):
        email = st.text_input("Correo Institucional")
        telefono = st.text_input("Teléfono Celular")
        submitted = st.form_submit_button("Enviar Código de Verificación")
        
        if submitted and email and telefono:
            st.session_state['temp_email'] = email
            st.session_state['temp_tel'] = telefono
            # AQUÍ IRÍA EL ENVÍO REAL DE SMS/EMAIL (Twilio/Sendgrid)
            # Para el MVP, mostramos el código en pantalla:
            st.session_state['codigo_real'] = "123456" 
            st.success(f"SIMULACIÓN: Tu código de verificación es {st.session_state['codigo_real']}")
            st.session_state['esperando_codigo'] = True

    if st.session_state.get('esperando_codigo'):
        codigo_ingresado = st.text_input("Ingresa el código de 6 dígitos")
        if st.button("Verificar"):
            if codigo_ingresado == st.session_state['codigo_real']:
                st.session_state['usuario_validado'] = True
                st.session_state['asesor_email'] = st.session_state['temp_email']
                st.session_state['asesor_tel'] = st.session_state['temp_tel']
                st.rerun()
            else:
                st.error("Código incorrecto.")
    
    st.stop() # Detiene la app aquí si no está logueado

# --- INTERFAZ: APP PRINCIPAL ---

st.sidebar.success(f"Asesor: {st.session_state['asesor_email']}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['usuario_validado'] = False
    st.rerun()

st.title("📄 Procesador de Pólizas (Seguro)")

uploaded_file = st.file_uploader("Sube póliza (PDF)", type=['pdf', 'png', 'jpg'])

if 'datos_temp' not in st.session_state:
    st.session_state['datos_temp'] = {}

if uploaded_file:
    if st.button("🔍 Extraer Datos"):
        with st.spinner('Analizando...'):
            data = extract_data_with_gemini(uploaded_file)
            if data:
                st.session_state['datos_temp'] = data
            else:
                st.error("No se pudo leer.")

    if st.session_state['datos_temp']:
        d = st.session_state['datos_temp']
        
        with st.form("final_review"):
            st.subheader("Datos Detectados")
            c1, c2 = st.columns(2)
            
            # Campos editables
            # El cliente se muestra legible aquí, pero se encriptará al guardar
            cliente = c1.text_input("CLIENTE (Se encriptará)", value=d.get('CLIENTE'))
            poliza = c2.text_input("PÓLIZA", value=d.get('POLIZA'))
            cis = c1.text_input("CIS", value=d.get('CIS'))
            
            vigencia = c2.text_input("VIGENCIA FIN (YYYY-MM-DD HH:MM)", value=d.get('VIGENCIA_FIN'))
            contratacion = c1.text_input("CONTRATACIÓN (YYYY-MM-DD HH:MM)", value=d.get('FECHA_CONTRATACION'))
            
            if st.form_submit_button("🔒 Encriptar y Guardar"):
                # Encriptación
                cliente_enc = encrypt_data(cliente)
                
                # Preparar registro
                registro = pd.DataFrame([{
                    "ID_Registro": str(datetime.now().timestamp()), # ID único simple
                    "Cliente_Encriptado": cliente_enc,
                    "Poliza": poliza,
                    "CIS": cis,
                    "Vigencia_Fin": vigencia,
                    "Fecha_Contratacion": contratacion,
                    "Email_Asesor": st.session_state['asesor_email'],
                    "Tel_Asesor": st.session_state['asesor_tel'],
                    "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    existente = conn.read(ttl=0)
                    nuevo = pd.concat([existente, registro], ignore_index=True).dropna(how="all")
                    conn.update(data=nuevo)
                    
                    st.success("✅ Guardado seguro.")
                    st.info(f"Dato guardado en nube: {cliente_enc[:10]}...") # Muestra un pedacito encriptado
                    st.session_state['datos_temp'] = {}
                except Exception as e:
                    st.error(f"Error Sheets: {e}")
