import streamlit as st
from datetime import datetime, date
import time
import requests


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

# ---------- ESTADOS INICIALES ----------
if 'aviso_success' not in st.session_state:
    st.session_state.aviso_success = False
if 'aviso_error' not in st.session_state:
    st.session_state.aviso_error = None

# ---------- ENCABEZADO ----------
st.markdown("""
<div class='crear-aviso-container'>
    <div class='section-title'>📝 Crear Nuevo Aviso Oficial</div>
""", unsafe_allow_html=True)

def normalizar_url(url):
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url

# ---------- FORMULARIO ----------
with st.form("form_aviso"):
    nombre_evento = st.text_input("Nombre del Evento", max_chars=255)
    fecha_evento = st.date_input("Fecha del Evento", value=date.today())
    descripcion = st.text_area("Descripción", height=150)
    enlace = st.text_input("Enlace (URL)", placeholder="https://ejemplo.com")

    col_guardar, col_cancelar = st.columns([1, 1])
    submitted = col_guardar.form_submit_button("Guardar Aviso")
    cancelado = col_cancelar.form_submit_button("Cancelar")

    if submitted:
        # Validación básica
        if not (nombre_evento.strip() and descripcion.strip() and enlace.strip()):
            st.session_state.aviso_error = "❌ Todos los campos son obligatorios."
            st.session_state.aviso_success = False
        else:
            try:
                aviso_data = {
                    "nombre_evento": nombre_evento.strip(),
                    "fecha": fecha_evento.isoformat(),  # 'YYYY-MM-DD'
                    "descripcion": descripcion.strip(),
                    "enlace": normalizar_url(enlace),
                }

                # Cambia si el backend está en otra dirección
                backend_url = "http://localhost:8000/api/avisos/"
                response = requests.post(backend_url, json=aviso_data)

                if response.status_code == 200:
                    result = response.json()
                    st.session_state.aviso_success = True
                    st.session_state.aviso_error = None
                    st.success("✅ Aviso creado exitosamente.")

                    # Muestra información del aviso recién creado
                    aviso = result.get("data", {})
                    st.markdown(f"**ID:** {aviso.get('id')}")
                    st.markdown(f"**Evento:** {aviso.get('nombre_evento')}")
                    st.markdown(f"**Fecha:** {aviso.get('fecha')}")
                    st.markdown(f"**Descripción:** {aviso.get('descripcion')}")
                    st.markdown(f"**Enlace:** [Ir al evento]({aviso.get('enlace')})")

                    # Redirigir después de unos segundos
                    time.sleep(3)
                    st.rerun()
                else:
                    error_msg = response.json().get("detail", "Error desconocido")
                    st.session_state.aviso_error = f"❌ {error_msg}"
                    st.session_state.aviso_success = False

            except Exception as e:
                st.session_state.aviso_error = f"🚨 Error al conectar con el backend: {e}"
                st.session_state.aviso_success = False

    if cancelado:
        # Limpia todos los campos y estados
        for key in ["aviso_success", "aviso_error"]:
            st.session_state.pop(key, None)
        st.rerun()

# ---------- MENSAJES ----------
if st.session_state.aviso_error:
    st.error(st.session_state.aviso_error)

st.markdown("</div>", unsafe_allow_html=True)