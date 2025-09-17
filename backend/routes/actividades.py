from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime
import aiomysql
from config.db import fetch_one, fetch_all, execute_query
import pytz
from utils.fecha import obtener_fecha_hora_cdmx_completa, convertir_fecha_a_cdmx
import os
import logging
from cryptography.fernet import Fernet, InvalidToken
from typing import List, Optional

router = APIRouter()

logger = logging.getLogger("api_actividades")

# Schema para crear o actualizar actividad
class ActividadCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=100)
    descripcion: str | None = None
    fecha_entrega: str  # formato: "YYYY-MM-DD"
    hora_entrega: str   # formato: "HH:MM:SS"
    id_clase: int
    valor_maximo: float = Field(..., ge=0, le=10)


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


# --- Crear nueva actividad ---
@router.post("/")
async def crear_actividad(data: ActividadCreate):
    try:
        # Combinar fecha y hora de entrega
        fecha_entrega_completa = f"{data.fecha_entrega} {data.hora_entrega}"
        fecha_creacion = datetime.now()

        query = """
            INSERT INTO actividad (titulo, descripcion, fecha_creacion, fecha_entrega, id_clase, valor_maximo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            data.titulo,
            data.descripcion,
            fecha_creacion,
            fecha_entrega_completa,
            data.id_clase,
            data.valor_maximo
        )

        id_actividad = await execute_query(query, values)
        return {"mensaje": "Actividad creada con éxito", "id_actividad": id_actividad}

    except Exception as e:
        print(f"Error crear_actividad: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error creando la actividad")


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

# Clave Fernet desde .env
# Configuración de Fernet
FERNET_KEY = os.getenv('FERNET_KEY')
if not FERNET_KEY:
    raise ValueError("FERNET_KEY no está configurada en las variables de entorno")
fernet_instance = Fernet(FERNET_KEY)


@router.post("/entrega")
async def registrar_entrega(request: EntregaQRRequest):
    if not request.qr or not request.id_actividad:
        raise HTTPException(status_code=400, detail="Falta QR o id_actividad")

    try:
        # 🔐 Desencriptar QR
        fernet_instance = Fernet(FERNET_KEY)
        decrypted = fernet_instance.decrypt(request.qr.encode()).decode("utf-8")
        logging.info(f"QR desencriptado: {decrypted}")

        partes = [p.strip() for p in decrypted.split("|")]
        if len(partes) < 4:
            raise HTTPException(status_code=400, detail="Formato QR inválido")

        nombre_completo = partes[0]
        matricula = partes[1]
        grupo_qr = partes[2]
        clave_unica = partes[3]

        # 1️⃣ Validar actividad
        actividad = await fetch_one(
            """
            SELECT id_actividad, id_clase, fecha_entrega, valor_maximo
            FROM actividad
            WHERE id_actividad=%s AND fecha_entrega >= CURDATE()
            """,
            (request.id_actividad,)
        )
        if not actividad:
            raise HTTPException(status_code=400, detail="Actividad inválida o vencida")

        # 2️⃣ Buscar estudiante por matrícula
        estudiante = await fetch_one(
            "SELECT id_estudiante, id_grupo FROM estudiante WHERE matricula=%s",
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

        # 4️⃣ Validar que la actividad corresponde al grupo del estudiante
        clase = await fetch_one(
            "SELECT id_grupo FROM clase WHERE id_clase=%s",
            (actividad["id_clase"],)
        )
        if not clase or clase["id_grupo"] != estudiante["id_grupo"]:
            raise HTTPException(status_code=400, detail="La actividad no corresponde al grupo del estudiante")

        # 5️⃣ Fecha de entrega real
        fecha_entrega_real = obtener_fecha_hora_cdmx_completa()

        # 6️⃣ Verificar si ya existe registro
        entrega = await fetch_one(
            "SELECT estado FROM actividad_estudiante WHERE id_actividad=%s AND id_estudiante=%s",
            (request.id_actividad, estudiante["id_estudiante"])
        )

        if entrega:
            if entrega["estado"] == "entregado":
                return {"success": True, "mensaje": f"{nombre_completo} ya entregó esta actividad anteriormente."}

            # Actualizar registro existente
            await execute_query(
                """
                UPDATE actividad_estudiante
                SET estado='entregado', fecha_entrega_real=%s, calificacion=%s
                WHERE id_actividad=%s AND id_estudiante=%s
                """,
                (fecha_entrega_real, actividad["valor_maximo"], request.id_actividad, estudiante["id_estudiante"])
            )
            return {"success": True, "mensaje": f"{nombre_completo} actualizó su entrega de la actividad"}

        # 7️⃣ Insertar nuevo registro
        await execute_query(
            """
            INSERT INTO actividad_estudiante
            (id_actividad, id_estudiante, estado, fecha_entrega, fecha_creacion, fecha_entrega_real, calificacion)
            VALUES (%s, %s, 'entregado', %s, NOW(), %s, %s)
            """,
            (request.id_actividad, estudiante["id_estudiante"], actividad["fecha_entrega"], fecha_entrega_real, actividad["valor_maximo"])
        )

        return {"success": True, "mensaje": f"{nombre_completo} entregó la actividad"}

    except InvalidToken:
        raise HTTPException(status_code=400, detail="QR inválido o expirado")
    except Exception as e:
        logging.error(f"Error en registrar_entrega: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")
    

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
            ae.id_actividad_estudiante
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
                "id_actividad_estudiante": estudiante.get("id_actividad_estudiante", 0)
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

# DTO de salida (simplificado)
class EstadoEstudianteResponse(BaseModel):
    success: bool
    message: str
    data: dict = None

@router.post("/actualizar-estado-estudiante", response_model=EstadoEstudianteResponse)
async def actualizar_estado_estudiante(payload: EstadoEstudianteRequest):
    estudiante_id = payload.estudiante_id
    actividad_id = payload.actividad_id
    nuevo_estado = payload.nuevo_estado.lower()

    # Validaciones
    if not estudiante_id or not actividad_id or not nuevo_estado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faltan datos requeridos"
        )

    estados_validos = ['pendiente', 'entregado', 'no entregado']
    if nuevo_estado not in estados_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado no válido. Debe ser uno de: {', '.join(estados_validos)}"
        )

    try:
        # 1. Verificar si ya existe registro
        check_query = """
            SELECT ae.id_actividad_estudiante, ae.estado, 
                   e.nombre, e.apellido, e.id_estudiante
            FROM actividad_estudiante ae
            JOIN estudiante e ON ae.id_estudiante = e.id_estudiante
            WHERE ae.id_actividad = %s AND ae.id_estudiante = %s
        """
        existente = await fetch_one(check_query, (actividad_id, estudiante_id))

        fecha_entrega = obtener_fecha_hora_cdmx_completa() if nuevo_estado == 'entregado' else None

        if existente:
            # Actualizar registro existente
            update_query = """
                UPDATE actividad_estudiante
                SET estado = %s,
                    fecha_entrega_real = %s
                WHERE id_actividad = %s AND id_estudiante = %s
            """
            await execute_query(update_query, (nuevo_estado, fecha_entrega, actividad_id, estudiante_id))

            return {
                "success": True,
                "message": f"Estado de {existente['nombre']} {existente['apellido']} actualizado a: {nuevo_estado}",
                "data": {
                    "id_actividad_estudiante": existente['id_actividad_estudiante'],
                    "estado": nuevo_estado,
                    "fecha_entrega_real": fecha_entrega.isoformat() if fecha_entrega else None,
                    "estudiante": {
                        "id": existente['id_estudiante'],
                        "nombre": existente['nombre'],
                        "apellido": existente['apellido']
                    }
                }
            }
        else:
            # Verificar que el estudiante exista
            estudiante_query = "SELECT id_estudiante, nombre, apellido FROM estudiante WHERE id_estudiante = %s"
            estudiante = await fetch_one(estudiante_query, (estudiante_id,))
            if not estudiante:
                raise HTTPException(status_code=404, detail="El estudiante especificado no existe")

            fecha_registro = obtener_fecha_hora_cdmx_completa()
            insert_query = """
                INSERT INTO actividad_estudiante (id_actividad, id_estudiante, estado, fecha_entrega_real, fecha_registro)
                VALUES (%s, %s, %s, %s, %s)
            """
            await execute_query(insert_query, (actividad_id, estudiante_id, nuevo_estado, fecha_entrega, fecha_registro))

            return {
                "success": True,
                "message": f"Registro creado para {estudiante['nombre']} {estudiante['apellido']} con estado: {nuevo_estado}",
                "data": {
                    "estado": nuevo_estado,
                    "fecha_entrega_real": fecha_entrega.isoformat() if fecha_entrega else None,
                    "fecha_registro": fecha_registro.isoformat(),
                    "estudiante": {
                        "id": estudiante['id_estudiante'],
                        "nombre": estudiante['nombre'],
                        "apellido": estudiante['apellido']
                    }
                }
            }

    except Exception as e:
        # Manejo de errores genéricos
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar estado: {str(e)}"
        )
    
# Modelo de respuesta
class ActividadOut(BaseModel):
    id_actividad: int
    titulo: str
    descripcion: Optional[str]
    fecha_entrega: str
    fecha_creacion: str
    valor_maximo: float
    estado_estudiante: Optional[str] = None  # pendiente, entregado, no entregado

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
        SELECT id_actividad, titulo, descripcion, fecha_entrega, fecha_creacion, valor_maximo
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
                "valor_maximo": float(act["valor_maximo"]),
                "estado_estudiante": estado
            })

        logger.info(f"✅ Actividades obtenidas para clase {id_clase}, total: {len(resultado)}")
        return resultado

    except Exception as e:
        logger.error(f"❌ Error al obtener actividades: {e}")
        return []