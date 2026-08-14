import streamlit as st
import requests
import base64
import re
import zipfile
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"
BACKEND_URL = "https://control-actividades.onrender.com"

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
    page_title="Generar QR Masivo",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
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

    .stButton > button, .stDownloadButton > button {
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

    .stButton > button:hover, .stDownloadButton > button:hover {
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
    <div class='section-title'>📦 Generar QR de todo un grupo</div>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def obtener_grupos():
    resp = requests.get(f"{BACKEND_URL}/api/grupos/lista", timeout=10)
    resp.raise_for_status()
    return resp.json()


def sanitizar_nombre_archivo(texto: str) -> str:
    texto = texto.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9_\-]", "", texto)


def generar_qr_estudiante(matricula: str):
    """Pide al backend el QR ya cifrado con la FERNET_KEY correcta."""
    url = f"{BACKEND_URL}/api/qr/por-matricula/{matricula}"
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        detalle = resp.json().get("detail", "Error desconocido") if resp.content else resp.status_code
        raise RuntimeError(detalle)

    data = resp.json()["data"]
    qr_base64 = data["qr"]["imagen"]
    prefix = "data:image/png;base64,"
    if qr_base64.startswith(prefix):
        qr_base64 = qr_base64[len(prefix):]

    return {
        "matricula": matricula,
        "nombre": data["estudiante"]["nombre"],
        "imagen": base64.b64decode(qr_base64),
    }


try:
    grupos = obtener_grupos()
except Exception as e:
    grupos = []
    st.error(f"🚨 No se pudo obtener la lista de grupos: {e}")

if grupos:
    opciones = {f"{g['nombre']} ({g.get('turno', '')} {g.get('nivel', '')})".strip(): g["id_grupo"] for g in grupos}
    grupo_label = st.selectbox("Selecciona un grupo", list(opciones.keys()))
    id_grupo = opciones[grupo_label]

    if "masivo_zip" not in st.session_state:
        st.session_state.masivo_zip = None
    if "masivo_resumen" not in st.session_state:
        st.session_state.masivo_resumen = None

    if st.button("🚀 Generar QR del grupo"):
        st.session_state.masivo_zip = None
        st.session_state.masivo_resumen = None

        try:
            resp = requests.get(f"{BACKEND_URL}/api/grupos/{id_grupo}/estudiantes", timeout=15)
            resp.raise_for_status()
            data = resp.json()["data"]
            estudiantes = data["estudiantes"]
        except Exception as e:
            st.error(f"🚨 No se pudo obtener a los estudiantes del grupo: {e}")
            estudiantes = []

        activos = [e for e in estudiantes if e.get("estado_actual") == "activo"]
        inactivos = len(estudiantes) - len(activos)

        if not activos:
            st.warning("⚠️ Este grupo no tiene estudiantes activos.")
        else:
            progreso = st.progress(0.0, text=f"Generando 0/{len(activos)} códigos QR...")
            generados = []
            errores = []

            with ThreadPoolExecutor(max_workers=8) as executor:
                futuros = {
                    executor.submit(generar_qr_estudiante, e["matricula"]): e
                    for e in activos
                }
                completados = 0
                for futuro in as_completed(futuros):
                    estudiante = futuros[futuro]
                    completados += 1
                    try:
                        generados.append(futuro.result())
                    except Exception as e:
                        errores.append(f"{estudiante['matricula']} - {estudiante['nombre']} {estudiante['apellido']}: {e}")
                    progreso.progress(
                        completados / len(activos),
                        text=f"Generando {completados}/{len(activos)} códigos QR..."
                    )

            progreso.empty()

            if generados:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for item in generados:
                        nombre_archivo = f"{item['matricula']}_{sanitizar_nombre_archivo(item['nombre'])}.png"
                        zf.writestr(nombre_archivo, item["imagen"])
                zip_buffer.seek(0)
                st.session_state.masivo_zip = zip_buffer.getvalue()

            st.session_state.masivo_resumen = {
                "total": len(estudiantes),
                "generados": len(generados),
                "inactivos": inactivos,
                "errores": errores,
            }

    resumen = st.session_state.get("masivo_resumen")
    if resumen:
        st.success(f"✅ {resumen['generados']} QR generados de {resumen['total']} estudiantes del grupo.")
        if resumen["inactivos"]:
            st.info(f"ℹ️ {resumen['inactivos']} estudiante(s) omitido(s) por no estar activos.")
        if resumen["errores"]:
            with st.expander(f"⚠️ {len(resumen['errores'])} error(es)"):
                for err in resumen["errores"]:
                    st.text(err)

    if st.session_state.get("masivo_zip"):
        st.download_button(
            label="⬇️ Descargar todos (.zip)",
            data=st.session_state.masivo_zip,
            file_name=f"qrs_grupo_{id_grupo}.zip",
            mime="application/zip",
        )
else:
    st.info("No hay grupos disponibles todavía.")

# ---------- CIERRE DIV PRINCIPAL ----------
st.markdown("</div>", unsafe_allow_html=True)
