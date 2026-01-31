import streamlit as st
import google.generativeai as genai

st.title("👨‍⚕️ Diagnóstico de Conexión Gemini")

# 1. Input de API Key directo para probar
api_key = st.text_input("Pega tu API Key nueva aquí:", type="password")

if st.button("Probar Conexión"):
    if not api_key:
        st.error("Pega la llave primero.")
    else:
        genai.configure(api_key=api_key)
        
        st.write("---")
        st.write("1. Intentando listar modelos disponibles...")
        
        try:
            # Intentamos ver qué modelos ve tu llave
            modelos = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    modelos.append(m.name)
            
            if modelos:
                st.success(f"✅ ¡Conexión Exitosa! Tu llave ve estos modelos: {modelos}")
                st.info("Copia uno de esos nombres (ej: 'models/gemini-1.5-flash') para usarlo en tu código final.")
            else:
                st.warning("⚠️ La conexión funcionó, pero no devolvió ningún modelo. Revisa permisos.")
                
        except Exception as e:
            # AQUÍ VEREMOS EL ERROR REAL
            st.error("❌ ERROR CRÍTICO:")
            st.code(str(e))
            st.markdown("""
            **Interpretación del error:**
            * **403 Permission Denied:** No has habilitado la "Generative Language API" en Google Cloud Console.
            * **400 Bad Request:** Tu API Key es inválida o tiene caracteres extraños.
            * **404 Not Found:** La librería está desactualizada (revisa requirements.txt).
            """)
