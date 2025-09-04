import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Panel de Control - LCR", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

# --- Simulación de datos ---
clases = [
    {"id_clase": 1, "nombre_materia": "Matemáticas", "nrc": "12345", "nombre_grupo": "1A"},
    {"id_clase": 2, "nombre_materia": "Historia", "nrc": "67890", "nombre_grupo": "2B"},
    {"id_clase": 3, "nombre_materia": "Física", "nrc": "54321", "nombre_grupo": "3C"}
]

alumnos = [
    {"matricula": "A001", "nombre": "Juan", "apellido": "Pérez", "estado": "presente", "no_lista": 1},
    {"matricula": "A002", "nombre": "Ana", "apellido": "López", "estado": "ausente", "no_lista": 2},
    {"matricula": "A003", "nombre": "Luis", "apellido": "Ramírez", "estado": "justificante", "no_lista": 3},
    {"matricula": "A004", "nombre": "María", "apellido": "González", "estado": "presente", "no_lista": 4},
    {"matricula": "A005", "nombre": "Carlos", "apellido": "Mendoza", "estado": "presente", "no_lista": 5}
]

# --- Header personalizado ---
st.markdown("""
<div class="custom-header">
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="width: 60px;"></div>
        <h1 class="header-title">UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
        <div style="width: 60px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Barra superior de información ---
col_fecha, col_user, col_btn = st.columns([2, 2, 1])

with col_fecha:
    st.markdown(f"""
    <div class="datetime-info">
        📅 {datetime.now().strftime("%d/%m/%Y")}<br>
        🕐 {datetime.now().strftime("%H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)

with col_user:
    st.info("👋 Bienvenido, Profesor")

with col_btn:
    if st.button("🚪 Cerrar Sesión", type="secondary"):
        st.session_state.clear()
        st.success("Sesión cerrada correctamente")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Selector de clase ---
st.markdown('<h2 class="section-title">📘 Control de Asistencia por Clase</h2>', unsafe_allow_html=True)

clase_seleccionada = st.selectbox(
    "Selecciona una clase",
    [f"{c['nombre_materia']} - {c['nrc']} - {c['nombre_grupo']}" for c in clases],
    key="selector_clase"
)

# --- Botones de acción ---
col_acc1, col_acc2, col_acc3, col_acc4 = st.columns(4)
with col_acc1:
    st.button("📊 Ver Todas las Clases")
with col_acc2:
    if st.button("📢 Crear Nuevo Aviso"):
        st.switch_page("pages/crearaviso.py")
with col_acc3:
    st.button("📥 Cargar Datos")
with col_acc4:
    st.button("📝 Justificantes")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Estadísticas ---
st.markdown('<h2 class="section-title">📈 Estadísticas de la Clase</h2>', unsafe_allow_html=True)

presentes = sum(1 for a in alumnos if a["estado"] == "presente")
ausentes = sum(1 for a in alumnos if a["estado"] == "ausente")
justificantes = sum(1 for a in alumnos if a["estado"] == "justificante")
total = len(alumnos)

col_est1, col_est2, col_est3 = st.columns([1, 1, 2])

with col_est1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total}</div>
        <div class="metric-label">Total Alumnos</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{presentes}</div>
        <div class="metric-label">Presentes</div>
    </div>
    """, unsafe_allow_html=True)

with col_est2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{ausentes}</div>
        <div class="metric-label">Ausentes</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{justificantes}</div>
        <div class="metric-label">Justificantes</div>
    </div>
    """, unsafe_allow_html=True)

with col_est3:
    df_estadisticas = pd.DataFrame([
        {"Estado": "Presentes", "Cantidad": presentes},
        {"Estado": "Ausentes", "Cantidad": ausentes},
        {"Estado": "Justificantes", "Cantidad": justificantes}
    ])
    
    # Colores personalizados para el gráfico
    colors = ['#2563eb', '#ef4444', '#f59e0b']
    
    fig = px.pie(
        df_estadisticas, 
        values="Cantidad", 
        names="Estado", 
        title="Distribución de Asistencia",
        color_discrete_sequence=colors
    )
    
    fig.update_layout(
        font_family="Inter",
        title_font_size=16,
        title_font_color='#1f2937',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# --- Lista de alumnos ---
st.markdown('<h2 class="section-title">👨‍🎓 Lista de Alumnos</h2>', unsafe_allow_html=True)

for i, alumno in enumerate(alumnos):
    col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
    
    with col_a1:
        st.markdown(f"""
        <div class="student-info">
            {alumno['nombre']} {alumno['apellido']} — {alumno['matricula']}
        </div>
        """, unsafe_allow_html=True)
    
    with col_a2:
        estado = alumno['estado'].title()
        button_class = f"status-{alumno['estado']}"
        
        if st.button(f"📋 {estado}", key=f"estado_{alumno['matricula']}", help=f"Cambiar estado de {alumno['nombre']}"):
            st.toast(f"Estado de {alumno['nombre']} actualizado", icon="✅")
    
    with col_a3:
        if st.button("ℹ️ Detalles", key=f"info_{alumno['matricula']}", help=f"Ver información de {alumno['nombre']}"):
            st.info(f"Información detallada de {alumno['nombre']} {alumno['apellido']}")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Mapa de asientos ---
st.markdown('<h2 class="section-title">🪑 Mapa de Asientos</h2>', unsafe_allow_html=True)

st.markdown("### Distribución del Aula")
rows, cols = 5, 6

for i in range(rows):
    cols_seat = st.columns(cols)
    for j in range(cols):
        seat_number = i * cols + j + 1
        alumno_asiento = next((a for a in alumnos if a.get("no_lista") == seat_number), None)
        
        with cols_seat[j]:
            if alumno_asiento:
                estado_color = {
                    "presente": "🟢",
                    "ausente": "🔴", 
                    "justificante": "🟡"
                }.get(alumno_asiento["estado"], "⚪")
                
                if st.button(
                    f"{estado_color} {alumno_asiento['nombre'][0]}{alumno_asiento['apellido'][0]}", 
                    key=f"seat_{i}_{j}",
                    help=f"{alumno_asiento['nombre']} {alumno_asiento['apellido']} - {alumno_asiento['estado'].title()}"
                ):
                    st.info(f"Asiento {seat_number}: {alumno_asiento['nombre']} {alumno_asiento['apellido']}")
            else:
                st.button("⚪ ---", key=f"empty_seat_{i}_{j}", disabled=True, help="Asiento vacío")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Resumen General ---
st.markdown('<h2 class="section-title">📊 Resumen General del Día</h2>', unsafe_allow_html=True)

col_r1, col_r2 = st.columns([1, 1])

with col_r1:
    st.markdown("""
    <div class="info-card">
        <h4 style="color: #2563eb; margin: 0 0 1rem 0;">📈 Estadísticas Generales</h4>
        <p><strong>Total de estudiantes:</strong> 120</p>
        <p><strong>Asistencia promedio:</strong> 85%</p>
        <p><strong>Clases del día:</strong> 8</p>
        <p><strong>Última actualización:</strong> Hace 5 minutos</p>
    </div>
    """, unsafe_allow_html=True)

with col_r2:
    df_general = pd.DataFrame([
        {"Estado": "Presentes", "Cantidad": 90},
        {"Estado": "Ausentes", "Cantidad": 20},
        {"Estado": "Justificantes", "Cantidad": 10}
    ])
    
    fig2 = px.pie(
        df_general, 
        values="Cantidad", 
        names="Estado", 
        title="Resumen General del Día",
        color_discrete_sequence=['#2563eb', '#ef4444', '#f59e0b']
    )
    
    fig2.update_layout(
        font_family="Inter",
        title_font_size=16,
        title_font_color='#1f2937'
    )
    
    st.plotly_chart(fig2, use_container_width=True)

# --- Footer con QR ---
st.markdown("<hr>", unsafe_allow_html=True)

col_qr1, col_qr2 = st.columns([3, 1])

with col_qr1:
    st.markdown("""
    <div class="info-card">
        <h4 style="color: #2563eb; margin: 0 0 0.5rem 0;">📱 Código QR para Estudiantes</h4>
        <p>Los estudiantes pueden escanear el código QR para registrar su asistencia de forma autónoma.</p>
    </div>
    """, unsafe_allow_html=True)

with col_qr2:
    if st.button("📲 Generar QR", help="Generar código QR para autoregistro"):
        st.switch_page("pages/generarqr.py")
        st.success("¡Código QR generado exitosamente!")
        st.info("Código válido por 30 minutos")

# Footer
st.markdown("""
<div style="text-align: center; padding: 2rem 0; color: #6b7280; border-top: 1px solid #e5e7eb; margin-top: 2rem;">
    <p>© 2025 UA PREP. LÁZARO CARDENAS DEL RÍO - Sistema de Control</p>
</div>
""", unsafe_allow_html=True)