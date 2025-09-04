from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from utils.fecha import obtener_fecha_hora_cdmx
from config.db import fetch_all, fetch_one
from datetime import datetime, timedelta

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
async def obtener_clases_hoy(turno: Optional[str] = "matutino"):
    """
    Devuelve las clases del día de hoy según el turno (matutino, vespertino o todos),
    considerando solapamiento de horarios.
    """
    try:
        fecha_hoy = obtener_fecha_hora_cdmx()["fecha"]
        dia_semana = obtener_fecha_hora_cdmx()["dia"]

        # Definir horarios por turno
        if turno == "matutino":
            hora_inicio_turno = "07:00:00"
            hora_fin_turno    = "13:05:00"
        elif turno == "vespertino":
            hora_inicio_turno = "13:35:00"
            hora_fin_turno    = "19:20:00"
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

@router.get("/por-bloque")
async def clases_por_bloque(horaInicio: str = Query(...), horaFin: str = Query(...), dia: str = Query(...)):
    if not horaInicio or not horaFin or not dia:
        raise HTTPException(status_code=400, detail="Faltan parámetros horaInicio, horaFin o dia")
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
            JOIN profesor p ON c.id_profesor = p.id_profesor
            JOIN estudiante e ON e.id_grupo = g.id_grupo AND e.estado_actual = 'activo'
            LEFT JOIN asistencia a 
                ON a.id_clase = c.id_clase AND a.id_estudiante = e.id_estudiante AND a.fecha = %s
            WHERE LOWER(hc.dia) = LOWER(%s)
              AND hc.hora_fin > %s
              AND hc.hora_inicio < %s
            GROUP BY c.id_clase, m.nombre, c.nrc, g.nombre, g.id_grupo, p.nombre, hc.hora_inicio, hc.hora_fin
            ORDER BY hc.hora_inicio ASC
        """
        result = await fetch_all(query, (fecha_hoy, dia, horaInicio, horaFin))
        
        # Convertir los campos de hora
        for clase in result:
            clase['hora_inicio'] = convertir_a_hora(clase['hora_inicio'])
            clase['hora_fin']    = convertir_a_hora(clase['hora_fin'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener clases por bloque: {str(e)}")
    

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