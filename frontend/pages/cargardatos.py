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
        --red-500: #ef4444;
        --green-500: #22c55e;
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
    
    /* Tarjeta de estudiante */
    .student-card {
        background: white;
        border: 1px solid var(--gray-200);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .student-card h3 {
        color: var(--primary-blue);
        margin-top: 0;
        font-size: 1.25rem;
    }
    
    .student-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .info-item {
        padding: 0.5rem;
        background: var(--gray-50);
        border-radius: 6px;
    }
    
    .info-label {
        font-size: 0.875rem;
        color: var(--gray-600);
        font-weight: 500;
    }
    
    .info-value {
        font-size: 1rem;
        color: var(--gray-800);
        margin-top: 0.25rem;
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

# Rutas de la API
API_BASE = "http://localhost:8000/api/importar"
API_ESTUDIANTES = "http://localhost:8000/api/importar"
API_GRUPOS = "http://localhost:8000/api/grupos/lista"

# ---------- ESTADOS INICIALES ----------
if 'tipo_datos' not in st.session_state:
    st.session_state.tipo_datos = ""
if 'estudiante_seleccionado' not in st.session_state:
    st.session_state.estudiante_seleccionado = None
if 'modo_edicion' not in st.session_state:
    st.session_state.modo_edicion = False

# Simulaciones de datos
columnas_esperadas = {
    "estudiantes": ["matricula", "nombre", "apellido", "email", "grupo"],
    "profesores": ["nombre", "apellido"],
    "grupos": ["nombre", "grado", "turno"],
    "clases": ["materia", "grupo", "profesor"],
    "materias": ["nombre", "codigo"],
    "calificaciones": ["matricula", "nrc", "parcial_1", "parcial_2", "ordinario"]
}

imagenes_referencia = {
    "estudiantes": "assets/tabla-estudiante.png",
    "profesores": "assets/tabla-profesor.png",
    "grupos": "assets/tabla-grupo.png",
    "clases": "assets/tabla-clase.png",
    "materias": "assets/tabla-materia.png",
    "calificaciones": "assets/tabla-calificaciones.png"
}

# ---------- FUNCIONES AUXILIARES ----------
def obtener_grupos():
    """Obtiene la lista de grupos disponibles"""
    try:
        response = requests.get(API_GRUPOS)
        if response.status_code == 200:
            grupos = response.json()
            
            if not isinstance(grupos, list):
                return []
            
            if not grupos:
                return []
            
            if isinstance(grupos[0], dict) and 'id_grupo' in grupos[0] and 'nombre' in grupos[0]:
                return grupos
            
            return []
                
    except Exception as e:
        st.error(f"Error al obtener grupos: {e}")
        return []

def buscar_estudiante_por_matricula(matricula):
    """Busca un estudiante por matrícula"""
    try:
        response = requests.get(f"{API_ESTUDIANTES}/estudiante/buscar/matricula/{matricula}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error al buscar estudiante: {e}")
        return None

def editar_estudiante(id_estudiante, datos):
    """Edita la información de un estudiante"""
    try:
        response = requests.put(f"{API_ESTUDIANTES}/estudiante/editar/{id_estudiante}", json=datos)
        if response.status_code == 200:
            return True, "Estudiante actualizado correctamente"
        else:
            error = response.json().get("detail", "Error desconocido")
            return False, error
    except Exception as e:
        return False, f"Error al editar estudiante: {e}"

def eliminar_estudiante(id_estudiante):
    """Elimina un estudiante del sistema"""
    try:
        response = requests.delete(f"{API_ESTUDIANTES}/estudiante/eliminar/{id_estudiante}")
        if response.status_code == 200:
            return True, "Estudiante eliminado correctamente"
        else:
            error = response.json().get("detail", "Error desconocido")
            return False, error
    except Exception as e:
        return False, f"Error al eliminar estudiante: {e}"

def mostrar_tarjeta_estudiante(estudiante):
    """Muestra una tarjeta con la información del estudiante"""
    st.markdown(f"""
    <div class="student-card">
        <h3>👤 {estudiante['nombre']} {estudiante['apellido']}</h3>
        <div class="student-info">
            <div class="info-item">
                <div class="info-label">Matrícula</div>
                <div class="info-value">{estudiante['matricula']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Correo</div>
                <div class="info-value">{estudiante.get('correo', 'N/A')}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Grupo</div>
                <div class="info-value">{estudiante['nombre_grupo']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">No. Lista</div>
                <div class="info-value">{estudiante['no_lista']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Estado</div>
                <div class="info-value">{estudiante['estado_actual'].capitalize()}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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

# ---------- TABS PRINCIPALES ----------
tab1, tab2 = st.tabs(["📥 Cargar Datos", "🔧 Gestionar Estudiantes"])

# ==================== TAB 1: CARGAR DATOS ====================
with tab1:
    st.header("📥 Cargar datos al sistema")
    
    tipo = st.selectbox(
        "¿Qué tipo de datos deseas subir?", 
        ["", "estudiantes", "profesores", "grupos", "clases", "materias", "calificaciones"], 
        key="tipo_datos"
    )
    
    if tipo:
        st.markdown("### 📌 Instrucciones")
        st.markdown("1. Prepara un archivo Excel con las siguientes columnas:")

        for col in columnas_esperadas.get(tipo, []):
            st.markdown(f"- `{col}`")

        # Información adicional para calificaciones
        if tipo == "calificaciones":
            st.info("""
            **Notas importantes para calificaciones:**
            - `matricula` y `nrc` son obligatorios
            - Al menos una calificación debe estar presente (parcial_1, parcial_2 o ordinario)
            - Las calificaciones deben estar en el rango de 0 a 10
            - Si una calificación ya existe, será actualizada automáticamente
            """)

        # Mostrar imagen de referencia si existe
        if tipo in imagenes_referencia:
            try:
                st.image(imagenes_referencia.get(tipo), caption=f"Ejemplo para {tipo}", width='stretch')
            except:
                st.warning("⚠️ No se encontró la imagen de referencia para este tipo de datos.")

        st.markdown("2. El tamaño máximo permitido es 5MB.")
        st.markdown("3. Arrastra el archivo o haz clic para seleccionarlo.")
        st.markdown("4. Haz clic en 'Guardar Cambios' para subir los datos.")

        archivo = st.file_uploader("📁 Subir archivo Excel", type=["xlsx", "xls"])

        if archivo:
            try:
                df = pd.read_excel(archivo)
                columnas_archivo = set(df.columns)
                columnas_requeridas = set(columnas_esperadas[tipo])
                
                # Validación especial para calificaciones
                if tipo == "calificaciones":
                    columnas_obligatorias = {"matricula", "nrc"}
                    columnas_opcionales = {"parcial_1", "parcial_2", "ordinario"}
                    
                    # Verificar columnas obligatorias
                    faltantes_obligatorias = columnas_obligatorias - columnas_archivo
                    if faltantes_obligatorias:
                        st.error(f"❌ Faltan columnas obligatorias: {', '.join(faltantes_obligatorias)}")
                        columnas_validas = False
                    else:
                        # Verificar que al menos una columna opcional esté presente
                        tiene_calificaciones = bool(columnas_opcionales & columnas_archivo)
                        if not tiene_calificaciones:
                            st.error(f"❌ Debe incluir al menos una columna de calificaciones: {', '.join(columnas_opcionales)}")
                            columnas_validas = False
                        else:
                            st.success("✅ Archivo válido. Puedes guardar los cambios.")
                            columnas_validas = True
                            
                            # Mostrar vista previa
                            st.markdown("#### Vista previa de datos:")
                            st.dataframe(df.head(10), width='stretch')
                else:
                    # Validación estándar para otros tipos
                    columnas_validas = columnas_archivo >= columnas_requeridas
                    if not columnas_validas:
                        faltantes = columnas_requeridas - columnas_archivo
                        st.error(f"❌ Faltan las siguientes columnas: {', '.join(faltantes)}")
                    else:
                        st.success("✅ Archivo válido. Puedes guardar los cambios.")
                        st.markdown("#### Vista previa de datos:")
                        st.dataframe(df.head(10), width='stretch')
                        
            except Exception as e:
                st.error(f"❌ Error al leer el archivo: {e}")
                columnas_validas = False
        else:
            columnas_validas = False

        if st.button("💾 Guardar Cambios", disabled=not archivo or not columnas_validas):
            try:
                tipo_actual = st.session_state.tipo_datos
                url = f"{API_BASE}/{tipo_actual}/archivo"

                file_data = {
                    "file": (archivo.name, archivo.getvalue(), archivo.type)
                }

                with st.spinner(f"Subiendo {tipo_actual}..."):
                    response = requests.post(url, files=file_data)

                if response.status_code == 200:
                    resultado = response.json()
                    
                    # Mensaje especial para calificaciones con estadísticas
                    if tipo_actual == "calificaciones":
                        st.success(f"✅ Calificaciones procesadas correctamente")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Insertadas", resultado.get("calificaciones_insertadas", 0))
                        with col2:
                            st.metric("Actualizadas", resultado.get("calificaciones_actualizadas", 0))
                        with col3:
                            st.metric("Total", resultado.get("total_procesadas", 0))
                        
                        # Mostrar errores si existen
                        if resultado.get("errores") and len(resultado["errores"]) > 0:
                            with st.expander(f"⚠️ Ver errores ({resultado['total_errores']})"):
                                for error in resultado["errores"]:
                                    st.warning(f"- {error}")
                        
                        st.balloons()
                    else:
                        st.success(f"✅ {tipo_actual.capitalize()} importados correctamente.")
                        st.balloons()
                else:
                    error = response.json().get("detail", "Error desconocido")
                    st.error(f"❌ Error al importar: {error}")

            except Exception as e:
                st.error(f"❌ Error al enviar el archivo: {e}")

# ==================== TAB 2: GESTIONAR ESTUDIANTES ====================
with tab2:
    st.header("🔧 Gestionar Estudiantes")
    
    # Sección para agregar nuevo estudiante
    with st.expander("➕ Agregar Nuevo Estudiante", expanded=False):
        st.markdown("### Formulario de Nuevo Estudiante")
        lista_grupos = obtener_grupos()
        
        if not lista_grupos:
            st.error("❌ Error al cargar los grupos. Por favor, verifica que existan grupos en el sistema.")
        else:
            nombres_grupos = [g["nombre"] for g in lista_grupos]
            
            with st.form("form_nuevo_estudiante"):
                col1, col2 = st.columns(2)
                
                with col1:
                    matricula = st.text_input("Matrícula*", placeholder="Ej: 202112345")
                    nombre = st.text_input("Nombre*", placeholder="Ej: Juan")
                    correo = st.text_input("Correo Electrónico", placeholder="ejemplo@alumno.buap.mx")
                
                with col2:
                    apellido = st.text_input("Apellido*", placeholder="Ej: Pérez García")
                    grupo_nombre = st.selectbox("Grupo*", options=["Selecciona un grupo"] + nombres_grupos)
                
                submitted = st.form_submit_button("💾 Guardar Estudiante", width='stretch')
                
                if submitted:
                    if not matricula or not nombre or not apellido or grupo_nombre == "Selecciona un grupo":
                        st.error("❌ Por favor completa todos los campos obligatorios (*)")
                    else:
                        nuevo = {
                            "matricula": matricula,
                            "nombre": nombre,
                            "apellido": apellido,
                            "email": correo if correo else "",
                            "grupo": grupo_nombre
                        }
                        
                        try:
                            response = requests.post(f"{API_ESTUDIANTES}/nuevo", json=nuevo)
                            if response.status_code == 200:
                                st.success("✅ Estudiante agregado exitosamente y lista reordenada.")
                                st.balloons()
                            else:
                                error = response.json().get("detail", "Error desconocido")
                                st.error(f"❌ Error: {error}")
                        except Exception as e:
                            st.error(f"❌ Error al agregar estudiante: {e}")
    
    st.markdown("---")
    
    # ========== BÚSQUEDA Y GESTIÓN SIMPLIFICADA ==========
    st.markdown("### 🔍 Buscar Estudiante por Matrícula")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        matricula_buscar = st.text_input(
            "Ingresa la matrícula del estudiante:", 
            placeholder="Ej: 202112345",
            key="matricula_input"
        )
    with col2:
        st.write("")
        st.write("")
        buscar_btn = st.button("🔍 Buscar", width='stretch', type="primary")
    
    # Realizar búsqueda
    if buscar_btn and matricula_buscar:
        estudiante = buscar_estudiante_por_matricula(matricula_buscar)
        if estudiante:
            st.session_state.estudiante_seleccionado = estudiante
        else:
            st.warning("⚠️ No se encontró ningún estudiante con esa matrícula.")
            st.session_state.estudiante_seleccionado = None
    
    # ========== MOSTRAR ESTUDIANTE ENCONTRADO ==========
    if st.session_state.estudiante_seleccionado and not st.session_state.modo_edicion:
        st.markdown("---")
        st.subheader("📋 Estudiante Encontrado")
        
        estudiante = st.session_state.estudiante_seleccionado
        mostrar_tarjeta_estudiante(estudiante)
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✏️ Editar Información", width='stretch', type="primary"):
                st.session_state.modo_edicion = True
                st.rerun()
        
        with col2:
            if st.button("🗑️ Eliminar Estudiante", width='stretch', type="secondary"):
                st.session_state.confirmar_eliminar = True
                st.rerun()
    
    # ========== MODO EDICIÓN ==========
    if st.session_state.estudiante_seleccionado and st.session_state.modo_edicion:
        st.markdown("---")
        st.subheader("✏️ Editar Estudiante")
        
        est = st.session_state.estudiante_seleccionado
        lista_grupos = obtener_grupos()
        
        if not lista_grupos:
            st.error("❌ Error al cargar los grupos. No se puede editar el estudiante.")
        else:
            with st.form("form_editar_estudiante"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nueva_matricula = st.text_input("Matrícula", value=est['matricula'])
                    nuevo_nombre = st.text_input("Nombre", value=est['nombre'])
                    nuevo_correo = st.text_input("Correo", value=est.get('correo', ''))
                
                with col2:
                    nuevo_apellido = st.text_input("Apellido", value=est['apellido'])
                    
                    grupo_ids = [g["id_grupo"] for g in lista_grupos]
                    try:
                        indice_actual = grupo_ids.index(est['id_grupo'])
                    except ValueError:
                        indice_actual = 0
                    
                    nuevo_grupo = st.selectbox(
                        "Grupo", 
                        options=grupo_ids,
                        index=indice_actual,
                        format_func=lambda x: next((g["nombre"] for g in lista_grupos if g["id_grupo"] == x), "")
                    )
                    nuevo_estado = st.selectbox(
                        "Estado", 
                        ["activo", "inactivo", "egresado"], 
                        index=["activo", "inactivo", "egresado"].index(est['estado_actual'])
                    )
                
                col_save, col_cancel = st.columns(2)
                
                with col_save:
                    guardar = st.form_submit_button("💾 Guardar Cambios", width='stretch')
                
                with col_cancel:
                    cancelar = st.form_submit_button("❌ Cancelar", width='stretch')
                
                if guardar:
                    datos_edicion = {}
                    
                    if nueva_matricula != est['matricula']:
                        datos_edicion['matricula'] = nueva_matricula
                    if nuevo_nombre != est['nombre']:
                        datos_edicion['nombre'] = nuevo_nombre
                    if nuevo_apellido != est['apellido']:
                        datos_edicion['apellido'] = nuevo_apellido
                    if nuevo_correo != est.get('correo', ''):
                        datos_edicion['correo'] = nuevo_correo
                    if nuevo_grupo != est['id_grupo']:
                        datos_edicion['id_grupo'] = nuevo_grupo
                    if nuevo_estado != est['estado_actual']:
                        datos_edicion['estado_actual'] = nuevo_estado
                    
                    if datos_edicion:
                        exito, mensaje = editar_estudiante(est['id_estudiante'], datos_edicion)
                        if exito:
                            st.success(f"✅ {mensaje}")
                            st.session_state.estudiante_seleccionado = None
                            st.session_state.modo_edicion = False
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ {mensaje}")
                    else:
                        st.info("ℹ️ No se detectaron cambios.")
                
                if cancelar:
                    st.session_state.modo_edicion = False
                    st.rerun()
    
    # ========== CONFIRMACIÓN DE ELIMINACIÓN ==========
    if hasattr(st.session_state, 'confirmar_eliminar') and st.session_state.confirmar_eliminar:
        st.markdown("---")
        st.error("⚠️ CONFIRMACIÓN DE ELIMINACIÓN")
        
        est = st.session_state.estudiante_seleccionado
        
        st.warning(f"¿Estás seguro de que deseas eliminar a **{est['nombre']} {est['apellido']}** (Matrícula: {est['matricula']})?")
        st.warning("⚠️ Esta acción no se puede deshacer. El estudiante será eliminado permanentemente del sistema.")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🗑️ Sí, eliminar definitivamente", type="primary", width='stretch'):
                exito, mensaje = eliminar_estudiante(est['id_estudiante'])
                if exito:
                    st.success(f"✅ {mensaje}")
                    st.session_state.estudiante_seleccionado = None
                    st.session_state.confirmar_eliminar = False
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {mensaje}")
        
        with col2:
            if st.button("❌ No, cancelar", width='stretch'):
                st.session_state.confirmar_eliminar = False
                st.rerun()