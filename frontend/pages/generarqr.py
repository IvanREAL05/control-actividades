import streamlit as st
from datetime import datetime
import qrcode
from io import BytesIO
import base64
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"

def load_image_base64(image_name):
    try:
        image_path = ASSETS_DIR / image_name
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.warning(f"⚠️ Imagen {image_name} no encontrada")
        return ""

# ---------- CONFIGURACIÓN DE LA PÁGINA ----------
st.set_page_config(
    page_title="Generar QR",
    page_icon="🔑",
    layout="wide",
    initial_sidebar_state="expanded"   # ✅ habilita menú lateral
)
# ---------- OCULTAR MENÚ LATERAL POR DEFECTO ----------
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)
# ---------- CSS PERSONALIZADO ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main {
        padding: 1rem 4rem;
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
        max-width: 100%;
        width: 100%;
    }

    .custom-header {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .header-title {
        font-size: 1.5rem;
        font-weight: 600;
        text-align: center;
        margin: 0;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------- CABECERA ----------
st.markdown("""
<div class="custom-header">
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 1rem;">
        <img src="data:image/jpeg;base64,{}" style="height: 60px; width: auto; object-fit: contain;" alt="Logo BUAP">
        <h1 class="header-title" style="margin: 0; flex: 1; text-align: center;">UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
        <img src="data:image/jpeg;base64,{}" style="height: 60px; width: auto; object-fit: contain;" alt="Logo Institución">
    </div>
</div>
""".format(
    load_image_base64("logo_buap.jpg"),
    load_image_base64("logo1.jpeg")
), unsafe_allow_html=True)

# ---------- BOTÓN DE VOLVER ----------
col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
with col_back2:
    if st.button("🏠 Volver al panel principal", key="main_back"):
        st.switch_page("pages/panel.py")

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- MENÚ LATERAL ----------
st.sidebar.title("Menú")
st.sidebar.page_link("pages/panel.py", label="🏠 Panel Principal")
st.sidebar.page_link("pages/generarqr.py", label="🔑 Generar QR")
st.sidebar.page_link("pages/generarqr_masivo.py", label="📦 QR Masivo")
st.sidebar.page_link("pages/justificantes.py", label="📑 Justificantes")
st.sidebar.page_link("pages/vertodasclases.py", label="📊 Ver todas las clases")
st.sidebar.page_link("pages/cargardatos.py", label="📊 Subir datos")
st.sidebar.page_link("pages/gestionar.py", label="🗂️ Gestionar datos")
st.sidebar.page_link("app.py", label="🚪 Cerrar sesión")

# ---------- CONTENIDO PRINCIPAL ----------
st.markdown("""
<div class='generadorqr-main-content'>
    <div class='section-title'>📷 Generar QR por Matrícula</div>
""", unsafe_allow_html=True)

# ---------- INPUT CONTROLADO ----------
st.text_input("Ingrese matrícula", placeholder="Ej: 12345678", max_chars=15, key="matricula")

# ---------- ESTADOS ----------
if 'loading' not in st.session_state:
    st.session_state.loading = False
if 'qr_image' not in st.session_state:
    st.session_state.qr_image = None
if 'nombre_alumno' not in st.session_state:
    st.session_state.nombre_alumno = None
if 'error' not in st.session_state:
    st.session_state.error = None

# ---------- BOTONES ----------
col_gen, col_clean = st.columns([1, 1])

# Botón Generar QR
with col_gen:
    if st.button("🚀 Generar QR", disabled=st.session_state.loading):
        st.session_state.loading = True
        st.session_state.qr_image = None
        st.session_state.nombre_alumno = None
        st.session_state.error = None

        matricula_clean = st.session_state.matricula.strip()

        if matricula_clean == "":
            st.session_state.error = "⚠️ Por favor, ingrese una matrícula válida."
        else:
            try:
                url = f"https://control-actividades.onrender.com/api/qr/por-matricula/{matricula_clean}"
                response = requests.get(url)

                if response.status_code == 200:
                    data = response.json()
                    qr_base64 = data["data"]["qr"]["imagen"]
                    nombre_alumno = data["data"]["estudiante"]["nombre"]

                    # Limpiar prefijo base64
                    prefix = "data:image/png;base64,"
                    if qr_base64.startswith(prefix):
                        qr_base64 = qr_base64[len(prefix):]

                    st.session_state.qr_image = base64.b64decode(qr_base64)
                    st.session_state.nombre_alumno = nombre_alumno
                    st.session_state.error = None
                else:
                    error_msg = response.json().get("detail", "Error desconocido")
                    st.session_state.error = f"🚫 {error_msg}"
            except Exception as e:
                st.session_state.error = f"🚨 Error al conectar con el servidor: {e}"

        st.session_state.loading = False
        st.rerun()

# Botón Limpiar
with col_clean:
    if st.button("🧹 Limpiar"):
        for key in ["qr_image", "nombre_alumno", "error", "matricula"]:
            st.session_state.pop(key, None)
        st.rerun()

# ---------- RESULTADOS ----------
if st.session_state.get("error"):
    st.markdown(
        f"<p class='generadorqr-error-message'>{st.session_state.error}</p>",
        unsafe_allow_html=True
    )

if st.session_state.get("nombre_alumno") and not st.session_state.get("error"):
    st.markdown(
        f"<p class='generadorqr-nombre-alumno'>Alumno: {st.session_state.nombre_alumno}</p>",
        unsafe_allow_html=True
    )

if st.session_state.get("qr_image"):
    st.image(st.session_state.qr_image, caption="QR generado", width=200)

    b64 = base64.b64encode(st.session_state.qr_image).decode()
    filename = f"qr_{st.session_state.get('matricula', 'qr')}.png"
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}" class="generadorqr-download-link">📥 Descargar QR</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---------- CIERRE DIV PRINCIPAL ----------
st.markdown("</div>", unsafe_allow_html=True)