from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict
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
    WebSocket para tabla dinámica - Versión optimizada
    """
    # ✅ El manager ya llama a accept(), no lo llamamos aquí
    await tabla_manager.connect(websocket, id_clase)
    logger.info(f"✅ Cliente conectado a clase {id_clase}. Total: {len(tabla_manager.active_connections.get(id_clase, []))}")
    
    try:
        # Enviar datos iniciales
        datos_iniciales = await obtener_datos_tabla_completos(id_clase)
        await websocket.send_text(json.dumps(datos_iniciales, ensure_ascii=False))
        logger.info(f"📤 Datos iniciales enviados a clase {id_clase}")
        
        # ✅ LOOP SIMPLE SIN TIMEOUT - Mantiene conexión abierta
        while True:
            # Recibir cualquier mensaje del cliente
            data = await websocket.receive_text()
            
            # Responder a pings (keep-alive)
            if data == "ping":
                await websocket.send_text("pong")
                logger.debug(f"🏓 Ping/Pong con clase {id_clase}")
                
    except WebSocketDisconnect:
        logger.info(f"🔌 Cliente desconectado de clase {id_clase}")
    except Exception as e:
        logger.error(f"❌ Error WebSocket clase {id_clase}: {e}")
    finally:
        tabla_manager.disconnect(websocket, id_clase)
        logger.info(f"🔴 Conexión cerrada para clase {id_clase}. Restantes: {len(tabla_manager.active_connections.get(id_clase, []))}")


async def obtener_datos_tabla_completos(id_clase: int) -> Dict:
    """
    Obtiene toda la información de la clase con estudiantes y actividades
    """
    hoy = date.today().strftime('%Y-%m-%d')
    
    # 1. Actividades del día
    query_actividades = """
        SELECT 
            id_actividad,
            titulo,
            tipo_actividad,
            fecha_entrega,
            valor_maximo
        FROM actividad
        WHERE id_clase = %s
            AND DATE(fecha_creacion) = CURDATE()
        ORDER BY fecha_creacion DESC
    """
    actividades = await fetch_all(query_actividades, (id_clase,))
    logger.info(f"📚 {len(actividades)} actividades encontradas para clase {id_clase}")
    
    # 2. Info de la clase
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
    
    # 3. Estudiantes con asistencia
    query_estudiantes = """
        SELECT 
            e.id_estudiante,
            e.nombre,
            e.apellido,
            CONCAT(e.nombre, ' ', e.apellido) as nombre_completo,
            e.matricula,
            g.nombre as grupo,
            COALESCE(a.estado, 'ausente') as asistencia,
            COALESCE(TIME_FORMAT(a.hora_entrada, '%%H:%%i:%%s'), '') as hora_entrada
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
    logger.info(f"👥 {len(estudiantes)} estudiantes encontrados para clase {id_clase}")
    
    # 4. Agregar estado de actividades a cada estudiante
    estudiantes_completos = []
    
    for estudiante in estudiantes:
        est_data = dict(estudiante)
        est_data['actividades'] = {}
        
        # Obtener estado de cada actividad para este estudiante
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
        
        estudiantes_completos.append(est_data)
    
    # 5. Estructurar respuesta
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
        "estudiantes": estudiantes_completos
    }


@router.get("/{id_clase}/datos")
async def obtener_datos_api(id_clase: int):
    """
    Endpoint REST para cargar datos iniciales
    """
    try:
        datos = await obtener_datos_tabla_completos(id_clase)
        logger.info(f"✅ API devolvió datos para clase {id_clase}")
        return datos
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================
# 📡 FUNCIONES PARA NOTIFICAR CAMBIOS
# ============================================

async def notificar_asistencia(id_clase: int, id_estudiante: int, estado: str, hora: str):
    """
    Notifica cambio de asistencia a todos los dashboards conectados
    """
    mensaje = {
        "tipo": "asistencia",
        "data": {
            "id_estudiante": id_estudiante,
            "estado": estado,
            "hora": hora
        }
    }
    await tabla_manager.broadcast(json.dumps(mensaje, ensure_ascii=False), id_clase)
    logger.info(f"📢 Asistencia notificada: clase {id_clase}, estudiante {id_estudiante} → {estado}")


async def notificar_actividad(id_clase: int, matricula: str, id_actividad: int, estado: str = "entregado"):
    """
    Notifica entrega de actividad a todos los dashboards conectados
    """
    mensaje = {
        "tipo": "actividad",
        "data": {
            "matricula": matricula,
            "id_actividad": id_actividad,
            "estado": estado
        }
    }
    await tabla_manager.broadcast(json.dumps(mensaje, ensure_ascii=False), id_clase)
    logger.info(f"📢 Actividad notificada: clase {id_clase}, matrícula {matricula} → actividad {id_actividad}")


# ============================================
# 🧪 ENDPOINTS DE PRUEBA
# ============================================

@router.get("/test/notificar/{id_clase}")
async def test_notificacion(id_clase: int):
    """
    Prueba: http://localhost:8000/api/tabla/test/notificar/34
    """
    await notificar_asistencia(
        id_clase=id_clase,
        id_estudiante=5,
        estado="presente",
        hora="20:55:46"
    )
    
    conexiones = len(tabla_manager.active_connections.get(id_clase, []))
    logger.info(f"🧪 Test ejecutado para clase {id_clase}. Conexiones activas: {conexiones}")
    
    return {
        "success": True,
        "mensaje": f"Notificación enviada a clase {id_clase}",
        "conexiones_activas": conexiones,
        "tipo_notificacion": "asistencia"
    }


@router.get("/test/actividad/{id_clase}")
async def test_actividad(id_clase: int):
    """
    Prueba: http://localhost:8000/api/tabla/test/actividad/34
    """
    await notificar_actividad(
        id_clase=id_clase,
        matricula="202400184",
        id_actividad=1,
        estado="entregado"
    )
    
    return {
        "success": True,
        "mensaje": f"Notificación de actividad enviada a clase {id_clase}"
    }