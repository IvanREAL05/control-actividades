import streamlit as st
from datetime import datetime
import pandas as pd
import requests
import base64

# Configuración de la página
st.set_page_config(
    page_title="Cargar Datos",
    page_icon="📊",
    layout="wide"
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
    
    /* Info cards */
    .stAlert {
        background: linear-gradient(135deg, var(--light-blue) 0%, white 100%);
        border: 1px solid var(--primary-blue);
        border-radius: 8px;
        color: var(--dark-blue);
    }
    
    /* Divisores */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, var(--light-blue), transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

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
# Ruta base de tu API (ajústala si usas otro host o puerto)
API_BASE = "http://localhost:8000/api/importar"
# ---------- ESTADOS INICIALES ----------
if 'tipo_datos' not in st.session_state:
    st.session_state.tipo_datos = ""
if 'mostrar_form_nuevo' not in st.session_state:
    st.session_state.mostrar_form_nuevo = False
if 'nuevo_estudiante' not in st.session_state:
    st.session_state.nuevo_estudiante = {
        "matricula": "",
        "nombre": "",
        "apellido": "",
        "email": "",
        "grupo": ""
    }

# Simulaciones de datos
columnas_esperadas = {
    "estudiantes": ["matricula", "nombre", "apellido", "email", "grupo"],
    "profesores": ["nombre", "apellido", "email"],
    "grupos": ["nombre", "grado", "turno"],
    "clases": ["materia", "grupo", "profesor"],
    "materias": ["nombre", "codigo"]
}

imagenes_referencia = {
    "estudiantes": "https://via.placeholder.com/400x150?text=Excel+Estudiantes",
    "profesores": "https://via.placeholder.com/400x150?text=Excel+Profesores",
    "grupos": "https://via.placeholder.com/400x150?text=Excel+Grupos",
    "clases": "https://via.placeholder.com/400x150?text=Excel+Clases",
    "materias": "https://via.placeholder.com/400x150?text=Excel+Materias",
}

lista_grupos = [{"id_grupo": 1, "nombre": "Grupo A"}, {"id_grupo": 2, "nombre": "Grupo B"}]

# ---------- ENCABEZADO ----------
st.markdown("""
<div class="custom-header">
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 1rem;">
        <img src="data:image/jpeg;base64,{}" style="height: 60px; width: auto; object-fit: contain;" alt="Logo BUAP">
        <h1 class="header-title" style="margin: 0; flex: 1; text-align: center;">UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
        <img src="data:image/jpeg;base64,{}" style="height: 60px; width: auto; object-fit: contain;" alt="Logo Institución">
    </div>
</div>
""".format(
    base64.b64encode(open("assets/logo_buap.jpg", "rb").read()).decode(),
    base64.b64encode(open("assets/logo1.jpeg", "rb").read()).decode()
), unsafe_allow_html=True)

# Botón de volver al panel
col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
with col_back2:
    if st.button("🏠 Volver al panel principal", key="main_back"):
        st.switch_page("pages/panel.py")

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- FORMULARIO CARGA DE DATOS ----------
st.header("📥 Cargar datos al sistema")

# Selección de tipo de datos
tipo = st.selectbox("¿Qué tipo de datos deseas subir?", ["", "estudiantes", "profesores", "grupos", "clases", "materias"], key="tipo_datos")

# Mostrar botón para agregar nuevo estudiante
if tipo == "estudiantes":
    if st.button("Agregar Estudiante Nuevo"):
        st.session_state.mostrar_form_nuevo = True

# Formulario de estudiante nuevo
if st.session_state.mostrar_form_nuevo:
    st.subheader("➕ Agregar Estudiante Nuevo")

    st.session_state.nuevo_estudiante["matricula"] = st.text_input("Matrícula", value=st.session_state.nuevo_estudiante["matricula"])
    st.session_state.nuevo_estudiante["nombre"] = st.text_input("Nombre", value=st.session_state.nuevo_estudiante["nombre"])
    st.session_state.nuevo_estudiante["apellido"] = st.text_input("Apellido", value=st.session_state.nuevo_estudiante["apellido"])
    st.session_state.nuevo_estudiante["email"] = st.text_input("Correo Electrónico (opcional)", value=st.session_state.nuevo_estudiante["email"])
    st.session_state.nuevo_estudiante["grupo"] = st.selectbox("Grupo", [""] + [g["nombre"] for g in lista_grupos], index=0)

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("Guardar"):
            API_BASE = "http://localhost:8000"
            response = requests.post(f"{API_BASE}/api/estudiante/nuevo", json=st.session_state.nuevo_estudiante)
            if response.status_code == 200:
                st.success("✅ Estudiante agregado exitosamente.")
                st.session_state.mostrar_form_nuevo = False
                st.session_state.nuevo_estudiante = {"matricula": "", "nombre": "", "apellido": "", "email": "", "grupo": ""}
            else:
                st.error("❌ Error al agregar estudiante.")
    with col_cancel:
        if st.button("Cancelar"):
            st.session_state.mostrar_form_nuevo = False

# ---------- INSTRUCCIONES Y SUBIDA ----------
if tipo:
    st.markdown("### 📌 Instrucciones")
    st.markdown("1. Prepara un archivo Excel con las siguientes columnas:")

    for col in columnas_esperadas.get(tipo, []):
        st.markdown(f"- `{col}`")

    st.image(imagenes_referencia.get(tipo), caption=f"Ejemplo para {tipo}", width="stretch")
    st.markdown("2. El tamaño máximo permitido es 5MB.")
    st.markdown("3. Arrastra el archivo o haz clic para seleccionarlo.")
    st.markdown("4. Haz clic en 'Guardar Cambios' para subir los datos.")

    archivo = st.file_uploader("📁 Subir archivo Excel", type=["xlsx", "xls"])

    if archivo:
        try:
            df = pd.read_excel(archivo)
            columnas_validas = set(df.columns) >= set(columnas_esperadas[tipo])
            if not columnas_validas:
                st.error("❌ Las columnas del archivo no son válidas.")
            else:
                st.success("✅ Archivo válido. Puedes guardar los cambios.")
        except Exception as e:
            st.error(f"❌ Error al leer el archivo: {e}")
            columnas_validas = False
    else:
        columnas_validas = False

    # Botón para guardar los datos
    if st.button("Guardar Cambios", disabled=not archivo or not columnas_validas):
        try:
            tipo_actual = st.session_state.tipo_datos
            url = f"{API_BASE}/{tipo_actual}/archivo"

            # Prepara archivo como multipart/form-data
            file_data = {
                "file": (archivo.name, archivo.getvalue(), archivo.type)
            }

            # Enviar POST al backend
            response = requests.post(url, files=file_data)

            if response.status_code == 200:
                st.success(f"✅ {tipo_actual.capitalize()} importados correctamente.")
            else:
                error = response.json().get("detail", "Error desconocido")
                st.error(f"❌ Error al importar: {error}")

        except Exception as e:
            st.error(f"❌ Error al enviar el archivo: {e}")
    if st.button("Volver al Panel"):
        st.switch_page("pages/panel.py")  # Ruta de tu panel

