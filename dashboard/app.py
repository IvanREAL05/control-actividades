import streamlit as st
import requests
import qrcode
from io import BytesIO
import base64
import time
from PIL import Image
import numpy as np
import os
import json

# ============================================
# CONFIGURACIÓN DE IPs
# ============================================
BACKEND_IP = "192.168.100.11"  # PC donde corre FastAPI
BACKEND_PORT = "8000"
FRONTEND_IP = "192.168.100.11"  # PC donde corre Streamlit
FRONTEND_PORT = "8501"

st.set_page_config(
    page_title="Sistema de Control de Asistencias",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS para hacer todo más grande y visible
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp {
    margin: 0 !important;
    padding: 0 !important;
}
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
section.main > div {
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# Verificar si venimos de un login exitoso
query_params = st.query_params
if query_params.get("login") == "success":
    st.session_state.login_exitoso = True
    st.session_state.id_clase = int(query_params.get("id_clase"))
    st.session_state.id_profesor = int(query_params.get("id_profesor"))
    st.session_state.nombre_profesor = query_params.get("nombre_profesor", "")
    st.session_state.materia = query_params.get("materia", "")
    st.session_state.grupo = query_params.get("grupo", "")
    st.query_params.clear()
    st.rerun()

# Si ya hay sesión activa, mostrar dashboard con tabla
if st.session_state.get("login_exitoso"):
    id_clase = st.session_state.id_clase
    
    @st.cache_data(ttl=300)
    def obtener_datos_iniciales(id_clase):
        try:
            response = requests.get(
                f"http://{BACKEND_IP}:{BACKEND_PORT}/api/tabla/{id_clase}/datos",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    datos = obtener_datos_iniciales(id_clase)
    
    if not datos or not datos.get('estudiantes'):
        st.warning("⚠️ No hay estudiantes registrados en esta clase.")
        if st.button("🚪 Cerrar Sesión"):
            for key in list(st.session_state.keys()):
                if not key.startswith('_'):
                    del st.session_state[key]
            st.rerun()
        st.stop()
    
    clase_info = datos.get('clase', {})
    actividades = datos.get('actividades', [])
    datos_json = json.dumps(datos)
    actividades_headers = "".join([f'<th class="act-header">{act["nombre"]}</th>' for act in actividades])
    
    html_tabla = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', sans-serif;
            }}
            html, body {{
                height: 100vh;
                width: 100vw;
                overflow: hidden;
                background: #f3f4f6;
            }}
            .main-container {{
                height: 100vh;
                width: 100vw;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }}
            .live-indicator {{
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
                color: white;
                padding: 12px 24px;
                border-radius: 30px;
                font-weight: 700;
                font-size: 16px;
                box-shadow: 0 4px 20px rgba(16, 185, 129, 0.5);
                z-index: 10000;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; transform: scale(1); }}
                50% {{ opacity: 0.8; transform: scale(1.05); }}
            }}
            .header {{
                background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                padding: 25px 40px;
                box-shadow: 0 4px 20px rgba(30, 64, 175, 0.3);
                flex-shrink: 0;
            }}
            .header-content {{
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .header-title {{
                text-align: center;
            }}
            .header-title h1 {{
                color: white;
                margin: 0;
                font-size: 36px;
                font-weight: 700;
                text-shadow: 2px 2px 6px rgba(0,0,0,0.3);
            }}
            .header-title p {{
                color: #e0e7ff;
                margin: 12px 0 0 0;
                font-size: 20px;
                font-weight: 600;
            }}
            .info-bar {{
                background: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-around;
                gap: 30px;
                box-shadow: 0 2px 15px rgba(0,0,0,0.1);
                flex-shrink: 0;
            }}
            .info-item {{
                text-align: center;
            }}
            .info-label {{
                font-size: 14px;
                color: #6b7280;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .info-value {{
                font-size: 32px;
                font-weight: 700;
                color: #1e40af;
                margin-top: 8px;
            }}
            .content-area {{
                flex: 1;
                padding: 25px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }}
            .table-container {{
                background: white;
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.12);
                flex: 1;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }}
            .table-wrapper {{
                flex: 1;
                overflow: auto;
            }}
            table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                font-size: 16px;
            }}
            thead {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                position: sticky;
                top: 0;
                z-index: 100;
            }}
            th {{
                color: white;
                padding: 18px 16px;
                text-align: left;
                font-weight: 700;
                font-size: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            th.act-header {{
                text-align: center;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            }}
            tbody tr {{
                border-bottom: 2px solid #e5e7eb;
                transition: background 0.2s;
            }}
            tbody tr:hover {{
                background: #f9fafb;
            }}
            td {{
                padding: 18px 16px;
                color: #374151;
                font-size: 15px;
            }}
            td.act-cell {{
                text-align: center;
            }}
            .badge {{
                display: inline-block;
                padding: 8px 16px;
                border-radius: 25px;
                font-weight: 700;
                font-size: 13px;
                text-transform: uppercase;
                white-space: nowrap;
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
                padding: 10px 20px;
                border-radius: 25px;
                font-size: 14px;
                font-weight: 700;
                box-shadow: 0 4px 20px rgba(16, 185, 129, 0.5);
                z-index: 10000;
            }}
            .ws-status.disconnected {{
                background: #ef4444;
            }}
            .table-wrapper::-webkit-scrollbar {{
                width: 10px;
                height: 10px;
            }}
            .table-wrapper::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 10px;
            }}
            .table-wrapper::-webkit-scrollbar-thumb {{
                background: #667eea;
                border-radius: 10px;
            }}
            .table-wrapper::-webkit-scrollbar-thumb:hover {{
                background: #764ba2;
            }}
        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="live-indicator">🔴 EN VIVO</div>
            <div class="header">
                <div class="header-content">
                    <div class="header-title">
                        <h1>UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
                        <p>📋 Bienvenido {st.session_state.nombre_profesor} - Clase {id_clase}</p>
                    </div>
                </div>
            </div>
            <div class="info-bar">
                <div class="info-item"><div class="info-label">Materia</div><div class="info-value" id="nombre-materia">-</div></div>
                <div class="info-item"><div class="info-label">Grupo</div><div class="info-value" id="nombre-grupo">-</div></div>
                <div class="info-item"><div class="info-label">Total Estudiantes</div><div class="info-value" id="total-estudiantes">0</div></div>
                <div class="info-item"><div class="info-label">Presentes</div><div class="info-value" style="color: #10b981;" id="total-presentes">0</div></div>
                <div class="info-item"><div class="info-label">Actividades Hoy</div><div class="info-value" style="color: #3b82f6;" id="total-actividades">0</div></div>
            </div>
            <div class="content-area">
                <div class="table-container">
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th>Grupo</th><th>Nombre</th><th>Matrícula</th><th>Asistencia</th><th>Hora</th>{actividades_headers}</tr></thead>
                            <tbody id="tabla-body"><tr><td colspan="100" style="text-align:center; padding: 40px; font-size: 18px;">Cargando datos...</td></tr></tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="ws-status" id="ws-status">Conectando...</div>
        </div>
        <script>
            const datosIniciales = {datos_json};
            const ID_CLASE = {id_clase};
            const claseInfo = datosIniciales.clase;
            const actividades = datosIniciales.actividades;
            const estudiantesMap = new Map();
            datosIniciales.estudiantes.forEach(est => estudiantesMap.set(est.id_estudiante, est));
            
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
            
            function renderizarTabla() {{
                const tbody = document.getElementById('tabla-body');
                tbody.innerHTML = '';
                estudiantesMap.forEach((estudiante, id) => tbody.appendChild(crearFila(estudiante, id)));
                actualizarEstadisticas();
            }}
            
            function crearFila(estudiante, id) {{
                const tr = document.createElement('tr');
                tr.setAttribute('data-id', id);
                const estado = estadoMap[estudiante.asistencia] || estadoMap['pendiente'];
                let actividadesCells = '';
                actividades.forEach(act => {{
                    const actIdStr = String(act.id);
                    const estadoAct = estudiante.actividades && estudiante.actividades[actIdStr] ? estudiante.actividades[actIdStr] : 'pendiente';
                    const badgeClass = estadoAct === 'entregado' ? 'badge-entregado' : 'badge-pendiente';
                    const emoji = estadoAct === 'entregado' ? '✅' : '⚪';
                    const texto = estadoAct === 'entregado' ? 'Entregado' : 'Pendiente';
                    actividadesCells += `<td class="act-cell"><span class="badge ${{badgeClass}}">${{emoji}} ${{texto}}</span></td>`;
                }});
                tr.innerHTML = `<td>${{estudiante.grupo}}</td>
                    <td><strong>${{estudiante.nombre_completo}}</strong></td>
                    <td>${{estudiante.matricula}}</td>
                    <td><span class="badge ${{estado.badge}}">${{estado.emoji}} ${{estado.texto}}</span></td>
                    <td>${{estudiante.hora_entrada || '-'}}</td>
                    ${{actividadesCells}}`;
                return tr;
            }}
            
            function actualizarEstadisticas() {{
                let total = 0, presentes = 0;
                estudiantesMap.forEach(est => {{
                    total++;
                    if (est.asistencia === 'presente') presentes++;
                }});
                document.getElementById('total-estudiantes').textContent = total;
                document.getElementById('total-presentes').textContent = presentes;
            }}

            // ✅ AGREGAR ESTA NUEVA FUNCIÓN AQUÍ
            function renderizarTablaCompleta() {{
                // 1. Actualizar el header con las nuevas columnas
                const thead = document.querySelector('thead tr');
                let actividadesHeaders = '';
                actividades.forEach(act => {{
                    actividadesHeaders += `<th class="act-header">${{act.nombre}}</th>`;
                }});
                thead.innerHTML = `<th>Grupo</th><th>Nombre</th><th>Matrícula</th><th>Asistencia</th><th>Hora</th>${{actividadesHeaders}}`;
                
                // 2. Actualizar el contador de actividades en la barra superior
                document.getElementById('total-actividades').textContent = actividades.length;
                
                // 3. Re-renderizar todas las filas
                renderizarTabla();
                
                console.log('🔄 Tabla completa re-renderizada con', actividades.length, 'actividades');
            }}
            
            renderizarTabla();
            
            let ws = new WebSocket('ws://{BACKEND_IP}:{BACKEND_PORT}/ws/tabla/{id_clase}');
            console.log("📡 Intentando conectar WebSocket...");
            const wsStatus = document.getElementById('ws-status');
            
            ws.onopen = () => {{
                console.log("✅ WebSocket conectado correctamente al servidor");
                wsStatus.textContent = '🟢 Conectado';
                wsStatus.classList.remove('disconnected');
            }};
            
            ws.onmessage = (event) => {{
                console.log("📩 Mensaje recibido del servidor:", event.data);
                try {{
                    const mensaje = JSON.parse(event.data);
                    console.log("🧩 Tipo de mensaje:", mensaje.tipo, "→", mensaje.data);
                    
                    if (mensaje.tipo === 'asistencia') {{
                        const est = estudiantesMap.get(mensaje.data.id_estudiante);
                        if (est) {{
                            est.asistencia = mensaje.data.estado;
                            est.hora_entrada = mensaje.data.hora || '';
                            console.log(`✅ Actualizando fila de ${{est.nombre_completo}} → ${{est.asistencia}}`);
                            renderizarTabla();
                        }}
                    }}
                    // ✅ MEJORADO: Manejar múltiples tipos de eventos de actividad
                    else if (mensaje.tipo === 'actividad' || mensaje.tipo === 'entrega_nueva' || mensaje.tipo === 'entrega_actualizada') {{
                        const matricula = mensaje.data.matricula;
                        const idActividad = mensaje.data.id_actividad;
                        
                        for (let [id, est] of estudiantesMap) {{
                            if (est.matricula === matricula) {{
                                if (!est.actividades) est.actividades = {{}};
                                est.actividades[String(idActividad)] = 'entregado';
                                console.log(`📘 Actividad entregada para ${{est.nombre_completo}} (tipo: ${{mensaje.tipo}})`);
                                renderizarTabla();
                                break;
                            }}
                        }}
                    }}
                    else if (mensaje.tipo === 'nueva_actividad') {{
                        console.log("🆕 Nueva actividad detectada:", mensaje.data);
                        
                        actividades.push({{
                            id: mensaje.data.id,
                            nombre: mensaje.data.nombre,
                            tipo: mensaje.data.tipo
                        }});
                        
                        estudiantesMap.forEach((est) => {{
                            if (!est.actividades) est.actividades = {{}};
                            est.actividades[String(mensaje.data.id)] = 'pendiente';
                        }});
                        
                        renderizarTablaCompleta();
                        
                        console.log(`✅ Nueva columna agregada: "${{mensaje.data.nombre}}" (ID: ${{mensaje.data.id}})`);
                    }}
                }} catch(e) {{
                    console.error("❌ Error procesando mensaje WebSocket:", e);
                }}
            }};
            
            ws.onerror = (e) => {{
                console.error("❌ Error en WebSocket:", e);
                wsStatus.textContent = '🔴 Error';
                wsStatus.classList.add('disconnected');
            }};
            
            ws.onclose = (e) => {{
                console.warn("🔌 WebSocket cerrado:", e);
                wsStatus.textContent = '🔴 Desconectado';
                wsStatus.classList.add('disconnected');
            }};
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_tabla, height=900, scrolling=False)
    
    if st.button("🚪 Cerrar Sesión"):
        for key in list(st.session_state.keys()):
            if not key.startswith('_'):
                del st.session_state[key]
        st.rerun()
    
    st.stop()

# ============================================
# PÁGINA DE LOGIN CON QR Y WEBSOCKET
# ============================================

def generar_sesion_qr():
    """Generar session_id"""
    try:
        response = requests.post(
            f"http://{BACKEND_IP}:{BACKEND_PORT}/api/login/auth/generar-sesion-qr",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data["session_id"], data["expires_in"] - 30 
    except:
        pass
    return None, None

# ✅ MEJORADO: Regenerar QR cuando expire o no exista
if "session_id" not in st.session_state or st.session_state.session_id is None or st.session_state.get("qr_expirado", False):
    session_id, expires_in = generar_sesion_qr()
    if session_id:
        st.session_state.session_id = session_id
        st.session_state.expires_at = time.time() + expires_in
        st.session_state.qr_expirado = False  # ⬅️ NUEVO
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(session_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#667eea", back_color="white")
        st.session_state.qr_image = np.array(img.convert('RGB'))
    else:
        st.error("❌ Error conectando con el servidor")
        if st.button("🔄 Reintentar"):  # ⬅️ NUEVO
            st.rerun()
        st.stop()

tiempo_restante = int(st.session_state.expires_at - time.time())
if tiempo_restante <= 0:
    st.session_state.qr_expirado = True  # ⬅️ NUEVO: marcar como expirado
    st.warning("⏱️ Código QR expirado")
    if st.button("🔄 Generar Nuevo Código"):
        st.rerun()  # ⬅️ Ya no necesitas limpiar session_id manualmente
    st.stop()

session_id = st.session_state.session_id
minutos = tiempo_restante // 60
segundos = tiempo_restante % 60

buffered = BytesIO()
Image.fromarray(st.session_state.qr_image).save(buffered, format="PNG")
qr_base64 = base64.b64encode(buffered.getvalue()).decode()

html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login QR</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', sans-serif;
        }}
        html, body {{
            height: 100vh;
            width: 100vw;
            overflow: hidden;
        }}
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 25px;
            padding: 35px 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 480px;
            width: 100%;
            max-height: 95vh;
            overflow-y: auto;
        }}
        .logo-section {{
            margin-bottom: 20px;
        }}
        .logo-section h2 {{
            color: #1e40af;
            font-size: 1.3rem;
            margin-bottom: 5px;
            font-weight: 700;
        }}
        .logo-section p {{
            color: #667eea;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 3px;
        }}
        h1 {{
            color: #2d3748;
            font-size: 1.8rem;
            margin-bottom: 8px;
            font-weight: 700;
        }}
        .subtitle {{
            color: #718096;
            margin-bottom: 20px;
            font-size: 1rem;
        }}
        .qr-container {{
            background: #f7fafc;
            padding: 25px;
            border-radius: 15px;
            margin: 20px 0;
        }}
        .qr-image {{
            width: 220px;
            height: 220px;
            margin: 0 auto;
        }}
        .timer {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px 25px;
            border-radius: 50px;
            font-size: 1.3rem;
            font-weight: bold;
            margin: 15px 0;
            display: inline-block;
        }}
        .status {{
            background: #48bb78;
            color: white;
            padding: 10px 20px;
            border-radius: 50px;
            font-weight: 600;
            margin: 15px 0;
            display: inline-block;
            font-size: 0.95rem;
        }}
        .status.connecting {{
            background: #ed8936;
        }}
        .status.error {{
            background: #f56565;
        }}
        .instructions {{
            text-align: left;
            margin-top: 20px;
            color: #4a5568;
        }}
        .instructions h3 {{
            margin-bottom: 12px;
            color: #2d3748;
            font-size: 1.1rem;
            text-align: center;
        }}
        .step {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px;
            margin: 8px 0;
            background: #f7fafc;
            border-radius: 10px;
        }}
        .step-number {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
            font-size: 13px;
        }}
        .step div {{
            font-size: 0.9rem;
        }}
        .container::-webkit-scrollbar {{
            width: 8px;
        }}
        .container::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 10px;
        }}
        .container::-webkit-scrollbar-thumb {{
            background: #667eea;
            border-radius: 10px;
        }}
        .container::-webkit-scrollbar-thumb:hover {{
            background: #764ba2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-section">
            <h2>🎓 Sistema de Control de Asistencias en Tiempo Real</h2>
            <p>Preparatoria Gral. Lázaro Cárdenas del Río</p>
        </div>
        <h1>🔐 Acceso Seguro</h1>
        <p class="subtitle">Escanea el código QR con tu app móvil</p>
        <div class="status" id="status">⏳ Esperando escaneo...</div>
        <div class="qr-container">
            <img src="data:image/png;base64,{qr_base64}" class="qr-image" alt="QR Code">
        </div>
        <div class="timer" id="timer">{minutos:02d}:{segundos:02d}</div>
        <div class="instructions">
            <h3>📋 Instrucciones</h3>
            <div class="step"><div class="step-number">1</div><div>Abre la app móvil de docente</div></div>
            <div class="step"><div class="step-number">2</div><div>Toca en "Acceder al Dashboard"</div></div>
            <div class="step"><div class="step-number">3</div><div>Escanea este código QR</div></div>
            <div class="step"><div class="step-number">4</div><div>Selecciona tu clase y confirma</div></div>
        </div>
    </div>
    <script>
        const ws = new WebSocket('ws://{BACKEND_IP}:{BACKEND_PORT}/ws/login/auth/{session_id}');
        const statusEl = document.getElementById('status');
        const timerEl = document.getElementById('timer');
        let tiempoRestante = {tiempo_restante};
        
        const interval = setInterval(() => {{
            tiempoRestante--;
            const mins = Math.floor(tiempoRestante / 60);
            const secs = tiempoRestante % 60;
            timerEl.textContent = `${{mins.toString().padStart(2, '0')}}:${{secs.toString().padStart(2, '0')}}`;
            
            if (tiempoRestante <= 0) {{
                clearInterval(interval);
                statusEl.textContent = '❌ Código expirado';
                statusEl.className = 'status error';
                setTimeout(() => window.location.reload(), 2000);
            }}
        }}, 1000);
        
        ws.onopen = () => {{
            statusEl.textContent = '⏳ Esperando escaneo...';
            statusEl.className = 'status';
        }};
        
        ws.onmessage = (event) => {{
            if (event.data === 'pong') return;
            try {{
                const data = JSON.parse(event.data);
                if (data.tipo === 'login_exitoso') {{
                    clearInterval(interval);
                    statusEl.textContent = '✅ ¡Login exitoso!';
                    statusEl.className = 'status';
                    const datos = data.datos;
                    const params = new URLSearchParams();
                    params.set('login', 'success');
                    params.set('id_clase', datos.id_clase);
                    params.set('id_profesor', datos.id_profesor);
                    params.set('nombre_profesor', datos.nombre_profesor);
                    params.set('materia', datos.materia);
                    params.set('grupo', datos.grupo);
                    window.location.href = 'http://{FRONTEND_IP}:{FRONTEND_PORT}/?' + params.toString();
                }}
            }} catch (error) {{
                console.error(error);
            }}
        }};
        
        ws.onerror = () => {{
            statusEl.textContent = '⚠️ Error de conexión';
            statusEl.className = 'status error';
        }};
        
        setInterval(() => {{
            if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }}, 20000);
    </script>
</body>
</html>
"""

st.components.v1.html(html_content, height=750, scrolling=False)