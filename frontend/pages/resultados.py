import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit.components.v1 as components
import json
import base64
import requests
from collections import defaultdict
from datetime import datetime

st.set_page_config(page_title="Resultados en Tiempo Real", layout="wide")

# --- Estilos CSS globales ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Quicksand', sans-serif !important;
    }
    
    .main { 
        background-color: #f0f4f8; 
        font-family: 'Quicksand', sans-serif;
    }
    
    .stApp { 
        background-color: #f0f4f8; 
        font-family: 'Quicksand', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6, p, span, div {
        font-family: 'Quicksand', sans-serif !important;
    }
    
    /* Ocultar elementos de navegación de Streamlit */
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    button[kind="header"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    .css-1dp5vir {display: none;}
    
    /* Indicador de actualización en tiempo real */
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

# --- Cabecera Azul con Logos ---
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
                       text-shadow: 2px 2px 4px rgba(0,0,0,0.2); font-family: 'Quicksand', sans-serif;">
                UA PREP. "GRAL. LÁZARO CÁRDENAS DEL RÍO"
            </h1>
            <p style="color: #e0e7ff; margin: 10px 0 0 0; font-size: 18px; font-weight: 600; 
                      font-family: 'Quicksand', sans-serif;">
                📊 Asistencias en Tiempo Real
            </p>
        </div>
        <img src="data:image/jpeg;base64,{base64.b64encode(open('assets/logo1.jpeg','rb').read()).decode()}" 
             height="75" style="border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
    </div>
</div>
""", unsafe_allow_html=True)

# Indicador de actualización en tiempo real
st.markdown("""
<div class="live-indicator">
    🔴 EN VIVO
</div>
""", unsafe_allow_html=True)

# ===============================
# Botón de recarga manual
# ===============================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Recargar Clases de Hoy", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# ===============================
# Cargar datos iniciales
# ===============================
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_initial_data():
    """Carga los datos iniciales desde el backend"""
    try:
        resp = requests.get("http://localhost:8000/api/clases/hoy", timeout=5)
        resp.raise_for_status()
        clases = resp.json()
        
        print(f"✅ Datos cargados: {len(clases)} clases")
        return clases
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return []

# Cargar datos
clases_data = load_initial_data()

if not clases_data or len(clases_data) == 0:
    st.warning("⚠️ No hay clases programadas para hoy o no se pudo conectar al backend")
    st.info("🔍 Verifica que el backend esté corriendo en http://localhost:8000")
    st.stop()

# ===============================
# Procesar datos
# ===============================
data_dict = {}
for clase in clases_data:
    id_clase = clase["id_clase"]
    
    # Convertir Decimal a int/float
    presentes = int(clase.get("presentes", 0))
    justificantes = int(clase.get("justificantes", 0))
    ausentes = int(clase.get("ausentes", 0))
    total = int(clase.get("total_estudiantes", 0))
    
    data_dict[id_clase] = {
        "presentes": presentes,
        "justificantes": justificantes,
        "ausentes": ausentes,
        "total": total,
        "nombre_materia": clase.get("nombre_materia", "Sin nombre"),
        "nombre_grupo": clase.get("nombre_grupo", "Sin grupo")
    }

print(f"📊 Datos procesados: {len(data_dict)} clases")

# ===============================
# Renderizar dashboard
# ===============================
total_clases = len(data_dict)
slide_counter = 0
slides_html = ""

for id_clase, info in data_dict.items():
    slide_counter += 1
    porcentaje_asistencia = (info['presentes'] / info['total'] * 100) if info['total'] > 0 else 0
    
    df = pd.DataFrame([
        {"Estado": "Presentes", "Cantidad": info["presentes"]},
        {"Estado": "Justificantes", "Cantidad": info["justificantes"]},
        {"Estado": "Ausentes", "Cantidad": info["ausentes"]},
    ])
    
    fig_bar = px.bar(
        df, x="Estado", y="Cantidad", text="Cantidad",
        color="Estado",
        color_discrete_map={"Presentes": "#10b981", "Ausentes": "#ef4444", "Justificantes": "#f59e0b"}
    )
    fig_bar.update_traces(textfont_size=22, textposition="outside", textfont_family="Quicksand")
    fig_bar.update_layout(
        margin=dict(t=60, b=40, l=30, r=30), 
        height=450, 
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(size=16, color='#374151', family='Quicksand'),
        xaxis=dict(title=None),
        yaxis=dict(title=None, gridcolor='#e5e7eb')
    )
    chart_bar_html = pio.to_html(fig_bar, full_html=False, include_plotlyjs="cdn")

    slides_html += f"""
    <div class="swiper-slide" data-clase-id="{id_clase}">
        <div class="slide-counter">{slide_counter} / {total_clases}</div>
        <div class="slide-card">
            <div class="card-header">
                <h3>{info['nombre_materia']}</h3>
                <span class="grupo-badge">{info['nombre_grupo']}</span>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card total-card">
                    <div class="stat-icon">👥</div>
                    <div class="stat-content">
                        <div class="stat-number" data-stat="total">{info['total']}</div>
                        <div class="stat-label">Total</div>
                    </div>
                </div>
                
                <div class="stat-card present-card">
                    <div class="stat-icon">✅</div>
                    <div class="stat-content">
                        <div class="stat-number" data-stat="presentes">{info['presentes']}</div>
                        <div class="stat-label">Presentes</div>
                    </div>
                </div>
                
                <div class="stat-card justified-card">
                    <div class="stat-icon">📄</div>
                    <div class="stat-content">
                        <div class="stat-number" data-stat="justificantes">{info['justificantes']}</div>
                        <div class="stat-label">Justificantes</div>
                    </div>
                </div>
                
                <div class="stat-card absent-card">
                    <div class="stat-icon">❌</div>
                    <div class="stat-content">
                        <div class="stat-number" data-stat="ausentes">{info['ausentes']}</div>
                        <div class="stat-label">Ausentes</div>
                    </div>
                </div>
            </div>
            
            <div class="percentage-section">
                <div class="percentage-label">
                    Porcentaje de Asistencia: <span class="percentage-value" data-stat="porcentaje">{porcentaje_asistencia:.1f}%</span>
                </div>
                <div class="percentage-bar">
                    <div class="percentage-fill" data-stat="barra" style="width: {porcentaje_asistencia}%">
                        <span class="percentage-text">{porcentaje_asistencia:.0f}%</span>
                    </div>
                </div>
            </div>
            
            <div class="charts-container" data-chart-id="{id_clase}">
                {chart_bar_html}
            </div>
        </div>
    </div>
    """

html = f"""
<link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css" />
<link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
* {{ 
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: 'Quicksand', sans-serif !important;
}}

body {{
    font-family: 'Quicksand', sans-serif;
}}

.swiper-container {{ 
    width: 100%; 
    padding: 25px 0 60px 0; 
}}

.swiper-slide {{ 
    width: 1000px; 
    display: flex; 
    justify-content: center; 
}}

.slide-card {{ 
    background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);
    border: none;
    border-radius: 25px; 
    padding: 40px; 
    width: 100%; 
    box-shadow: 0 15px 45px rgba(0,0,0,0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}}

.slide-card:hover {{
    transform: translateY(-8px);
    box-shadow: 0 20px 55px rgba(0,0,0,0.15);
}}

.card-header {{
    text-align: center;
    margin-bottom: 35px;
    padding-bottom: 25px;
    border-bottom: 3px solid #e5e7eb;
}}

.card-header h3 {{ 
    font-size: 32px; 
    margin: 0 0 15px 0; 
    color: #1e40af;
    font-weight: 700;
    letter-spacing: -0.5px;
    font-family: 'Quicksand', sans-serif;
}}

.grupo-badge {{
    display: inline-block;
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    padding: 10px 25px;
    border-radius: 30px;
    font-size: 17px;
    font-weight: 600;
    box-shadow: 0 6px 15px rgba(59, 130, 246, 0.35);
    font-family: 'Quicksand', sans-serif;
}}

.stats-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 25px;
    margin-bottom: 35px;
}}

.stat-card {{
    background: white;
    border-radius: 20px;
    padding: 28px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    transition: all 0.3s ease;
    border-top: 5px solid;
}}

.stat-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
}}

.stat-icon {{
    font-size: 44px;
    margin-bottom: 15px;
}}

.stat-content {{
    text-align: center;
    width: 100%;
}}

.stat-number {{
    font-size: 58px;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 12px;
    font-family: 'Quicksand', sans-serif;
    transition: all 0.4s ease;
}}

.stat-label {{
    font-size: 16px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6b7280;
    font-family: 'Quicksand', sans-serif;
}}

.total-card {{ 
    border-top-color: #3b82f6; 
    background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
}}
.total-card .stat-number {{ color: #3b82f6; }}

.present-card {{ 
    border-top-color: #10b981; 
    background: linear-gradient(135deg, #ffffff 0%, #ecfdf5 100%);
}}
.present-card .stat-number {{ color: #10b981; }}

.justified-card {{ 
    border-top-color: #f59e0b; 
    background: linear-gradient(135deg, #ffffff 0%, #fffbeb 100%);
}}
.justified-card .stat-number {{ color: #f59e0b; }}

.absent-card {{ 
    border-top-color: #ef4444; 
    background: linear-gradient(135deg, #ffffff 0%, #fef2f2 100%);
}}
.absent-card .stat-number {{ color: #ef4444; }}

.percentage-section {{
    margin-bottom: 40px;
    padding: 25px;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-radius: 20px;
    border: 2px solid #3b82f6;
}}

.percentage-label {{
    font-size: 22px;
    font-weight: 700;
    color: #1e40af;
    margin-bottom: 15px;
    text-align: center;
    font-family: 'Quicksand', sans-serif;
}}

.percentage-value {{
    color: #10b981;
    font-size: 26px;
    font-family: 'Quicksand', sans-serif;
    transition: all 0.4s ease;
}}

.percentage-bar {{
    width: 100%;
    height: 40px;
    background: #dbeafe;
    border-radius: 20px;
    overflow: hidden;
    position: relative;
    border: 2px solid #93c5fd;
}}

.percentage-fill {{
    height: 100%;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #6ee7b7 100%);
    border-radius: 18px;
    transition: width 0.8s ease;
    box-shadow: 0 2px 10px rgba(16, 185, 129, 0.5);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 15px;
}}

.percentage-text {{
    color: white;
    font-weight: 700;
    font-size: 18px;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    font-family: 'Quicksand', sans-serif;
}}

.charts-container {{ 
    display: flex; 
    justify-content: center;
    background: white;
    border-radius: 20px;
    padding: 25px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    min-height: 500px;
}}

.swiper-button-next, .swiper-button-prev {{
    color: #3b82f6;
    background: white;
    width: 55px;
    height: 55px;
    border-radius: 50%;
    box-shadow: 0 6px 18px rgba(0,0,0,0.15);
    transition: all 0.3s ease;
}}

.swiper-button-next:hover, .swiper-button-prev:hover {{
    background: #3b82f6;
    color: white;
    transform: scale(1.1);
}}

.swiper-button-next:after, .swiper-button-prev:after {{
    font-size: 22px;
    font-weight: 900;
}}

.swiper-pagination {{
    bottom: 10px !important;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
}}

.swiper-pagination-bullet {{
    width: 10px;
    height: 10px;
    background: #3b82f6;
    opacity: 0.4;
    transition: all 0.3s ease;
    margin: 0 3px !important;
}}

.swiper-pagination-bullet-active {{
    opacity: 1;
    background: #1e40af;
    width: 28px;
    border-radius: 5px;
}}

.swiper-pagination-bullets {{
    display: flex;
    flex-wrap: wrap;
    max-width: 90%;
    justify-content: center;
    gap: 5px;
}}

.slide-counter {{
    position: absolute;
    top: 15px;
    right: 25px;
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    color: white;
    padding: 8px 18px;
    border-radius: 20px;
    font-size: 16px;
    font-weight: 700;
    box-shadow: 0 4px 12px rgba(30, 64, 175, 0.3);
    z-index: 10;
    font-family: 'Quicksand', sans-serif;
}}

@keyframes updateFlash {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.15); }}
}}

.stat-number.updating {{
    animation: updateFlash 0.6s ease;
}}

@media (max-width: 1024px) {{
    .stats-grid {{
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
    }}
    .stat-number {{
        font-size: 50px;
    }}
}}

@media (max-width: 768px) {{ 
    .swiper-slide {{ 
        width: 95vw; 
    }}
    .slide-card {{
        padding: 25px;
    }}
    .stats-grid {{
        grid-template-columns: 1fr;
        gap: 15px;
    }}
    .stat-number {{
        font-size: 45px;
    }}
    .card-header h3 {{
        font-size: 24px;
    }}
    .percentage-label {{
        font-size: 18px;
    }}
}}
</style>

<div class="swiper-container">
    <div class="swiper-wrapper">
        {slides_html}
    </div>
    <div class="swiper-button-prev"></div>
    <div class="swiper-button-next"></div>
    <div class="swiper-pagination"></div>
</div>

<script src="https://unpkg.com/swiper/swiper-bundle.min.js"></script>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script>
console.log('🚀 Iniciando dashboard...');

const totalSlides = {total_clases};
console.log('📊 Total de clases:', totalSlides);

const swiper = new Swiper('.swiper-container', {{
    slidesPerView: 1, 
    spaceBetween: 35, 
    loop: totalSlides > 1,
    pagination: {{ 
        el: '.swiper-pagination', 
        clickable: true,
        dynamicBullets: totalSlides > 10,
        dynamicMainBullets: 5
    }},
    navigation: {{ 
        nextEl: '.swiper-button-next', 
        prevEl: '.swiper-button-prev' 
    }},
    autoplay: totalSlides > 1 ? {{ 
        delay: 7000, 
        disableOnInteraction: false,
        pauseOnMouseEnter: true
    }} : false,
    keyboard: {{
        enabled: true,
        onlyInViewport: true
    }},
    mousewheel: {{
        forceToAxis: true
    }}
}});

swiper.on('slideChange', function() {{
    console.log('📄 Slide actual:', swiper.realIndex + 1, 'de', totalSlides);
}});

// ===================================
// WebSocket para actualizaciones en tiempo real
// ===================================
let ws;
let reconnectInterval = 5000;
let isConnecting = false;

function connectWebSocket() {{
    if (isConnecting) {{
        console.log('⏳ Ya hay una conexión en proceso...');
        return;
    }}
    
    isConnecting = true;
    console.log('🔄 Intentando conectar WebSocket...');
    
    try {{
        ws = new WebSocket('ws://localhost:8000/api/clases/ws/attendances');
        
        ws.onopen = function() {{
            console.log('🟢 WebSocket conectado correctamente');
            isConnecting = false;
        }};
        
        ws.onmessage = function(event) {{
            try {{
                const data = JSON.parse(event.data);
                console.log('📩 Mensaje recibido:', data);
                updateSlideData(data);
            }} catch (error) {{
                console.error('❌ Error parseando mensaje:', error);
            }}
        }};
        
        ws.onerror = function(error) {{
            console.error('❌ WebSocket error:', error);
            isConnecting = false;
        }};
        
        ws.onclose = function() {{
            console.log('🔴 WebSocket cerrado');
            isConnecting = false;
            console.log('⏰ Reconectando en 5 segundos...');
            setTimeout(connectWebSocket, reconnectInterval);
        }};
    }} catch (error) {{
        console.error('❌ Error creando WebSocket:', error);
        isConnecting = false;
        setTimeout(connectWebSocket, reconnectInterval);
    }}
}}

function updateSlideData(data) {{
    const idClase = data.id_clase;
    const estado = data.estado;
    
    console.log(`🔄 Actualizando clase ${{idClase}} - Estado: ${{estado}}`);
    
    const slide = document.querySelector(`[data-clase-id="${{idClase}}"]`);
    if (!slide) {{
        console.warn('⚠️ No se encontró slide para clase:', idClase);
        return;
    }}
    
    const presentesEl = slide.querySelector('[data-stat="presentes"]');
    const justificantesEl = slide.querySelector('[data-stat="justificantes"]');
    const ausentesEl = slide.querySelector('[data-stat="ausentes"]');
    const totalEl = slide.querySelector('[data-stat="total"]');
    const porcentajeValueEl = slide.querySelector('[data-stat="porcentaje"]');
    const barraEl = slide.querySelector('[data-stat="barra"]');
    const barraTextEl = barraEl.querySelector('.percentage-text');
    
    let presentes = parseInt(presentesEl.textContent);
    let justificantes = parseInt(justificantesEl.textContent);
    let ausentes = parseInt(ausentesEl.textContent);
    let total = parseInt(totalEl.textContent);
    
    if (estado === 'presente') {{
        presentes++;
        presentesEl.textContent = presentes;
        presentesEl.classList.add('updating');
        setTimeout(() => presentesEl.classList.remove('updating'), 600);
    }} else if (estado === 'justificante') {{
        justificantes++;
        justificantesEl.textContent = justificantes;
        justificantesEl.classList.add('updating');
        setTimeout(() => justificantesEl.classList.remove('updating'), 600);
    }} else if (estado === 'ausente') {{
        ausentes++;
        ausentesEl.textContent = ausentes;
        ausentesEl.classList.add('updating');
        setTimeout(() => ausentesEl.classList.remove('updating'), 600);
    }}
    
    total = presentes + justificantes + ausentes;
    totalEl.textContent = total;
    totalEl.classList.add('updating');
    setTimeout(() => totalEl.classList.remove('updating'), 600);
    
    const porcentaje = total > 0 ? (presentes / total * 100) : 0;
    porcentajeValueEl.textContent = porcentaje.toFixed(1) + '%';
    barraEl.style.width = porcentaje + '%';
    barraTextEl.textContent = Math.round(porcentaje) + '%';
    
    updateChart(idClase, presentes, justificantes, ausentes);
    
    console.log(`✅ Actualizado correctamente: P=${{presentes}} J=${{justificantes}} A=${{ausentes}}`);
}}

function updateChart(idClase, presentes, justificantes, ausentes) {{
    const chartContainer = document.querySelector(`[data-chart-id="${{idClase}}"]`);
    if (!chartContainer) {{
        console.warn('⚠️ No se encontró contenedor de gráfico para clase:', idClase);
        return;
    }}
    
    const plotlyDiv = chartContainer.querySelector('.plotly-graph-div');
    if (!plotlyDiv) {{
        console.warn('⚠️ No se encontró div de Plotly');
        return;
    }}
    
    try {{
        Plotly.restyle(plotlyDiv, {{
            y: [[presentes, justificantes, ausentes]],
            text: [[presentes, justificantes, ausentes]]
        }}, [0]);
        console.log('📊 Gráfico actualizado');
    }} catch (error) {{
        console.error('❌ Error actualizando gráfico:', error);
    }}
}}

// Iniciar WebSocket al cargar
console.log('🚀 Iniciando WebSocket...');
connectWebSocket();

console.log('✅ Dashboard cargado completamente');
</script>
"""

components.html(html, height=1150, scrolling=False)