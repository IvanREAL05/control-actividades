import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import math
import plotly.io as pio
import uuid
import streamlit.components.v1 as components
import base64
from pathlib import Path

# ✅ Obtener rutas correctas de las imágenes
# Como estamos en pages/, subimos un nivel para llegar a frontend/
BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"

# Función helper para cargar imágenes
def load_image_base64(image_name):
    try:
        image_path = ASSETS_DIR / image_name
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.warning(f"⚠️ Imagen {image_name} no encontrada")
        return ""




API_BASE_URL = "https://control-actividades.onrender.com/api/"
# CSS personalizado para el tema azul y blanco
st.markdown("""
<style>
    /* Importar fuente moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variables CSS para colores */
    :root {
        --primary-blue: #2563eb;
        --secondary-blue: #3b82f6;
        --light-blue: #dbeafe;
        --dark-blue: #1e40af;
        --white: #ffffff;
        --gray-50: #f9fafb;
        --gray-100: #f3f4f6;
        --gray-200: #e5e7eb;
        --gray-600: #4b5563;
        --gray-800: #1f2937;
    }
    
    /* Resetear estilos base */
    .main {
        padding: 1rem 2rem;
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, var(--gray-50) 0%, var(--white) 100%);
    }
    
    /* Header personalizado */
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
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    
    /* Tarjetas de información */
    .info-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border-left: 4px solid var(--primary-blue);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .info-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Botones personalizados */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, var(--dark-blue) 0%, var(--primary-blue) 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
    }
    
    /* Botones de estado específicos */
    .status-presente {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        border-radius: 20px !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 1rem !important;
    }
    
    .status-ausente {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
        border-radius: 20px !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 1rem !important;
    }
    
    .status-justificante {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        border-radius: 20px !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 1rem !important;
    }
    
    /* Selectbox personalizado */
    .stSelectbox > div > div > div {
        background: white;
        border: 2px solid var(--light-blue);
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
    }
    
    .stSelectbox > div > div > div:focus-within {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    
    /* Métricas personalizadas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        text-align: center;
        border-top: 3px solid var(--primary-blue);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary-blue);
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: var(--gray-600);
        font-weight: 500;
        margin: 0.25rem 0 0 0;
    }
    
    /* Lista de estudiantes */
    .student-row {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 3px solid var(--light-blue);
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s ease;
    }
    
    .student-row:hover {
        border-left-color: var(--primary-blue);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .student-info {
        font-weight: 500;
        color: var(--gray-800);
    }
    
    /* Mapa de asientos */
    .seat-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 0.5rem;
        margin: 1rem 0;
    }
    
    .seat {
        aspect-ratio: 1;
        background: white;
        border: 2px solid var(--light-blue);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        color: var(--primary-blue);
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .seat:hover {
        background: var(--light-blue);
        border-color: var(--primary-blue);
    }
    
    .seat.occupied {
        background: var(--primary-blue);
        color: white;
    }
    
    /* Secciones */
    .section-title {
        color: var(--dark-blue);
        font-size: 1.25rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Divisores */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, var(--light-blue), transparent);
        margin: 2rem 0;
    }
    
    /* Info cards */
    .stAlert {
        background: linear-gradient(135deg, var(--light-blue) 0%, white 100%);
        border: 1px solid var(--primary-blue);
        border-radius: 8px;
        color: var(--dark-blue);
    }
    
    /* Fecha y hora */
    .datetime-info {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid var(--primary-blue);
        font-weight: 500;
        color: var(--gray-800);
    }
</style>
""", unsafe_allow_html=True)
#Configuracion 
st.set_page_config(
    page_title="Panel",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Ocultar menú y footer ---
hide_menu = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

# --- Protección de acceso ---
if "usuario" not in st.session_state:
    st.warning("⚠️ Debes iniciar sesión primero")
    st.switch_page("app.py")
    st.stop()

usuario = st.session_state["usuario"]

# --- Encabezado superior ---
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

# Información del usuario y botón de cerrar sesión
col_user, col_btn = st.columns([4, 1])
# Fecha y hora (estática)

# Usuario
with col_user:
    st.info(f"👋 Bienvenido, {usuario['nombre_completo']}")

# Botón cerrar sesión
with col_btn:
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.switch_page("app.py")
        
# ---------- OCULTAR MENÚ LATERAL POR DEFECTO ----------
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# ---------- MENÚ LATERAL ----------
st.sidebar.title("Menú")
st.sidebar.page_link("pages/panel.py", label="🏠 Panel Principal")
st.sidebar.page_link("pages/generarqr.py", label="🔑 Generar QR")
st.sidebar.page_link("pages/justificantes.py", label="📑 Justificantes")
st.sidebar.page_link("pages/vertodasclases.py", label="📊 Ver todas las clases")
st.sidebar.page_link("pages/cargardatos.py", label="📊 Subir datos")
st.sidebar.page_link("app.py", label="🚪 Cerrar sesión")

st.markdown("<hr>", unsafe_allow_html=True)


# 1. Obtener clases del día desde el backend
try:
    res_clases = requests.get("https://control-actividades.onrender.com/api/clases/hoy/todas")
    res_clases.raise_for_status()
    clases = res_clases.json()
except Exception as e:
    st.error(f"Error al cargar clases del día: {e}")
    clases = []


# 2. Selector de clase
st.markdown('<h2 class="section-title">📘 Control de Asistencia por Clase</h2>', unsafe_allow_html=True)

id_clase = None  # inicializamos por seguridad

if clases:
    opciones = [f"{c['nombre_materia']} - {c['nrc']} - {c['nombre_grupo']}" for c in clases]
    seleccion = st.selectbox("Selecciona una clase", opciones, key="selector_clase")

    if seleccion and seleccion in opciones:
        id_clase = clases[opciones.index(seleccion)]["id_clase"]
    else:
        st.warning("Selecciona una clase válida.")
else:
    st.warning("⚠️ No hay clases disponibles para hoy.")

# Botones de acción
col_acc1, col_acc2, col_acc3, col_acc4, col_acc5= st.columns(5)
with col_acc1:
    if st.button("📊 Ver Todas las Clases"):
        st.switch_page("pages/vertodasclases.py")
with col_acc2:
    if st.button("📢 Crear Nuevo Aviso"):
        st.switch_page("pages/crearaviso.py")
with col_acc3:
    if st.button("📥 Cargar Datos"):
        st.switch_page("pages/cargardatos.py")

with col_acc4:
    if st.button("📝 Justificantes"):
        st.switch_page("pages/justificantes.py")

with col_acc5:
    if st.button("✅Ver clases del momento "):
        st.switch_page("pages/resultados.py")
st.markdown("<hr>", unsafe_allow_html=True)

#Endpoint resumen del turno actual 
# --- 1. Resumen del turno actual ---
st.markdown('<h2 class="section-title">📊 Resumen del Turno</h2>', unsafe_allow_html=True)

turno = st.selectbox("Selecciona turno", ["matutino", "vespertino"], index=0, key="turno_resumen")


try:
    response = requests.get(f"{API_BASE_URL}asistencias/resumen", params={"turno": turno}, timeout=6)
    response.raise_for_status()
    resumen = response.json() or {}
except Exception as e:
    st.error(f"❌ Error al obtener resumen del turno: {e}")
    resumen = {"totalAlumnos": 0, "presentes": 0, "justificantes": 0, "ausentes": 0, "porcentaje": 0}

# Mostrar métricas en columnas
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("👥 Total", resumen.get("totalAlumnos"))
col2.metric("✅ Presentes", resumen.get("presentes"))
col3.metric("📄 Justificantes", resumen.get("justificantes"))
col4.metric("❌ Ausentes", resumen.get("ausentes"))
col5.metric("📊 % Asistencia", f"{resumen.get('porcentaje')}%")

# --- 2. Resumen General de la Escuela ---
st.markdown('<h2 class="section-title">🏫 Resumen General</h2>', unsafe_allow_html=True)

turno_general = st.selectbox("Selecciona turno", ["matutino", "vespertino"], index=0, key="turno_resumen_general")

try:
    response = requests.get(f"{API_BASE_URL}asistencias/resumen-general", params={"turno": turno_general}, timeout=6)
    response.raise_for_status()
    resumen_general = response.json() or {}
except Exception as e:
    st.error(f"❌ Error al obtener resumen general: {e}")
    resumen_general = {"totalAlumnos": 0, "presentes": 0, "justificantes": 0, "ausentes": 0, "porcentaje": 0}

# Mostrar métricas generales
gcol1, gcol2, gcol3, gcol4, gcol5 = st.columns(5)
gcol1.metric("👥 Total (escuela)", resumen_general.get("totalAlumnos", 0))
gcol2.metric("✅ Presentes", resumen_general.get("presentes", 0))
gcol3.metric("📄 Justificantes", resumen_general.get("justificantes", 0))
gcol4.metric("❌ Ausentes", resumen_general.get("ausentes", 0))
gcol5.metric("📊 % Asistencia", f"{resumen_general.get('porcentaje', 0)}%")
st.markdown("<hr>", unsafe_allow_html=True)


# Reemplaza la sección "--- 3. Resumen por Clase ---" con este código:

# --- 3. Resumen por Clase ---
st.markdown('<h2 class="section-title">📘 Resumen por Clase</h2>', unsafe_allow_html=True)
# pasar fecha opcional: usar hoy en formato YYYY-MM-DD
fecha_hoy = datetime.now().strftime("%Y-%m-%d")

try:
    response = requests.get(f"{API_BASE_URL}asistencias/por-clase", params={"fecha": fecha_hoy}, timeout=8)
    response.raise_for_status()
    clases_resumen = response.json()
except Exception as e:
    st.error(f"❌ Error al obtener resumen por clase: {e}")
    clases_resumen = []

if not clases_resumen:
    st.info("ℹ️ No hay clases registradas para la fecha.")
else:
    # Generar HTML completo con Swiper.js
    slides_html = ""
    for clase in clases_resumen:
        nombre = clase.get("nombre_clase") or clase.get("nombre_materia") or "Clase"
        grupo = clase.get("grupo", "")
        presentes = int(clase.get("presentes", 0))
        justificantes = int(clase.get("justificantes", 0))
        ausentes = int(clase.get("ausentes", 0))
        total_clase = presentes + justificantes + ausentes
        porcentaje = clase.get("porcentaje", 0)

        # Gráfica de pastel
        df_clase = pd.DataFrame([
            {"Estado": "Presentes", "Cantidad": presentes},
            {"Estado": "Ausentes", "Cantidad": ausentes},
            {"Estado": "Justificantes", "Cantidad": justificantes}
        ])
        df_clase["Estado"] = pd.Categorical(df_clase["Estado"], categories=["Presentes", "Ausentes", "Justificantes"])

        fig_pie = px.pie(
            df_clase,
            names="Estado",
            values="Cantidad",
            color="Estado",
            color_discrete_map={
                "Presentes": "#0ae73a",
                "Ausentes": "#e61010",
                "Justificantes": "#f3f70c"
            },
            title="Distribución de Asistencia"
        )
        fig_pie.update_layout(
            margin=dict(t=40, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            height=300,
            title_x=0.5,
            font_size=12
        )
        chart_pie_html = pio.to_html(fig_pie, full_html=False, include_plotlyjs="cdn")

        # Gráfica de tendencias (simulada con datos de ejemplo - puedes cambiar por datos reales)
        # Datos de ejemplo de los últimos 7 días
        fechas_ejemplo = pd.date_range(end=fecha_hoy, periods=7, freq='D')
        tendencia_data = pd.DataFrame({
            'Fecha': fechas_ejemplo,
            'Presentes': [presentes + i*2 - 6 for i in range(7)],
            'Ausentes': [ausentes + abs(i-3) for i in range(7)],
            'Justificantes': [justificantes + (i%3) for i in range(7)]
        })
        
        # Asegurar valores positivos
        for col in ['Presentes', 'Ausentes', 'Justificantes']:
            tendencia_data[col] = tendencia_data[col].clip(lower=0)

        fig_trend = px.line(
            tendencia_data, 
            x='Fecha', 
            y=['Presentes', 'Ausentes', 'Justificantes'],
            title="Tendencia de Asistencia (7 días)",
            color_discrete_map={
                "Presentes": "#0ae73a",
                "Ausentes": "#e61010",
                "Justificantes": "#f3f70c"
            }
        )
        fig_trend.update_layout(
            margin=dict(t=40, b=10, l=10, r=10),
            height=300,
            title_x=0.5,
            font_size=12,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        chart_trend_html = pio.to_html(fig_trend, full_html=False, include_plotlyjs="cdn")

        slides_html += f"""
        <div class="swiper-slide">
            <div class="slide-card">
                <h4>{nombre} — {grupo}</h4>
                <div class="metrics-info">
                    <p>👥 Total: {total_clase}</p>
                    <p>✅ Presentes: {presentes}</p>
                    <p>📄 Justificantes: {justificantes}</p>
                    <p>❌ Ausentes: {ausentes}</p>
                    <p>📊 % Asistencia: {porcentaje}%</p>
                </div>
                <div class="charts-container">
                    <div class="chart-item">
                        {chart_pie_html}
                    </div>
                    <div class="chart-item">
                        {chart_trend_html}
                    </div>
                </div>
            </div>
        </div>
        """

    html = f"""
    <link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro&display=swap" rel="stylesheet">
    <style>
        .swiper-container {{
            width: 100%;
            padding: 30px 0;
        }}
        .swiper-wrapper {{
            display: flex;
            align-items: stretch;
        }}
        .swiper-slide {{
            flex-shrink: 0;
            width: 900px;
            box-sizing: border-box;
            display: flex;
            justify-content: center;
        }}
        .slide-card {{
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            width: 100%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            font-family: "Source Sans Pro", sans-serif;
            color: #333;
        }}
        .slide-card h4 {{
            font-family: "Source Sans Pro", sans-serif;
            font-size: 20px;
            margin-bottom: 15px;
            text-align: center;
            color: #2563eb;
        }}
        .metrics-info {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .metrics-info p {{
            font-family: "Source Sans Pro", sans-serif;
            margin: 4px 8px;
            font-size: 14px;
            font-weight: 500;
        }}
        .charts-container {{
            display: flex;
            gap: 20px;
            align-items: center;
            justify-content: space-between;
        }}
        .chart-item {{
            flex: 1;
            min-width: 0;
        }}
        
        /* Responsive para pantallas pequeñas */
        @media (max-width: 768px) {{
            .swiper-slide {{
                width: 95vw;
            }}
            .charts-container {{
                flex-direction: column;
                gap: 15px;
            }}
            .metrics-info {{
                justify-content: center;
            }}
        }}
    </style>

    <div class="swiper-container">
        <div class="swiper-wrapper">
            {slides_html}
        </div>
        <!-- Controles -->
        <div class="swiper-button-prev"></div>
        <div class="swiper-button-next"></div>
        <div class="swiper-pagination"></div>
    </div>

    <script src="https://unpkg.com/swiper/swiper-bundle.min.js"></script>
    <script>
        const swiper = new Swiper('.swiper-container', {{
            slidesPerView: 1,
            spaceBetween: 20,
            loop: true,
            pagination: {{
                el: '.swiper-pagination',
                clickable: true,
            }},
            navigation: {{
                nextEl: '.swiper-button-next',
                prevEl: '.swiper-button-prev',
            }},
            autoplay: {{
                delay: 5000,
                disableOnInteraction: false,
            }},
        }});
    </script>
    """

    components.html(html, height=800)

#5 Lista de alumnos
# --- Inicializar estado para ver todos los alumnos ---
if "ver_todos_alumnos" not in st.session_state:
    st.session_state.ver_todos_alumnos = False

# --- Lista de Alumnos ---
st.markdown('<h2 class="section-title">👨‍🎓 Lista de Alumnos</h2>', unsafe_allow_html=True)

alumnos = []
clase_info = None

# Solo si hay clase seleccionada
if id_clase:
    # Buscar la info de la clase
    clase_info = next((c for c in clases if c["id_clase"] == id_clase), None)
    if clase_info:
        id_grupo = clase_info["id_grupo"]

        try:
            # Llamada al endpoint para alumnos del grupo
            res_alumnos = requests.get(f"https://control-actividades.onrender.com/api/estudiantes/grupo/{id_grupo}")
            res_alumnos.raise_for_status()
            alumnos = res_alumnos.json()  # Se espera una lista de alumnos
        except Exception as e:
            st.error(f"❌ Error al obtener alumnos: {e}")
    else:
        st.warning("⚠️ No se encontró la información de la clase seleccionada.")

if alumnos:
    # Mostrar primeros 5 o todos según el estado
    mostrar_alumnos = alumnos if st.session_state.ver_todos_alumnos else alumnos[:5]

    for alumno in mostrar_alumnos:
        col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
        with col_a1:
            st.markdown(
                f"<div class='student-info'>{alumno['no_lista']}. {alumno['nombre']} {alumno['apellido']} — {alumno['matricula']}</div>",
                unsafe_allow_html=True
            )
        with col_a2:
            estado = alumno.get('estado_actual', 'N/A').title()
            if st.button(f"📋 {estado}", key=f"estado_{id_clase}_{alumno['id_estudiante']}"):
                st.toast(f"Estado de {alumno['nombre']} actualizado", icon="✅")
        with col_a3:
            if st.button("ℹ️ Detalles", key=f"info_{id_clase}_{alumno['id_estudiante']}"):
                st.info(
                    f"Nombre: {alumno['nombre']} {alumno['apellido']}\n"
                    f"Matrícula: {alumno['matricula']}\n"
                    f"No. Lista: {alumno['no_lista']}\n"
                    f"Estado actual: {estado}"
                )

    # Botón para alternar entre mostrar todos o menos
    if len(alumnos) > 5:
        if st.session_state.ver_todos_alumnos:
            if st.button("⬆️ Ver menos"):
                st.session_state.ver_todos_alumnos = False
                st.rerun()
        else:
            if st.button("⬇️ Ver más"):
                st.session_state.ver_todos_alumnos = True
                st.rerun()
else:
    st.warning("⚠️ No hay alumnos registrados para este grupo.")

st.markdown("<hr>", unsafe_allow_html=True)

def obtener_asistencia_clase(id_clase: int):
    try:
        response = requests.get(f"{API_BASE_URL}asistencias/clase/{id_clase}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener asistencia: {e}")
        return []
    
# 6 Mapa de asientos dinámico
st.markdown('<h2 class="section-title">🪑 Mapa de Asientos</h2>', unsafe_allow_html=True)

# ✅ Usar id_clase que ya está definida arriba
if id_clase:  # ✅ Esta variable ya existe de tu selector
    alumnos_con_asistencia = obtener_asistencia_clase(id_clase)

else:
    st.warning("⚠️ Selecciona una clase primero")
    alumnos_con_asistencia = []

if alumnos_con_asistencia:
    cols = 6
    total_alumnos = len(alumnos_con_asistencia)
    rows = math.ceil(total_alumnos / cols)

    for i in range(rows):
        cols_seat = st.columns(cols)
        for j in range(cols):
            seat_num = i * cols + j + 1
            a = next((x for x in alumnos_con_asistencia if x.get("no_lista") == seat_num), None)
            
            with cols_seat[j]:
                if a:
                    estado = a.get("estado", "ausente").lower()
                    color = {
                        "presente": "🟢",
                        "ausente": "🔴",
                        "justificante": "🟡"
                    }.get(estado, "⚪")

                    nombre = a.get("nombre", "")
                    apellido = a.get("apellido", "")
                    iniciales = (nombre[:1] + apellido[:1]).upper() if nombre and apellido else "--"

                    if st.button(f"{color} {iniciales}", key=f"seat_{seat_num}"):
                        st.info(f"Asiento {seat_num}: {nombre} {apellido} - {estado.title()}")
                else:
                    st.button("⚪ ---", key=f"empty_{seat_num}", disabled=True)

st.markdown("<hr>", unsafe_allow_html=True)


# QR y footer
st.markdown("<hr>", unsafe_allow_html=True)
col_qr1, col_qr2 = st.columns([3, 1])
with col_qr1:
    st.markdown("""
    <div class="info-card">
        <h4 style="color: #2563eb;">📱 Código QR para Estudiantes</h4>
        <p>Ingresa matricula de estudiante para generar QR</p>
    </div>
    """, unsafe_allow_html=True)
with col_qr2:
    if st.button("📲 Generar QR"):
        st.switch_page("pages/generarqr.py")
        st.success("¡Código QR generado exitosamente!")
        st.info("Código válido por 30 minutos")

# Reportes de excel
st.markdown("<hr>", unsafe_allow_html=True)
col_qr1, col_qr2 = st.columns([3, 1])
with col_qr1:
    st.markdown("""
    <div class="info-card">
        <h4 style="color: #2563eb;">📱 Reportes</h4>
        <p>Descarga reportes de asistencias en excel</p>
    </div>
    """, unsafe_allow_html=True)
with col_qr2:
    if st.button("📲 Ver todos los reportes"):
        st.switch_page("pages/reportes.py")
st.markdown("""
<div style="text-align: center; padding: 2rem 0; color: #6b7280; border-top: 1px solid #e5e7eb;">
    <p>© 2025 UA PREP. LÁZARO CARDENAS DEL RÍO - Sistema de Control</p>
</div>
""", unsafe_allow_html=True)