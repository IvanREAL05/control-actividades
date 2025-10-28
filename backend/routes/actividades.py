from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime
from routes.ws_manager import manager
import json
from config.db import fetch_one, fetch_all, execute_query
import pytz
from utils.fecha import obtener_fecha_hora_cdmx_completa, convertir_fecha_a_cdmx
import os
import logging
from cryptography.fernet import Fernet, InvalidToken
from typing import List, Optional
import json
from routes.ws_manager_tabla import tabla_manager

router = APIRouter()

logger = logging.getLogger("api_actividades")
logger.setLevel(logging.INFO)


# Formato de logs (opcional pero útil)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
# Schema para crear o actualizar actividad
class ActividadCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=100)
    descripcion: str | None = None
    tipo_actividad: str   # debe ser 'actividad', 'proyecto', 'practicas' o 'examen'
    fecha_entrega: str  # formato: "YYYY-MM-DD"
    hora_entrega: str   # formato: "HH:MM:SS"
    id_clase: int
    valor_maximo: int = Field(..., ge=0, le=100)  # ahora int

# --- Listar todas las actividades ---
@router.get("/")
async def listar_actividades():
    try:
        actividades = await fetch_all("SELECT * FROM actividad ORDER BY fecha_creacion DESC")
        return {"actividades": actividades}
    except Exception as e:
        print(f"Error listar_actividades: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error obteniendo actividades")

#Crear actividad
# Crear actividad - VERSIÓN INTEGRADA CON NOTIFICACIÓN
@router.post("/")
async def crear_actividad(data: ActividadCreate):
    """
    Crea una actividad y asigna automáticamente a todos los estudiantes del grupo con estado 'pendiente'.
    NOTIFICA a todos los dashboards conectados para agregar nueva columna.
    """
    try:
        # Combinar fecha y hora de entrega
        fecha_entrega_completa = f"{data.fecha_entrega} {data.hora_entrega}"
        fecha_creacion = datetime.now()

        # 1️⃣ Insertar la actividad
        query_insert = """
            INSERT INTO actividad 
                (titulo, descripcion, tipo_actividad, fecha_creacion, fecha_entrega, id_clase, valor_maximo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.titulo,
            data.descripcion,
            data.tipo_actividad,
            fecha_creacion,
            fecha_entrega_completa,
            data.id_clase,
            data.valor_maximo
        )
        cursor = await execute_query(query_insert, values)
        id_actividad = cursor.lastrowid if hasattr(cursor, "lastrowid") else cursor

        # 2️⃣ Obtener el grupo de la clase
        query_clase = "SELECT id_grupo FROM clase WHERE id_clase = %s"
        clase = await fetch_one(query_clase, (data.id_clase,))
        if not clase:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        id_grupo = clase["id_grupo"]

        # 3️⃣ Obtener todos los estudiantes del grupo
        query_estudiantes = "SELECT id_estudiante FROM estudiante WHERE id_grupo = %s"
        estudiantes = await fetch_all(query_estudiantes, (id_grupo,))

        # 4️⃣ Insertar registros en actividad_estudiante para todos
        if estudiantes:
            insert_actividad_estudiante = """
                INSERT INTO actividad_estudiante 
                    (id_actividad, id_estudiante, estado, fecha_entrega_real, calificacion)
                VALUES (%s, %s, %s, %s, %s)
            """
            for est in estudiantes:
                await execute_query(
                    insert_actividad_estudiante,
                    (id_actividad, est["id_estudiante"], "pendiente", None, None)
                )

        # ✅ NUEVO: Obtener los datos completos de la actividad creada para notificar
        query_actividad_creada = """
            SELECT 
                id_actividad,
                titulo,
                tipo_actividad,
                fecha_entrega,
                valor_maximo
            FROM actividad
            WHERE id_actividad = %s
        """
        actividad_creada = await fetch_one(query_actividad_creada, (id_actividad,))

        # ✅ NUEVO: Notificar a todos los dashboards conectados - INTEGRADO COMO EN ENTREGA
        evento_data = {
            "tipo": "nueva_actividad",
            "data": {
                "id": actividad_creada['id_actividad'],
                "nombre": actividad_creada['titulo'],
                "tipo": actividad_creada['tipo_actividad'],
                "fecha": str(actividad_creada['fecha_entrega']),
                "valor": float(actividad_creada['valor_maximo'])
            }
        }
        
        # 📡 Notificar a todos los dashboards conectados a esta clase
        await tabla_manager.broadcast(json.dumps(evento_data), id_clase=data.id_clase)
        logger.info(f"📢 Nueva actividad notificada: clase {data.id_clase}, actividad {actividad_creada['id_actividad']}")

        return {
            "success": True,
            "message": f"✅ Actividad creada y {len(estudiantes)} estudiantes registrados como pendientes",
            "id_actividad": id_actividad
        }

    except Exception as e:
        print(f"❌ Error crear_actividad: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# --- Actualizar actividad ---
@router.put("/{id_actividad}")
async def actualizar_actividad(id_actividad: int, data: ActividadCreate):
    try:
        fecha_str = data.fecha_entrega.split(" ")[0]
        fecha_entrega_completa = f"{fecha_str} {data.hora_entrega}"

        query = """
            UPDATE actividad
            SET titulo = %s,
                descripcion = %s,
                fecha_entrega = %s,
                id_clase = %s,
                valor_maximo = %s
            WHERE id_actividad = %s
        """
        valores = (
            data.titulo,
            data.descripcion,
            fecha_entrega_completa,
            data.id_clase,
            data.valor_maximo,
            id_actividad
        )

        rowcount = await execute_query(query, valores)
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        return {"mensaje": "Actividad actualizada con éxito"}

    except Exception as e:
        print(f"Error actualizar_actividad: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error actualizando la actividad")

# --- Eliminar actividad ---
@router.delete("/{id_actividad}")
async def eliminar_actividad(id_actividad: int):
    try:
        query = "DELETE FROM actividad WHERE id_actividad = %s"
        rowcount = await execute_query(query, (id_actividad,))
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        return {"mensaje": "Actividad eliminada con éxito"}

    except Exception as e:
        print(f"Error eliminar_actividad: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error eliminando la actividad")

#Obtener actividades de una clase
@router.get("/clase/{id_clase}")
async def obtener_actividades_por_clase(id_clase: int):
    try:
        query = """
            SELECT 
                a.*, 
                CASE 
                    WHEN NOW() <= a.fecha_entrega 
                    THEN 'vigente' 
                    ELSE 'caducada' 
                END AS vigencia
            FROM actividad a
            WHERE a.id_clase = %s
            ORDER BY a.fecha_creacion DESC
        """
        rows = await fetch_all(query, (id_clase,))

        # Convertir fechas a zona horaria de CDMX
        tz = pytz.timezone("America/Mexico_City")
        actividades = []
        for act in rows:
            if act.get("fecha_entrega"):
                fecha_entrega = act["fecha_entrega"]
                if isinstance(fecha_entrega, datetime):
                    act["fecha_entrega"] = fecha_entrega.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
            if act.get("fecha_creacion"):
                fecha_creacion = act["fecha_creacion"]
                if isinstance(fecha_creacion, datetime):
                    act["fecha_creacion"] = fecha_creacion.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
            actividades.append(act)

        return {"actividades": actividades}

    except Exception as e:
        print("❌ Error obteniendo actividades:", e)
        raise HTTPException(status_code=500, detail="Error obteniendo actividades")
    
# --- Request Body ---
class EntregaQRRequest(BaseModel):
    qr: str
    id_actividad: int
    calificacion: Optional[int] = None  # ← AÑADIR ESTE CAMPO

FERNET_KEY = os.getenv('FERNET_KEY')
if not FERNET_KEY:
    raise ValueError("FERNET_KEY no está configurada en las variables de entorno")
fernet_instance = Fernet(FERNET_KEY)

# --- Registrar entrega (QR escaneado) ---
@router.post("/entrega")
async def registrar_entrega(request: EntregaQRRequest):
    if not request.qr or not request.id_actividad:
        raise HTTPException(status_code=400, detail="Falta QR o id_actividad")

    try:
        fernet_instance = Fernet(FERNET_KEY)
        decrypted = fernet_instance.decrypt(request.qr.encode()).decode("utf-8")
        logger.info(f"QR desencriptado: {decrypted}")

        partes = [p.strip() for p in decrypted.split("|")]
        if len(partes) < 4:
            raise HTTPException(status_code=400, detail="Formato QR inválido")

        nombre_completo, matricula, grupo_qr, clave_unica = partes

        # 1️⃣ Validar actividad
        actividad = await fetch_one(
            """
            SELECT id_actividad, id_clase, fecha_entrega, valor_maximo, tipo_actividad
            FROM actividad
            WHERE id_actividad=%s AND fecha_entrega >= CURDATE()
            """,
            (request.id_actividad,)
        )
        if not actividad:
            raise HTTPException(status_code=400, detail="Actividad inválida o vencida")

        # 2️⃣ Buscar estudiante por matrícula
        estudiante = await fetch_one(
            "SELECT id_estudiante, nombre, id_grupo FROM estudiante WHERE matricula=%s",
            (matricula,)
        )
        if not estudiante:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")

        # 3️⃣ Validar grupo
        grupo_estudiante = await fetch_one(
            "SELECT nombre FROM grupo WHERE id_grupo=%s",
            (estudiante["id_grupo"],)
        )
        if grupo_estudiante["nombre"].lower() != grupo_qr.lower():
            raise HTTPException(status_code=400, detail="El grupo del estudiante no coincide con el grupo del QR")

        # 4️⃣ Validar relación clase ↔ grupo
        clase = await fetch_one(
            "SELECT id_grupo FROM clase WHERE id_clase=%s",
            (actividad["id_clase"],)
        )
        if not clase or clase["id_grupo"] != estudiante["id_grupo"]:
            raise HTTPException(status_code=400, detail="La actividad no corresponde al grupo del estudiante")

        fecha_entrega_real = obtener_fecha_hora_cdmx_completa()
        if isinstance(fecha_entrega_real, str):
            try:
                fecha_entrega_real = datetime.fromisoformat(fecha_entrega_real)
            except ValueError:
                logger.error(f"⚠️ Formato inesperado en fecha_entrega_real: {fecha_entrega_real}")
                raise HTTPException(status_code=500, detail="Error con la fecha del sistema")

        # 5️⃣ Verificar si ya existe registro
        entrega = await fetch_one(
            "SELECT estado FROM actividad_estudiante WHERE id_actividad=%s AND id_estudiante=%s",
            (request.id_actividad, estudiante["id_estudiante"])
        )

        # ✅ PREPARAR DATOS DEL EVENTO WEBSOCKET (ANTES de INSERT/UPDATE)
        # Determinar calificación según el tipo
        calificacion_asignada = actividad["valor_maximo"]
        if actividad["tipo_actividad"] == "examen":
            calificacion_asignada = None  # Se calificará manualmente
        elif request.calificacion is not None:
            calificacion_asignada = request.calificacion

        logger.info(f"📡 Preparando evento WebSocket para {nombre_completo}")

        if entrega:
            if entrega["estado"] == "entregado":
                # 🔸 Ya entregó antes
                evento_data = {
                    "tipo": "entrega_duplicada",
                    "data": {
                        "id_actividad": request.id_actividad,
                        "id_estudiante": estudiante["id_estudiante"],
                        "matricula": matricula,
                        "nombre": nombre_completo,
                        "estado": "entregado",
                        "mensaje": f"{nombre_completo} ya entregó esta {actividad['tipo_actividad']} anteriormente."
                    }
                }
                logger.info(f"📡 Emitiendo evento duplicado: {evento_data}")
                await manager.broadcast(json.dumps(evento_data))
                await tabla_manager.broadcast(json.dumps(evento_data), id_clase=actividad["id_clase"])
                
                return {
                    "success": True, 
                    "mensaje": f"{nombre_completo} ya entregó esta {actividad['tipo_actividad']} anteriormente."
                }

            # 🔄 Actualizar entrega existente
            await execute_query(
                """
                UPDATE actividad_estudiante
                SET estado='entregado', fecha_entrega_real=%s, calificacion=%s
                WHERE id_actividad=%s AND id_estudiante=%s
                """,
                (fecha_entrega_real, calificacion_asignada, request.id_actividad, estudiante["id_estudiante"])
            )

            # ✅ EVENTO WEBSOCKET MEJORADO
            evento_data = {
                "tipo": "entrega_actualizada",
                "data": {
                    "id_actividad": request.id_actividad,
                    "id_estudiante": estudiante["id_estudiante"],
                    "matricula": matricula,
                    "nombre": nombre_completo,
                    "estado": "entregado",
                    "calificacion": calificacion_asignada,
                    "fecha_entrega_real": fecha_entrega_real.isoformat() if isinstance(fecha_entrega_real, datetime) else str(fecha_entrega_real),
                    "tipo_actividad": actividad["tipo_actividad"]
                }
            }
            logger.info(f"📡 Emitiendo evento actualización: {evento_data}")
            await manager.broadcast(json.dumps(evento_data))
            await tabla_manager.broadcast(json.dumps(evento_data), id_clase=actividad["id_clase"])
            
            return {
                "success": True, 
                "mensaje": f"{nombre_completo} actualizó su entrega de la {actividad['tipo_actividad']}"
            }

        # 🆕 Nueva entrega
        await execute_query(
            """
            INSERT INTO actividad_estudiante
            (id_actividad, id_estudiante, estado, fecha_entrega_real, calificacion)
            VALUES (%s, %s, 'entregado', %s, %s)
            """,
            (request.id_actividad, estudiante["id_estudiante"], fecha_entrega_real, calificacion_asignada)
        )

        # ✅ EVENTO WEBSOCKET MEJORADO PARA NUEVA ENTREGA
        evento_data = {
            "tipo": "entrega_nueva",
            "data": {
                "id_actividad": request.id_actividad,
                "id_estudiante": estudiante["id_estudiante"],
                "matricula": matricula,
                "nombre": nombre_completo,
                "estado": "entregado",
                "calificacion": calificacion_asignada,
                "fecha_entrega_real": fecha_entrega_real.isoformat() if isinstance(fecha_entrega_real, datetime) else str(fecha_entrega_real),
                "tipo_actividad": actividad["tipo_actividad"]
            }
        }
        
        logger.info(f"📡 Emitiendo evento nueva entrega: {evento_data}")
        logger.info(f"   - id_actividad: {request.id_actividad}")
        logger.info(f"   - id_estudiante: {estudiante['id_estudiante']}")
        logger.info(f"   - nombre: {nombre_completo}")
        logger.info(f"   - calificación: {calificacion_asignada}")
        
        await manager.broadcast(json.dumps(evento_data))
        await tabla_manager.broadcast(json.dumps(evento_data), id_clase=actividad["id_clase"])
        
        logger.info(f"✅ Eventos WebSocket emitidos correctamente")
        
        return {
            "success": True, 
            "mensaje": f"{nombre_completo} entregó la {actividad['tipo_actividad']}"
        }
    
    except InvalidToken:
        raise HTTPException(status_code=400, detail="QR inválido o expirado")
    except Exception as e:
        logger.error(f"❌ Error en registrar_entrega: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error en el servidor")
    
    
# --- Obtener estudiantes por actividad ---
@router.get("/estudiantes/{id_actividad}")
async def obtener_estudiantes_por_actividad(id_actividad: int):
    query = """
        SELECT 
            e.id_estudiante,
            e.nombre,
            e.apellido,
            e.correo,
            e.matricula,
            e.no_lista,
            e.id_grupo,
            COALESCE(ae.estado, 'pendiente') as estado,
            ae.fecha_entrega_real,
            ae.fecha_registro,
            ae.calificacion,
            ae.id_actividad_estudiante,
            a.titulo,
            a.descripcion,
            a.tipo_actividad,   -- ✅ nuevo campo
            a.fecha_entrega,
            a.valor_maximo
        FROM estudiante e
        INNER JOIN actividad a ON a.id_actividad = %s
        INNER JOIN clase c ON c.id_clase = a.id_clase AND c.id_grupo = e.id_grupo
        LEFT JOIN actividad_estudiante ae 
            ON e.id_estudiante = ae.id_estudiante AND ae.id_actividad = %s
        WHERE a.id_actividad = %s
        ORDER BY e.no_lista ASC, e.apellido ASC, e.nombre ASC
    """

    try:
        rows = await fetch_all(query, (id_actividad, id_actividad, id_actividad))

        if not rows:
            raise HTTPException(status_code=404, detail="No se encontraron estudiantes para esta actividad")

        estudiantes_normalizados = []
        for estudiante in rows:
            fecha_entrega_real = convertir_fecha_a_cdmx(estudiante.get("fecha_entrega_real"))
            fecha_registro = convertir_fecha_a_cdmx(estudiante.get("fecha_registro"))

            estudiantes_normalizados.append({
                "id_estudiante": estudiante.get("id_estudiante"),
                "nombre": estudiante.get("nombre", ""),
                "apellido": estudiante.get("apellido", ""),
                "correo": estudiante.get("correo", ""),
                "matricula": estudiante.get("matricula", ""),
                "no_lista": estudiante.get("no_lista", 0),
                "id_grupo": estudiante.get("id_grupo", 0),
                "estado": estudiante.get("estado", "pendiente"),
                "fecha_entrega_real": fecha_entrega_real or "",
                "fecha_registro": fecha_registro or "",
                "calificacion": estudiante.get("calificacion", 0),
                "id_actividad_estudiante": estudiante.get("id_actividad_estudiante", 0),
                # 🔽 Info de la actividad
                "titulo": estudiante.get("titulo", ""),
                "descripcion": estudiante.get("descripcion", ""),
                "tipo_actividad": estudiante.get("tipo_actividad", "actividad"),
                "fecha_entrega": convertir_fecha_a_cdmx(estudiante.get("fecha_entrega")),
                "valor_maximo": estudiante.get("valor_maximo", 0)
            })

        return estudiantes_normalizados

    except Exception as e:
        print(f"❌ Error al obtener estudiantes de actividad: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener estudiantes de actividad")

# DTO de entrada
class EstadoEstudianteRequest(BaseModel):
    estudiante_id: int
    actividad_id: int
    nuevo_estado: str
    calificacion: Optional[int] = None 

# DTO de salida (simplificado)
class EstadoEstudianteResponse(BaseModel):
    success: bool
    message: str
    data: dict = None

@router.post("/actualizar-estado-estudiante", response_model=EstadoEstudianteResponse)
async def actualizar_estado_estudiante(payload: EstadoEstudianteRequest):
    print("Payload recibido:", payload)

    estudiante_id = payload.estudiante_id
    actividad_id = payload.actividad_id
    nuevo_estado = payload.nuevo_estado.lower() if payload.nuevo_estado else None

    # 🔹 Validaciones básicas
    if not estudiante_id or not actividad_id or not nuevo_estado:
        raise HTTPException(status_code=400, detail="Faltan datos requeridos")

    estados_validos = ["pendiente", "entregado", "no entregado"]
    if nuevo_estado not in estados_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Estado no válido. Debe ser uno de: {', '.join(estados_validos)}"
        )

    try:
        # 🔹 Obtener tipo de actividad y valor máximo
        actividad_query = "SELECT tipo_actividad, valor_maximo FROM actividad WHERE id_actividad = %s"
        actividad = await fetch_one(actividad_query, (actividad_id,))
        if not actividad:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        tipo_actividad = actividad["tipo_actividad"]
        valor_maximo = int(actividad["valor_maximo"]) if actividad["valor_maximo"] else None
        # 🔹 Determinar calificación según tipo
        calificacion_final = payload.calificacion
        # Si el estado es "no entregado" o "justificante", borrar calificación
        if nuevo_estado in ["no entregado", "pendiente"]:
            calificacion_final = None
        elif tipo_actividad != "examen":
            # Para actividades que no son examen, asignar calificación máxima automáticamente
            calificacion_final = valor_maximo
        elif tipo_actividad == "examen" and calificacion_final is None:
            # Si es examen pero no se envió calificación
            raise HTTPException(
                status_code=400,
                detail="Debe asignar una calificación manual al ser tipo 'examen'"
            )

        # 🔹 Buscar registro existente
        check_query = """
            SELECT ae.id_actividad_estudiante, ae.estado,
                   e.nombre, e.apellido, e.id_estudiante
            FROM actividad_estudiante ae
            JOIN estudiante e ON ae.id_estudiante = e.id_estudiante
            WHERE ae.id_actividad = %s AND ae.id_estudiante = %s
        """
        existente = await fetch_one(check_query, (actividad_id, estudiante_id))

        fecha_entrega = obtener_fecha_hora_cdmx_completa() if nuevo_estado == "entregado" else None

        # =====================================================
        # 🔹 SI YA EXISTE → ACTUALIZA
        # =====================================================
        if existente:
            update_query = """
                UPDATE actividad_estudiante
                SET estado = %s,
                    fecha_entrega_real = %s,
                    calificacion = %s
                WHERE id_actividad = %s AND id_estudiante = %s
            """
            await execute_query(update_query, (nuevo_estado, fecha_entrega, calificacion_final, actividad_id, estudiante_id))

            data_resp = {
                "id_actividad_estudiante": existente.get("id_actividad_estudiante"),
                "estado": nuevo_estado,
                "calificacion": calificacion_final,
                "fecha_entrega_real": str(fecha_entrega) if fecha_entrega else None,
                "estudiante": {
                    "id": existente.get("id_estudiante"),
                    "nombre": existente.get("nombre", ""),
                    "apellido": existente.get("apellido", "")
                }
            }

            return {
                "success": True,
                "message": f"✅ Estado de {data_resp['estudiante']['nombre']} {data_resp['estudiante']['apellido']} actualizado a: {nuevo_estado}",
                "data": data_resp
            }

        # =====================================================
        # 🔹 SI NO EXISTE → CREA NUEVO REGISTRO
        # =====================================================
        else:
            estudiante_query = "SELECT id_estudiante, nombre, apellido FROM estudiante WHERE id_estudiante = %s"
            estudiante = await fetch_one(estudiante_query, (estudiante_id,))
            if not estudiante:
                raise HTTPException(status_code=404, detail="El estudiante especificado no existe")

            fecha_registro = obtener_fecha_hora_cdmx_completa()

            insert_query = """
                INSERT INTO actividad_estudiante (
                    id_actividad, id_estudiante, estado, fecha_entrega_real, fecha_registro, calificacion
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            await execute_query(insert_query, (actividad_id, estudiante_id, nuevo_estado, fecha_entrega, fecha_registro, calificacion_final))

            data_resp = {
                "estado": nuevo_estado,
                "calificacion": calificacion_final,
                "fecha_entrega_real": str(fecha_entrega) if fecha_entrega else None,
                "fecha_registro": str(fecha_registro),
                "estudiante": {
                    "id": estudiante.get("id_estudiante"),
                    "nombre": estudiante.get("nombre", ""),
                    "apellido": estudiante.get("apellido", "")
                }
            }

            return {
                "success": True,
                "message": f"🆕 Registro creado para {data_resp['estudiante']['nombre']} {data_resp['estudiante']['apellido']} con estado: {nuevo_estado}",
                "data": data_resp
            }

    except HTTPException:
        raise  # volver a lanzar errores esperados

    except Exception as e:
        print("⚠️ Error interno:", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar estado: {str(e)}"
        )

@router.get("/actividades/{actividad_id}")
async def obtener_actividad_por_id(actividad_id: int):
    """
    Obtiene los detalles completos de una actividad específica
    """
    try:
        query = """
            SELECT 
                id_actividad, 
                id_clase, 
                titulo, 
                descripcion, 
                tipo_actividad, 
                fecha_entrega, 
                fecha_creacion, 
                valor_maximo
            FROM actividad
            WHERE id_actividad = %s 
        """
        
        actividad = await fetch_one(query, (actividad_id,))
        
        if not actividad:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró la actividad con ID {actividad_id}"
            )
        
        return actividad
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"⚠️ Error al obtener actividad: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener actividad: {str(e)}"
        )

# Modelo de respuesta
class ActividadOut(BaseModel):
    id_actividad: int
    titulo: str
    descripcion: Optional[str]
    fecha_entrega: str
    fecha_creacion: str
    valor_maximo: int
    estado_estudiante: Optional[str] = None  # pendiente, entregado, no entregado

#Cambio
@router.get("/{id_clase}/actividades-recientes", response_model=List[ActividadOut])
async def get_actividades_recientes(
    id_clase: int,
    id_estudiante: Optional[int] = Query(None, description="ID del estudiante (opcional)")
):
    """
    Retorna las últimas 5 actividades de la clase.
    Si se pasa id_estudiante, también devuelve su estado de entrega.
    """
    try:
        query_actividades = """
        SELECT id_actividad, titulo, descripcion, fecha_entrega, fecha_creacion, valor_maximo, tipo_actividad
        FROM actividad
        WHERE id_clase = %s
        ORDER BY fecha_creacion DESC
        LIMIT 5
        """
        actividades = await fetch_all(query_actividades, (id_clase,))
        resultado = []

        for act in actividades:
            estado = None
            if id_estudiante:
                query_estado = """
                SELECT estado 
                FROM actividad_estudiante 
                WHERE id_actividad = %s AND id_estudiante = %s
                """
                registro = await fetch_all(query_estado, (act["id_actividad"], id_estudiante))
                if registro:
                    estado = registro[0]["estado"]

            resultado.append({
                "id_actividad": act["id_actividad"],
                "titulo": act["titulo"],
                "descripcion": act["descripcion"],
                "fecha_entrega": convertir_fecha_a_cdmx(act["fecha_entrega"]),
                "fecha_creacion": convertir_fecha_a_cdmx(act["fecha_creacion"]),
                "valor_maximo": int(act["valor_maximo"]),
                "tipo_actividad": act["tipo_actividad"],   # ✅ agregado aquí
                "estado_estudiante": estado
            })

        logger.info(f"✅ Actividades obtenidas para clase {id_clase}, total: {len(resultado)}")
        return resultado

    except Exception as e:
        logger.error(f"❌ Error al obtener actividades: {e}")
        return []
    
#Nuevo
@router.get("/historial/{id_clase}")
async def get_historial(id_clase: int):
    """
    Retorna el historial de alumnos por clase con actividades,
    usando calificación real en lugar de valor_maximo.
    Incluye el tipo de actividad.
    
    🔥 CORREGIDO: Ahora solo trae actividades de la clase especificada.
    """

    try:
        # 1️⃣ Obtener el grupo de la clase
        clase_query = "SELECT id_grupo FROM clase WHERE id_clase = %s"
        clase = await fetch_one(clase_query, (id_clase,))
        if not clase:
            raise HTTPException(status_code=404, detail="Clase no encontrada")

        id_grupo = clase["id_grupo"]

        # 2️⃣ Traer todas las actividades de la clase
        actividades_query = """
            SELECT id_actividad, titulo, valor_maximo
            FROM actividad
            WHERE id_clase = %s
        """
        actividadesClase = await fetch_all(actividades_query, (id_clase,))

        # 3️⃣ 🔥 CORREGIDO: Filtrar actividades SOLO de esta clase
        estudiantes_query = """
            SELECT e.id_estudiante, e.nombre, e.apellido, e.matricula, e.no_lista,
                   e.correo, e.estado_actual, g.nombre AS grupo,
                   JSON_ARRAYAGG(
                       JSON_OBJECT(
                           'id_actividad', a.id_actividad,
                           'titulo', a.titulo,
                           'descripcion', a.descripcion,
                           'tipo_actividad', a.tipo_actividad,
                           'fecha_entrega', a.fecha_entrega,
                           'valor_maximo', a.valor_maximo,
                           'estado', ae.estado,
                           'fecha_entrega_real', ae.fecha_entrega_real,
                           'calificacion', ae.calificacion
                       )
                   ) AS actividades
            FROM estudiante e
            JOIN grupo g ON e.id_grupo = g.id_grupo
            LEFT JOIN actividad a ON a.id_clase = %s
            LEFT JOIN actividad_estudiante ae ON ae.id_estudiante = e.id_estudiante 
                                               AND ae.id_actividad = a.id_actividad
            WHERE e.id_grupo = %s
            GROUP BY e.id_estudiante, e.nombre, e.apellido, e.matricula,
                     e.no_lista, e.correo, e.estado_actual, g.nombre
            ORDER BY CAST(e.no_lista AS UNSIGNED), e.apellido ASC, e.nombre ASC
        """
        estudiantes = await fetch_all(estudiantes_query, (id_clase, id_grupo))

        # 4️⃣ Procesar entregado y ponderación
        historial = []
        for est in estudiantes:
            actividades = est["actividades"]

            # ⚠️ JSON_ARRAYAGG regresa string en aiomysql, hay que parsear
            if isinstance(actividades, str):
                actividades = json.loads(actividades)

            # 🔥 FILTRAR actividades NULL (cuando no hay entregas)
            actividades_validas = [act for act in actividades if act.get("id_actividad") is not None]

            entregado = 0
            ponderacion = 0

            for act in actividades_validas:
                if act.get("estado") == "entregado":
                    entregado += 1
                    calificacion = act.get("calificacion")
                    valor_maximo = act.get("valor_maximo") or 0
                    ponderacion += calificacion if calificacion is not None else valor_maximo

            historial.append({
                "id_estudiante": est["id_estudiante"],
                "nombre": est["nombre"],
                "apellido": est["apellido"],
                "matricula": est["matricula"],
                "no_lista": est["no_lista"],
                "correo": est["correo"],
                "estado_actual": est["estado_actual"],
                "grupo": est["grupo"],
                "actividades": actividades_validas,  # 🔥 Solo actividades válidas
                "entregado": entregado,
                "ponderacion": ponderacion
            })

        total_actividades = len(actividadesClase)
        total_ponderacion = sum(act["valor_maximo"] or 0 for act in actividadesClase)

        return {
            "total_actividades": total_actividades,
            "total_ponderacion": total_ponderacion,
            "historial": historial
        }

    except Exception as e:
        logger.error(f"❌ Error al obtener historial: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
@router.get("/alumno/{id_estudiante}/clase/{id_clase}")
async def get_detalle_alumno(id_estudiante: int, id_clase: int):
    """
    Retorna los detalles completos de un alumno en una clase,
    incluyendo actividades con calificación real y estado de entrega.
    """
    try:
        query = """
            SELECT 
                -- Datos del alumno
                e.id_estudiante,
                e.nombre AS nombre_alumno,
                e.apellido AS apellido_alumno,
                e.matricula,
                e.correo,
                g.nombre AS grupo,
                g.turno,

                -- Datos de la clase
                c.id_clase,
                c.nombre_clase,
                m.nombre AS materia,
                p.nombre AS profesor,

                -- Datos de las actividades
                a.id_actividad,
                a.titulo AS titulo_actividad,
                a.descripcion AS descripcion_actividad,
                a.fecha_entrega,
                a.valor_maximo,
                a.tipo_actividad,
                ae.estado AS estado_entrega,
                ae.fecha_entrega_real,
                ae.calificacion
            FROM estudiante e
            JOIN grupo g ON e.id_grupo = g.id_grupo
            JOIN clase c ON c.id_clase = %s
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN profesor p ON c.id_profesor = p.id_profesor
            LEFT JOIN actividad a ON a.id_clase = c.id_clase
            LEFT JOIN actividad_estudiante ae 
                ON a.id_actividad = ae.id_actividad AND ae.id_estudiante = e.id_estudiante
            WHERE e.id_estudiante = %s
            ORDER BY a.fecha_creacion ASC
        """

        rows = await fetch_all(query, (id_clase, id_estudiante))

        if not rows:
            raise HTTPException(status_code=404, detail="No se encontró información para este alumno en esta clase")

        # Alumno
        alumno_info = {
            "id_estudiante": rows[0]["id_estudiante"],
            "nombre": rows[0]["nombre_alumno"],
            "apellido": rows[0]["apellido_alumno"],
            "matricula": rows[0]["matricula"],
            "correo": rows[0]["correo"],
            "grupo": rows[0]["grupo"],
            "turno": rows[0]["turno"]
        }

        # Clase
        clase_info = {
            "id_clase": rows[0]["id_clase"],
            "nombre_clase": rows[0]["nombre_clase"],
            "materia": rows[0]["materia"],
            "profesor": rows[0]["profesor"]
        }

        # Actividades
        actividades = [
            {
                "id_actividad": r["id_actividad"],
                "titulo": r["titulo_actividad"],
                "descripcion": r["descripcion_actividad"],
                "fecha_entrega": convertir_fecha_a_cdmx(r["fecha_entrega"]),
                "valor_maximo": int(r["valor_maximo"]) if r["valor_maximo"] is not None else 0,
                "tipo_actividad": r["tipo_actividad"],
                "estado": r["estado_entrega"],
                "fecha_entrega_real": convertir_fecha_a_cdmx(r["fecha_entrega_real"]),
                "calificacion": int(r["calificacion"]) if r["calificacion"] is not None else None
            }
            for r in rows if r["id_actividad"] is not None
        ]

        return {
            "alumno": alumno_info,
            "clase": clase_info,
            "actividades": actividades
        }

    except Exception as e:
        print(f"❌ Error al obtener detalle del alumno: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Schema para request
class ValidarEntregaRequest(BaseModel):
    qr: str
    id_actividad: int

@router.post("/validar-entrega")
async def validar_entrega(data: ValidarEntregaRequest):
    logger.info("=== VALIDAR ENTREGA - REQUEST RECIBIDO ===")
    logger.info(f"Body: {data.json()}")

    qr = data.qr
    id_actividad = data.id_actividad

    if not qr or not id_actividad:
        raise HTTPException(status_code=400, detail="Falta QR o id_actividad")

    # Desencriptar QR
    fernet_key = os.getenv("FERNET_KEY").encode()  # debe estar en .env
    fernet = Fernet(fernet_key)

    try:
        decrypted_bytes = fernet.decrypt(qr.encode())
        decrypted = decrypted_bytes.decode()
        logger.info(f"QR desencriptado exitosamente: {decrypted}")
    except InvalidToken:
        logger.error("QR inválido o malformado")
        raise HTTPException(status_code=400, detail="QR inválido")

    partes = [p.strip() for p in decrypted.split("|")]
    if len(partes) < 4:
        raise HTTPException(status_code=400, detail="Formato QR inválido")

    nombre_completo, matricula, grupo_qr, *_ = partes

    # --- Consultas DB usando helpers ---
    actividad = await fetch_one(
        "SELECT id_actividad, id_clase, fecha_entrega, valor_maximo, tipo_actividad "
        "FROM actividad WHERE id_actividad=%s",
        (id_actividad,)
    )
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    matricula_str = matricula.strip()

    estudiante = await fetch_one(
        "SELECT id_estudiante, id_grupo FROM estudiante WHERE matricula=%s",
        (matricula_str,)
    )
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    grupo_db = await fetch_one(
        "SELECT nombre FROM grupo WHERE id_grupo=%s",
        (estudiante['id_grupo'],)
    )
    if not grupo_db or grupo_qr.lower() != grupo_db['nombre'].lower():
        raise HTTPException(status_code=400, detail="El grupo del estudiante no coincide con el QR")

    clase = await fetch_one(
        "SELECT id_grupo FROM clase WHERE id_clase=%s",
        (actividad['id_clase'],)
    )
    if not clase or clase['id_grupo'] != estudiante['id_grupo']:
        raise HTTPException(status_code=400, detail="La actividad no corresponde al grupo del estudiante")

    # Fecha actual CDMX
    fecha_entrega_real = obtener_fecha_hora_cdmx_completa()
    
    # Convertir a datetime si viene como string
# Convertir ISO string a datetime si es necesario
    if isinstance(fecha_entrega_real, str):
        try:
            fecha_entrega_real = datetime.fromisoformat(fecha_entrega_real)
        except ValueError:
            logger.error(f"⚠️ Formato inesperado en fecha_entrega_real: {fecha_entrega_real}")
            raise HTTPException(status_code=500, detail="Error con la fecha del sistema")

    entrega = await fetch_one(
        "SELECT estado, calificacion FROM actividad_estudiante "
        "WHERE id_actividad=%s AND id_estudiante=%s",
        (id_actividad, estudiante['id_estudiante'])
    )

    if entrega and entrega['estado'] == 'entregado':
        return {
            "success": True,
            "tarde": False,
            "id_estudiante": estudiante['id_estudiante'],
            "nombre": nombre_completo,
            "mensaje": f"({actividad['tipo_actividad']}) ya fue entregada anteriormente."
        }

    # Comparar fechas
    fecha_entrega_actividad = actividad['fecha_entrega']
    es_tarde = fecha_entrega_real > fecha_entrega_actividad
    es_examen = actividad['tipo_actividad'] == 'examen'

    if es_tarde or es_examen:
        return {
            "success": True,
            "tarde": True,
            "id_estudiante": estudiante['id_estudiante'],
            "nombre": nombre_completo,
            "mensaje": "Examen requiere calificación manual." if es_examen else "Entrega fuera de tiempo, se requiere calificación manual."
        }
    else:
        return {
            "success": True,
            "tarde": False,
            "id_estudiante": estudiante['id_estudiante'],
            "nombre": nombre_completo,
            "calificacion": actividad['valor_maximo'],
            "mensaje": "Entrega a tiempo, se asignará calificación máxima automáticamente."
        }