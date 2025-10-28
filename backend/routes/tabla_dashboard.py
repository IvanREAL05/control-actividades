from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict
import asyncio
import logging
import json
from datetime import datetime
from zoneinfo import ZoneInfo 
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
    # ✅ CAMBIO 1: Obtener fecha/hora actual en zona horaria de México
    ahora_cdmx = datetime.now(ZoneInfo("America/Mexico_City"))
    fecha_hoy = ahora_cdmx.strftime('%Y-%m-%d')
    
    logger.info(f"📅 Fecha actual (CDMX): {fecha_hoy} {ahora_cdmx.strftime('%H:%M:%S')}")
    
    # ✅ CAMBIO 2: Query mejorada - filtra por fecha explícita, no CURDATE()
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
            AND DATE(fecha_creacion) = %s
        ORDER BY fecha_creacion DESC
    """
    actividades = await fetch_all(query_actividades, (id_clase, fecha_hoy))
    logger.info(f"📚 {len(actividades)} actividades encontradas para clase {id_clase} en fecha {fecha_hoy}")
    
    # Log de debug para ver qué actividades se encontraron
    if actividades:
        for act in actividades:
            logger.debug(f"  📝 Actividad {act['id_actividad']}: {act['titulo']} (creada: {act['fecha_creacion']})")
    else:
        logger.warning(f"⚠️ No se encontraron actividades para clase {id_clase} en {fecha_hoy}")
    
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
    
    if not info_clase:
        logger.error(f"❌ No se encontró información para la clase {id_clase}")
        raise HTTPException(status_code=404, detail=f"Clase {id_clase} no encontrada")
    
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
    estudiantes = await fetch_all(query_estudiantes, (fecha_hoy, id_clase))
    logger.info(f"👥 {len(estudiantes)} estudiantes encontrados para clase {id_clase}")
    
    if not estudiantes:
        logger.warning(f"⚠️ No se encontraron estudiantes para clase {id_clase}")
        # Aún así retornar estructura válida con datos vacíos
        return {
            "tipo": "datos_iniciales",
            "clase": {
                "id_clase": info_clase[0]['id_clase'],
                "materia": info_clase[0]['nombre_materia'],
                "grupo": info_clase[0]['nombre_grupo']
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
            "estudiantes": [],
            "fecha_actual": fecha_hoy
        }
    
    # 4. ✅ OPTIMIZADO: Obtener TODOS los estados en UNA sola query
    estados_dict = {}
    if actividades:
        actividad_ids = [act['id_actividad'] for act in actividades]
        estudiante_ids = [est['id_estudiante'] for est in estudiantes]
        
        # Una sola query para obtener TODOS los estados
        placeholders_act = ','.join(['%s'] * len(actividad_ids))
        placeholders_est = ','.join(['%s'] * len(estudiante_ids))
        
        query_estados = f"""
            SELECT id_actividad, id_estudiante, estado
            FROM actividad_estudiante
            WHERE id_actividad IN ({placeholders_act})
                AND id_estudiante IN ({placeholders_est})
        """
        
        estados = await fetch_all(
            query_estados, 
            tuple(actividad_ids + estudiante_ids)
        )
        
        # Crear diccionario de estados para acceso rápido
        for estado in estados:
            key = f"{estado['id_estudiante']}_{estado['id_actividad']}"
            estados_dict[key] = estado['estado']
        
        logger.debug(f"📊 {len(estados)} estados de actividades obtenidos en 1 query")
    
    # 5. Armar datos completos de estudiantes
    estudiantes_completos = []
    for estudiante in estudiantes:
        est_data = dict(estudiante)
        est_data['actividades'] = {}
        
        # Buscar estado de cada actividad en el diccionario
        for actividad in actividades:
            key = f"{estudiante['id_estudiante']}_{actividad['id_actividad']}"
            estado = estados_dict.get(key, 'pendiente')
            est_data['actividades'][str(actividad['id_actividad'])] = estado
        
        estudiantes_completos.append(est_data)
    
    # 5. Estructurar respuesta
    resultado = {
        "tipo": "datos_iniciales",
        "clase": {
            "id_clase": info_clase[0]['id_clase'],
            "materia": info_clase[0]['nombre_materia'],
            "grupo": info_clase[0]['nombre_grupo']
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
        "estudiantes": estudiantes_completos,
        "fecha_actual": fecha_hoy
    }
    
    logger.info(f"✅ Datos preparados: {len(estudiantes_completos)} estudiantes, {len(actividades)} actividades")
    return resultado


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


async def notificar_nueva_actividad(id_clase: int, actividad_data: dict):
    """
    ✅ NUEVO: Notifica cuando se crea una nueva actividad
    """
    mensaje = {
        "tipo": "nueva_actividad",
        "data": {
            "id": actividad_data['id_actividad'],
            "nombre": actividad_data['titulo'],
            "tipo": actividad_data['tipo_actividad'],
            "fecha": str(actividad_data['fecha_entrega']),
            "valor": float(actividad_data['valor_maximo'])
        }
    }
    await tabla_manager.broadcast(json.dumps(mensaje, ensure_ascii=False), id_clase)
    logger.info(f"📢 Nueva actividad notificada: clase {id_clase}, actividad {actividad_data['titulo']}")


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


@router.get("/debug/actividades/{id_clase}")
async def debug_actividades(id_clase: int):
    """
    ✅ NUEVO: Endpoint de debug para ver actividades en BD
    Prueba: http://localhost:8000/api/tabla/debug/actividades/34
    """
    try:
        # Ver TODAS las actividades de la clase (sin filtro de fecha)
        query = """
            SELECT 
                id_actividad,
                titulo,
                tipo_actividad,
                DATE(fecha_creacion) as fecha_creacion,
                TIME(fecha_creacion) as hora_creacion,
                fecha_entrega,
                valor_maximo
            FROM actividad
            WHERE id_clase = %s
            ORDER BY fecha_creacion DESC
        """
        todas = await fetch_all(query, (id_clase,))
        
        # Ver actividades de HOY según CDMX
        ahora_cdmx = datetime.now(ZoneInfo("America/Mexico_City"))
        fecha_hoy = ahora_cdmx.strftime('%Y-%m-%d')
        
        query_hoy = """
            SELECT 
                id_actividad,
                titulo,
                DATE(fecha_creacion) as fecha_creacion
            FROM actividad
            WHERE id_clase = %s
                AND DATE(fecha_creacion) = %s
            ORDER BY fecha_creacion DESC
        """
        hoy = await fetch_all(query_hoy, (id_clase, fecha_hoy))
        
        return {
            "success": True,
            "fecha_servidor_cdmx": fecha_hoy,
            "hora_servidor_cdmx": ahora_cdmx.strftime('%H:%M:%S'),
            "total_actividades": len(todas),
            "actividades_hoy": len(hoy),
            "todas_las_actividades": todas,
            "actividades_filtradas_hoy": hoy
        }
        
    except Exception as e:
        logger.error(f"❌ Error en debug: {e}")
        raise HTTPException(status_code=500, detail=str(e))