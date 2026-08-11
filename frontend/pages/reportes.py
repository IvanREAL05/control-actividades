import streamlit as st
import requests
import base64
from datetime import datetime, date
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
    width: 100%;
}

.stButton > button:hover {
    background: linear-gradient(135deg, var(--dark-blue) 0%, var(--primary-blue) 100%);
}

.report-card {
    background: white;
    padding: 1.5rem;
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
st.sidebar.page_link("pages/generarqr_masivo.py", label="📦 QR Masivo")
st.sidebar.page_link("pages/justificantes.py", label="📑 Justificantes")
st.sidebar.page_link("app.py", label="🚪 Cerrar sesión")

# ---------- ENCABEZADO ----------
logo1 = load_image_base64("logo_buap.jpg")
logo2 = load_image_base64("logo1.jpeg")

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
API_BASE = "https://control-actividades.onrender.com/api/reportes"
API_HELPERS = "https://control-actividades.onrender.com/api/helpers"

# ---------- FUNCIONES AUXILIARES ----------
@st.cache_data(ttl=300)
def obtener_grupos():
    try:
        response = requests.get(f"{API_HELPERS}/grupos", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

@st.cache_data(ttl=300)
def obtener_estudiantes():
    try:
        response = requests.get(f"{API_HELPERS}/estudiantes", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

@st.cache_data(ttl=300)
def obtener_clases():
    try:
        response = requests.get(f"{API_HELPERS}/clases", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

@st.cache_data(ttl=300)
def obtener_profesores():
    try:
        response = requests.get(f"{API_HELPERS}/profesores", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def descargar_excel(url: str, params: dict = None):
    try:
        with st.spinner("⏳ Generando reporte... esto puede tardar unos segundos"):
            response = requests.get(url, params=params, timeout=60)
        
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
                key=f"download_{datetime.now().timestamp()}",
                use_container_width=True
            )
        else:
            error_msg = response.json().get("detail", response.text) if response.text else "Error desconocido"
            st.error(f"❌ Error del servidor: {error_msg}")
    except requests.exceptions.ConnectionError:
        st.error("❌ No se pudo conectar con el servidor. Verifica que FastAPI esté corriendo en localhost:8000")
    except requests.exceptions.Timeout:
        st.error("❌ La solicitud tardó demasiado. Intenta con un rango de fechas más pequeño.")
    except Exception as e:
        st.error(f"❌ Error inesperado: {str(e)}")

# ---------- SECCIÓN DE REPORTES ----------
st.subheader("📋 Generar Reportes")

# Usar pestañas para organizar mejor
tabs = st.tabs([
    "📚 Asistencias por Grupo",
    "👤 Reporte Individual",
    "📝 Actividades por Clase",
    "📊 Actividades General",
    "👨‍🏫 Reporte de Profesor"
])

# --- PESTAÑA 1: Asistencias por Grupo ---
with tabs[0]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("📄 Genera un reporte de asistencias de todos los alumnos de un grupo en un rango de fechas.")
    
    grupos = obtener_grupos()
    if grupos:
        opciones_grupos = {g["label"]: g["id"] for g in grupos}
        grupo_seleccionado = st.selectbox(
            "Selecciona el grupo",
            options=list(opciones_grupos.keys()),
            key="grupo_select"
        )
        id_grupo = opciones_grupos[grupo_seleccionado]
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio", value=date.today(), key="grupo_inicio")
        with col2:
            fecha_fin = st.date_input("Fecha fin", value=date.today(), key="grupo_fin")
        
        if fecha_fin < fecha_inicio:
            st.warning("⚠️ La fecha de fin no puede ser anterior a la de inicio.")
        else:
            if st.button("📊 Generar reporte de grupo", key="btn_grupo"):
                params = {
                    "id_grupo": id_grupo,
                    "fechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
                    "fechaFin": fecha_fin.strftime("%Y-%m-%d")
                }
                descargar_excel(f"{API_BASE}/excel", params)
    else:
        st.warning("⚠️ No se pudieron cargar los grupos. Verifica la conexión con el servidor.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 2: Reporte Individual ---
with tabs[1]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("👤 Reporte de asistencias de un estudiante específico en un rango de fechas.")
    
    # Buscar por matrícula
    matricula_buscar = st.text_input(
        "Ingresa la matrícula del estudiante",
        placeholder="Ejemplo: 100316933",
        key="matricula_input"
    )
    
    if matricula_buscar:
        try:
            # Buscar estudiante por matrícula
            response = requests.get(
                f"{API_HELPERS}/estudiantes",
                timeout=10
            )
            if response.status_code == 200:
                estudiantes = response.json()
                estudiante_encontrado = next(
                    (e for e in estudiantes if e["matricula"] == matricula_buscar),
                    None
                )
                
                if estudiante_encontrado:
                    st.success(f"✅ Estudiante encontrado: {estudiante_encontrado['label']}")
                    id_estudiante = estudiante_encontrado["id"]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        fecha_inicio = st.date_input("Fecha inicio", value=date.today(), key="est_inicio")
                    with col2:
                        fecha_fin = st.date_input("Fecha fin", value=date.today(), key="est_fin")
                    
                    if fecha_fin < fecha_inicio:
                        st.warning("⚠️ La fecha de fin no puede ser anterior a la de inicio.")
                    else:
                        if st.button("📄 Generar reporte individual", key="btn_est"):
                            params = {
                                "id_estudiante": id_estudiante,
                                "fechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
                                "fechaFin": fecha_fin.strftime("%Y-%m-%d")
                            }
                            descargar_excel(f"{API_BASE}/excel/individual", params)
                else:
                    st.error("❌ No se encontró ningún estudiante con esa matrícula.")
        except Exception as e:
            st.error(f"❌ Error al buscar estudiante: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 3: Actividades por Clase ---
with tabs[2]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("📚 Reporte detallado de actividades de una clase (una hoja por actividad).")
    
    # Buscar por NRC
    nrc_buscar = st.text_input(
        "Ingresa el NRC de la clase",
        placeholder="Ejemplo: 025",
        key="nrc_actividad_input"
    )
    
    if nrc_buscar:
        try:
            # Buscar clase por NRC
            response = requests.get(f"{API_HELPERS}/clases", timeout=10)
            if response.status_code == 200:
                clases = response.json()
                clase_encontrada = next(
                    (c for c in clases if c["nrc"] == nrc_buscar),
                    None
                )
                
                if clase_encontrada:
                    st.success(f"✅ Clase encontrada: {clase_encontrada['label']}")
                    id_clase = clase_encontrada["id"]
                    
                    if st.button("📝 Generar reporte de actividades", key="btn_act_clase"):
                        descargar_excel(f"{API_BASE}/excel/clase/{id_clase}")
                else:
                    st.error("❌ No se encontró ninguna clase con ese NRC.")
        except Exception as e:
            st.error(f"❌ Error al buscar clase: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 4: Reporte General de Actividades ---
with tabs[3]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("📊 Reporte consolidado de todas las actividades de una clase en una sola hoja.")
    
    # Buscar por NRC
    nrc_buscar = st.text_input(
        "Ingresa el NRC de la clase",
        placeholder="Ejemplo: 025",
        key="nrc_general_input"
    )
    
    if nrc_buscar:
        try:
            # Buscar clase por NRC
            response = requests.get(f"{API_HELPERS}/clases", timeout=10)
            if response.status_code == 200:
                clases = response.json()
                clase_encontrada = next(
                    (c for c in clases if c["nrc"] == nrc_buscar),
                    None
                )
                
                if clase_encontrada:
                    st.success(f"✅ Clase encontrada: {clase_encontrada['label']}")
                    id_clase = clase_encontrada["id"]
                    
                    if st.button("📊 Generar reporte general", key="btn_act_general"):
                        descargar_excel(f"{API_BASE}/excel/clase/general/{id_clase}")
                else:
                    st.error("❌ No se encontró ninguna clase con ese NRC.")
        except Exception as e:
            st.error(f"❌ Error al buscar clase: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- PESTAÑA 5: Reporte de Profesor ---
with tabs[4]:
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.info("👨‍🏫 Reporte de todas las clases asignadas a un profesor en un rango de fechas.")
    
    profesores = obtener_profesores()
    if profesores:
        opciones_profesores = {p["label"]: p["id"] for p in profesores}
        profesor_seleccionado = st.selectbox(
            "Selecciona el profesor",
            options=list(opciones_profesores.keys()),
            key="prof_select"
        )
        id_profesor = opciones_profesores[profesor_seleccionado]
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio", value=date(2025, 8, 4), key="prof_inicio")
        with col2:
            fecha_fin = st.date_input("Fecha fin", value=date.today(), key="prof_fin")
        
        if fecha_fin < fecha_inicio:
            st.warning("⚠️ La fecha de fin no puede ser anterior a la de inicio.")
        else:
            if st.button("👨‍🏫 Generar reporte del profesor", key="btn_prof"):
                params = {
                    "id_profesor": id_profesor,
                    "fechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
                    "fechaFin": fecha_fin.strftime("%Y-%m-%d")
                }
                descargar_excel(f"{API_BASE}/excel/profesor/{id_profesor}", params)
    else:
        st.warning("⚠️ No se pudieron cargar los profesores. Verifica la conexión con el servidor.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- PIE DE PÁGINA ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #6b7280; font-size: 0.875rem;'>"
    "Sistema de Reportes Académicos | UA PREP. GRAL. LÁZARO CÁRDENAS DEL RÍO"
    "</p>",
    unsafe_allow_html=True
)