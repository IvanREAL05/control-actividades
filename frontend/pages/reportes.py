import streamlit as st
import requests
import base64
from datetime import datetime, date

# ---------- CONFIGURACIÓN DE LA PÁGINA ----------
st.set_page_config(
    page_title="Reportes",
    page_icon="📊",
    layout="wide"
)

# ---------- CSS PERSONALIZADO ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary-blue: #2563eb;
    --secondary-blue: #3b82f6;
    --light-blue: #dbeafe;
    --dark-blue: #1e40af;
    --white: #ffffff;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
}

.main {
    padding: 1rem 2rem;
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, var(--white) 0%, var(--light-blue) 100%);
}

.custom-header {
    background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
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
}

.stButton > button {
    background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(135deg, var(--dark-blue) 0%, var(--primary-blue) 100%);
}

.report-card {
    background: white;
    padding: 1.2rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 1.5rem;
    border-left: 4px solid var(--primary-blue);
}
</style>
""", unsafe_allow_html=True)

# ---------- OCULTAR MENÚ LATERAL POR DEFECTO ----------
st.markdown("""
<style>
[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# ---------- MENÚ LATERAL ----------
st.sidebar.title("Menú")
st.sidebar.page_link("pages/panel.py", label="🏠 Panel Principal")
st.sidebar.page_link("pages/cargardatos.py", label="📥 Subir datos")
st.sidebar.page_link("pages/vertodasclases.py", label="📊 Ver todas las clases")
st.sidebar.page_link("pages/generarqr.py", label="🔑 Generar QR")
st.sidebar.page_link("pages/justificantes.py", label="📑 Justificantes")
st.sidebar.page_link("app.py", label="🚪 Cerrar sesión")

# ---------- ENCABEZADO ----------
try:
    logo1 = base64.b64encode(open("assets/logo_buap.jpg", "rb").read()).decode()
    logo2 = base64.b64encode(open("assets/logo1.jpeg", "rb").read()).decode()
except FileNotFoundError:
    st.warning("⚠️ Logos no encontrados en 'assets/'. Asegúrate de tener los archivos.")
    logo1 = logo2 = ""

st.markdown(f"""
<div class="custom-header">
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 1rem;">
        <img src="data:image/jpeg;base64,{logo1}" style="height: 60px; width: auto; object-fit: contain;" alt="Logo BUAP">
        <h1 class="header-title" style="margin: 0; flex: 1; text-align: center;">UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
        <img src="data:image/jpeg;base64,{logo2}" style="height: 60px; width: auto; object-fit: contain;" alt="Logo Institución">
    </div>
</div>
""", unsafe_allow_html=True)

# ---------- BOTÓN VOLVER ----------
col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
with col_back2:
    if st.button("🏠 Volver al panel principal"):
        st.switch_page("pages/panel.py")

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- CONFIGURACIÓN API ----------
API_BASE = "http://localhost:8000/api/reportes"

# ---------- FUNCIÓN DE DESCARGA MEJORADA ----------
def descargar_excel(url: str, params: dict = None):
    try:
        with st.spinner("Generando reporte... esto puede tardar unos segundos"):
            response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            content_disp = response.headers.get("content-disposition", "")
            if "filename=" in content_disp:
                filename = content_disp.split("filename=")[1].strip('"')
            else:
                filename = "reporte.xlsx"
            
            st.success("✅ Reporte generado correctamente")
            st.download_button(
                label="⬇️ Descargar Excel",
                data=response.content,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{datetime.now().timestamp()}"
            )
        else:
            error_msg = response.json().get("detail", response.text)
            st.error(f"❌ Error del servidor: {error_msg}")
    except requests.exceptions.ConnectionError:
        st.error("❌ No se pudo conectar con el servidor. ¿Está corriendo FastAPI en localhost:8000?")
    except requests.exceptions.Timeout:
        st.error("❌ La solicitud tardó demasiado. Intenta con un rango de fechas más pequeño.")
    except Exception as e:
        st.exception(f"Error inesperado: {e}")

# ---------- SECCIÓN DE REPORTES ----------
st.subheader("📋 Generar Reportes")

# Usar pestañas para organizar mejor
tabs = st.tabs([
    "Asistencias por Grupo",
    "Reporte Individual",
    "Actividades por Clase",
    "Actividades General",
    "Reporte de Profesor"
])

# --- PESTAÑA 1: Asistencias por Grupo ---
with tabs[0]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("📄 Genera un reporte de asistencias de todos los alumnos de un grupo en un rango de fechas.")
    
    col1, col2 = st.columns(2)
    with col1:
        id_grupo = st.number_input("ID del grupo", min_value=1, value=1, key="grupo_id")
    with col2:
        fecha_inicio = st.date_input("Fecha inicio", value=date.today(), key="grupo_inicio")
        fecha_fin = st.date_input("Fecha fin", value=date.today(), key="grupo_fin")
    
    if fecha_fin < fecha_inicio:
        st.warning("⚠️ La fecha de fin no puede ser anterior a la de inicio.")
    else:
        if st.button(" Generar reporte de grupo", key="btn_grupo"):
            params = {
                "id_grupo": id_grupo,
                "fechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
                "fechaFin": fecha_fin.strftime("%Y-%m-%d")
            }
            descargar_excel(f"{API_BASE}/excel", params)
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 2: Reporte Individual ---
with tabs[1]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("👤 Reporte de asistencias de un estudiante específico en un rango de fechas.")
    
    id_estudiante = st.number_input("ID del estudiante", min_value=1, value=1, key="est_id")
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=date.today(), key="est_inicio")
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=date.today(), key="est_fin")
    
    if fecha_fin < fecha_inicio:
        st.warning("⚠️ La fecha de fin no puede ser anterior a la de inicio.")
    else:
        if st.button(" Generar reporte individual", key="btn_est"):
            params = {
                "id_estudiante": id_estudiante,
                "fechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
                "fechaFin": fecha_fin.strftime("%Y-%m-%d")
            }
            descargar_excel(f"{API_BASE}/excel/individual", params)
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 3: Actividades por Clase ---
with tabs[2]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("📚 Reporte detallado de actividades de una clase (una hoja por actividad).")
    
    id_clase = st.number_input("ID de la clase", min_value=1, value=1, key="act_clase_id")
    if st.button(" Generar reporte de actividades", key="btn_act_clase"):
        descargar_excel(f"{API_BASE}/excel/clase/{id_clase}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 4: Reporte General de Actividades ---
with tabs[3]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("📊 Reporte consolidado de todas las actividades de una clase en una sola hoja.")
    
    id_clase = st.number_input("ID de la clase", min_value=1, value=1, key="act_general_id")
    if st.button(" Generar reporte general", key="btn_act_general"):
        descargar_excel(f"{API_BASE}/excel/clase/general/{id_clase}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 5: Reporte de Profesor ---
with tabs[4]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("👨‍🏫 Reporte de todas las clases asignadas a un profesor en un rango de fechas.")
    
    id_profesor = st.number_input("ID del profesor", min_value=1, value=1, key="prof_id")
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=date(2025, 8, 4), key="prof_inicio")
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=date.today(), key="prof_fin")
    
    if fecha_fin < fecha_inicio:
        st.warning("⚠️ La fecha de fin no puede ser anterior a la de inicio.")
    else:
        if st.button(" Generar reporte del profesor", key="btn_prof"):
            params = {
                "id_profesor": id_profesor,
                "fechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
                "fechaFin": fecha_fin.strftime("%Y-%m-%d")
            }
            descargar_excel(f"{API_BASE}/excel/profesor/{id_profesor}", params)
    st.markdown('</div>', unsafe_allow_html=True)