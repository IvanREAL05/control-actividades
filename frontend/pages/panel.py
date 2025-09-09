import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import math


# Configuración de la página
st.set_page_config(
    page_title="Panel de Control - LCR", 
    layout="wide",
    initial_sidebar_state="collapsed"
)
API_BASE_URL = "http://localhost:8000/api/"
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

# 1. Obtener clases del día desde el backend
try:
    res_clases = requests.get("http://localhost:8000/api/clases/hoy/todas")
    res_clases.raise_for_status()
    clases = res_clases.json()
except Exception as e:
    st.error(f"Error al cargar clases del día: {e}")
    clases = []

# Encabezado y barra superior
st.markdown("""<div class="custom-header">
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="width: 60px;"></div>
        <h1 class="header-title">UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
        <div style="width: 60px;"></div>
    </div>
</div>""", unsafe_allow_html=True)

col_fecha, col_user, col_btn = st.columns([2, 2, 1])
with col_fecha:
    st.markdown(f"📅 {datetime.now():%d/%m/%Y}<br>🕐 {datetime.now():%H:%M:%S}", unsafe_allow_html=True)
with col_user:
    st.info("👋 Bienvenido, Profesor")
with col_btn:
    if st.button("🚪 Cerrar Sesión", type="secondary"):
        st.session_state.clear()
        st.success("Sesión cerrada correctamente")
st.markdown("<hr>", unsafe_allow_html=True)


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
col_acc1, col_acc2, col_acc3, col_acc4 = st.columns(4)
with col_acc1:
    st.button("📊 Ver Todas las Clases")
with col_acc2:
    if st.button("📢 Crear Nuevo Aviso"):
        st.switch_page("pages/crearaviso.py")
with col_acc3:
    if st.button("📥 Cargar Datos"):
        st.switch_page("pages/cargardatos.py")

with col_acc4:
    if st.button("📝 Justificantes"):
        st.switch_page("pages/justificantes.py")
st.markdown("<hr>", unsafe_allow_html=True)

# Inicializar alumnos vacíos
alumnos = []
clase_info = {}

# 3. Obtener alumnos desde backend si se seleccionó una clase
if id_clase is not None:
    try:
        res_alumnos = requests.get(f"http://localhost:8000/api/profesor/clase/{id_clase}/estudiantes")
        res_alumnos.raise_for_status()
        resp = res_alumnos.json()
        alumnos = resp.get("data", {}).get("estudiantes", [])
        clase_info = resp.get("data", {}).get("clase", {})
    except Exception as e:
        st.error(f"Error al cargar estudiantes de clase: {e}")

# Estadísticas de asistencia
presentes = sum(1 for a in alumnos if a["estado_actual"] == "presente")
ausentes = sum(1 for a in alumnos if a["estado_actual"] == "ausente")
justificantes = sum(1 for a in alumnos if a["estado_actual"] == "justificante")
total = len(alumnos)


# Turno predeterminado
turno = "matutino"

# Llamada al endpoint de resumen
try:
    response = requests.get(f"{API_BASE_URL}/asistencias/resumen", params={"turno": turno})
    if response.status_code == 200:
        resumen = response.json()
        total = resumen["totalAlumnos"]
        presentes = resumen["presentes"]
        ausentes = resumen["ausentes"]
        justificantes = resumen["justificantes"]
        porcentaje = resumen["porcentaje"]
    else:
        st.error("⚠️ No se pudo obtener el resumen de asistencia.")
        total = presentes = ausentes = justificantes = porcentaje = 0
except Exception as e:
    st.error(f"❌ Error de conexión al backend: {e}")
    total = presentes = ausentes = justificantes = porcentaje = 0

st.markdown('<h2 class="section-title">📈 Estadísticas de la Clase</h2>', unsafe_allow_html=True)
col_est1, col_est2, col_est3 = st.columns([1, 1, 2])

with col_est1:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{total}</div><div class="metric-label">Total Alumnos</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card"><div class="metric-value">{presentes}</div><div class="metric-label">Presentes</div></div>', unsafe_allow_html=True)
with col_est2:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{ausentes}</div><div class="metric-label">Ausentes</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card"><div class="metric-value">{justificantes}</div><div class="metric-label">Justificantes</div></div>', unsafe_allow_html=True)
with col_est3:
    df_est = pd.DataFrame([
        {"Estado": "Presentes", "Cantidad": presentes},
        {"Estado": "Ausentes", "Cantidad": ausentes},
        {"Estado": "Justificantes", "Cantidad": justificantes}
    ])
    fig = px.pie(df_est, values="Cantidad", names="Estado", title="Distribución de Asistencia",
                 color_discrete_sequence=['#2563eb', '#ef4444', '#f59e0b'])
    fig.update_layout(font_family="Inter", title_font_size=16, title_font_color='#1f2937',
                      showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    st.plotly_chart(fig, use_container_width=True)



#Backend 
alumnos = []
clase_info = {}

if id_clase:
    # Buscar la clase seleccionada
    clase_info = next((c for c in clases if c["id_clase"] == id_clase), None)

    if clase_info:
        id_grupo = clase_info["id_grupo"]
        try:
            res_alumnos = requests.get(f"http://localhost:8000/api/estudiantes/grupo/{id_grupo}")
            res_alumnos.raise_for_status()
            alumnos = res_alumnos.json()
        except Exception as e:
            st.error(f"Error al obtener alumnos: {e}")
    else:
        st.warning("No se encontró la información de la clase seleccionada.")
# Inicializar el estado si no existe
if "ver_todos_alumnos" not in st.session_state:
    st.session_state.ver_todos_alumnos = False
#4 Lista de alumnos
st.markdown('<h2 class="section-title">👨‍🎓 Lista de Alumnos</h2>', unsafe_allow_html=True)

if alumnos:
    # Mostrar primeros 5 o todos según estado
    mostrar_alumnos = alumnos if st.session_state.ver_todos_alumnos else alumnos[:5]

    for alumno in mostrar_alumnos:
        col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
        with col_a1:
            st.markdown(
                f"<div class='student-info'>{alumno['no_lista']}. {alumno['nombre']} {alumno['apellido']} — {alumno['matricula']}</div>",
                unsafe_allow_html=True
            )
        with col_a2:
            estado = alumno['estado_actual'].title()
            if st.button(f"📋 {estado}", key=f"estado_{alumno['id_estudiante']}"):
                st.toast(f"Estado de {alumno['nombre']} actualizado", icon="✅")
        with col_a3:
            if st.button("ℹ️ Detalles", key=f"info_{alumno['id_estudiante']}"):
                st.info(f"Información detallada de {alumno['nombre']} {alumno['apellido']}")

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
    st.warning("No hay alumnos registrados para este grupo.")

st.markdown("<hr>", unsafe_allow_html=True)




# 5 Mapa de asientos dinámico
st.markdown('<h2 class="section-title">🪑 Mapa de Asientos</h2>', unsafe_allow_html=True)

cols = 6  # puedes cambiarlo a 5 u 8 según el ancho que prefieras
total_alumnos = len(alumnos)
rows = math.ceil(total_alumnos / cols)

for i in range(rows):
    cols_seat = st.columns(cols)
    for j in range(cols):
        seat_num = i * cols + j + 1
        a = next((x for x in alumnos if x.get("no_lista") == seat_num), None)
        
        with cols_seat[j]:
            if a:
                estado = a.get("estado_actual", "").lower()
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

# 4 Resumen general (podrías obtenerlo de otro endpoint si lo implementas)
st.markdown('<h2 class="section-title">📊 Resumen General del Día</h2>', unsafe_allow_html=True)
col_r1, col_r2 = st.columns([1, 1])
with col_r1:
    st.markdown(f"""
    <div class="info-card">
        <h4 style="color: #2563eb;">📈 Estadísticas Generales</h4>
        <p><strong>Total de estudiantes:</strong> {total}</p>
        <p><strong>Presentes:</strong> {presentes}</p>
        <p><strong>Ausentes:</strong> {ausentes}</p>
        <p><strong>Justificantes:</strong> {justificantes}</p>
    </div>
    """, unsafe_allow_html=True)
with col_r2:
    fig2 = px.pie(pd.DataFrame([
        {"Estado": "Presentes", "Cantidad": presentes},
        {"Estado": "Ausentes", "Cantidad": ausentes},
        {"Estado": "Justificantes", "Cantidad": justificantes}
    ]), values="Cantidad", names="Estado", title="Resumen General del Día",
               color_discrete_sequence=['#2563eb', '#ef4444', '#f59e0b'])
    fig2.update_layout(font_family="Inter", title_font_size=16, title_font_color='#1f2937')
    st.plotly_chart(fig2, use_container_width=True)

# QR y footer
st.markdown("<hr>", unsafe_allow_html=True)
col_qr1, col_qr2 = st.columns([3, 1])
with col_qr1:
    st.markdown("""
    <div class="info-card">
        <h4 style="color: #2563eb;">📱 Código QR para Estudiantes</h4>
        <p>Los estudiantes pueden escanear el código QR para registrar su asistencia de forma autónoma.</p>
    </div>
    """, unsafe_allow_html=True)
with col_qr2:
    if st.button("📲 Generar QR"):
        st.switch_page("pages/generarqr.py")
        st.success("¡Código QR generado exitosamente!")
        st.info("Código válido por 30 minutos")
st.markdown("""
<div style="text-align: center; padding: 2rem 0; color: #6b7280; border-top: 1px solid #e5e7eb;">
    <p>© 2025 UA PREP. LÁZARO CARDENAS DEL RÍO - Sistema de Control</p>
</div>
""", unsafe_allow_html=True)