import streamlit as st
from datetime import datetime

# ---------- ENCABEZADO / LOGOS ----------
col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.image("assets/logo1.jpeg", width=80)
with col2:
    st.markdown("## UA PREP. \"GRAL. LÁZARO CÁRDENAS DEL RÍO\"", help="Nombre de la institución")
with col3:
    st.image("assets/logo1.jpeg", width=80)

# ---------- BOTÓN DE CERRAR SESIÓN ----------
st.markdown("")
if st.button("Cerrar sesión"):
    st.switch_page("pages/app.py")  # Asegúrate que esta página exista

st.markdown("---")

# ---------- CONTENIDO PRINCIPAL ----------
st.markdown("### 🚧 En Construcción", unsafe_allow_html=True)

st.write("Sección donde se suben justificantes para las asistencias, se requiere subir documentos personales.")

# ---------- ALERTA TEMPORAL ----------
with st.container():
    st.markdown("#### 📋 Módulo de Justificantes")
    st.warning(
        "Temporalmente deshabilitado mientras se configura el servidor dedicado para el manejo seguro de documentos.",
        icon="⚠️"
    )

# ---------- TEXTO DE TRABAJO / LOADING ----------
with st.spinner("Trabajando en las mejoras..."):
    st.markdown("*Por favor, vuelve más tarde.*")

# ---------- BOTÓN PARA REGRESAR AL PANEL ----------
if st.button("← Regresar al Panel"):
    st.switch_page("pages/panel.py")  