from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import aiomysql
from utils.fecha import obtener_fecha_hora_cdmx, convertir_fecha_a_cdmx, obtener_fecha_hora_cdmx_completa
from config.db import fetch_one, fetch_all, execute_query


router = APIRouter()

def construir_condicion_fecha(fecha_inicio: Optional[str], fecha_fin: Optional[str]):
    condicion = ""
    if fecha_inicio and fecha_fin:
        condicion = f"AND a.fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
    elif fecha_inicio:
        condicion = f"AND a.fecha >= '{fecha_inicio}'"
    elif fecha_fin:
        condicion = f"AND a.fecha <= '{fecha_fin}'"
    return condicion

# Estadísticas generales por grupo
@router.get("/grupo/{id_grupo}")
async def estadisticas_grupo(id_grupo: int, fechaInicio: Optional[str] = None, fechaFin: Optional[str] = None):
    fecha_inicio = convertir_fecha_a_cdmx(fechaInicio) if fechaInicio else None
    fecha_fin = convertir_fecha_a_cdmx(fechaFin) if fechaFin else None
    condicion_fecha = construir_condicion_fecha(fecha_inicio, fecha_fin)

    query = f"""
        SELECT
            SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END) AS presentes,
            SUM(CASE WHEN a.estado = 'justificante' THEN 1 ELSE 0 END) AS justificantes,
            SUM(CASE WHEN a.estado = 'ausente' THEN 1 ELSE 0 END) AS ausentes,
            COUNT(*) AS total_registros,
            ROUND(SUM(CASE WHEN a.estado IN ('presente', 'justificante') THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS porcentaje_asistencia
        FROM asistencia a
        JOIN estudiante e ON a.id_estudiante = e.id_estudiante
        JOIN clase c ON a.id_clase = c.id_clase
        WHERE c.id_grupo = %s AND e.estado_actual = 'activo'
        {condicion_fecha}
    """
    try:
        row = await fetch_one(query, (id_grupo,))
        if not row or row['total_registros'] == 0:
            return {
                "presentes": 0, "justificantes": 0, "ausentes": 0, 
                "total_registros": 0, "porcentaje_asistencia": 0
            }
        return row
    except Exception as e:
        print("Error en /grupo/:", e)
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas del grupo")


# Detalle por materias dentro del grupo
@router.get("/grupo/{id_grupo}/materias")
async def estadisticas_grupo_materias(id_grupo: int, fechaInicio: Optional[str] = None, fechaFin: Optional[str] = None):
    fecha_inicio = convertir_fecha_a_cdmx(fechaInicio) if fechaInicio else None
    fecha_fin = convertir_fecha_a_cdmx(fechaFin) if fechaFin else None
    condicion_fecha = construir_condicion_fecha(fecha_inicio, fecha_fin)

    query = f"""
        SELECT
            m.nombre AS materia,
            SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END) AS presentes,
            SUM(CASE WHEN a.estado = 'justificante' THEN 1 ELSE 0 END) AS justificantes,
            SUM(CASE WHEN a.estado = 'ausente' THEN 1 ELSE 0 END) AS ausentes,
            COUNT(*) AS total_registros,
            ROUND(SUM(CASE WHEN a.estado IN ('presente', 'justificante') THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS porcentaje_asistencia
        FROM asistencia a
        JOIN estudiante e ON a.id_estudiante = e.id_estudiante
        JOIN clase c ON a.id_clase = c.id_clase
        JOIN materia m ON c.id_materia = m.id_materia
        WHERE c.id_grupo = %s AND e.estado_actual = 'activo'
        {condicion_fecha}
        GROUP BY m.id_materia, m.nombre
        ORDER BY m.nombre
    """
    try:
        rows = await fetch_all(query, (id_grupo,))
        return rows
    except Exception as e:
        print("Error en /grupo/:id_grupo/materias:", e)
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas por materia")


# Tendencia de asistencias por fecha
@router.get("/tendencia")
async def tendencia(id_grupo: int = Query(...), id_clase: Optional[int] = Query(None)):
    params = [id_grupo]
    filtro_clase = ""
    if id_clase:
        filtro_clase = "AND a.id_clase = %s"
        params.append(id_clase)

    query = f"""
        SELECT a.fecha, a.estado, COUNT(*) AS cantidad
        FROM asistencia a
        JOIN estudiante e ON a.id_estudiante = e.id_estudiante
        JOIN clase c ON a.id_clase = c.id_clase
        WHERE c.id_grupo = %s AND e.estado_actual = 'activo'
        {filtro_clase}
        GROUP BY a.fecha, a.estado
        ORDER BY a.fecha ASC
    """
    try:
        rows = await fetch_all(query, params)
        datos_por_fecha = {}
        for row in rows:
            fecha = convertir_fecha_a_cdmx(row["fecha"].strftime("%Y-%m-%d"))
            if fecha not in datos_por_fecha:
                datos_por_fecha[fecha] = {"fecha": fecha, "presente": 0, "ausente": 0, "justificante": 0}
            datos_por_fecha[fecha][row["estado"]] = int(row["cantidad"])
        return list(datos_por_fecha.values())
    except Exception as e:
        print("Error en /tendencia:", e)
        raise HTTPException(status_code=500, detail="Error al obtener la tendencia")


# Detalle completo de un grupo
@router.get("/detalle-grupo/{id_grupo}")
async def detalle_grupo(id_grupo: int):
    try:
        top_faltas_query = """
            SELECT CONCAT(e.nombre, ' ', e.apellido) AS nombre,
                   COUNT(*) AS faltas
            FROM asistencia a
            JOIN estudiante e ON a.id_estudiante = e.id_estudiante
            JOIN clase c ON a.id_clase = c.id_clase
            WHERE a.estado = 'ausente' AND c.id_grupo = %s AND e.estado_actual = 'activo'
            GROUP BY e.id_estudiante, e.nombre, e.apellido
            ORDER BY faltas DESC
            LIMIT 5
        """
        top_faltas = await fetch_all(top_faltas_query, (id_grupo,))

        top_asistencias_query = """
            SELECT CONCAT(e.nombre, ' ', e.apellido) AS nombre,
                   COUNT(*) AS asistencias
            FROM asistencia a
            JOIN estudiante e ON a.id_estudiante = e.id_estudiante
            JOIN clase c ON a.id_clase = c.id_clase
            WHERE a.estado = 'presente' AND c.id_grupo = %s AND e.estado_actual = 'activo'
            GROUP BY e.id_estudiante, e.nombre, e.apellido
            ORDER BY asistencias DESC
            LIMIT 5
        """
        top_asistencias = await fetch_all(top_asistencias_query, (id_grupo,))

        top_justificantes_query = """
            SELECT CONCAT(e.nombre, ' ', e.apellido) AS nombre,
                   COUNT(*) AS justificantes
            FROM asistencia a
            JOIN estudiante e ON a.id_estudiante = e.id_estudiante
            JOIN clase c ON a.id_clase = c.id_clase
            WHERE a.estado = 'justificante' AND c.id_grupo = %s AND e.estado_actual = 'activo'
            GROUP BY e.id_estudiante, e.nombre, e.apellido
            ORDER BY justificantes DESC
            LIMIT 5
        """
        top_justificantes = await fetch_all(top_justificantes_query, (id_grupo,))

        ranking_query = """
            SELECT e.id_estudiante AS id,
                   CONCAT(e.nombre, ' ', e.apellido) AS nombre,
                   SUM(CASE WHEN a.estado='presente' THEN 1 ELSE 0 END) AS asistencias,
                   SUM(CASE WHEN a.estado='ausente' THEN 1 ELSE 0 END) AS faltas,
                   SUM(CASE WHEN a.estado='justificante' THEN 1 ELSE 0 END) AS justificantes,
                   ROUND(SUM(CASE WHEN a.estado='presente' THEN 1 ELSE 0 END)/COUNT(*)*100,1) AS asistencia_porcentaje,
                   ROUND(SUM(CASE WHEN a.estado='ausente' THEN 1 ELSE 0 END)/COUNT(*)*100,1) AS faltas_porcentaje,
                   ROUND(SUM(CASE WHEN a.estado='justificante' THEN 1 ELSE 0 END)/COUNT(*)*100,1) AS justificantes_porcentaje
            FROM asistencia a
            JOIN estudiante e ON a.id_estudiante = e.id_estudiante
            JOIN clase c ON a.id_clase = c.id_clase
            WHERE c.id_grupo = %s AND e.estado_actual = 'activo'
            GROUP BY e.id_estudiante, e.nombre, e.apellido
            ORDER BY asistencia_porcentaje DESC
        """
        ranking = await fetch_all(ranking_query, (id_grupo,))

        materia_mas_faltada_query = """
            SELECT m.nombre, COUNT(*) AS total
            FROM asistencia a
            JOIN clase c ON a.id_clase = c.id_clase
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN estudiante e ON a.id_estudiante = e.id_estudiante
            WHERE a.estado='ausente' AND c.id_grupo = %s AND e.estado_actual = 'activo'
            GROUP BY m.id_materia, m.nombre
            ORDER BY total DESC
            LIMIT 2
        """
        materia_mas_faltada = await fetch_all(materia_mas_faltada_query, (id_grupo,))

        materia_mas_asistida_query = """
            SELECT m.nombre
            FROM asistencia a
            JOIN clase c ON a.id_clase = c.id_clase
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN estudiante e ON a.id_estudiante = e.id_estudiante
            WHERE a.estado='presente' AND c.id_grupo = %s AND e.estado_actual = 'activo'
            GROUP BY m.id_materia, m.nombre
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """
        materia_mas_asistida = await fetch_all(materia_mas_asistida_query, (id_grupo,))

        asistencia_perfecta_query = """
            SELECT CONCAT(e.nombre, ' ', e.apellido) AS nombre
            FROM estudiante e
            WHERE e.id_grupo = %s AND e.estado_actual = 'activo' AND NOT EXISTS (
                SELECT 1 FROM asistencia a
                JOIN clase c ON a.id_clase = c.id_clase
                WHERE a.id_estudiante = e.id_estudiante AND a.estado = 'ausente' AND c.id_grupo = %s
            )
        """
        asistencia_perfecta = await fetch_all(asistencia_perfecta_query, (id_grupo, id_grupo))

        promedios_query = """
            SELECT
                ROUND(AVG(CASE WHEN a.estado='presente' THEN 1 ELSE 0 END)*100,1) AS asistencia,
                ROUND(AVG(CASE WHEN a.estado='ausente' THEN 1 ELSE 0 END)*100,1) AS faltas,
                ROUND(AVG(CASE WHEN a.estado='justificante' THEN 1 ELSE 0 END)*100,1) AS justificantes
            FROM asistencia a
            JOIN clase c ON a.id_clase = c.id_clase
            JOIN estudiante e ON a.id_estudiante = e.id_estudiante
            WHERE c.id_grupo = %s AND e.estado_actual = 'activo'
        """
        promedios = await fetch_one(promedios_query, (id_grupo,))

        return {
            "topFaltas": top_faltas,
            "topAsistencias": top_asistencias,
            "topJustificantes": top_justificantes,
            "ranking": ranking,
            "materiaMasFaltada": [r["nombre"] for r in materia_mas_faltada],
            "materiaMasAsistida": materia_mas_asistida[0]["nombre"] if materia_mas_asistida else None,
            "asistenciaPerfecta": [r["nombre"] for r in asistencia_perfecta],
            "promedios": promedios if promedios else {"asistencia": 0, "faltas": 0, "justificantes": 0}
        }
    except Exception as e:
        print("Error en /detalle-grupo/:", e)
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas del grupo")


# Progreso individual
@router.get("/progreso/{id_alumno}")
async def progreso_alumno(id_alumno: int):
    try:
        query = """
            SELECT fecha,
                   SUM(CASE WHEN estado='presente' THEN 1 ELSE 0 END) AS asistencia,
                   SUM(CASE WHEN estado='ausente' THEN 1 ELSE 0 END) AS falta,
                   SUM(CASE WHEN estado='justificante' THEN 1 ELSE 0 END) AS justificante
            FROM asistencia
            WHERE id_estudiante = %s
            GROUP BY fecha
            ORDER BY fecha
        """
        rows = await fetch_all(query, (id_alumno,))
        for row in rows:
            row["fecha"] = convertir_fecha_a_cdmx(row["fecha"].strftime("%Y-%m-%d"))
        return rows
    except Exception as e:
        print("Error en /progreso/:", e)
        raise HTTPException(status_code=500, detail="Error al obtener progreso del alumno")


@router.get("/progreso-materias/{id_alumno}")
async def progreso_materias(id_alumno: int):
    try:
        query = """
            SELECT m.nombre AS materia,
                   SUM(CASE WHEN a.estado='presente' THEN 1 ELSE 0 END) AS asistencias,
                   SUM(CASE WHEN a.estado='ausente' THEN 1 ELSE 0 END) AS faltas,
                   SUM(CASE WHEN a.estado='justificante' THEN 1 ELSE 0 END) AS justificantes,
                   ROUND(SUM(CASE WHEN a.estado IN ('presente', 'justificante') THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS porcentaje_asistencia
            FROM asistencia a
            JOIN clase c ON a.id_clase = c.id_clase
            JOIN materia m ON c.id_materia = m.id_materia
            WHERE a.id_estudiante = %s
            GROUP BY m.id_materia, m.nombre
            ORDER BY porcentaje_asistencia DESC
        """
        rows = await fetch_all(query, (id_alumno,))
        return rows
    except Exception as e:
        print("Error en /progreso-materias/:", e)
        raise HTTPException(status_code=500, detail="Error al obtener resumen por materias")


# Resumen de clase para docente
@router.get("/estadisticas-asistencias/{id_clase}")
async def resumen_clase(id_clase: int):
    try:
        fecha_actual = obtener_fecha_hora_cdmx()["fecha"]

        # Resumen de hoy
        query_hoy = """
            SELECT estado, COUNT(*) AS cantidad
            FROM asistencia
            WHERE id_clase = %s AND fecha = %s
            GROUP BY estado
        """
        rows_hoy = await fetch_all(query_hoy, (id_clase, fecha_actual))
        hoy = {"presentes": 0, "ausentes": 0, "justificantes": 0}
        for row in rows_hoy:
            if row["estado"] == "presente":
                hoy["presentes"] = int(row["cantidad"])
            elif row["estado"] == "ausente":
                hoy["ausentes"] = int(row["cantidad"])
            elif row["estado"] == "justificante":
                hoy["justificantes"] = int(row["cantidad"])

        # Resumen histórico
        query_hist = """
            SELECT estado, COUNT(*) AS cantidad
            FROM asistencia
            WHERE id_clase = %s
            GROUP BY estado
        """
        rows_hist = await fetch_all(query_hist, (id_clase,))
        historial = {"presentes": 0, "ausentes": 0, "justificantes": 0}
        for row in rows_hist:
            if row["estado"] == "presente":
                historial["presentes"] = int(row["cantidad"])
            elif row["estado"] == "ausente":
                historial["ausentes"] = int(row["cantidad"])
            elif row["estado"] == "justificante":
                historial["justificantes"] = int(row["cantidad"])

        total_registros = historial["presentes"] + historial["ausentes"] + historial["justificantes"]
        porcentaje_asistencia = round(((historial["presentes"] + historial["justificantes"]) / total_registros) * 100) if total_registros > 0 else 0

        # Estudiantes únicos
        query_estudiantes = """
            SELECT COUNT(DISTINCT e.id_estudiante) AS total_estudiantes 
            FROM estudiante e
            JOIN clase c ON e.id_grupo = c.id_grupo
            WHERE c.id_clase = %s AND e.estado_actual = 'activo'
        """
        res_estudiantes = await fetch_one(query_estudiantes, (id_clase,))
        total_estudiantes = int(res_estudiantes["total_estudiantes"]) if res_estudiantes else 0

        # Ranking
        def ranking_query(estado):
            return f"""
                SELECT e.id_estudiante, e.nombre, e.apellido, COUNT(*) AS cantidad
                FROM asistencia a
                JOIN estudiante e ON e.id_estudiante = a.id_estudiante
                WHERE a.id_clase = %s AND a.estado = '{estado}' AND e.estado_actual = 'activo'
                GROUP BY e.id_estudiante, e.nombre, e.apellido
                ORDER BY cantidad DESC
                LIMIT 3
            """

        mas_asisten = await fetch_all(ranking_query("presente"), (id_clase,))
        mas_faltan = await fetch_all(ranking_query("ausente"), (id_clase,))
        mas_justifican = await fetch_all(ranking_query("justificante"), (id_clase,))

        return {
            "hoy": hoy,
            "historial": {
                **historial,
                "porcentaje_asistencia": porcentaje_asistencia,
                "total_registros": total_registros,
                "total_estudiantes": total_estudiantes
            },
            "top": {
                "mas_asisten": mas_asisten,
                "mas_faltan": mas_faltan,
                "mas_justifican": mas_justifican
            }
        }

    except Exception as e:
        print("Error en /resumen-clase/:", e)
        raise HTTPException(status_code=500, detail="Error al obtener resumen de clase")
    
# Resumen de actividades en app movil
@router.get("/clases-actividades/{id_clase}/resumen")
async def resumen_clase(id_clase: int):
    """
    Devuelve un resumen analítico de actividades de una clase
    en formato estructurado.
    """
    # 🔹 Totales de actividades
    query_totales = """
        SELECT COUNT(*) AS total_actividades, MAX(valor_maximo) AS max_valor
        FROM actividad
        WHERE id_clase=%s
    """
    totales = await fetch_one(query_totales, (id_clase,))
    if not totales:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    # 🔹 Estado de entregas
    query_entregas = """
        SELECT ae.estado, COUNT(*) AS cantidad
        FROM actividad_estudiante ae
        INNER JOIN actividad a ON ae.id_actividad = a.id_actividad
        WHERE a.id_clase=%s
        GROUP BY ae.estado
    """
    entregas_raw = await fetch_all(query_entregas, (id_clase,))
    entregas = {row["estado"]: row["cantidad"] for row in entregas_raw}

    # 🔹 Calificaciones
    query_calif = """
        SELECT ae.calificacion
        FROM actividad_estudiante ae
        INNER JOIN actividad a ON ae.id_actividad = a.id_actividad
        WHERE a.id_clase=%s AND ae.calificacion IS NOT NULL
    """
    calif_rows = await fetch_all(query_calif, (id_clase,))
    calificaciones = [row["calificacion"] for row in calif_rows]

    if calificaciones:
        promedio = sum(calificaciones) / len(calificaciones)
        distribucion = {
            "0-5": sum(1 for c in calificaciones if c <= 5),
            "6-7": sum(1 for c in calificaciones if 6 <= c <= 7),
            "8-10": sum(1 for c in calificaciones if c >= 8)
        }
    else:
        promedio, distribucion = 0, {"0-5": 0, "6-7": 0, "8-10": 0}

    # 🔹 Actividades más y menos entregadas
    query_entregadas = """
        SELECT a.titulo, COUNT(*) AS total
        FROM actividad_estudiante ae
        INNER JOIN actividad a ON ae.id_actividad = a.id_actividad
        WHERE a.id_clase=%s AND ae.estado='entregado'
        GROUP BY a.titulo
        ORDER BY total DESC
    """
    entregadas = await fetch_all(query_entregadas, (id_clase,))
    mas_entregada = entregadas[0]["titulo"] if entregadas else None
    menos_entregada = entregadas[-1]["titulo"] if entregadas else None

    # 🔹 Actividad con mayor y menor promedio
    query_promedios = """
        SELECT a.titulo, AVG(ae.calificacion) AS promedio
        FROM actividad_estudiante ae
        INNER JOIN actividad a ON ae.id_actividad = a.id_actividad
        WHERE a.id_clase=%s AND ae.calificacion IS NOT NULL
        GROUP BY a.titulo
        ORDER BY promedio DESC
    """
    promedios = await fetch_all(query_promedios, (id_clase,))
    mayor_promedio = promedios[0]["titulo"] if promedios else None
    menor_promedio = promedios[-1]["titulo"] if promedios else None
    fecha_info = obtener_fecha_hora_cdmx()
    fecha_legible = f"{fecha_info['dia']}, {fecha_info['fecha'].strftime('%d/%m/%Y')} {fecha_info['hora']}"

    return {
        "fecha_consulta": fecha_legible,
        "totales": {
            "actividades": totales["total_actividades"],
            "valor_maximo_promedio": totales["max_valor"],
        },
        "estado_entregas": {
            "pendiente": entregas.get("pendiente", 0),
            "entregado": entregas.get("entregado", 0),
            "no_entregado": entregas.get("no_entregado", 0),
        },
        "calificaciones": {
            "promedio_general": round(promedio, 2),
            "distribucion": distribucion,
        },
        "mejores_peores": {
            "mas_entregada": mas_entregada,
            "menos_entregada": menos_entregada,
            "mayor_promedio": mayor_promedio,
            "menor_promedio": menor_promedio,
        }
    }