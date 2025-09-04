import streamlit as st
from datetime import datetime
import time

# ---------- CONFIGURACIÓN DE LA PÁGINA ----------
st.set_page_config(page_title="Crear Aviso", layout="wide")

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

    .cabecera-panel {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .logo-nombre {
        display: flex;
        align-items: center;
        gap: 15px;
    }

    .logo, .logoU {
        height: 60px;
    }

    .bienvenida {
        text-align: right;
    }

    .fecha-hora {
        font-size: 14px;
    }

    .crear-aviso-container {
        background: white;
        padding: 2rem 3rem;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #2563eb;
        margin-top: 20px;
        width: 100%;
    }

    .stTextInput > div > input,
    .stDateInput > div,
    .stTextArea > div > textarea {
        border-radius: 8px;
        border: 2px solid #dbeafe;
        padding: 0.75rem;
        font-family: 'Inter', sans-serif;
        transition: border-color 0.2s ease;
    }

    .stTextInput > div > input:focus,
    .stDateInput > div:focus-within,
    .stTextArea > div > textarea:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
        outline: none;
    }

    .stButton > button {
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

    .stButton > button:hover {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
    }

    .btn-cancel {
        background: #ef4444;
        color: white;
        padding: 0.5rem 1rem;
        text-decoration: none;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 500;
    }

    .btn-cancel:hover {
        background: #dc2626;
    }

    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1e40af;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------- CABECERA ----------
col1, col2 = st.columns([4, 1])

with col1:
    st.markdown("""
    <div class="cabecera-panel">
        <div class="logo-nombre">
            <img src="assets/logo1.jpeg" class="logo" />
            <h3>UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h3>
            <img src="assets/logo1.jpeg" class="logoU" />
        </div>
    """, unsafe_allow_html=True)

with col2:
    now = datetime.now()
    fecha = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M:%S")
    st.markdown(f"""
    <div class="bienvenida">
        <div class="fecha-hora">
            <p>📅 {fecha}</p>
            <p>🕐 {hora}</p>
        </div>
        <p>Bienvenido</p>
        <a href="/" class="btn-cancel">Cerrar sesión</a>
    </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- FORMULARIO ----------
st.markdown("""
<div class='crear-aviso-container'>
    <div class='section-title'>📝 Crear Nuevo Aviso Oficial</div>
""", unsafe_allow_html=True)
# Estados del formulario
success = False
error = None

# Formulario
with st.form("form_aviso"):
    nombre_evento = st.text_input("Nombre del Evento", max_chars=255)
    fecha_evento = st.date_input("Fecha del Evento")
    descripcion = st.text_area("Descripción", height=150)
    enlace = st.text_input("Enlace (URL)", placeholder="https://ejemplo.com")

    col_guardar, col_cancelar = st.columns([1, 1])
    submitted = col_guardar.form_submit_button("Guardar Aviso")
    cancelado = col_cancelar.form_submit_button("Cancelar")

    if submitted:
        if not (nombre_evento and descripcion and enlace):
            error = "Todos los campos son obligatorios."
        else:
            success = True
            # Aquí podrías guardar el aviso en base de datos o archivo
            # save_aviso(nombre_evento, fecha_evento, descripcion, enlace)

    if cancelado:
        st.experimental_rerun()

# ---------- MENSAJES ----------
if success:
    st.success("✅ Aviso creado exitosamente. Redirigiendo...")
    time.sleep(2)
    st.experimental_rerun()

if error:
    st.error(f"❌ {error}")

st.markdown("</div>", unsafe_allow_html=True)
