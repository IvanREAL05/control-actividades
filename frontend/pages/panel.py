import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Panel de Control", layout="wide")

# --- Simulación de datos (luego conectarás con tu backend) ---
clases = [
    {"id_clase": 1, "nombre_materia": "Matemáticas", "nrc": "12345", "nombre_grupo": "1A"},
    {"id_clase": 2, "nombre_materia": "Historia", "nrc": "67890", "nombre_grupo": "2B"}
]

alumnos = [
    {"matricula": "A001", "nombre": "Juan", "apellido": "Pérez", "estado": "presente"},
    {"matricula": "A002", "nombre": "Ana", "apellido": "López", "estado": "ausente"},
    {"matricula": "A003", "nombre": "Luis", "apellido": "Ramírez", "estado": "justificante"}
]

# --- Cabecera ---
col1, col2, col3 = st.columns([1,3,1])
with col1:
    st.image("assets/logo_buap.jpg", width=80)
with col2:
    st.markdown("<h2 style='text-align:center;'>UA PREP. \"GRAL. LÁZARO CÁRDENAS DEL RÍO\"</h2>", unsafe_allow_html=True)
with col3:
    st.image("assets/logo_buap.jpg", width=80)

col_fecha, col_user, col_btn = st.columns([2,2,1])
with col_fecha:
    st.write(datetime.now().strftime("%d/%m/%Y"))
    st.write(datetime.now().strftime("%H:%M:%S"))
with col_user:
    st.info("Bienvenido 👋")
with col_btn:
    if st.button("Cerrar sesión 🚪"):
        st.session_state.clear()
        st.switch_page("app.py")

st.markdown("---")

# --- Selector de clase ---
st.subheader("📘 Control de Asistencia por Clase")
clase_seleccionada = st.selectbox(
    "Selecciona una clase",
    [f"{c['nombre_materia']} - {c['nrc']} - {c['nombre_grupo']}" for c in clases]
)

col_acc1, col_acc2, col_acc3, col_acc4 = st.columns(4)
with col_acc1:
    st.button("📊 Ver todas las clases")
with col_acc2:
    st.button("📢 Crear nuevo aviso")
with col_acc3:
    st.button("📥 Cargar datos")
with col_acc4:
    st.button("📝 Justificantes")

# --- Estadísticas ---
st.subheader("📈 Estadísticas de la clase")
df_estadisticas = pd.DataFrame([
    {"estado": "Presentes", "valor": sum(1 for a in alumnos if a["estado"] == "presente")},
    {"estado": "Ausentes", "valor": sum(1 for a in alumnos if a["estado"] == "ausente")},
    {"estado": "Justificantes", "valor": sum(1 for a in alumnos if a["estado"] == "justificante")}
])

col_est1, col_est2 = st.columns([1,2])
with col_est1:
    st.metric("Total alumnos", len(alumnos))
    st.metric("Presentes", df_estadisticas.loc[df_estadisticas.estado == "Presentes", "valor"].values[0])
    st.metric("Ausentes", df_estadisticas.loc[df_estadisticas.estado == "Ausentes", "valor"].values[0])
with col_est2:
    fig = px.pie(df_estadisticas, values="valor", names="estado", title="Distribución asistencia")
    st.plotly_chart(fig, use_container_width=True)

# --- Lista de alumnos ---
st.subheader("👨‍🎓 Lista de alumnos")
for alumno in alumnos:
    col_a1, col_a2, col_a3 = st.columns([3,1,1])
    with col_a1:
        st.write(f"{alumno['nombre']} {alumno['apellido']} — {alumno['matricula']}")
    with col_a2:
        estado = alumno['estado']
        if st.button(f"{estado}", key=alumno["matricula"]):
            # Aquí podrías actualizar el estado vía API
            st.toast(f"Estado de {alumno['nombre']} cambiado")
    with col_a3:
        st.button("ℹ️ Info", key=f"info_{alumno['matricula']}")

st.markdown("---")

# --- Resumen General ---
st.subheader("📊 Resumen General")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.metric("Total alumnos", 120)
    st.metric("Asistencia promedio", "85%")
with col_r2:
    df_general = pd.DataFrame([
        {"estado": "Presentes", "valor": 90},
        {"estado": "Ausentes", "valor": 20},
        {"estado": "Justificantes", "valor": 10}
    ])
    fig2 = px.pie(df_general, values="valor", names="estado", title="Resumen general")
    st.plotly_chart(fig2, use_container_width=True)

# --- Mapa de asientos (ejemplo simple con grid) ---
st.subheader("🪑 Mapa de Asientos")
rows, cols = 5, 6
for i in range(rows):
    cols_list = st.columns(cols)
    for j in range(cols):
        alumno = next((a for a in alumnos if a.get("no_lista") == i*cols + j + 1), None)
        if alumno:
            cols_list[j].button(f"{alumno['nombre'][0]}", key=f"seat_{i}_{j}")
        else:
            cols_list[j].markdown(" ")

st.markdown("---")
st.button("📲 Generar QR")
