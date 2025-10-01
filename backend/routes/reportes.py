from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from datetime import datetime, timedelta
import io
from typing import Optional
from config.db import fetch_all, fetch_one
from utils.fecha import obtener_fecha_hora_cdmx

router = APIRouter()

# Colores para estados
COLOR_PRESENTE = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
COLOR_AUSENTE = PatternFill(start_color="FF7F7F", end_color="FF7F7F", fill_type="solid")
COLOR_JUSTIFICANTE = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
COLOR_ENTREGADO = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
COLOR_PENDIENTE = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
COLOR_NO_ENTREGADO = PatternFill(start_color="FF7F7F", end_color="FF7F7F", fill_type="solid")

def generar_rango_fechas(fecha_inicio: str, fecha_fin: str):
    """Genera lista de fechas entre inicio y fin"""
    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
    fechas = []
    
    while inicio <= fin:
        fechas.append(inicio.strftime("%Y-%m-%d"))
        inicio += timedelta(days=1)
    
    return fechas

def limpiar_nombre_hoja(nombre: str, max_length: int = 31) -> str:
    """Limpia el nombre de la hoja para Excel"""
    invalidos = ['*', '?', ':', '\\', '/', '[', ']']
    for char in invalidos:
        nombre = nombre.replace(char, '_')
    return nombre[:max_length]

# ==================== REPORTE DE ASISTENCIAS POR GRUPO ====================
@router.get("/excel")
async def generar_reporte_grupo(
    id_grupo: int = Query(..., description="ID del grupo"),
    fechaInicio: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fechaFin: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD")
):
    """Genera reporte Excel de asistencias por grupo con filtros de fecha"""
    try:
        # Si no hay fechas, usar valores por defecto
        if not fechaInicio:
            min_fecha = await fetch_one("SELECT MIN(fecha) as min_fecha FROM asistencia")
            fechaInicio = min_fecha["min_fecha"] if min_fecha["min_fecha"] else "2025-08-04"
        
        if not fechaFin:
            fechaFin = obtener_fecha_hora_cdmx()["fecha"]
        
        print(f"📅 Rango usado: {fechaInicio} a {fechaFin}")
        
        # Generar lista de fechas
        fechas = generar_rango_fechas(fechaInicio, fechaFin)
        
        # Consultar asistencias
        query = """
            SELECT
                m.nombre AS materia,
                e.nombre,
                e.apellido,
                e.matricula,
                e.no_lista,
                a.fecha,
                a.estado
            FROM clase c
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN estudiante e ON e.id_grupo = c.id_grupo
            LEFT JOIN asistencia a 
                ON a.id_estudiante = e.id_estudiante
                AND a.id_clase = c.id_clase
                AND a.fecha BETWEEN %s AND %s
            WHERE c.id_grupo = %s
            ORDER BY materia, apellido, nombre, fecha
        """
        
        datos = await fetch_all(query, (fechaInicio, fechaFin, id_grupo))
        
        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)  # Remover hoja por defecto
        
        # Agrupar por materia
        materias = {}
        for row in datos:
            mat = row["materia"]
            if mat not in materias:
                materias[mat] = []
            materias[mat].append(row)
        
        # Crear hoja por materia
        for materia, rows in materias.items():
            ws = wb.create_sheet(limpiar_nombre_hoja(materia))
            
            # Encabezados
            headers = ["Nombre", "Apellido", "Matrícula", "No. Lista", *fechas]
            ws.append(headers)
            
            # Aplicar estilo al encabezado
            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")
            
            # Agrupar por alumno
            alumnos = {}
            for row in rows:
                key = row["matricula"]
                if key not in alumnos:
                    alumnos[key] = {
                        "nombre": row["nombre"],
                        "apellido": row["apellido"],
                        "matricula": row["matricula"],
                        "no_lista": row["no_lista"],
                        "asistencias": {}
                    }
                if row["fecha"]:
                    fecha_str = row["fecha"].strftime("%Y-%m-%d") if isinstance(row["fecha"], datetime) else row["fecha"]
                    alumnos[key]["asistencias"][fecha_str] = row["estado"]
            
            # Agregar filas
            for alumno in alumnos.values():
                row_data = [
                    alumno["nombre"],
                    alumno["apellido"],
                    alumno["matricula"],
                    alumno["no_lista"]
                ]
                
                # Agregar estados por fecha
                for fecha in fechas:
                    estado = alumno["asistencias"].get(fecha, "")
                    row_data.append(estado)
                
                ws.append(row_data)
                
                # Colorear celdas de estado
                current_row = ws.max_row
                for col_idx, fecha in enumerate(fechas, start=5):
                    cell = ws.cell(row=current_row, column=col_idx)
                    estado = cell.value.lower() if cell.value else ""
                    
                    if estado == "presente":
                        cell.fill = COLOR_PRESENTE
                    elif estado == "ausente":
                        cell.fill = COLOR_AUSENTE
                    elif estado == "justificante":
                        cell.fill = COLOR_JUSTIFICANTE
            
            # Ajustar ancho de columnas
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 15
        
        # Guardar en buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=asistencias.xlsx"}
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")

# ==================== REPORTE INDIVIDUAL DE ESTUDIANTE ====================
@router.get("/excel/individual")
async def generar_reporte_individual(
    id_estudiante: int = Query(..., description="ID del estudiante"),
    fechaInicio: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    fechaFin: str = Query(..., description="Fecha fin YYYY-MM-DD")
):
    """Genera reporte individual de un estudiante"""
    try:
        print(f"📅 Rango usado: {fechaInicio} a {fechaFin}")
        
        # Obtener datos del estudiante
        estudiante = await fetch_one(
            "SELECT nombre, apellido, matricula FROM estudiante WHERE id_estudiante = %s",
            (id_estudiante,)
        )
        
        if not estudiante:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
        
        # Generar fechas
        fechas = generar_rango_fechas(fechaInicio, fechaFin)
        
        # Obtener asistencias agrupadas por materia
        query = """
            SELECT
                m.nombre AS materia,
                a.fecha,
                a.estado
            FROM asistencia a
            JOIN clase c ON a.id_clase = c.id_clase
            JOIN materia m ON c.id_materia = m.id_materia
            WHERE a.id_estudiante = %s
                AND a.fecha BETWEEN %s AND %s
            ORDER BY m.nombre, a.fecha
        """
        
        asistencias = await fetch_all(query, (id_estudiante, fechaInicio, fechaFin))
        
        # Agrupar por materia
        materias = {}
        for row in asistencias:
            mat = row["materia"]
            if mat not in materias:
                materias[mat] = {}
            fecha_str = row["fecha"].strftime("%Y-%m-%d") if isinstance(row["fecha"], datetime) else row["fecha"]
            materias[mat][fecha_str] = row["estado"]
        
        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Asistencias"
        
        # Encabezados
        headers = ["Materia", *fechas]
        ws.append(headers)
        
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
        
        # Agregar filas por materia
        for materia, asist_fechas in materias.items():
            row_data = [materia]
            
            for fecha in fechas:
                estado = asist_fechas.get(fecha, "")
                row_data.append(estado.capitalize() if estado else "")
            
            ws.append(row_data)
            
            # Colorear celdas
            current_row = ws.max_row
            for col_idx in range(2, len(fechas) + 2):
                cell = ws.cell(row=current_row, column=col_idx)
                estado = cell.value.lower() if cell.value else ""
                
                if estado == "presente":
                    cell.fill = COLOR_PRESENTE
                elif estado == "ausente":
                    cell.fill = COLOR_AUSENTE
                elif estado == "justificante":
                    cell.fill = COLOR_JUSTIFICANTE
        
        # Ajustar columnas
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 12
        
        # Guardar
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"reporte_alumno_{estudiante['matricula']}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")

# ==================== REPORTE DE ACTIVIDADES POR CLASE ====================
@router.get("/excel/clase/{id_clase}")
async def generar_reporte_actividades_clase(id_clase: int):
    """Genera reporte de actividades de una clase"""
    try:
        # Obtener datos de la clase
        clase = await fetch_one("""
            SELECT 
                c.id_clase,
                m.nombre AS materia,
                g.nombre AS grupo
            FROM clase c
            LEFT JOIN materia m ON c.id_materia = m.id_materia
            LEFT JOIN grupo g ON c.id_grupo = g.id_grupo
            WHERE c.id_clase = %s
        """, (id_clase,))
        
        if not clase:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        
        # Obtener actividades
        actividades = await fetch_all("""
            SELECT id_actividad, titulo, fecha_entrega, valor_maximo
            FROM actividad
            WHERE id_clase = %s
            ORDER BY fecha_entrega ASC
        """, (id_clase,))
        
        if not actividades:
            raise HTTPException(status_code=404, detail="No hay actividades para esta clase")
        
        # Obtener alumnos
        alumnos = await fetch_all("""
            SELECT id_estudiante, nombre, apellido, matricula, no_lista
            FROM estudiante
            WHERE id_grupo = (SELECT id_grupo FROM clase WHERE id_clase = %s)
            ORDER BY apellido, nombre
        """, (id_clase,))
        
        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)
        
        # Crear hoja por actividad
        for act in actividades:
            ws = wb.create_sheet(limpiar_nombre_hoja(act["titulo"]))
            
            # Info de la actividad
            ws.append([f"Actividad: {act['titulo']}"])
            ws.append([f"Fecha entrega: {act['fecha_entrega']}"])
            ws.append([f"Valor máximo: {act['valor_maximo']}"])
            ws.append([])
            
            # Encabezados
            ws.append(["Alumno", "Matrícula", "Estado", "Fecha entrega real", "Calificación"])
            ws[5].font = Font(bold=True)
            
            # Obtener entregas
            entregas = await fetch_all("""
                SELECT id_estudiante, estado, fecha_entrega_real, calificacion
                FROM actividad_estudiante
                WHERE id_actividad = %s
            """, (act["id_actividad"],))
            
            entregas_map = {e["id_estudiante"]: e for e in entregas}
            
            # Agregar alumnos
            for alumno in alumnos:
                entrega = entregas_map.get(alumno["id_estudiante"])
                estado = entrega["estado"] if entrega else "pendiente"
                
                row_data = [
                    f"{alumno['apellido']} {alumno['nombre']}",
                    alumno["matricula"],
                    estado,
                    entrega["fecha_entrega_real"] if entrega else "",
                    entrega["calificacion"] if entrega and entrega["calificacion"] is not None else ""
                ]
                
                ws.append(row_data)
                
                # Colorear estado
                current_row = ws.max_row
                estado_cell = ws.cell(row=current_row, column=3)
                
                estado_lower = estado.lower()
                if estado_lower == "entregado":
                    estado_cell.fill = COLOR_ENTREGADO
                elif estado_lower == "pendiente":
                    estado_cell.fill = COLOR_PENDIENTE
                elif estado_lower == "no entregado":
                    estado_cell.fill = COLOR_NO_ENTREGADO
            
            # Ajustar columnas
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 20
        
        # Guardar
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Actividades_{clase['materia']}_{clase['grupo']}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")

# ==================== REPORTE GENERAL DE ACTIVIDADES ====================
@router.get("/excel/clase/general/{id_clase}")
async def generar_reporte_general_actividades(id_clase: int):
    """Genera reporte general con todas las actividades en una sola hoja"""
    try:
        # Obtener clase
        clase = await fetch_one("""
            SELECT c.id_clase, m.nombre AS materia, g.nombre AS grupo
            FROM clase c
            LEFT JOIN materia m ON c.id_materia = m.id_materia
            LEFT JOIN grupo g ON c.id_grupo = g.id_grupo
            WHERE c.id_clase = %s
        """, (id_clase,))
        
        if not clase:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        
        # Obtener actividades
        actividades = await fetch_all("""
            SELECT id_actividad, titulo
            FROM actividad
            WHERE id_clase = %s
            ORDER BY fecha_entrega ASC
        """, (id_clase,))
        
        if not actividades:
            raise HTTPException(status_code=404, detail="No hay actividades")
        
        # Obtener alumnos
        alumnos = await fetch_all("""
            SELECT id_estudiante, nombre, apellido, matricula, no_lista
            FROM estudiante
            WHERE id_grupo = (SELECT id_grupo FROM clase WHERE id_clase = %s)
            ORDER BY no_lista
        """, (id_clase,))
        
        # Obtener entregas
        ids_actividades = [a["id_actividad"] for a in actividades]
        placeholders = ','.join(['%s'] * len(ids_actividades))
        entregas = await fetch_all(f"""
            SELECT id_estudiante, id_actividad, estado, calificacion
            FROM actividad_estudiante
            WHERE id_actividad IN ({placeholders})
        """, tuple(ids_actividades))
        
        entregas_map = {}
        for e in entregas:
            key = f"{e['id_estudiante']}_{e['id_actividad']}"
            entregas_map[key] = e
        
        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"{clase['materia']}-{clase['grupo']}"
        
        # Encabezados
        headers = ["No Lista", "Matrícula", "Nombre", "Grupo"]
        for act in actividades:
            headers.append(act["titulo"])
            headers.append(f"Cal - {act['titulo']}")
        
        ws.append(headers)
        ws[1].font = Font(bold=True)
        for cell in ws[1]:
            cell.alignment = Alignment(horizontal="center")
        
        # Agregar filas
        for alumno in alumnos:
            row_data = [
                alumno["no_lista"],
                alumno["matricula"],
                f"{alumno['apellido']} {alumno['nombre']}",
                clase["grupo"]
            ]
            
            for act in actividades:
                key = f"{alumno['id_estudiante']}_{act['id_actividad']}"
                entrega = entregas_map.get(key)
                
                estado = entrega["estado"] if entrega else "pendiente"
                calificacion = entrega["calificacion"] if entrega and entrega["calificacion"] is not None else 0
                
                row_data.append(estado)
                row_data.append(calificacion)
            
            ws.append(row_data)
            
            # Colorear estados
            current_row = ws.max_row
            col_idx = 5
            for _ in actividades:
                estado_cell = ws.cell(row=current_row, column=col_idx)
                estado = estado_cell.value.lower() if estado_cell.value else ""
                
                if estado == "entregado":
                    estado_cell.fill = COLOR_ENTREGADO
                elif estado == "pendiente":
                    estado_cell.fill = COLOR_PENDIENTE
                elif estado == "no entregado":
                    estado_cell.fill = COLOR_NO_ENTREGADO
                
                col_idx += 2
        
        # Ajustar columnas
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 20
        
        # Guardar
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Actividades_General_{clase['materia']}_{clase['grupo']}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")

# ==================== REPORTE DE PROFESOR ====================
@router.get("/excel/profesor/{id_profesor}")
async def generar_reporte_profesor(
    id_profesor: int,
    fechaInicio: Optional[str] = Query("2025-08-04"),
    fechaFin: Optional[str] = Query(None)
):
    """Genera reporte de todas las clases de un profesor"""
    try:
        if not fechaFin:
            fechaFin = obtener_fecha_hora_cdmx()["fecha"]
        
        # Obtener clases del profesor
        clases = await fetch_all("""
            SELECT c.id_clase, c.nombre_clase,
                   m.nombre AS materia, g.nombre AS grupo
            FROM clase c
            LEFT JOIN materia m ON c.id_materia = m.id_materia
            LEFT JOIN grupo g ON c.id_grupo = g.id_grupo
            WHERE c.id_profesor = %s
        """, (id_profesor,))
        
        if not clases:
            raise HTTPException(status_code=404, detail="El profesor no tiene clases asignadas")
        
        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)
        
        for clase in clases:
            nombre_hoja = f"{clase['materia']} - {clase['grupo']}"
            ws = wb.create_sheet(limpiar_nombre_hoja(nombre_hoja))
            
            # Obtener estudiantes
            estudiantes = await fetch_all("""
                SELECT e.id_estudiante, e.nombre, e.apellido, e.matricula, 
                       e.no_lista, g.nombre AS grupo
                FROM estudiante e
                JOIN grupo g ON e.id_grupo = g.id_grupo
                WHERE e.id_grupo = (SELECT id_grupo FROM clase WHERE id_clase = %s)
                ORDER BY e.no_lista
            """, (clase["id_clase"],))
            
            # Obtener solo fechas donde hubo clase
            fechas_clase = await fetch_all("""
                SELECT DISTINCT fecha
                FROM asistencia
                WHERE id_clase = %s
                    AND fecha BETWEEN %s AND %s
                ORDER BY fecha
            """, (clase["id_clase"], fechaInicio, fechaFin))
            
            fechas = [f["fecha"].strftime("%Y-%m-%d") if isinstance(f["fecha"], datetime) else f["fecha"] 
                     for f in fechas_clase]
            
            # Obtener asistencias
            asistencias = await fetch_all("""
                SELECT id_estudiante, fecha, estado
                FROM asistencia
                WHERE id_clase = %s
                    AND fecha BETWEEN %s AND %s
            """, (clase["id_clase"], fechaInicio, fechaFin))
            
            asist_map = {}
            for a in asistencias:
                fecha_str = a["fecha"].strftime("%Y-%m-%d") if isinstance(a["fecha"], datetime) else a["fecha"]
                key = f"{a['id_estudiante']}_{fecha_str}"
                asist_map[key] = a["estado"]
            
            # Encabezados
            headers = ["No Lista", "Matrícula", "Nombre", "Grupo", *fechas]
            ws.append(headers)
            ws[1].font = Font(bold=True)
            
            # Agregar filas
            for est in estudiantes:
                row_data = [
                    est["no_lista"],
                    est["matricula"],
                    f"{est['nombre']} {est['apellido']}",
                    est["grupo"]
                ]
                
                for fecha in fechas:
                    key = f"{est['id_estudiante']}_{fecha}"
                    estado = asist_map.get(key, "—")
                    row_data.append(estado)
                
                ws.append(row_data)
                
                # Colorear
                current_row = ws.max_row
                for col_idx in range(5, 5 + len(fechas)):
                    cell = ws.cell(row=current_row, column=col_idx)
                    estado = cell.value.lower() if cell.value else ""
                    
                    if estado == "presente":
                        cell.fill = COLOR_PRESENTE
                    elif estado == "ausente":
                        cell.fill = COLOR_AUSENTE
                    elif estado == "justificante":
                        cell.fill = COLOR_JUSTIFICANTE
            
            # Ajustar columnas
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 15
        
        # Guardar
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=Reporte_Profesor_{id_profesor}.xlsx"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")