from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict
import asyncio
import logging
import json
from datetime import date
from config.db import fetch_all
from routes.ws_manager_tabla import tabla_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/tabla/{id_clase}")
async def websocket_tabla(websocket: WebSocket, id_clase: int):
    """
    WebSocket para tabla dinámica de una clase específica.
    Mantiene la conexión abierta para recibir actualizaciones en tiempo real.
    """
    await websocket.accept()
    logger.info(f"✅ WebSocket aceptado para clase {id_clase}")
    await tabla_manager.connect(websocket, id_clase)
    logger.info(f"📋 Dashboard tabla conectado para clase {id_clase}. Total clientes: {len(tabla_manager.active_connections.get(id_clase, []))}")
    
    try:
        # Enviar datos iniciales
        datos_iniciales = await obtener_datos_tabla_completos(id_clase)
        await websocket.send_json(datos_iniciales)
        logger.info(f"📤 Enviados datos iniciales a clase {id_clase}")
        
        # ✅ MANTENER CONEXIÓN ABIERTA - Escuchar mensajes del cliente
        while True:
            try:
                # Esperar mensaje del cliente con timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(), 
                    timeout=60.0  # Timeout de 60 segundos
                )
                
                try:
                    mensaje = json.loads(data)
                    
                    # Responder a pings para mantener conexión viva
                    if mensaje.get("tipo") == "ping":
                        logger.debug(f"💓 Ping recibido de clase {id_clase}")
                        await websocket.send_json({"tipo": "pong"})
                    else:
                        logger.debug(f"📨 Mensaje recibido de clase {id_clase}: {mensaje.get('tipo', 'desconocido')}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Mensaje no JSON recibido de clase {id_clase}")
                    
            except asyncio.TimeoutError:
                # Si no hay mensajes por 60 segundos, enviar ping al cliente
                try:
                    await websocket.send_json({"tipo": "ping"})
                    logger.debug(f"💓 Ping enviado a clase {id_clase}")
                except Exception as e:
                    logger.error(f"❌ Error enviando ping a clase {id_clase}: {e}")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Error recibiendo mensaje de clase {id_clase}: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"📋 Cliente desconectado voluntariamente de clase {id_clase}")
    except Exception as e:
        logger.error(f"❌ Error en WebSocket tabla clase {id_clase}: {e}")
    finally:
        tabla_manager.disconnect(websocket, id_clase)
        logger.info(f"🔴 WebSocket cerrado para clase {id_clase}. Clientes restantes: {len(tabla_manager.active_connections.get(id_clase, []))}")


async def obtener_datos_tabla_completos(id_clase: int) -> Dict:
    """
    Obtiene TODA la información de la clase:
    - Estudiantes con asistencia
    - Actividades del día
    - Estado de cada estudiante en cada actividad
    """
    hoy = date.today().strftime('%Y-%m-%d')
    
    # 1️⃣ Obtener actividades de HOY para esta clase
    query_actividades = """
        SELECT 
            id_actividad,
            titulo,
            tipo_actividad,
            fecha_entrega,
            valor_maximo,
            fecha_creacion
        FROM actividad
        WHERE id_clase = %s
            AND DATE(fecha_creacion) = CURDATE()
        ORDER BY fecha_creacion DESC
    """
    actividades = await fetch_all(query_actividades, (id_clase,))
    
    # 2️⃣ Obtener info de la clase
    query_clase = """
        SELECT 
            c.id_clase,
            m.nombre as nombre_materia,
            g.nombre as nombre_grupo
        FROM clase c
        JOIN materia m ON c.id_materia = m.id_materia
        JOIN grupo g ON c.id_grupo = g.id_grupo
        WHERE c.id_clase = %s
    """
    info_clase = await fetch_all(query_clase, (id_clase,))
    
    # 3️⃣ Obtener estudiantes con asistencia
    query_estudiantes = """
        SELECT 
            e.id_estudiante,
            e.nombre,
            e.apellido,
            CONCAT(e.nombre, ' ', e.apellido) as nombre_completo,
            e.matricula,
            g.nombre as grupo,
            COALESCE(a.estado, 'pendiente') as asistencia,
            COALESCE(a.hora_entrada, '') as hora_entrada
        FROM estudiante e
        JOIN grupo g ON e.id_grupo = g.id_grupo
        JOIN clase c ON c.id_grupo = g.id_grupo
        LEFT JOIN asistencia a ON a.id_estudiante = e.id_estudiante 
            AND a.id_clase = c.id_clase 
            AND a.fecha = %s
        WHERE c.id_clase = %s
        ORDER BY e.apellido, e.nombre
    """
    estudiantes = await fetch_all(query_estudiantes, (hoy, id_clase))
    
    # 4️⃣ Obtener estado de actividades para cada estudiante
    estudiantes_con_actividades = []
    
    for estudiante in estudiantes:
        est_data = dict(estudiante)
        est_data['actividades'] = {}
        
        # Para cada actividad, obtener el estado
        for actividad in actividades:
            query_estado = """
                SELECT estado
                FROM actividad_estudiante
                WHERE id_actividad = %s AND id_estudiante = %s
            """
            resultado = await fetch_all(
                query_estado, 
                (actividad['id_actividad'], estudiante['id_estudiante'])
            )
            
            estado = resultado[0]['estado'] if resultado else 'pendiente'
            est_data['actividades'][str(actividad['id_actividad'])] = estado
        
        estudiantes_con_actividades.append(est_data)
    
    # 5️⃣ Estructurar respuesta
    return {
        "tipo": "datos_iniciales",
        "clase": {
            "id_clase": info_clase[0]['id_clase'] if info_clase else id_clase,
            "materia": info_clase[0]['nombre_materia'] if info_clase else "Sin materia",
            "grupo": info_clase[0]['nombre_grupo'] if info_clase else "Sin grupo"
        },
        "actividades": [
            {
                "id": act['id_actividad'],
                "nombre": act['titulo'], 
                "tipo": act['tipo_actividad'],
                "fecha": str(act['fecha_entrega']),
                "valor": float(act['valor_maximo'])
            }
            for act in actividades
        ],
        "estudiantes": estudiantes_con_actividades
    }


@router.get("/{id_clase}/datos")
async def obtener_datos_api(id_clase: int):
    """
    Endpoint REST para cargar datos iniciales.
    """
    try:
        datos = await obtener_datos_tabla_completos(id_clase)
        logger.info(f"✅ API devolvió datos completos para clase {id_clase}")
        
        return {
            "success": True,
            **datos
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")