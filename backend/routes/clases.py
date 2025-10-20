from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional, List
from utils.fecha import obtener_fecha_hora_cdmx
from config.db import fetch_all, fetch_one
from datetime import datetime, timedelta
from routes.ws_manager import manager
import asyncio
from pydantic import BaseModel   # ✅ <--- ESTA LÍNEA ES LA CLAVE

router = APIRouter()

# =======================
# /api/clases/hoy
# =======================

def convertir_a_hora(valor) -> str:
    """Convierte timedelta (TIME de MySQL) a 'HH:MM:SS'."""
    if isinstance(valor, timedelta):
        total_segundos = int(valor.total_seconds())
        h = total_segundos // 3600
        m = (total_segundos % 3600) // 60
        s = total_segundos % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    return str(valor) 

@router.get("/hoy")
async def obtener_clases_hoy(turno: Optional[str] = None):
    """
    Devuelve las clases del día de hoy según el turno.
    Si no se especifica turno, lo detecta automáticamente según la hora actual.
    """
    try:
        datos_cdmx = obtener_fecha_hora_cdmx()
        fecha_hoy = datos_cdmx["fecha"]
        dia_semana = datos_cdmx["dia"]
        hora_actual = datos_cdmx["hora"]  # Esto es un objeto time

        # Si no se especifica turno, detectarlo automáticamente
        if turno is None:
            # Matutino: 7:20 - 13:50
            if hora_actual >= datetime.strptime("07:20:00", "%H:%M:%S").time() and \
               hora_actual <= datetime.strptime("13:50:00", "%H:%M:%S").time():
                turno = "matutino"
            # Vespertino: 14:10 - 19:50
            elif hora_actual >= datetime.strptime("14:10:00", "%H:%M:%S").time() and \
                 hora_actual <= datetime.strptime("19:50:00", "%H:%M:%S").time():
                turno = "vespertino"
            # Fuera de horario: mostrar el siguiente turno
            elif hora_actual < datetime.strptime("07:20:00", "%H:%M:%S").time():
                turno = "matutino"  # Antes de las 7:20, mostrar matutino
            else:
                turno = "vespertino"  # Después de las 19:50, mostrar vespertino del día

        # Definir horarios por turno
        if turno == "matutino":
            hora_inicio_turno = "07:20:00"
            hora_fin_turno    = "13:50:00"
        elif turno == "vespertino":
            hora_inicio_turno = "14:10:00"
            hora_fin_turno    = "19:50:00"
        else:  # turno = "todos"
            hora_inicio_turno = "00:00:00"
            hora_fin_turno    = "23:59:59"

        query = """
            SELECT 
                c.id_clase,
                m.nombre AS nombre_materia,
                c.nrc,
                g.nombre AS nombre_grupo,
                g.id_grupo,
                hc.hora_inicio,
                hc.hora_fin,
                COUNT(DISTINCT e.id_estudiante) AS total_estudiantes,
                COALESCE(SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END), 0) AS presentes,
                COALESCE(SUM(CASE WHEN a.estado = 'justificante' THEN 1 ELSE 0 END), 0) AS justificantes,
                COUNT(DISTINCT e.id_estudiante) - 
                COALESCE(SUM(CASE WHEN a.estado IN ('presente','justificante') THEN 1 ELSE 0 END), 0) AS ausentes
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN estudiante e ON e.id_grupo = g.id_grupo AND e.estado_actual = 'activo'
            LEFT JOIN asistencia a 
                ON a.id_clase = c.id_clase AND a.id_estudiante = e.id_estudiante AND a.fecha = %s
            WHERE hc.dia = %s
              AND hc.hora_inicio < %s
              AND hc.hora_fin   > %s
            GROUP BY c.id_clase, m.nombre, c.nrc, g.nombre, g.id_grupo, hc.hora_inicio, hc.hora_fin
            ORDER BY hc.hora_inicio ASC
        """
        result = await fetch_all(query, (fecha_hoy, dia_semana, hora_fin_turno, hora_inicio_turno))
        
        # Convertir los campos de hora
        for clase in result:
            clase['hora_inicio'] = convertir_a_hora(clase['hora_inicio'])
            clase['hora_fin'] = convertir_a_hora(clase['hora_fin'])
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener clases de hoy: {str(e)}")

# =======================
# /api/clases/hoy/todas
# =======================
@router.get("/hoy/todas")
async def obtener_todas_clases_hoy():
    try:
        dia_semana = obtener_fecha_hora_cdmx()["dia"]

        query = """
            SELECT 
                c.id_clase,
                m.nombre AS nombre_materia,
                c.nrc,
                g.nombre AS nombre_grupo,
                g.id_grupo,
                hc.hora_inicio,
                hc.hora_fin,
                p.nombre AS nombre_profesor
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN profesor p ON c.id_profesor = p.id_profesor
            WHERE hc.dia = %s
            ORDER BY hc.hora_inicio ASC
        """
        result = await fetch_all(query, (dia_semana,))
        for clase in result:
            clase['hora_inicio'] = convertir_a_hora(clase['hora_inicio'])
            clase['hora_fin']    = convertir_a_hora(clase['hora_fin'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener todas las clases: {str(e)}")


# =======================
# /api/clases/por-bloque
# =======================
# ===== VERSIÓN FINAL OPTIMIZADA =====

@router.get("/por-bloque")
async def clases_por_bloque(
    horaInicio: str = Query(..., description="Hora de inicio en formato HH:MM:SS"),
    horaFin: str = Query(..., description="Hora de fin en formato HH:MM:SS"), 
    dia: str = Query(..., description="Día de la semana")
):
    """Endpoint principal para obtener clases por bloque de horario"""
    try:
        fecha_hoy = obtener_fecha_hora_cdmx()["fecha"]
        
        query = """
            SELECT 
                c.id_clase,
                m.nombre AS nombre_materia,
                c.nrc,
                g.nombre AS nombre_grupo,
                g.id_grupo,
                p.nombre AS nombre_profesor,
                c.aula AS nombre_aula,
                hc.hora_inicio,
                hc.hora_fin,
                COUNT(DISTINCT e.id_estudiante) AS total_estudiantes,
                COALESCE(SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END), 0) AS presentes,
                COALESCE(SUM(CASE WHEN a.estado = 'justificante' THEN 1 ELSE 0 END), 0) AS justificantes
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN profesor p ON c.id_profesor = p.id_profesor
            LEFT JOIN estudiante e ON e.id_grupo = g.id_grupo AND e.estado_actual = 'activo'
            LEFT JOIN asistencia a 
                ON a.id_clase = c.id_clase 
                AND a.id_estudiante = e.id_estudiante 
                AND a.fecha = %s
            WHERE LOWER(hc.dia) = LOWER(%s)
              AND CAST(hc.hora_inicio AS TIME) >= CAST(%s AS TIME)
              AND CAST(hc.hora_inicio AS TIME) <= CAST(%s AS TIME)
            GROUP BY 
                c.id_clase, m.nombre, c.nrc, g.nombre, g.id_grupo, 
                p.nombre, c.aula, hc.hora_inicio, hc.hora_fin
            ORDER BY hc.hora_inicio ASC
        """
        
        result = await fetch_all(query, (fecha_hoy, dia, horaInicio, horaFin))
        
        # Procesar resultados
        for clase in result:
            clase['ausentes'] = clase['total_estudiantes'] - clase['presentes'] - clase['justificantes']
            
            # Convertir timedelta a string
            if hasattr(clase['hora_inicio'], 'total_seconds'):
                clase['hora_inicio'] = convertir_timedelta_a_string(clase['hora_inicio'])
            if hasattr(clase['hora_fin'], 'total_seconds'):
                clase['hora_fin'] = convertir_timedelta_a_string(clase['hora_fin'])
        
        return result
        
    except Exception as e:
        print(f"Error en /por-bloque: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener clases por bloque: {str(e)}")

@router.get("/por-dia/{dia}")
async def clases_por_dia(dia: str):
    """Obtener todas las clases de un día específico"""
    try:
        fecha_hoy = obtener_fecha_hora_cdmx()["fecha"]
        
        query = """
            SELECT 
                c.id_clase,
                m.nombre AS nombre_materia,
                c.nrc,
                g.nombre AS nombre_grupo,
                g.id_grupo,
                p.nombre AS nombre_profesor,
                c.aula AS nombre_aula,
                hc.hora_inicio,
                hc.hora_fin,
                COUNT(DISTINCT e.id_estudiante) AS total_estudiantes,
                COALESCE(SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END), 0) AS presentes,
                COALESCE(SUM(CASE WHEN a.estado = 'justificante' THEN 1 ELSE 0 END), 0) AS justificantes
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN profesor p ON c.id_profesor = p.id_profesor
            LEFT JOIN estudiante e ON e.id_grupo = g.id_grupo AND e.estado_actual = 'activo'
            LEFT JOIN asistencia a 
                ON a.id_clase = c.id_clase 
                AND a.id_estudiante = e.id_estudiante 
                AND a.fecha = %s
            WHERE LOWER(hc.dia) = LOWER(%s)
            GROUP BY 
                c.id_clase, m.nombre, c.nrc, g.nombre, g.id_grupo, 
                p.nombre, c.aula, hc.hora_inicio, hc.hora_fin
            ORDER BY hc.hora_inicio ASC
        """
        
        result = await fetch_all(query, (fecha_hoy, dia))
        
        # Procesar resultados
        for clase in result:
            clase['ausentes'] = clase['total_estudiantes'] - clase['presentes'] - clase['justificantes']
            
            if hasattr(clase['hora_inicio'], 'total_seconds'):
                clase['hora_inicio'] = convertir_timedelta_a_string(clase['hora_inicio'])
            if hasattr(clase['hora_fin'], 'total_seconds'):
                clase['hora_fin'] = convertir_timedelta_a_string(clase['hora_fin'])
        
        return result
        
    except Exception as e:
        print(f"Error en /por-dia: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener clases del día: {str(e)}")

# ===== FUNCIÓN HELPER =====
def convertir_timedelta_a_string(timedelta_obj):
    """Convierte un objeto timedelta a string formato HH:MM:SS"""
    if hasattr(timedelta_obj, 'total_seconds'):
        segundos_total = int(timedelta_obj.total_seconds())
        horas = segundos_total // 3600
        minutos = (segundos_total % 3600) // 60
        segundos = segundos_total % 60
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
    return str(timedelta_obj)

# ===== ENDPOINTS DE DEBUG (mantener solo si necesitas debugging) =====
@router.get("/debug-dia/{dia}")
async def debug_clases_dia(dia: str):
    """Debug: Ver todas las clases de un día específico"""
    try:
        query = """
            SELECT 
                hc.dia,
                hc.hora_inicio,
                hc.hora_fin,
                c.nrc,
                m.nombre as materia,
                g.nombre as grupo,
                p.nombre as profesor
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN profesor p ON c.id_profesor = p.id_profesor
            WHERE LOWER(hc.dia) = LOWER(%s)
            ORDER BY hc.hora_inicio
        """
        result = await fetch_all(query, (dia,))
        
        # Convertir campos de hora
        for row in result:
            if hasattr(row['hora_inicio'], 'total_seconds'):
                row['hora_inicio'] = convertir_timedelta_a_string(row['hora_inicio'])
            if hasattr(row['hora_fin'], 'total_seconds'):
                row['hora_fin'] = convertir_timedelta_a_string(row['hora_fin'])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/debug-grupos")
async def debug_grupos():
    """Debug: Ver grupos y cantidad de estudiantes"""
    try:
        query = """
            SELECT 
                g.id_grupo,
                g.nombre as grupo,
                COUNT(e.id_estudiante) as total_estudiantes,
                COUNT(CASE WHEN e.estado_actual = 'activo' THEN 1 END) as activos
            FROM grupo g
            LEFT JOIN estudiante e ON e.id_grupo = g.id_grupo
            GROUP BY g.id_grupo, g.nombre
            ORDER BY g.nombre
        """
        result = await fetch_all(query, ())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# =======================
# /api/clases/por-dia
# =======================
@router.get("/por-dia")
async def clases_por_dia(dia: str = Query(...), turno: Optional[str] = "matutino"):
    if not dia:
        raise HTTPException(status_code=400, detail="Falta el parámetro dia")
    try:
        fecha_hoy = obtener_fecha_hora_cdmx()["fecha"]

        if turno == "matutino":
            hora_inicio_turno = "07:00:00"
            hora_fin_turno = "13:05:00"
        elif turno == "vespertino":
            hora_inicio_turno = "13:35:00"
            hora_fin_turno = "19:20:00"
        else:
            hora_inicio_turno = "07:00:00"
            hora_fin_turno = "19:20:00"

        dia_lower = dia.lower()

        query = """
            SELECT 
                c.id_clase,
                m.nombre AS nombre_materia,
                c.nrc,
                g.nombre AS nombre_grupo,
                g.id_grupo,
                hc.hora_inicio,
                hc.hora_fin,
                COUNT(DISTINCT e.id_estudiante) AS total_estudiantes,
                COALESCE(SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END), 0) AS presentes,
                COALESCE(SUM(CASE WHEN a.estado = 'justificante' THEN 1 ELSE 0 END), 0) AS justificantes,
                COUNT(DISTINCT e.id_estudiante) - COALESCE(SUM(CASE WHEN a.estado IN ('presente','justificante') THEN 1 ELSE 0 END), 0) AS ausentes
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN estudiante e ON e.id_grupo = g.id_grupo AND e.estado_actual = 'activo'
            LEFT JOIN asistencia a 
                ON a.id_clase = c.id_clase AND a.id_estudiante = e.id_estudiante AND a.fecha = %s
            WHERE LOWER(hc.dia) = %s
              AND hc.hora_fin > %s
              AND hc.hora_inicio < %s
            GROUP BY c.id_clase, m.nombre, c.nrc, g.nombre, g.id_grupo, hc.hora_inicio, hc.hora_fin
            ORDER BY hc.hora_inicio ASC
        """
        result = await fetch_all(query, (fecha_hoy, dia_lower, hora_inicio_turno, hora_fin_turno))
        
        # Convertir los campos de hora
        for clase in result:
            clase['hora_inicio'] = convertir_a_hora(clase['hora_inicio'])
            clase['hora_fin']    = convertir_a_hora(clase['hora_fin'])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener clases por día: {str(e)}")


# =======================
# /api/clases?grupo=
# =======================

@router.get("/")
async def clases_por_grupo(grupo: str = Query(...)):
    try:
        query = """
            SELECT 
                c.id_clase, 
                c.nombre_clase,
                m.nombre AS nombre_materia,
                g.nombre AS nombre_grupo,
                p.nombre AS nombre_profesor,
                hc.dia,
                hc.hora_inicio, 
                hc.hora_fin
            FROM clase c
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN profesor p ON c.id_profesor = p.id_profesor
            LEFT JOIN horario_clase hc ON c.id_clase = hc.id_clase
            WHERE g.nombre = %s
            ORDER BY hc.dia, hc.hora_inicio
        """
        result = await fetch_all(query, (grupo,))
        for clase in result:
            clase['hora_inicio'] = convertir_a_hora(clase['hora_inicio'])
            clase['hora_fin']    = convertir_a_hora(clase['hora_fin'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener clases: {str(e)}")

@router.websocket("/ws/attendances")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket que envía actualizaciones de asistencia en tiempo real.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Solo mantén la conexión viva, sin bloquear
            await asyncio.sleep(1)  # ✅ Evita CPU al 100%
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Schema de respuesta
class ClaseInfo(BaseModel):
    id_clase: int
    materia: str
    grupo: str
    nrc: str = None
    aula: Optional[str] = None

class ClasesProfesorResponse(BaseModel):
    success: bool
    clases: List[ClaseInfo]
    total: int

@router.get("/profesor/{id_profesor}", response_model=ClasesProfesorResponse)
async def obtener_clases_profesor(id_profesor: int):
    """
    Obtiene todas las clases asignadas a un profesor.
    Usado por la app móvil para seleccionar clase en el login del dashboard.
    
    URL: GET /api/clases/profesor/{id_profesor}
    """
    try:
        # Validar que el profesor existe
        profesor = await fetch_one(
            "SELECT id_profesor, nombre FROM profesor WHERE id_profesor = %s",
            (id_profesor,)
        )
        
        if not profesor:
            raise HTTPException(
                status_code=404,
                detail=f"Profesor con ID {id_profesor} no encontrado"
            )
        
        # Obtener las clases del profesor
        query = """
            SELECT 
                c.id_clase,
                c.nrc,
                c.aula,
                m.nombre as materia,
                g.nombre as grupo
            FROM clase c
            INNER JOIN materia m ON c.id_materia = m.id_materia
            INNER JOIN grupo g ON c.id_grupo = g.id_grupo
            WHERE c.id_profesor = %s
            ORDER BY m.nombre, g.nombre
        """
        
        clases = await fetch_all(query, (id_profesor,))
        
        # Transformar resultado
        clases_info = [
            ClaseInfo(
                id_clase=clase['id_clase'],
                materia=clase['materia'],
                grupo=clase['grupo'],
                nrc=clase.get('nrc'),
                aula=clase.get('aula')
            )
            for clase in clases
        ]
        
        return ClasesProfesorResponse(
            success=True,
            clases=clases_info,
            total=len(clases_info)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo clases del profesor {id_profesor}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )