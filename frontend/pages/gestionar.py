"""
Gestión de datos: borrado lógico de grupos y alumnos + papelera.

Página temporal para limpiar el sistema entre ciclos mientras se construye
el CRUD definitivo. Nada se borra de verdad: todo se marca como eliminado
y se puede restaurar desde la pestaña Papelera.
"""

import streamlit as st
import requests
import base64
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"
BACKEND_URL = "https://control-actividades.onrender.com"


def load_image_base64(image_name):
    try:
        image_path = ASSETS_DIR / image_name
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.warning(f"⚠️ Imagen {image_name} no encontrada")
        return ""


# ---------- CONFIGURACIÓN DE LA PÁGINA ----------
st.set_page_config(
    page_title="Gestionar datos",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main {
        padding: 1rem 4rem;
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
    }

    .custom-header {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
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

    .section-title {
        color: #1e40af;
        font-size: 1.25rem;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
    }

    .stButton > button, .stDownloadButton > button {
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

    .stButton > button:hover, .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
    }

    /* Los botones marcados como primary son los destructivos */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #b91c1c 0%, #dc2626 100%);
        box-shadow: 0 2px 4px rgba(220, 38, 38, 0.25);
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #991b1b 0%, #b91c1c 100%);
        box-shadow: 0 4px 8px rgba(220, 38, 38, 0.35);
    }

    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #dbeafe, transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------- PROTECCIÓN DE ACCESO ----------
if "usuario" not in st.session_state:
    st.warning("⚠️ Debes iniciar sesión primero")
    st.switch_page("app.py")
    st.stop()

usuario = st.session_state["usuario"]
usuario_nombre = usuario.get("nombre_completo") or usuario.get("usuario_login") or "sistema"

# ---------- CABECERA ----------
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

col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
with col_back2:
    if st.button("🏠 Volver al panel principal", key="main_back"):
        st.switch_page("pages/panel.py")

# ---------- MENÚ LATERAL ----------
st.sidebar.title("Menú")
st.sidebar.page_link("pages/panel.py", label="🏠 Panel Principal")
st.sidebar.page_link("pages/generarqr.py", label="🔑 Generar QR")
st.sidebar.page_link("pages/generarqr_masivo.py", label="📦 QR Masivo")
st.sidebar.page_link("pages/justificantes.py", label="📑 Justificantes")
st.sidebar.page_link("pages/vertodasclases.py", label="📊 Ver todas las clases")
st.sidebar.page_link("pages/cargardatos.py", label="📊 Subir datos")
st.sidebar.page_link("pages/gestionar.py", label="🗂️ Gestionar datos")
st.sidebar.page_link("app.py", label="🚪 Cerrar sesión")

st.markdown("<hr>", unsafe_allow_html=True)


# =====================================================================
# LLAMADAS AL BACKEND
# =====================================================================
@st.cache_data(ttl=60)
def obtener_grupos():
    resp = requests.get(f"{BACKEND_URL}/api/grupos/lista", timeout=15)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=60)
def obtener_alumnos(id_grupo: int):
    resp = requests.get(f"{BACKEND_URL}/api/estudiantes/grupo/{id_grupo}", timeout=15)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def obtener_impacto(id_grupo: int):
    resp = requests.get(f"{BACKEND_URL}/api/papelera/grupo/{id_grupo}/impacto", timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


@st.cache_data(ttl=30)
def obtener_papelera_grupos():
    resp = requests.get(f"{BACKEND_URL}/api/papelera/grupos", timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


@st.cache_data(ttl=30)
def obtener_papelera_alumnos():
    resp = requests.get(f"{BACKEND_URL}/api/papelera/estudiantes", timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


@st.cache_data(ttl=30)
def obtener_resumen_papelera():
    resp = requests.get(f"{BACKEND_URL}/api/papelera/resumen", timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


def limpiar_cache():
    """Invalida todas las listas después de borrar o restaurar."""
    obtener_grupos.clear()
    obtener_alumnos.clear()
    obtener_impacto.clear()
    obtener_papelera_grupos.clear()
    obtener_papelera_alumnos.clear()
    obtener_resumen_papelera.clear()


def llamar_backend(metodo: str, ruta: str, payload=None):
    """POST/GET al backend devolviendo (ok, datos_o_mensaje)."""
    try:
        resp = requests.request(metodo, f"{BACKEND_URL}{ruta}", json=payload, timeout=30)
    except Exception as e:
        return False, f"No se pudo conectar con el servidor: {e}"

    if resp.status_code == 200:
        return True, resp.json()

    try:
        detalle = resp.json().get("detail", resp.text)
    except Exception:
        detalle = resp.text or f"Error {resp.status_code}"
    return False, detalle


# =====================================================================
# DIÁLOGOS DE CONFIRMACIÓN
# =====================================================================
@st.dialog("⚠️ Confirmar borrado de grupo")
def confirmar_borrar_grupo(grupo_nombre: str, id_grupo: int, impacto: dict):
    st.markdown(f"Vas a enviar a la papelera el grupo **{grupo_nombre}** y con él:")
    st.markdown(
        f"- **{impacto.get('alumnos', 0)}** alumnos\n"
        f"- **{impacto.get('clases', 0)}** clases\n"
        f"- **{impacto.get('horarios', 0)}** horarios"
    )
    st.info("Nada se borra de la base de datos. Todo se puede restaurar desde la pestaña 🗑️ Papelera.")

    texto = st.text_input(f"Escribe **{grupo_nombre}** para confirmar", key="confirmar_texto_grupo")

    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button(
            "🗑️ Sí, enviar a la papelera",
            type="primary",
            disabled=texto.strip() != grupo_nombre,
            use_container_width=True,
        ):
            ok, res = llamar_backend(
                "POST",
                f"/api/papelera/grupo/{id_grupo}/eliminar",
                {"usuario": usuario_nombre},
            )
            limpiar_cache()
            st.session_state["resultado_accion"] = (ok, res)
            st.rerun()
    with col_cancel:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


@st.dialog("⚠️ Confirmar borrado de alumnos")
def confirmar_borrar_alumnos(seleccionados: list, reordenar: bool):
    st.markdown(f"Vas a enviar a la papelera **{len(seleccionados)}** alumno(s):")
    for a in seleccionados[:10]:
        st.markdown(f"- {a['matricula']} — {a['apellido']} {a['nombre']}")
    if len(seleccionados) > 10:
        st.markdown(f"- … y {len(seleccionados) - 10} más")

    if reordenar:
        st.info("Se renumerará la lista del grupo para que no queden huecos en el mapa de asientos.")
    else:
        st.info("Se conservarán los números de lista actuales (quedarán huecos).")

    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button("🗑️ Sí, enviar a la papelera", type="primary", use_container_width=True):
            ok, res = llamar_backend(
                "POST",
                "/api/papelera/estudiantes/eliminar",
                {
                    "ids": [a["id_estudiante"] for a in seleccionados],
                    "usuario": usuario_nombre,
                    "reordenar": reordenar,
                },
            )
            limpiar_cache()
            st.session_state["resultado_accion"] = (ok, res)
            st.rerun()
    with col_cancel:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


# ---------- Mensaje de la última acción ----------
if "resultado_accion" in st.session_state:
    ok, res = st.session_state.pop("resultado_accion")
    if ok:
        st.success(f"✅ {res.get('message', 'Operación completada')}")
        omitidos = (res.get("data") or {}).get("omitidos") or []
        if omitidos:
            with st.expander(f"⚠️ {len(omitidos)} alumno(s) no se pudieron restaurar"):
                for o in omitidos:
                    st.text(o)
    else:
        st.error(f"🚨 {res}")


# =====================================================================
# PESTAÑAS
# =====================================================================
try:
    resumen_papelera = obtener_resumen_papelera()
except Exception:
    resumen_papelera = {}

etiqueta_papelera = "🗑️ Papelera"
total_en_papelera = (resumen_papelera.get("grupos", 0) or 0) + (resumen_papelera.get("estudiantes", 0) or 0)
if total_en_papelera:
    etiqueta_papelera = f"🗑️ Papelera ({total_en_papelera})"

tab_grupos, tab_alumnos, tab_papelera = st.tabs(["🏫 Borrar grupo", "👨‍🎓 Borrar alumnos", etiqueta_papelera])

try:
    grupos = obtener_grupos()
except Exception as e:
    grupos = []
    st.error(f"🚨 No se pudo obtener la lista de grupos: {e}")


# =====================================================================
# PESTAÑA 1: BORRAR GRUPO
# =====================================================================
with tab_grupos:
    st.markdown('<div class="section-title">🏫 Enviar un grupo a la papelera</div>', unsafe_allow_html=True)
    st.caption(
        "Al borrar un grupo también se marcan como eliminados sus alumnos, sus clases y sus horarios. "
        "Todo se puede restaurar después."
    )

    if not grupos:
        st.info("No hay grupos activos.")
    else:
        opciones = {
            f"{g['nombre']} ({g.get('turno', '')} {g.get('nivel', '') or ''})".strip(): g["id_grupo"]
            for g in grupos
        }
        etiqueta = st.selectbox("Selecciona el grupo a borrar", list(opciones.keys()), key="grupo_borrar")
        id_grupo_sel = opciones[etiqueta]
        nombre_grupo_sel = next(g["nombre"] for g in grupos if g["id_grupo"] == id_grupo_sel)

        try:
            impacto = obtener_impacto(id_grupo_sel)
        except Exception as e:
            impacto = {}
            st.error(f"🚨 No se pudo calcular el impacto: {e}")

        if impacto:
            c1, c2, c3 = st.columns(3)
            c1.metric("👨‍🎓 Alumnos", impacto.get("alumnos", 0))
            c2.metric("📚 Clases", impacto.get("clases", 0))
            c3.metric("🕐 Horarios", impacto.get("horarios", 0))

            st.markdown("<hr>", unsafe_allow_html=True)

            if st.button(f"🗑️ Borrar grupo {nombre_grupo_sel}", type="primary", key="btn_borrar_grupo"):
                # Limpiar la confirmación anterior: si no, al cancelar y volver
                # a abrir el diálogo el nombre quedaría ya escrito.
                st.session_state.pop("confirmar_texto_grupo", None)
                confirmar_borrar_grupo(nombre_grupo_sel, id_grupo_sel, impacto)


# =====================================================================
# PESTAÑA 2: BORRAR ALUMNOS
# =====================================================================
with tab_alumnos:
    st.markdown('<div class="section-title">👨‍🎓 Enviar alumnos a la papelera</div>', unsafe_allow_html=True)
    st.caption("Marca uno o varios alumnos. Sirve igual para borrar a uno solo o a todo el grupo.")

    if not grupos:
        st.info("No hay grupos activos.")
    else:
        opciones_a = {
            f"{g['nombre']} ({g.get('turno', '')} {g.get('nivel', '') or ''})".strip(): g["id_grupo"]
            for g in grupos
        }
        etiqueta_a = st.selectbox("Grupo", list(opciones_a.keys()), key="grupo_alumnos")
        id_grupo_a = opciones_a[etiqueta_a]

        try:
            alumnos = obtener_alumnos(id_grupo_a)
        except Exception as e:
            alumnos = []
            st.error(f"🚨 No se pudo obtener a los alumnos: {e}")

        if not alumnos:
            st.info("Este grupo no tiene alumnos activos.")
        else:
            busqueda = st.text_input(
                "🔍 Filtrar por matrícula o nombre",
                key="busqueda_alumnos",
                placeholder="Deja vacío para ver a todos",
            ).strip().lower()

            visibles = [
                a for a in alumnos
                if not busqueda
                or busqueda in str(a.get("matricula", "")).lower()
                or busqueda in f"{a.get('nombre', '')} {a.get('apellido', '')}".lower()
            ]

            if not visibles:
                st.warning("Ningún alumno coincide con el filtro.")
            else:
                marcar_todos = st.checkbox(
                    f"Marcar los {len(visibles)} alumnos visibles",
                    key=f"marcar_todos_{id_grupo_a}",
                )

                df = pd.DataFrame([
                    {
                        "Borrar": marcar_todos,
                        "No.": a.get("no_lista"),
                        "Matrícula": a.get("matricula"),
                        "Alumno": f"{a.get('apellido', '')} {a.get('nombre', '')}".strip(),
                        "Correo": a.get("correo") or "",
                        "id": a["id_estudiante"],
                    }
                    for a in visibles
                ])

                editado = st.data_editor(
                    df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Borrar": st.column_config.CheckboxColumn("Borrar", width="small"),
                        "No.": st.column_config.NumberColumn("No.", width="small", disabled=True),
                        "Matrícula": st.column_config.TextColumn("Matrícula", disabled=True),
                        "Alumno": st.column_config.TextColumn("Alumno", width="large", disabled=True),
                        "Correo": st.column_config.TextColumn("Correo", disabled=True),
                        "id": None,
                    },
                    key=f"editor_alumnos_{id_grupo_a}_{marcar_todos}",
                )

                ids_marcados = set(editado.loc[editado["Borrar"], "id"].tolist())
                seleccionados = [a for a in visibles if a["id_estudiante"] in ids_marcados]

                st.markdown("<hr>", unsafe_allow_html=True)

                reordenar = st.checkbox(
                    "Renumerar la lista del grupo después de borrar",
                    value=True,
                    key="reordenar_alumnos",
                    help=(
                        "Recomendado: evita huecos en el mapa de asientos. Desactívalo si ya se "
                        "repartieron listas impresas con la numeración actual."
                    ),
                )

                if seleccionados:
                    st.warning(f"Vas a borrar **{len(seleccionados)}** alumno(s) de {etiqueta_a}.")
                    if st.button(
                        f"🗑️ Enviar {len(seleccionados)} alumno(s) a la papelera",
                        type="primary",
                        key="btn_borrar_alumnos",
                    ):
                        confirmar_borrar_alumnos(seleccionados, reordenar)
                else:
                    st.info("Marca la casilla **Borrar** de los alumnos que quieras eliminar.")


# =====================================================================
# PESTAÑA 3: PAPELERA
# =====================================================================
with tab_papelera:
    st.markdown('<div class="section-title">🗑️ Papelera</div>', unsafe_allow_html=True)
    st.caption("Todo lo eliminado sigue guardado en la base de datos y se puede restaurar desde aquí.")

    if resumen_papelera:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("🏫 Grupos", resumen_papelera.get("grupos", 0))
        p2.metric("👨‍🎓 Alumnos", resumen_papelera.get("estudiantes", 0))
        p3.metric("📚 Clases", resumen_papelera.get("clases", 0))
        p4.metric("🕐 Horarios", resumen_papelera.get("horarios", 0))

    if st.button("🔄 Actualizar", key="refrescar_papelera"):
        limpiar_cache()
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Grupos eliminados ----------
    st.markdown("#### 🏫 Grupos eliminados")
    try:
        grupos_borrados = obtener_papelera_grupos()
    except Exception as e:
        grupos_borrados = []
        st.error(f"🚨 No se pudo consultar la papelera: {e}")

    if not grupos_borrados:
        st.info("No hay grupos en la papelera.")
    else:
        for g in grupos_borrados:
            col_info, col_btn = st.columns([4, 1])
            with col_info:
                fecha = str(g.get("fecha_eliminado") or "")[:19].replace("T", " ")
                st.markdown(
                    f"**{g['nombre']}** ({g.get('turno', '')} {g.get('nivel', '') or ''}) — "
                    f"{g.get('alumnos', 0)} alumnos, {g.get('clases', 0)} clases  \n"
                    f"<span style='color:#6b7280;font-size:0.85rem'>Borrado el {fecha} por {g.get('eliminado_por') or '—'}</span>",
                    unsafe_allow_html=True,
                )
            with col_btn:
                if st.button("♻️ Restaurar", key=f"restaurar_grupo_{g['id_grupo']}"):
                    ok, res = llamar_backend("POST", f"/api/papelera/grupo/{g['id_grupo']}/restaurar")
                    limpiar_cache()
                    st.session_state["resultado_accion"] = (ok, res)
                    st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Alumnos eliminados ----------
    st.markdown("#### 👨‍🎓 Alumnos eliminados individualmente")
    st.caption("Los alumnos que cayeron al borrar un grupo se restauran junto con su grupo.")

    try:
        alumnos_borrados = obtener_papelera_alumnos()
    except Exception as e:
        alumnos_borrados = []
        st.error(f"🚨 No se pudo consultar la papelera: {e}")

    if not alumnos_borrados:
        st.info("No hay alumnos sueltos en la papelera.")
    else:
        df_papelera = pd.DataFrame([
            {
                "Restaurar": False,
                "Matrícula": a.get("matricula"),
                "Alumno": f"{a.get('apellido', '')} {a.get('nombre', '')}".strip(),
                "Grupo": a.get("grupo") or "—",
                "Borrado el": str(a.get("fecha_eliminado") or "")[:19].replace("T", " "),
                "Por": a.get("eliminado_por") or "—",
                "id": a["id_estudiante"],
            }
            for a in alumnos_borrados
        ])

        editado_papelera = st.data_editor(
            df_papelera,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Restaurar": st.column_config.CheckboxColumn("Restaurar", width="small"),
                "Matrícula": st.column_config.TextColumn("Matrícula", disabled=True),
                "Alumno": st.column_config.TextColumn("Alumno", width="large", disabled=True),
                "Grupo": st.column_config.TextColumn("Grupo", disabled=True),
                "Borrado el": st.column_config.TextColumn("Borrado el", disabled=True),
                "Por": st.column_config.TextColumn("Por", disabled=True),
                "id": None,
            },
            key="editor_papelera",
        )

        ids_restaurar = editado_papelera.loc[editado_papelera["Restaurar"], "id"].tolist()

        if ids_restaurar:
            if st.button(f"♻️ Restaurar {len(ids_restaurar)} alumno(s)", key="btn_restaurar_alumnos"):
                ok, res = llamar_backend(
                    "POST",
                    "/api/papelera/estudiantes/restaurar",
                    {"ids": [int(i) for i in ids_restaurar]},
                )
                limpiar_cache()
                st.session_state["resultado_accion"] = (ok, res)
                st.rerun()
        else:
            st.info("Marca la casilla **Restaurar** de los alumnos que quieras recuperar.")

st.markdown("""
<div style="text-align: center; padding: 2rem 0; color: #6b7280; border-top: 1px solid #e5e7eb;">
    <p>© 2025 UA PREP. LÁZARO CARDENAS DEL RÍO - Sistema de Control</p>
</div>
""", unsafe_allow_html=True)
