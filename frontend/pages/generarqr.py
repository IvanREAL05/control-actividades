import streamlit as st
from datetime import datetime
import qrcode
from io import BytesIO
import base64

# ---------- CONFIGURACIÓN DE LA PÁGINA ----------
st.set_page_config(page_title="Generar QR", layout="wide")

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

    .logo {
        height: 60px;
    }

    .bienvenida {
        text-align: right;
    }

    .fecha-hora {
        font-size: 14px;
    }

    .generadorqr-main-content {
        background: white;
        padding: 2rem 3rem;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #2563eb;
        margin-top: 20px;
        width: 100%;
    }

    .generadorqr-input input {
        border-radius: 8px;
        border: 2px solid #dbeafe;
        padding: 0.75rem;
        font-family: 'Inter', sans-serif;
        width: 100%;
        transition: border-color 0.2s ease;
    }

    .generadorqr-input input:focus {
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

    .generadorqr-error-message {
        color: #dc2626;
        font-weight: bold;
        margin-top: 10px;
    }

    .generadorqr-nombre-alumno {
        font-weight: 600;
        margin-top: 20px;
        font-size: 18px;
        color: #1e40af;
    }

    .generadorqr-download-link {
        display: inline-block;
        margin-top: 10px;
        text-decoration: none;
        color: #2563eb;
        font-weight: 600;
    }

    .generadorqr-download-link:hover {
        color: #1e40af;
    }
</style>
""", unsafe_allow_html=True)

# ---------- ENCABEZADO ----------
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("""
    <div class="cabecera-panel">
        <div class="logo-nombre">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Logo_UANL.svg/2048px-Logo_UANL.svg.png" class="logo" />
            <h3>UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h3>
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
        <a href="/" class="generadorqr-download-link">Cerrar sesión</a>
    </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- CONTENIDO PRINCIPAL ----------
st.markdown("""
<div class='generadorqr-main-content'>
    <div class='section-title'>📷 Generar QR por Matrícula</div>
""", unsafe_allow_html=True)

matricula = st.text_input("Ingrese matrícula", placeholder="Ej: 12345678", max_chars=15)

# ---------- ESTADOS ----------
if 'loading' not in st.session_state:
    st.session_state.loading = False
if 'qr_image' not in st.session_state:
    st.session_state.qr_image = None
if 'nombre_alumno' not in st.session_state:
    st.session_state.nombre_alumno = None
if 'error' not in st.session_state:
    st.session_state.error = None

# ---------- LÓGICA DE GENERACIÓN ----------
if st.button("Generar QR", disabled=st.session_state.loading):
    st.session_state.loading = True
    st.session_state.qr_image = None
    st.session_state.nombre_alumno = None
    st.session_state.error = None

    if matricula.strip() == "":
        st.session_state.error = "⚠️ Por favor, ingrese una matrícula válida."
    else:
        # Simula una base de datos
        base_datos_mock = {
            "12345": "Juan Pérez",
            "67890": "Ana López",
            "54321": "Carlos Martínez"
        }

        nombre = base_datos_mock.get(matricula.strip())

        if nombre:
            st.session_state.nombre_alumno = nombre

            # Generar QR
            qr = qrcode.make(f"Matrícula: {matricula} | Alumno: {nombre}")
            buffered = BytesIO()
            qr.save(buffered, format="PNG")
            st.session_state.qr_image = buffered.getvalue()
        else:
            st.session_state.error = "🚫 Matrícula no encontrada en el sistema."

    st.session_state.loading = False
    st.experimental_rerun()

# ---------- RESULTADOS ----------
if st.session_state.error:
    st.markdown(f"<p class='generadorqr-error-message'>{st.session_state.error}</p>", unsafe_allow_html=True)

if st.session_state.nombre_alumno and not st.session_state.error:
    st.markdown(f"<p class='generadorqr-nombre-alumno'>Alumno: {st.session_state.nombre_alumno}</p>", unsafe_allow_html=True)

if st.session_state.qr_image:
    st.image(st.session_state.qr_image, caption="QR generado", width=200)

    b64 = base64.b64encode(st.session_state.qr_image).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="qr_{matricula}.png" class="generadorqr-download-link">📥 Descargar QR</a>'
    st.markdown(href, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
