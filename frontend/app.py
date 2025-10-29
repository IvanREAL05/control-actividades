import streamlit as st
import requests

API_URL = "https://control-actividades.onrender.com/api/login"

st.set_page_config(page_title="Login", page_icon="🔐", initial_sidebar_state="collapsed")

# --- Ocultar menú, footer y sidebar ---
hide_menu = """
<style>
    [data-testid="stSidebar"] {display: none;}   /* 🔒 oculta sidebar */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

# --- Si ya hay sesión, mandar directo al panel ---
if "usuario" in st.session_state:
    st.switch_page("pages/panel.py")

# --- LOGIN UI ---
st.markdown("<h2 style='text-align:center'>🔐 Iniciar Sesión</h2>", unsafe_allow_html=True)
st.markdown("<div class='login-box'>", unsafe_allow_html=True)

usuario = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
password = st.text_input("🔑 Contraseña", type="password", placeholder="Ingresa tu contraseña")

if st.button("Ingresar"):
    if usuario and password:
        try:
            response = requests.post(API_URL, json={
                "usuario_login": usuario,
                "contrasena": password
            })
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    st.session_state["usuario"] = data["data"]["usuario"]
                    st.success(f"✅ Bienvenido {data['data']['usuario']['nombre_completo']}")
                    st.switch_page("pages/panel.py")
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            elif response.status_code == 401:
                st.error("❌ Credenciales inválidas")
            else:
                st.error(f"⚠️ Error en el servidor: {response.status_code}")
        except Exception as e:
            st.error(f"🚨 No se pudo conectar con el servidor: {e}")
    else:
        st.warning("⚠️ Ingresa tu usuario y contraseña")

st.markdown("</div>", unsafe_allow_html=True)
