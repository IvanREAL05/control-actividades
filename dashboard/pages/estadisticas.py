# dashboard/pages/tabla_dashboard.py
import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import json

st.set_page_config(
    page_title="Tabla en Tiempo Real",
    layout="wide",
    page_icon="📋"
)

# Verificar ID de clase
id_clase = st.session_state.get("id_clase", None)

if not id_clase:
    st.warning("⚠️ No se encontró un ID de clase. Regresa al inicio.")
    if st.button("← Volver al inicio"):
        st.switch_page("app.py")
    st.stop()
st.write("🔍 DEBUG - Session State:")
st.write({
    "login_exitoso": st.session_state.get("login_exitoso"),
    "id_clase": st.session_state.get("id_clase"),
    "id_profesor": st.session_state.get("id_profesor"),
    "nombre_profesor": st.session_state.get("nombre_profesor"),
})

st.write("🔍 DEBUG - Query Params:")
st.write(dict(st.query_params))
# =============================================
# ESTILOS CSS
# =============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Quicksand', sans-serif !important;
    }
    
    .main { 
        background-color: #f0f4f8; 
    }
    
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .live-indicator {
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 25px;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
        z-index: 9999;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
</style>
""", unsafe_allow_html=True)

# =============================================
# CABECERA
# =============================================
try:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); 
                padding: 30px 40px; 
                border-radius: 20px; 
                margin-bottom: 35px;
                box-shadow: 0 8px 25px rgba(30, 64, 175, 0.35);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap: wrap;">
            <img src="data:image/jpeg;base64,{base64.b64encode(open('assets/logo_buap.jpg','rb').read()).decode()}" 
                 height="75" style="border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
            <div style="flex: 1; text-align: center; padding: 0 25px;">
                <h1 style="color: white; margin: 0; font-size: 32px; font-weight: 700; 
                           text-shadow: 2px 2px 4px rgba(0,0,0,0.2);">
                    UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"
                </h1>
                <p style="color: #e0e7ff; margin: 10px 0 0 0; font-size: 18px; font-weight: 600;">
                    📋 Tabla de Asistencias y Actividades - Clase {id_clase}
                </p>
            </div>
            <img src="data:image/jpeg;base64,{base64.b64encode(open('assets/logo1.jpeg','rb').read()).decode()}" 
                 height="75" style="border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
        </div>
    </div>
    """, unsafe_allow_html=True)
except FileNotFoundError:
    st.title(f"📋 Tabla de Clase {id_clase}")

st.markdown("""
<div class="live-indicator">
    🔴 EN VIVO
</div>
""", unsafe_allow_html=True)

# =============================================
# CARGAR DATOS INICIALES
# =============================================
@st.cache_data(ttl=300)
def obtener_datos_iniciales(id_clase):
    try:
        response = requests.get(
            f"http://localhost:8000/api/tabla/{id_clase}/datos",
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None

datos = obtener_datos_iniciales(id_clase)

if not datos or not datos.get('estudiantes'):
    st.warning("⚠️ No hay estudiantes registrados en esta clase.")
    st.stop()

# Extraer datos
clase_info = datos.get('clase', {})
actividades = datos.get('actividades', [])
estudiantes = datos.get('estudiantes', [])

# Convertir a JSON para JavaScript
datos_json = json.dumps(datos)

# =============================================
# GENERAR HTML CON WEBSOCKET
# =============================================
# Generar headers dinámicos de actividades
actividades_headers = "".join([
    f'<th class="act-header">{act["nombre"]}</th>' 
    for act in actividades
])

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Quicksand', sans-serif;
        }}

        body {{
            background: transparent;
            padding: 20px;
        }}

        .info-bar {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .info-item {{
            text-align: center;
        }}

        .info-label {{
            font-size: 12px;
            color: #6b7280;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}

        .info-value {{
            font-size: 24px;
            font-weight: 700;
            color: #1e40af;
        }}

        .table-container {{
            background: white;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            min-width: 800px;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}

        th {{
            color: white;
            padding: 16px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }}

        th.act-header {{
            text-align: center;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        }}

        th:first-child {{
            border-top-left-radius: 10px;
        }}

        th:last-child {{
            border-top-right-radius: 10px;
        }}

        tbody tr {{
            transition: all 0.3s ease;
            border-bottom: 1px solid #e5e7eb;
        }}

        tbody tr:hover {{
            background: #f9fafb;
        }}

        td {{
            padding: 16px 12px;
            color: #374151;
            font-size: 14px;
        }}

        td.act-cell {{
            text-align: center;
        }}

        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
        }}

        .badge-presente {{
            background: #d1fae5;
            color: #065f46;
        }}

        .badge-retardo {{
            background: #fef3c7;
            color: #92400e;
        }}

        .badge-ausente {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .badge-justificante {{
            background: #dbeafe;
            color: #1e40af;
        }}

        .badge-pendiente {{
            background: #f3f4f6;
            color: #6b7280;
        }}

        .badge-entregado {{
            background: #d1fae5;
            color: #065f46;
        }}

        .row-updating {{
            animation: highlightRow 0.8s ease;
        }}

        @keyframes highlightRow {{
            0%, 100% {{ background: white; }}
            50% {{ background: #fef3c7; }}
        }}

        .ws-status {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
            z-index: 9999;
        }}

        .ws-status.disconnected {{
            background: #ef4444;
        }}
    </style>
</head>
<body>
    <!-- Barra de información -->
    <div class="info-bar">
        <div class="info-item">
            <div class="info-label">Materia</div>
            <div class="info-value" id="nombre-materia">-</div>
        </div>
        <div class="info-item">
            <div class="info-label">Grupo</div>
            <div class="info-value" id="nombre-grupo">-</div>
        </div>
        <div class="info-item">
            <div class="info-label">Total Estudiantes</div>
            <div class="info-value" id="total-estudiantes">0</div>
        </div>
        <div class="info-item">
            <div class="info-label">Presentes</div>
            <div class="info-value" style="color: #10b981;" id="total-presentes">0</div>
        </div>
        <div class="info-item">
            <div class="info-label">Actividades Hoy</div>
            <div class="info-value" style="color: #3b82f6;" id="total-actividades">0</div>
        </div>
    </div>

    <!-- Tabla principal -->
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Grupo</th>
                    <th>Nombre</th>
                    <th>Matrícula</th>
                    <th>Asistencia de Hoy</th>
                    <th>Hora</th>
                    {actividades_headers}
                </tr>
            </thead>
            <tbody id="tabla-body">
                <tr><td colspan="100" style="text-align:center; padding: 30px;">Cargando datos...</td></tr>
            </tbody>
        </table>
    </div>

    <div class="ws-status" id="ws-status">Conectando...</div>

    <script>
        console.log('🚀 Iniciando tabla dinámica...');

        // ===============================
        // DATOS INICIALES
        // ===============================
        const datosIniciales = {datos_json};
        const ID_CLASE = {id_clase};
        
        const claseInfo = datosIniciales.clase;
        const actividades = datosIniciales.actividades;
        const estudiantesMap = new Map();
        
        datosIniciales.estudiantes.forEach(est => {{
            estudiantesMap.set(est.id_estudiante, est);
        }});

        console.log('📦 Cargados', estudiantesMap.size, 'estudiantes');
        console.log('📝 Actividades:', actividades.length);
        console.log('🔍 IDs de actividades:', actividades.map(a => ({{ id: a.id, tipo: typeof a.id, nombre: a.nombre }})));

        // Actualizar info superior
        document.getElementById('nombre-materia').textContent = claseInfo.materia;
        document.getElementById('nombre-grupo').textContent = claseInfo.grupo;
        document.getElementById('total-actividades').textContent = actividades.length;

        const estadoMap = {{
            'presente': {{ badge: 'badge-presente', emoji: '✅', texto: 'Presente' }},
            'retardo': {{ badge: 'badge-retardo', emoji: '⏰', texto: 'Retardo' }},
            'ausente': {{ badge: 'badge-ausente', emoji: '❌', texto: 'Ausente' }},
            'justificante': {{ badge: 'badge-justificante', emoji: '📝', texto: 'Justificante' }},
            'pendiente': {{ badge: 'badge-pendiente', emoji: '⚪', texto: 'Pendiente' }}
        }};

        // ===============================
        // RENDERIZADO
        // ===============================
        function renderizarTabla() {{
            const tbody = document.getElementById('tabla-body');
            tbody.innerHTML = '';
            
            estudiantesMap.forEach((estudiante, id) => {{
                const row = crearFila(estudiante, id);
                tbody.appendChild(row);
            }});
            
            actualizarEstadisticas();
        }}

        function crearFila(estudiante, id) {{
            const tr = document.createElement('tr');
            tr.setAttribute('data-id', id);
            
            const estado = estadoMap[estudiante.asistencia] || estadoMap['pendiente'];
            
            // ✅ CORRECCIÓN: Generar celdas comparando IDs correctamente
            let actividadesCells = '';
            
            actividades.forEach(act => {{
                // ✅ Convertir ambos IDs a string para comparación confiable
                const actIdStr = String(act.id);
                const estadoAct = estudiante.actividades && estudiante.actividades[actIdStr] 
                    ? estudiante.actividades[actIdStr] 
                    : 'pendiente';
                
                const badgeClass = estadoAct === 'entregado' ? 'badge-entregado' : 'badge-pendiente';
                const emoji = estadoAct === 'entregado' ? '✅' : '⚪';
                const texto = estadoAct === 'entregado' ? 'Entregado' : 'Pendiente';
                
                actividadesCells += `
                    <td class="act-cell" data-act-id="${{actIdStr}}">
                        <span class="badge ${{badgeClass}}">
                            ${{emoji}} ${{texto}}
                        </span>
                    </td>
                `;
            }});
            
            tr.innerHTML = `
                <td>${{estudiante.grupo}}</td>
                <td><strong>${{estudiante.nombre_completo}}</strong></td>
                <td>${{estudiante.matricula}}</td>
                <td>
                    <span class="badge ${{estado.badge}}">
                        ${{estado.emoji}} ${{estado.texto}}
                    </span>
                </td>
                <td>${{estudiante.hora_entrada || '-'}}</td>
                ${{actividadesCells}}
            `;
            
            return tr;
        }}

        function actualizarEstadisticas() {{
            let total = 0, presentes = 0;
            
            estudiantesMap.forEach(estudiante => {{
                total++;
                if (estudiante.asistencia === 'presente') presentes++;
            }});
            
            document.getElementById('total-estudiantes').textContent = total;
            document.getElementById('total-presentes').textContent = presentes;
        }}

        renderizarTabla();

        // ===============================
        // WEBSOCKET
        // ===============================
        let ws;
        let reconnectAttempts = 0;
        const wsStatus = document.getElementById('ws-status');

        function conectarWebSocket() {{
            console.log('🔄 Conectando WebSocket...');
            wsStatus.textContent = 'Conectando...';
            wsStatus.classList.add('disconnected');

            ws = new WebSocket('ws://localhost:8000/ws/tabla/{id_clase}');

            ws.onopen = () => {{
                console.log('✅ WebSocket conectado');
                wsStatus.textContent = '🟢 Conectado';
                wsStatus.classList.remove('disconnected');
                reconnectAttempts = 0;
            }};

            ws.onmessage = (event) => {{
                try {{
                    const mensaje = JSON.parse(event.data);
                    console.log('📩 Mensaje recibido:', mensaje);
                    procesarMensaje(mensaje);
                }} catch (error) {{
                    console.error('❌ Error:', error);
                }}
            }};

            ws.onerror = (error) => {{
                console.error('❌ Error WebSocket:', error);
            }};

            ws.onclose = () => {{
                console.log('🔴 WebSocket cerrado');
                wsStatus.textContent = '🔴 Desconectado';
                wsStatus.classList.add('disconnected');
                
                if (reconnectAttempts < 5) {{
                    reconnectAttempts++;
                    setTimeout(conectarWebSocket, Math.min(1000 * reconnectAttempts, 5000));
                }}
            }};
        }}

        function procesarMensaje(mensaje) {{
            console.log('🔍 Tipo de mensaje:', mensaje.tipo || mensaje.evento);
            
            if (mensaje.tipo === 'asistencia' || mensaje.evento) {{
                actualizarAsistencia(mensaje.data || mensaje);
            }} else if (mensaje.tipo === 'actividad') {{
                console.log('📝 Procesando actividad:', {{
                    id_actividad: mensaje.data.id_actividad,
                    tipo: typeof mensaje.data.id_actividad,
                    matricula: mensaje.data.matricula
                }});
                actualizarActividad(mensaje.data);
            }}
        }}

        function actualizarAsistencia(data) {{
            const idEstudiante = data.id_estudiante;
            
            if (estudiantesMap.has(idEstudiante)) {{
                const estudiante = estudiantesMap.get(idEstudiante);
                estudiante.asistencia = data.estado;
                estudiante.hora_entrada = data.hora || '';
                
                console.log(`✅ Asistencia: ${{estudiante.nombre_completo}} -> ${{data.estado}}`);
                
                renderizarFila(idEstudiante, true);
                actualizarEstadisticas();
            }}
        }}

        function actualizarActividad(data) {{
            const matricula = data.matricula;
            const actividadId = data.id_actividad;

            if (!actividadId) {{
                console.warn("⚠️ No se recibió id_actividad:", data);
                return;
            }}

            // ✅ Buscar estudiante por matrícula
            for (let [id, estudiante] of estudiantesMap) {{
                if (estudiante.matricula === matricula) {{
                    
                    // ✅ Inicializar objeto de actividades si no existe
                    if (!estudiante.actividades) {{
                        estudiante.actividades = {{}};
                    }}
                    
                    // ✅ IMPORTANTE: Convertir actividadId a string
                    const actIdStr = String(actividadId);
                    estudiante.actividades[actIdStr] = 'entregado';

                    console.log(`📝 Entrega registrada:`, {{
                        nombre: estudiante.nombre_completo,
                        matricula: matricula,
                        actividadId: actIdStr,
                        actividades: estudiante.actividades
                    }});

                    // ✅ Renderizar solo esta fila con highlight
                    renderizarFila(id, true);
                    break;
                }}
            }}
        }}

        function renderizarFila(idEstudiante, highlight = false) {{
            const estudiante = estudiantesMap.get(idEstudiante);
            const tbody = document.getElementById('tabla-body');
            const existingRow = tbody.querySelector(`tr[data-id="${{idEstudiante}}"]`);
            
            const newRow = crearFila(estudiante, idEstudiante);
            
            if (highlight) {{
                newRow.classList.add('row-updating');
                setTimeout(() => newRow.classList.remove('row-updating'), 800);
            }}
            
            if (existingRow) {{
                tbody.replaceChild(newRow, existingRow);
            }} else {{
                tbody.appendChild(newRow);
            }}
        }}

        conectarWebSocket();
        console.log('✅ Tabla cargada');
    </script>
</body>
</html>
"""

components.html(html, height=900, scrolling=True)