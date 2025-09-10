import streamlit as st
from datetime import datetime
import pandas as pd
import requests
import io

# Ruta base de tu API (ajústala si usas otro host o puerto)
API_BASE = "http://localhost:8000/api/importar"
# ---------- ESTADOS INICIALES ----------
if 'tipo_datos' not in st.session_state:
    st.session_state.tipo_datos = ""
if '            mostrar_form_nuevo' not in st.session_state:
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
col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.image("assets/logo1.jpeg", width=80)
with col2:
    st.markdown("""<div class="custom-header">
    <div style="display: flex; align-items: center; justify-content: center;">
        <h1 class="header-title">UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
    </div>
    </div>""", unsafe_allow_html=True)
with col3:
    st.image("assets/logo1.jpeg", width=80)

col_fecha, col_saludo, col_btn = st.columns([1, 2, 1])
with col_fecha:
    st.write(datetime.now().strftime("%d/%m/%Y"))
    st.write(datetime.now().strftime("%H:%M:%S"))

with col_saludo:
    st.markdown("**Bienvenido**")

with col_btn:
    if st.button("Cerrar sesión"):
        st.switch_page("pages/app.py")  

st.markdown("---")

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

    st.image(imagenes_referencia.get(tipo), caption=f"Ejemplo para {tipo}", use_container_width=True)
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

