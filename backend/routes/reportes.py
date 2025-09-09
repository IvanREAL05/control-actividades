from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from config.db import fetch_one, fetch_all
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from utils.fecha import convertir_fecha_a_cdmx

router = APIRouter()

def limpiar_nombre_hoja(nombre: str) -> str:
    """Limpiar caracteres inválidos para nombre de hoja de Excel"""
    invalid_chars = ['\\', '/', '*', '[', ']', ':', '?']
    for ch in invalid_chars:
        nombre = nombre.replace(ch, "")
    return nombre[:31]  # Máximo 31 caracteres para Excel

@router.get("/excel/clase/{id_clase}")
async def generar_excel_clase(id_clase: int):
    # 1️⃣ Obtener datos de la clase
    clase_query = """
        SELECT 
            c.id_clase,
            m.nombre AS materia,
            g.nombre AS grupo
        FROM clase c
        LEFT JOIN materia m ON c.id_materia = m.id_materia
        LEFT JOIN grupo g ON c.id_grupo = g.id_grupo
        WHERE c.id_clase = %s
    """
    clase = await fetch_one(clase_query, [id_clase])
    if not clase:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    materia = clase.get("materia") or "SinMateria"
    grupo = clase.get("grupo") or "SinGrupo"

    # 2️⃣ Obtener actividades de la clase
    actividades_query = """
        SELECT id_actividad, titulo, fecha_entrega, valor_maximo
        FROM actividad
        WHERE id_clase = %s
        ORDER BY fecha_entrega ASC
    """
    actividades = await fetch_all(actividades_query, [id_clase])
    if not actividades:
        raise HTTPException(status_code=404, detail="No hay actividades para esta clase")

    # 3️⃣ Obtener alumnos del grupo
    alumnos_query = """
        SELECT id_estudiante, nombre, apellido, matricula
        FROM estudiante
        WHERE id_grupo = (SELECT id_grupo FROM clase WHERE id_clase = %s)
        ORDER BY apellido, nombre
    """
    alumnos = await fetch_all(alumnos_query, [id_clase])

    # 4️⃣ Crear libro Excel
    wb = Workbook()
    # Eliminar la hoja inicial vacía
    wb.remove(wb.active)

    for act in actividades:
        sheet = wb.create_sheet(title=limpiar_nombre_hoja(act["titulo"] or f"Actividad_{act['id_actividad']}"))

        # Encabezado
        sheet.append([f"Actividad: {act['titulo']}"])
        sheet.append([f"Fecha entrega: {act['fecha_entrega']}"])
        sheet.append([f"Valor máximo: {act['valor_maximo']}"])
        sheet.append([])  # fila vacía
        sheet.append(["Alumno", "Matrícula", "Estado", "Fecha entrega real", "Calificación"])

        # Obtener entregas de la actividad
        entregas_query = """
            SELECT id_estudiante, estado, fecha_entrega_real, calificacion
            FROM actividad_estudiante
            WHERE id_actividad = %s
        """
        entregas_list = await fetch_all(entregas_query, [act["id_actividad"]])
        entregas = {e["id_estudiante"]: e for e in entregas_list}

        # Agregar filas de alumnos
        for alumno in alumnos:
            entrega = entregas.get(alumno["id_estudiante"])
            estado = entrega["estado"] if entrega else "pendiente"
            fecha_entrega_real = convertir_fecha_a_cdmx(entrega["fecha_entrega_real"]) if entrega else ""
            calificacion = entrega["calificacion"] if entrega and entrega["calificacion"] is not None else ""

            row = [
                f"{alumno['apellido']} {alumno['nombre']}",
                alumno["matricula"],
                estado,
                fecha_entrega_real,
                calificacion
            ]
            sheet.append(row)

            # Colorear celda "Estado"
            estado_cell = sheet.cell(row=sheet.max_row, column=3)
            estado_lower = estado.lower()
            if estado_lower == "entregado":
                estado_cell.fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")  # verde
            elif estado_lower == "pendiente":
                estado_cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")  # amarillo
            elif estado_lower == "no entregado":
                estado_cell.fill = PatternFill(start_color="FF7F7F", end_color="FF7F7F", fill_type="solid")  # rojo

        # Estilos encabezado
        header_row = sheet[5]
        for cell in header_row:
            cell.font = Font(bold=True)
        for col in sheet.columns:
            col[0].width = 20

    # 5️⃣ Generar archivo en memoria
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"Actividades_{materia}_{grupo}.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
