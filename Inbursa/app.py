import streamlit as st
from google import genai
import os
import json
import requests
from datetime import datetime
import uuid
from cryptography.fernet import Fernet

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Panel IA - Pólizas", layout="wide", initial_sidebar_state="expanded")

# Recuperar claves desde los Secrets de Streamlit Cloud
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    enc_key = st.secrets["ENCRYPTION_KEY"]
    # Es mejor poner tu Webhook URL en los secrets también
    url_webhook = st.secrets.get("WEBHOOK_URL", "AQUI_TU_URL_DE_PRUEBA_O_PRODUCCION") 
except Exception as e:
    st.error("⚠️ Faltan claves en Secrets (GEMINI_API_KEY o ENCRYPTION_KEY).")
    st.stop()

cipher_suite = Fernet(enc_key)

# --- FUNCIONES DE SEGURIDAD ---
def encrypt_data(text):
    if not text: return None
    return cipher_suite.encrypt(text.encode()).decode()

# --- GESTIÓN DE SESIÓN (LOGIN) ---
if 'usuario_validado' not in st.session_state:
    st.session_state['usuario_validado'] = False
if 'polizas_procesadas' not in st.session_state:
    st.session_state.polizas_procesadas = []

# --- INTERFAZ: LOGIN ---
if not st.session_state['usuario_validado']:
    st.title("🔐 Acceso Asesores - Inbursa & Multimarca")
    
    with st.form("login_form"):
        email = st.text_input("Correo Institucional")
        telefono = st.text_input("Teléfono Celular")
        submitted = st.form_submit_button("Enviar Código de Verificación")
        
        if submitted and email and telefono:
            st.session_state['temp_email'] = email
            st.session_state['temp_tel'] = telefono
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
    
    st.stop() 

# --- INTERFAZ: APP PRINCIPAL ---
with st.sidebar:
    st.success(f"👤 Asesor conectado:\n{st.session_state['asesor_email']}")
    if st.button("Cerrar Sesión"):
        st.session_state['usuario_validado'] = False
        st.session_state.polizas_procesadas = []
        st.rerun()

st.title("🛡️ Panel Inteligente de Extracción de Pólizas")
st.markdown("---")

st.subheader("📁 Carga de Documentos")
uploaded_files = st.file_uploader("Arrastra una o varias pólizas en PDF", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("Procesar Documentos", type="primary"):
        client = genai.Client(api_key=api_key)
        st.session_state.polizas_procesadas = [] 
        
        st.markdown("### 📊 Resultados de Extracción")
        
        for file in uploaded_files:
            col_info, col_json = st.columns([1, 1])
            with col_info:
                st.write(f"**Documento:** `{file.name}`")
                with st.spinner("Analizando con Gemini 2.5 Flash..."):
                    try:
                        temp_pdf_path = f"temp_{file.name}"
                        with open(temp_pdf_path, "wb") as f:
                            f.write(file.getbuffer())
                        
                        archivo_gemini = client.files.upload(file=temp_pdf_path)
                        
                        prompt_extraccion = """
                        Eres un analista de datos experto en pólizas de seguros en México. Extrae la información del PDF adjunto y devuélvela ESTRICTAMENTE en JSON válido.
                        {
                          "institucion_emisora": "Nombre de la aseguradora",
                          "nombre_cliente": "Nombre completo del titular",
                          "tipo_poliza": "Clasifícalo estrictamente en: Auto, Moto, Vida, GMM, Accidentes Personales, o Tarjeta/Cuenta",
                          "numero_poliza": "El identificador alfanumérico principal. REGLA ESTRICTA: Elimina cualquier símbolo especial (como %, #, -, o espacios). Debe ser puramente alfanumérico. Si hay un número corto y uno largo, extrae la cadena alfanumérica más larga.",
                          "fecha_inicio_vigencia": "Formato YYYY-MM-DD",
                          "fecha_fin_vigencia": "Formato YYYY-MM-DD",
                          "hora_fin_vigencia": "Hora exacta en que termina la vigencia en formato de 24 horas (ej. 12:00). Si no especifica, devuelve '12:00'.",
                          "precio_total": "El costo final a pagar. Devuelve ESTRICTAMENTE solo el valor numérico con decimales, sin comas y sin el signo de pesos (ej. 11144.26).",
                          "moneda": "Devuelve estrictamente 'MXN' o 'USD'."
                        }
                        Ignora fechas de emisión o expedición. Solo fechas reales de vigencia.
                        """
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', 
                            contents=[archivo_gemini, prompt_extraccion]
                        )
                        
                        texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
                        datos_json = json.loads(texto_limpio)
                        
                        # --- INYECCIÓN DE DATOS DE SISTEMA Y ENCRIPTACIÓN ---
                        datos_json["ID_Registro"] = str(uuid.uuid4())[:8].upper() 
                        datos_json["Email_Asesor"] = st.session_state['asesor_email']
                        datos_json["Tel_Asesor"] = st.session_state['asesor_tel']
                        datos_json["Numero_Cliente_CIS"] = "" 
                        # Encriptamos el nombre para guardarlo seguro en la base de datos
                        datos_json["Cliente_Encriptado"] = encrypt_data(datos_json["nombre_cliente"])
                        # ----------------------------------------------------
                        
                        st.session_state.polizas_procesadas.append(datos_json)
                        
                        # Lógica visual de vigencia
                        try:
                            fecha_fin = datetime.strptime(datos_json["fecha_fin_vigencia"], "%Y-%m-%d").date()
                            hoy = datetime.now().date()
                            dias_restantes = (fecha_fin - hoy).days
                            
                            if dias_restantes < 0:
                                st.error(f"🔴 VENCIDA (Hace {abs(dias_restantes)} días)")
                            elif dias_restantes <= 30:
                                st.warning(f"🟡 PRÓXIMA A VENCER (En {dias_restantes} días)")
                            else:
                                st.success(f"🟢 VIGENTE (Vence en {dias_restantes} días)")
                        except:
                            pass

                        os.remove(temp_pdf_path)
                        client.files.delete(name=archivo_gemini.name)
                        
                    except Exception as e:
                        st.error(f"Error procesando {file.name}: {e}")
            
            with col_json:
                st.json(datos_json)
            st.markdown("---")

if len(st.session_state.polizas_procesadas) > 0:
    st.info(f"✅ Tienes {len(st.session_state.polizas_procesadas)} póliza(s) lista(s) en memoria para exportar.")
    
    if st.button("🚀 Enviar TODAS a Base de Datos y Sheets", type="primary", use_container_width=True):
        if url_webhook != "AQUI_TU_URL_DE_PRUEBA_O_PRODUCCION":
            try:
                paquete_masivo = {"polizas": st.session_state.polizas_procesadas}
                respuesta_n8n = requests.post(url_webhook, json=paquete_masivo)
                
                if respuesta_n8n.status_code == 200:
                    st.balloons()
                    st.success("¡Envío masivo exitoso! Los datos ya están en la base de datos.")
                    st.session_state.polizas_procesadas = [] 
                else:
                    st.error(f"El servidor de n8n rechazó la conexión. Código: {respuesta_n8n.status_code}")
            except Exception as e:
                st.error(f"No hay conexión a internet o la URL es inválida: {e}")
        else:
            st.error("⚠️ Falta configurar la URL del Webhook en los secrets de Streamlit.")
