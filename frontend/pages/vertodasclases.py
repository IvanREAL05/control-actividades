import streamlit as st
import datetime
import time
import requests
import base64
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
        --success-green: #10b981;
        --warning-orange: #f59e0b;
        --danger-red: #ef4444;
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
        text-align: center;
    }
    
    .header-title {
        font-size: 1.8rem;
        font-weight: 700;
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
        width: 100%;
        margin-bottom: 0.5rem;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, var(--dark-blue) 0%, var(--primary-blue) 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
    }
    
    /* Botón de regreso */
    .back-button > button {
        background: linear-gradient(135deg, var(--gray-600) 0%, var(--gray-800) 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Botones de semestre */
    .semester-button > button {
        background: linear-gradient(135deg, var(--success-green) 0%, #059669 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 1rem 2rem !important;
        font-size: 1.1rem !important;
        margin-bottom: 0.75rem !important;
        width: 100% !important;
    }
    
    /* Tarjeta de clase */
    .class-card {
        background: white;
        border: 1px solid var(--gray-200);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        border-left: 4px solid var(--primary-blue);
    }
    
    .class-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transform: translateY(-1px);
    }
    
    .class-title {
        color: var(--primary-blue);
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .class-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.5rem;
        margin-top: 0.75rem;
    }
    
    .info-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0;
        color: var(--gray-600);
        font-weight: 500;
    }
    
    .info-value {
        color: var(--gray-800);
        font-weight: 600;
    }
    
    /* Estadísticas de asistencia */
    .attendance-stats {
        display: flex;
        justify-content: space-around;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--gray-200);
    }
    
    .stat-item {
        text-align: center;
        flex: 1;
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    
    .stat-present {
        color: var(--success-green);
    }
    
    .stat-justified {
        color: var(--warning-orange);
    }
    
    .stat-absent {
        color: var(--danger-red);
    }
    
    .stat-label {
        font-size: 0.8rem;
        color: var(--gray-600);
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Información de fecha y hora */
    .datetime-info {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid var(--primary-blue);
        font-weight: 500;
        color: var(--gray-800);
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Contador en pausa */
    .pause-counter {
        background: linear-gradient(135deg, var(--warning-orange) 0%, #d97706 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);
    }
    
    /* Secciones */
    .section-title {
        color: var(--dark-blue);
        font-size: 1.4rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, var(--light-blue) 0%, white 100%);
        border-radius: 8px;
        border-left: 4px solid var(--primary-blue);
    }
    
    /* Divisores */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(to right, transparent, var(--primary-blue), transparent);
        margin: 2rem 0;
    }
    
    /* Mensaje de advertencia */
    .warning-message {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--warning-orange);
        text-align: center;
        font-weight: 500;
        margin: 1rem 0;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main {
            padding: 0.5rem 1rem;
        }
        
        .class-info {
            grid-template-columns: 1fr;
        }
        
        .attendance-stats {
            flex-direction: column;
            gap: 1rem;
        }
        
        .datetime-info {
            flex-direction: column;
            text-align: center;
            gap: 0.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Ocultar menú y footer ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Configuración de la página
st.set_page_config(
    page_title="Ver todas las clases",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
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
st.sidebar.page_link("pages/generarqr_masivo.py", label="📦 QR Masivo")
st.sidebar.page_link("pages/justificantes.py", label="📑 Justificantes")
st.sidebar.page_link("pages/vertodasclases.py", label="📊 Ver todas las clases")
st.sidebar.page_link("pages/cargardatos.py", label="📊 Subir datos")
st.sidebar.page_link("app.py", label="🚪 Cerrar sesión")

# URL del backend actualizada
API_URL = "https://control-actividades.onrender.com/api/clases/por-bloque" 
DEBUG_URL = "https://control-actividades.onrender.com/api/clases/debug-dia"




# Función mejorada para llamar al backend
def obtener_clases_por_bloque(hora_inicio, hora_fin, dia):
    try:
        # Mapear días de inglés a español - CORREGIDO
        dias_mapping = {
            'Monday': 'Lunes',      # ⚠️ Esto está mal, debe ser Lunes
            'Tuesday': 'Martes', 
            'Wednesday': 'Miércoles',
            'Thursday': 'Jueves',
            'Friday': 'Viernes',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        
        dia_esp = dias_mapping.get(dia, dia)
        
        # 🔍 DEBUG: Mostrar parámetros enviados
        if st.sidebar.checkbox("Ver parámetros de búsqueda"):
            st.write("🔍 **Debug - Parámetros enviados:**")
            st.json({
                "horaInicio": hora_inicio,
                "horaFin": hora_fin,
                "dia": dia_esp,
                "dia_original": dia
            })
        
        params = {
            "horaInicio": hora_inicio,
            "horaFin": hora_fin,
            "dia": dia_esp
        }
        
        # 🔍 DEBUG: Verificar qué clases hay en ese día
        if st.sidebar.checkbox("Ver todas las clases del día"):
            try:
                debug_response = requests.get(f"{DEBUG_URL}/{dia_esp}")
                if debug_response.status_code == 200:
                    debug_data = debug_response.json()
                    st.write(f"🔍 **Debug - Clases disponibles en {dia_esp}:**")
                    if debug_data:
                        for clase in debug_data:
                            st.write(f"   - {clase['materia']} ({clase.get('grupo', 'N/A')}): {clase['hora_inicio']} - {clase['hora_fin']}")
                    else:
                        st.warning(f"❌ No hay clases registradas para {dia_esp}")
            except Exception as debug_e:
                st.error(f"Error en debug: {debug_e}")
        
        # Hacer la petición principal
        response = requests.get(API_URL, params=params, timeout=10)
        
        if st.sidebar.checkbox("Ver respuesta del servidor"):
            st.write(f"🌐 **Response Status:** {response.status_code}")
            st.write(f"🌐 **Response URL:** {response.url}")
        
        if response.status_code == 200:
            data = response.json()
            
            if st.sidebar.checkbox("Ver datos JSON completos"):
                st.write(f"📊 **Clases encontradas:** {len(data)}")
                if data:
                    st.json(data)
            
            return data
        else:
            st.error(f"❌ Error HTTP {response.status_code}: {response.text}")
            return []
            
    except requests.exceptions.Timeout:
        st.error("❌ Timeout: El servidor tardó mucho en responder")
        return []
    except requests.exceptions.ConnectionError:
        st.error("❌ Error de conexión: No se puede conectar al servidor")
        return []
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        return []

# Definir bloques de horario - CORREGIDOS para que coincidan con tu base de datos
horariosMatutinos = [
    # ⚠️ PROBLEMA: Tus bloques originales no coinciden con tu BD
    # BD: 07:20:00 - 08:50:00, pero tu bloque 1 era 07:20:00 - 08:05:00
    {'id': '1', 'nombre': 'Bloque 1', 'hora': '7:20:00 - 8:50:00', 'inicio': '07:20:00', 'fin': '08:50:00'},
    {'id': '2', 'nombre': 'Bloque 2', 'hora': '8:05:00 - 8:50:00', 'inicio': '08:05:00', 'fin': '08:50:00'},
    {'id': '3', 'nombre': 'Bloque 3', 'hora': '8:50:00 - 9:35:00', 'inicio': '08:50:00', 'fin': '09:35:00'},
    {'id': '4', 'nombre': 'Bloque 4', 'hora': '9:35:00 - 10:20:00', 'inicio': '09:35:00', 'fin': '10:20:00'},
    {'id': '5', 'nombre': 'Bloque 5', 'hora': '10:50:00 - 11:35:00', 'inicio': '10:50:00', 'fin': '11:35:00'},
    {'id': '6', 'nombre': 'Bloque 6', 'hora': '11:35:00 - 12:20:00', 'inicio': '11:35:00', 'fin': '12:20:00'},
    {'id': '7', 'nombre': 'Bloque 7', 'hora': '12:20:00 - 13:50:00', 'inicio': '12:20:00', 'fin': '13:50:00'}, # ⚠️ Corregido para coincidir con BD
]

horariosVespertinos = [
    {'id': '1', 'nombre': 'Bloque 1', 'hora': '13:35:00 - 14:20:00', 'inicio': '13:35:00', 'fin': '14:20:00'},
    {'id': '2', 'nombre': 'Bloque 2', 'hora': '14:20:00 - 15:05:00', 'inicio': '14:20:00', 'fin': '15:05:00'},
    {'id': '3', 'nombre': 'Bloque 3', 'hora': '15:05:00 - 15:50:00', 'inicio': '15:05:00', 'fin': '15:50:00'},
    {'id': '4', 'nombre': 'Bloque 4', 'hora': '15:50:00 - 16:35:00', 'inicio': '15:50:00', 'fin': '16:35:00'},
    {'id': '5', 'nombre': 'Bloque 5', 'hora': '17:05:00 - 17:50:00', 'inicio': '17:05:00', 'fin': '17:50:00'},
    {'id': '6', 'nombre': 'Bloque 6', 'hora': '17:50:00 - 18:35:00', 'inicio': '17:50:00', 'fin': '18:35:00'},
    {'id': '7', 'nombre': 'Bloque 7', 'hora': '18:35:00 - 19:20:00', 'inicio': '18:35:00', 'fin': '19:20:00'}
]

# Inicializar estado
if 'horaSeleccionada' not in st.session_state:
    st.session_state.horaSeleccionada = None
    st.session_state.turnoSeleccionado = None
    st.session_state.gradoActual = None
    st.session_state.pausado = False
    st.session_state.tiempoEnPausa = 0
    st.session_state.tiempoInicio = None
    st.session_state.clasesPorBloque = []

# Cabecera estilizada
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



# Botón de volver al panel
col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
with col_back2:
    if st.button("🏠 Volver al panel principal", key="main_back"):
        st.session_state.horaSeleccionada = None
        st.session_state.turnoSeleccionado = None
        st.session_state.gradoActual = None
        st.session_state.pausado = False
        st.session_state.tiempoEnPausa = 0
        st.session_state.clasesPorBloque = []
        st.switch_page("pages/panel.py")

st.markdown("---")

# Modo selección de horario
if not st.session_state.horaSeleccionada:
    st.markdown('<div class="section-title">🌅 Asistencia por Horario - Turno Matutino</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    for i, bloque in enumerate(horariosMatutinos):
        with col1 if i % 2 == 0 else col2:
            if st.button(f"🕐 {bloque['nombre']} ({bloque['hora']})", key=f"mat_{bloque['id']}"):
                st.session_state.horaSeleccionada = bloque
                st.session_state.turnoSeleccionado = 'matutino'
                dia_actual = datetime.datetime.now().strftime("%A")
                clases = obtener_clases_por_bloque(bloque['inicio'], bloque['fin'], dia_actual)
                st.session_state.clasesPorBloque = clases
                st.rerun()

    st.markdown('<div class="section-title">🌆 Asistencia por Horario - Turno Vespertino</div>', unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    for i, bloque in enumerate(horariosVespertinos):
        with col3 if i % 2 == 0 else col4:
            if st.button(f"🕐 {bloque['nombre']} ({bloque['hora']})", key=f"ves_{bloque['id']}"):
                st.session_state.horaSeleccionada = bloque
                st.session_state.turnoSeleccionado = 'vespertino'
                dia_actual = datetime.datetime.now().strftime("%A")
                clases = obtener_clases_por_bloque(bloque['inicio'], bloque['fin'], dia_actual)
                st.session_state.clasesPorBloque = clases
                st.rerun()

else:
    # Botón volver a horarios
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav2:
        if st.button("← Volver a selección de horarios", key="back_schedule"):
            st.session_state.horaSeleccionada = None
            st.session_state.gradoActual = None
            st.session_state.clasesPorBloque = []
            st.session_state.pausado = False
            st.session_state.tiempoEnPausa = 0
            st.rerun()

    # Mostrar información del bloque seleccionado
    bloque = st.session_state.horaSeleccionada
    if isinstance(bloque, dict):
        turno_emoji = "🌅" if st.session_state.turnoSeleccionado == 'matutino' else "🌆"
        st.markdown(f"""
        <div class="info-card">
            <h2 style="color: var(--primary-blue); margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                {turno_emoji} {bloque.get('nombre', 'Bloque desconocido')} - {bloque.get('hora', 'Hora desconocida')}
            </h2>
            <p style="margin: 0.5rem 0 0 0; color: var(--gray-600);">
                <strong>Turno:</strong> {st.session_state.turnoSeleccionado.title()}
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-message">⚠️ No se pudo cargar la información del bloque.</div>', unsafe_allow_html=True)

    # Obtener grados únicos desde las clases
    if st.session_state.clasesPorBloque:
        grupos = [c['nombre_grupo'] for c in st.session_state.clasesPorBloque]
        grados_unicos = sorted({g.split(" ")[0] for g in grupos})  # Asumiendo "1A", "3B", etc.
    else:
        grados_unicos = []

    if not grados_unicos:
        st.markdown('<div class="warning-message">📚 No hay clases registradas para este bloque en el día de hoy.</div>', unsafe_allow_html=True)
        
        # Mostrar las clases encontradas para debug
        if st.session_state.clasesPorBloque:
            st.write("🔍 **Clases encontradas pero sin grados reconocibles:**")
            for clase in st.session_state.clasesPorBloque:
                st.write(f"- {clase.get('nombre_materia', 'N/A')} - Grupo: {clase.get('nombre_grupo', 'N/A')}")
    else:
        st.markdown('<div class="section-title">📊 Seleccionar Semestre</div>', unsafe_allow_html=True)
        
        # Mostrar botones por grado en columnas
        cols = st.columns(3)
        for i, grado in enumerate(grados_unicos):
            with cols[i % 3]:
                if st.button(f"📖 {grado}º semestre", key=f"grado_{grado}"):
                    if st.session_state.gradoActual == grado:
                        st.session_state.pausado = not st.session_state.pausado
                        if st.session_state.pausado:
                            st.session_state.tiempoInicio = time.time()
                        else:
                            st.session_state.tiempoEnPausa += int(time.time() - st.session_state.tiempoInicio)
                    else:
                        st.session_state.gradoActual = grado
                        st.session_state.pausado = False
                        st.session_state.tiempoEnPausa = 0
                        st.session_state.tiempoInicio = None
                    st.rerun()

        # Mostrar tiempo en pausa si aplica
        if st.session_state.pausado:
            tiempo_total = int(time.time() - st.session_state.tiempoInicio) + st.session_state.tiempoEnPausa
            minutos = tiempo_total // 60
            segundos = tiempo_total % 60
            st.markdown(f"""
            <div class="pause-counter">
                ⏸️ Contador en pausa: {minutos} min {segundos} seg
            </div>
            """, unsafe_allow_html=True)

        # Mostrar clases del semestre seleccionado
        if st.session_state.gradoActual:
            grado = st.session_state.gradoActual
            st.markdown(f'<div class="section-title">📚 Clases del {grado}º Semestre</div>', unsafe_allow_html=True)

            clases_filtradas = [
                c for c in st.session_state.clasesPorBloque
                if c['nombre_grupo'].startswith(grado)
            ]

            if not clases_filtradas:
                st.markdown('<div class="warning-message">😔 No hay clases disponibles en este semestre por el momento.</div>', unsafe_allow_html=True)
            else:
                for clase in clases_filtradas:
                    # Calcular porcentajes para mejor visualización
                    total = clase.get('total_estudiantes', 0)
                    presentes = clase.get('presentes', 0)
                    justificantes = clase.get('justificantes', 0)
                    ausentes = clase.get('ausentes', 0)
                    
                    # Asegurar que ausentes se calcule correctamente
                    if ausentes == 0 and total > 0:
                        ausentes = total - presentes - justificantes
                    
                    porcentaje_presentes = (presentes / total * 100) if total > 0 else 0
                    porcentaje_justificantes = (justificantes / total * 100) if total > 0 else 0
                    porcentaje_ausentes = (ausentes / total * 100) if total > 0 else 0
                    
                    # Usar columnas de Streamlit para mejor compatibilidad
                    with st.container():
                        st.markdown(f"""
                        <div style="background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); border-left: 4px solid #2563eb;">
                            <h4 style="color: #2563eb; margin: 0 0 1rem 0;">📘 {clase.get('nombre_materia', 'Materia desconocida')}</h4>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Información en columnas
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**👥 Grupo:** {clase.get('nombre_grupo', 'N/A')}")
                            st.write(f"**👨‍🏫 Profesor:** {clase.get('nombre_profesor', 'N/A')}")
                            st.write(f"**🏷️ NRC:** {clase.get('nrc', 'N/A')}")
                            if clase.get('nombre_aula'):
                                st.write(f"**🏫 Aula:** {clase.get('nombre_aula', 'N/A')}")
                            
                        with col2:
                            hora_inicio = clase.get('hora_inicio', 'N/A')
                            hora_fin = clase.get('hora_fin', 'N/A')
                            st.write(f"**⏰ Horario:** {hora_inicio} - {hora_fin}")
                            st.write(f"**📊 Total Estudiantes:** {total}")
                        
                        # Estadísticas de asistencia
                        st.markdown("---")
                        col_stats1, col_stats2, col_stats3 = st.columns(3)
                        
                        with col_stats1:
                            st.markdown(f"""
                            <div style="text-align: center; padding: 1rem; background: #f0f9ff; border-radius: 8px;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: #10b981; margin-bottom: 0.25rem;">✅ {presentes}</div>
                                <div style="font-size: 0.8rem; color: #4b5563; font-weight: 500;">PRESENTES ({porcentaje_presentes:.1f}%)</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with col_stats2:
                            st.markdown(f"""
                            <div style="text-align: center; padding: 1rem; background: #fffbeb; border-radius: 8px;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: #f59e0b; margin-bottom: 0.25rem;">🟡 {justificantes}</div>
                                <div style="font-size: 0.8rem; color: #4b5563; font-weight: 500;">JUSTIFICANTES ({porcentaje_justificantes:.1f}%)</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with col_stats3:
                            st.markdown(f"""
                            <div style="text-align: center; padding: 1rem; background: #fef2f2; border-radius: 8px;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: #ef4444; margin-bottom: 0.25rem;">❌ {ausentes}</div>
                                <div style="font-size: 0.8rem; color: #4b5563; font-weight: 500;">AUSENTES ({porcentaje_ausentes:.1f}%)</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)

# 🚀 Auto-refresh cada 30 segundos si hay clases seleccionadas
if st.session_state.clasesPorBloque and not st.session_state.pausado:
    time.sleep(30)
    st.rerun()