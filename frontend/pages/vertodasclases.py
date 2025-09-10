import streamlit as st
import datetime
import time
import requests

# Configuración de la página
st.set_page_config(
    page_title="Ver todas las clases",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# URL del backend
API_URL = "http://localhost:8000/clases/por-bloque"

# Función para llamar al backend
def obtener_clases_por_bloque(hora_inicio, hora_fin, dia):
    try:
        params = {
            "horaInicio": hora_inicio,
            "horaFin": hora_fin,
            "dia": dia.lower()
        }
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ Error al obtener clases: {e}")
        return []

# Definir bloques de horario
horariosMatutinos = [
    {'id': '1', 'nombre': 'Bloque 1', 'hora': '7:20:00 - 8:05:00', 'inicio': '7:20:00', 'fin': '8:05:00'},
    {'id': '2', 'nombre': 'Bloque 2', 'hora': '8:05:00 - 8:50:00', 'inicio': '8:05:00', 'fin': '8:50:00'},
    {'id': '3', 'nombre': 'Bloque 3', 'hora': '8:50:00 - 9:35:00', 'inicio': '8:50:00', 'fin': '9:35:00'},
    {'id': '4', 'nombre': 'Bloque 4', 'hora': '9:35:00 - 10:20:00', 'inicio': '9:35:00', 'fin': '10:20:00'},
    {'id': '5', 'nombre': 'Bloque 5', 'hora': '10:50:00 - 11:35:00', 'inicio': '10:50:00', 'fin': '11:35:00'},
    {'id': '6', 'nombre': 'Bloque 6', 'hora': '11:35:00 - 12:20:00', 'inicio': '11:35:00', 'fin': '12:20:00'},
    {'id': '7', 'nombre': 'Bloque 7', 'hora': '12:20:00 - 13:05:00', 'inicio': '12:20:00', 'fin': '13:05:00'}
]

horariosVespertinos = [
    {'id': '1', 'nombre': 'Bloque 1', 'hora': '13:35:00 - 14:20:00', 'inicio': '13:35:00', 'fin': '14:20:00'},
    {'id': '2', 'nombre': 'Bloque 2', 'hora': '14:20:00 - 15:05:00', 'inicio': '14:20:00', 'fin': '15:05:00'},
    {'id': '3', 'nombre': 'Bloque 3', 'hora': '15:05:00 - 15:50:00', 'inicio': '15:05:00', 'fin': '15:50:00'},
    {'id': '4', 'nombre': 'Bloque 4', 'hora': '15:50:00 - 16:35:00', 'inicio': '15:50:00', 'fin': '16:35:00'},
    {'id': '5', 'nombre': 'Blouqe 5', 'hora': '17:05:00 - 17:50:00', 'inicio': '17:05:00', 'fin': '17:50:00'},
    {'id': '6', 'nombre': 'Bloque 6', 'hora': '17:50:00 - 18:35:00', 'inicio': '17:50:00', 'fin': '18:35:00'},
    {'id': '7', 'nombre': 'Bloque 7', 'hora': '18:35:00 - 19:20:00', 'inicio': '19:35:00', 'fin': '19:20:00'}
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

# Cabecera
col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.image("assets/logo1.jpeg", width=80)
with col2:
    st.markdown("<h1 style='text-align: center;'>UA PREP. 'GRAL. LÁZARO CÁRDENAS DEL RÍO'</h1>", unsafe_allow_html=True)
with col3:
    st.image("assets/logo1.jpeg", width=80)

st.markdown("---")
fecha = datetime.datetime.now().strftime("%d/%m/%Y")
hora = datetime.datetime.now().strftime("%H:%M:%S")
st.write(f"📅 {fecha} - ⏰ {hora}")
st.write("👋 Bienvenido")

# Botón de volver al panel
if st.button("Volver al panel"):
    st.session_state.horaSeleccionada = None
    st.session_state.turnoSeleccionado = None
    st.session_state.gradoActual = None
    st.session_state.pausado = False
    st.session_state.tiempoEnPausa = 0
    st.session_state.clasesPorBloque = []
    st.rerun()

# Modo selección de horario
if not st.session_state.horaSeleccionada:
    st.header("Asistencia por Horario - Turno Matutino")
    for bloque in horariosMatutinos:
        if st.button(f"{bloque['nombre']} ({bloque['hora']})"):
            st.session_state.horaSeleccionada = bloque
            st.session_state.turnoSeleccionado = 'matutino'
            dia_actual = datetime.datetime.now().strftime("%A")
            clases = obtener_clases_por_bloque(bloque['inicio'], bloque['fin'], dia_actual)
            st.session_state.clasesPorBloque = clases
            st.rerun()

    st.header("Asistencia por Horario - Turno Vespertino")
    for bloque in horariosVespertinos:
        if st.button(f"{bloque['nombre']} ({bloque['hora']})"):
            st.session_state.horaSeleccionada = bloque
            st.session_state.turnoSeleccionado = 'vespertino'
            dia_actual = datetime.datetime.now().strftime("%A")
            clases = obtener_clases_por_bloque(bloque['inicio'], bloque['fin'], dia_actual)
            st.session_state.clasesPorBloque = clases
            st.rerun()

else:
    # Botón volver a horarios
    if st.button("← Volver a horarios"):
        st.session_state.horaSeleccionada = None
        st.session_state.gradoActual = None
        st.session_state.clasesPorBloque = []
        st.session_state.pausado = False
        st.session_state.tiempoEnPausa = 0
        st.rerun()

    bloque = st.session_state.horaSeleccionada
    if isinstance(bloque, dict):
        st.subheader(f"{bloque.get('nombre', 'Bloque desconocido')} - {bloque.get('hora', 'Hora desconocida')}")
    else:
        st.warning("⚠️ No se pudo cargar la información del bloque.")

    # Obtener grados únicos desde las clases
    grupos = [c['nombre_grupo'] for c in st.session_state.clasesPorBloque]
    grados_unicos = sorted({g.split(" ")[0] for g in grupos})  # Asumiendo "1A", "3B", etc.

    if not grados_unicos:
        st.warning("No hay clases registradas para este bloque.")
    else:
        # Mostrar botones por grado
        for grado in grados_unicos:
            if st.button(f"{grado}º semestre"):
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
            st.info(f"⏸️ Contador en pausa: {minutos} min {segundos} seg")

        # Mostrar clases del semestre seleccionado
        if st.session_state.gradoActual:
            grado = st.session_state.gradoActual
            st.markdown(f"### {grado}º Semestre")

            clases_filtradas = [
                c for c in st.session_state.clasesPorBloque
                if c['nombre_grupo'].startswith(grado)
            ]

            if not clases_filtradas:
                st.warning(":( No hay clases disponibles en este semestre por el momento.")
            else:
                for clase in clases_filtradas:
                    st.markdown(f"""
                    <div style='border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 6px;'>
                        <h4>📘 {clase['nombre_materia']}</h4>
                        <ul>
                            <li><strong>Grupo:</strong> {clase['nombre_grupo']}</li>
                            <li><strong>Profesor:</strong> {clase['nombre_profesor']}</li>
                            <li><strong>NRC:</strong> {clase['nrc']}</li>
                            <li><strong>Horario:</strong> {clase['hora_inicio']} - {clase['hora_fin']}</li>
                            <li><strong>Estudiantes:</strong> {clase['total_estudiantes']}</li>
                            <li><strong>✅ Presentes:</strong> {clase['presentes']}</li>
                            <li><strong>🟡 Justificantes:</strong> {clase['justificantes']}</li>
                            <li><strong>❌ Ausentes:</strong> {clase['ausentes']}</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
