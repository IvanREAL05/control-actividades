import streamlit as st
import requests

# URL de tu API FastAPI
API_URL = "http://127.0.0.1:8000/api/login/"

st.set_page_config(page_title="Control de Actividades - Login", page_icon="🔐", layout="centered")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #1f2937, #3b82f6);
        color: white;
    }
    .stTextInput>div>div>input {
        background-color: #f9fafb;
        border-radius: 10px;
    }
    .stButton>button {
        width: 100%;
        background-color: #3b82f6;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 10px;
    }
    .stButton>button:hover {
        background-color: #2563eb;
        transform: scale(1.02);
    }
    .login-box {
        background-color: transparent;
        box-shadow: none;
    }
    </style>
""", unsafe_allow_html=True)

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
                    st.success(f"✅ Bienvenido {data['data']['usuario']['nombre_completo']}")
                    st.session_state["usuario"] = data["data"]["usuario"]
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

# --- Si ya hay sesión ---
if "usuario" in st.session_state:
    st.write("### Panel de Control")
    st.json(st.session_state["usuario"])