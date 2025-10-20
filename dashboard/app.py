import streamlit as st
import requests
import qrcode
from io import BytesIO
import base64
import time
from PIL import Image
import numpy as np
import os

st.set_page_config(
    page_title="Sistema de Asistencias - Login",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def verificar_login_desde_params():
    """
    Lee los datos de login desde query parameters después del redirect del WebSocket.
    Los query params son más confiables que sessionStorage con Streamlit.
    """
    query_params = st.query_params
    
    if query_params.get("login_exitoso") == "true":
        print("✅ Login detectado en query params")
        
        # Guardar en session_state
        st.session_state.login_exitoso = True
        st.session_state.id_clase = int(query_params.get("id_clase", 0))
        st.session_state.id_profesor = int(query_params.get("id_profesor", 0))
        st.session_state.nombre_profesor = query_params.get("nombre_profesor", "")
        st.session_state.materia = query_params.get("materia", "")
        st.session_state.grupo = query_params.get("grupo", "")
        
        print(f"📊 Datos guardados: Profesor {st.session_state.id_profesor} → Clase {st.session_state.id_clase}")
        
        # ⚠️ IMPORTANTE: Limpiar query params antes de redirigir
        st.query_params.clear()
        
        return True
    
    return False

# =============================================
# ESTILOS CSS PROFESIONALES
# =============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0;
    }
    
    .main-header {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        padding: 1.5rem 3rem;
        border-radius: 0 0 25px 25px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .logo-container {
        display: flex;
        align-items: center;
        gap: 2rem;
    }
    
    .logo-img {
        height: 70px;
        width: auto;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .school-info {
        text-align: center;
        flex-grow: 1;
    }
    
    .school-name {
        font-size: 1.4rem;
        font-weight: 700;
        color: #2d3748;
        margin: 0;
    }
    
    .school-system {
        font-size: 1rem;
        color: #718096;
        margin: 0.3rem 0 0 0;
        font-weight: 500;
    }
    
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 2rem;
    }
    
    .info-panel {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 3rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        height: 100%;
    }
    
    .qr-panel {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 3rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        height: 100%;
        text-align: center;
    }
    
    .feature-item {
        display: flex;
        align-items: flex-start;
        gap: 1.5rem;
        margin: 2rem 0;
        padding: 1.5rem;
        background: white;
        border-radius: 16px;
        border-left: 4px solid #667eea;
        transition: transform 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    .feature-item:hover {
        transform: translateX(8px);
        background: #f8fafc;
    }
    
    .feature-icon {
        font-size: 2rem;
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 12px;
        flex-shrink: 0;
    }
    
    .status-badge {
        background: linear-gradient(135deg, #48bb78, #38a169);
        color: white;
        padding: 1rem 2.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1.1rem;
        display: inline-block;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(72, 187, 120, 0.3);
    }
    
    .timer-display {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 1.2rem 2.5rem;
        border-radius: 50px;
        font-size: 1.4rem;
        font-weight: 700;
        display: inline-block;
        margin: 1.5rem 0;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        font-variant-numeric: tabular-nums;
    }
    
    .step {
        display: flex;
        align-items: center;
        gap: 1.2rem;
        margin: 1.2rem 0;
        padding: 1.2rem;
        background: #f7fafc;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    
    .step-number {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1rem;
        flex-shrink: 0;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 2.5rem;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        margin-top: 1.5rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
    }
    
    .feature-title {
        color: #2d3748 !important;
        font-size: 1.3rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }
    
    .feature-text {
        color: #4a5568 !important;
        margin: 0;
        line-height: 1.5;
    }
    
    .welcome-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem;
        line-height: 1.2;
    }
    
    .welcome-subtitle {
        font-size: 1.2rem;
        color: #4a5568;
        margin-bottom: 3rem;
        line-height: 1.6;
        font-weight: 500;
    }
    
    .expired-badge {
        background: #e53e3e;
        color: white;
        padding: 1rem 2rem;
        border-radius: 50px;
        display: inline-block;
        font-weight: 600;
        margin: 2rem 0;
    }
    
    .success-panel {
        background: linear-gradient(135deg, #48bb78, #38a169);
        color: white;
        padding: 3rem;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 20px 60px rgba(72, 187, 120, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# =============================================
# FUNCIONES
# =============================================

def cargar_logo_base64(ruta_archivo):
    """Cargar imagen y convertir a base64"""
    try:
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'rb') as f:
                return base64.b64encode(f.read()).decode()
        return None
    except:
        return None

def generar_sesion_qr():
    """Solicitar al backend un nuevo session_id"""
    try:
        response = requests.post(
            "http://localhost:8000/api/login/auth/generar-sesion-qr",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data["session_id"], data["expires_in"]
        return None, None
    except:
        return None, None

def crear_qr_pil_image(session_id: str):
    """Generar imagen QR como numpy array"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(session_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#667eea", back_color="white")
    return np.array(img.convert('RGB'))

# =============================================
# VERIFICAR SI YA HAY LOGIN ACTIVO
# =============================================


#✅ PRIMERO: Verificar si vienen datos en query params (después del WebSocket)
if verificar_login_desde_params():
    print("🔄 Redirigiendo a estadísticas desde query params...")
    st.switch_page("pages/estadisticas.py")

# ✅ SEGUNDO: Si ya hay login en session_state, redirigir
if st.session_state.get("login_exitoso", False):
    print("🔄 Redirigiendo a estadísticas desde session_state...")
    st.switch_page("pages/estadisticas.py")
# =============================================
# INICIALIZACIÓN
# =============================================

if "session_id" not in st.session_state:
    st.session_state.session_id = None
    st.session_state.qr_image = None
    st.session_state.expires_at = None
    st.session_state.login_status = "waiting"
    st.session_state.login_exitoso = False

if st.session_state.session_id is None:
    with st.spinner("🔄 Generando código de acceso..."):
        session_id, expires_in = generar_sesion_qr()
        if session_id:
            st.session_state.session_id = session_id
            st.session_state.qr_image = crear_qr_pil_image(session_id)
            st.session_state.expires_at = time.time() + expires_in
            st.session_state.login_status = "waiting"
            st.rerun()
        else:
            st.error("❌ No se pudo conectar con el servidor")
            st.stop()

# =============================================
# HEADER
# =============================================

logo_buap = cargar_logo_base64('assets/logo_buap.jpg')
logo_prep = cargar_logo_base64('assets/logo1.jpeg')

header_html = f"""
<div class="main-header">
    <div class="header-content">
        <div class="logo-container">
            {f'<img src="data:image/jpeg;base64,{logo_buap}" class="logo-img" alt="BUAP">' if logo_buap else '<div class="logo-img" style="background: #667eea; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">BUAP</div>'}
            <div class="school-info">
                <h1 class="school-name">PREPARATORIA "GRAL. LÁZARO CÁRDENAS DEL RÍO"</h1>
                <p class="school-system">Sistema de Control de Asistencias</p>
            </div>
            {f'<img src="data:image/jpeg;base64,{logo_prep}" class="logo-img" alt="Preparatoria">' if logo_prep else '<div class="logo-img" style="background: #764ba2; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">PREP</div>'}
        </div>
    </div>
</div>
"""

st.markdown(header_html, unsafe_allow_html=True)

# =============================================
# CONTENIDO PRINCIPAL
# =============================================

st.markdown('<div class="main-container">', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div class="info-panel">
        <h1 class="welcome-title">Bienvenido al Sistema</h1>
        <p class="welcome-subtitle">
            Accede de forma segura mediante código QR y gestiona tus clases 
            en tiempo real con nuestra plataforma integrada.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    features = [
        {"icon": "📊", "title": "Estadísticas en Tiempo Real", "text": "Visualiza datos actualizados de asistencia y rendimiento de tus grupos al instante."},
        {"icon": "✅", "title": "Control Simplificado", "text": "Gestiona asistencias, actividades y evaluaciones de manera eficiente y organizada."},
        {"icon": "🔒", "title": "Acceso Seguro", "text": "Autenticación de dos factores mediante QR para máxima seguridad de los datos."},
        {"icon": "📱", "title": "Sincronización Móvil", "text": "Integración perfecta con la aplicación móvil para acceso en cualquier momento."}
    ]
    
    for feature in features:
        st.markdown(f"""
        <div class="feature-item">
            <div class="feature-icon">{feature['icon']}</div>
            <div class="feature-content">
                <div class="feature-title">{feature['title']}</div>
                <div class="feature-text">{feature['text']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    if st.session_state.login_status == "waiting":
        tiempo_restante = int(st.session_state.expires_at - time.time())
        
        if tiempo_restante > 0:
            minutos = tiempo_restante // 60
            segundos = tiempo_restante % 60
            
            st.markdown("""
            <div class="qr-panel">
                <h2 style="font-size: 2rem; font-weight: 700; color: #2d3748; margin-bottom: 1rem;">
                    🔐 Acceso Seguro
                </h2>
                <p style="font-size: 1.1rem; color: #4a5568; margin-bottom: 2rem; line-height: 1.5; font-weight: 500;">
                    Escanea este código QR con la aplicación móvil para acceder al sistema
                </p>
            """, unsafe_allow_html=True)
            
            st.markdown("""
                <div class="status-badge">
                    ⏳ Esperando autenticación...
                </div>
            """, unsafe_allow_html=True)
            
            st.image(st.session_state.qr_image, width=280)
            
            st.markdown(f"""
                <div class="timer-display">
                    ⏱️ {minutos:02d}:{segundos:02d}
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
                <div style="margin-top: 2.5rem; text-align: left;">
                    <h3 style="color: #2d3748; font-size: 1.3rem; font-weight: 600; margin-bottom: 1.5rem; text-align: center;">
                        📋 Instrucciones de Acceso
                    </h3>
            """, unsafe_allow_html=True)
            
            steps = [
                "Abre la aplicación móvil de docente",
                "Selecciona 'Acceder al Dashboard'",
                "Escanea este código QR con la cámara", 
                "Selecciona tu clase y confirma"
            ]
            
            for i, step in enumerate(steps, 1):
                st.markdown(f"""
                    <div class="step">
                        <div class="step-number">{i}</div>
                        <div style="color: #4a5568; font-weight: 500; line-height: 1.5;">{step}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("🔄 Generar Nuevo Código QR", use_container_width=True, key="refresh_btn"):
                st.session_state.session_id = None
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
                
        else:
            st.session_state.login_status = "expired"
            st.rerun()
    
    elif st.session_state.login_status == "expired":
        st.markdown("""
        <div class="qr-panel">
            <h2 style="font-size: 2rem; font-weight: 700; color: #2d3748; margin-bottom: 1rem;">
                ⏱️ Código Expirado
            </h2>
            <p style="font-size: 1.1rem; color: #4a5568; margin-bottom: 2rem; line-height: 1.5; font-weight: 500;">
                El código QR ha caducado por motivos de seguridad
            </p>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <div class="expired-badge">
                ❌ Código Expirado
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <p style="color: #4a5568; margin: 2rem 0; line-height: 1.6; font-weight: 500;">
                Por seguridad, los códigos QR tienen un tiempo limitado de valencia.<br>
                Genera un nuevo código para continuar con el acceso al sistema.
            </p>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Generar Nuevo Código QR", use_container_width=True, key="refresh_expired"):
            st.session_state.session_id = None
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =============================================
# WEBSOCKET Y AUTO-REFRESH
# =============================================
if st.session_state.login_status == "waiting":
    import streamlit.components.v1 as components
    
    # ✅ VERSIÓN CORREGIDA CON LOGS Y REDIRECT POR QUERY PARAMS
    html_ws = f"""
    <script>
        console.log('🚀 Iniciando WebSocket para sesión: {st.session_state.session_id}');
        
        const ws = new WebSocket('ws://localhost:8000/ws/login/auth/{st.session_state.session_id}');
        
        ws.onopen = () => {{
            console.log('✅ WebSocket conectado exitosamente');
        }};
        
        ws.onmessage = (event) => {{
            console.log('📩 RAW MESSAGE:', event.data);
            
            try {{
                const data = JSON.parse(event.data);
                console.log('📦 PARSED DATA:', JSON.stringify(data, null, 2));
                console.log('🔑 TIPO:', data.tipo);
                console.log('📊 DATOS:', data.datos);
                
                if (data.tipo === 'login_exitoso') {{
                    console.log('🎉 Login exitoso detectado!');
                    console.log('📊 Datos completos:', data.datos);
                    
                    // Verificar que tengamos todos los campos necesarios
                    if (!data.datos || !data.datos.id_clase) {{
                        console.error('❌ Faltan datos en la respuesta:', data.datos);
                        return;
                    }}
                    
                    // Construir URL con query parameters
                    const params = new URLSearchParams({{
                        login_exitoso: 'true',
                        id_clase: data.datos.id_clase,
                        id_profesor: data.datos.id_profesor,
                        nombre_profesor: data.datos.nombre_profesor,
                        materia: data.datos.materia,
                        grupo: data.datos.grupo
                    }});
                    
                    console.log('🔗 Query params construidos:', params.toString());
                    
                    // Cerrar WebSocket antes de redirigir
                    ws.close();
                    
                    // Construir URL completa
                    const baseUrl = window.location.origin + window.location.pathname;
                    const newUrl = baseUrl + '?' + params.toString();
                    
                    console.log('🔄 Redirigiendo a:', newUrl);
                    
                    // Redirigir con los datos en query params
                    window.location.href = newUrl;
                }}
            }} catch (error) {{
                console.error('❌ Error procesando mensaje:', error);
                console.error('Stack:', error.stack);
            }}
        }};
        
        ws.onerror = (error) => {{
            console.error('❌ Error en WebSocket:', error);
        }};
        
        ws.onclose = (event) => {{
            console.log('🔴 WebSocket cerrado');
            console.log('   - Code:', event.code);
            console.log('   - Reason:', event.reason);
            console.log('   - Was Clean:', event.wasClean);
        }};
        
        // Enviar ping cada 30 segundos para mantener conexión viva
        setInterval(() => {{
            if (ws.readyState === WebSocket.OPEN) {{
                ws.send('ping');
                console.log('🏓 Ping enviado');
            }}
        }}, 30000);
    </script>
    """
    
    components.html(html_ws, height=0)
    
    # Esperar un momento antes de refrescar para permitir que el WebSocket se conecte
    time.sleep(1)
    st.rerun()