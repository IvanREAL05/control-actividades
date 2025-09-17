from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import os
from config.db import execute_query, fetch_all, fetch_one
from utils.fecha import convertir_fecha_a_cdmx

router = APIRouter()

@router.post("/justificantes")
async def registrar_justificante(
    fecha_expedicion: str = Form(...),
    matricula: str = Form(...),
    nombre_estudiante: str = Form(...),
    fecha_inicio: str = Form(...),
    fecha_fin: str = Form(...),
    gestor: Optional[str] = Form(None),
    numero_gestor: Optional[str] = Form(None),
    situacion: Optional[str] = Form(None),
    folio_aprobacion: Optional[str] = Form(None),
    ejecutivo: Optional[str] = Form(None),
    documento_pdf: Optional[UploadFile] = File(None),
    documento_ine: Optional[UploadFile] = File(None)
):
    # Validar fechas
    try:
        fecha_exp = datetime.fromisoformat(fecha_expedicion)
        fecha_ini = datetime.fromisoformat(fecha_inicio)
        fecha_fin_dt = datetime.fromisoformat(fecha_fin)

        if fecha_exp > fecha_ini:
            raise HTTPException(status_code=400, detail="La fecha de expedición no puede ser posterior a la fecha de inicio del permiso")
        if fecha_exp > fecha_fin_dt:
            raise HTTPException(status_code=400, detail="La fecha de expedición no puede ser posterior a la fecha de fin del permiso")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Formato de fecha inválido: {e}")

    # Guardar archivos si existen
    pdf_filename = None
    ine_filename = None

    upload_dir = "uploads/justificantes"
    os.makedirs(upload_dir, exist_ok=True)

    if documento_pdf:
        pdf_filename = os.path.join(upload_dir, documento_pdf.filename)
        with open(pdf_filename, "wb") as f:
            f.write(await documento_pdf.read())

    if documento_ine:
        ine_filename = os.path.join(upload_dir, documento_ine.filename)
        with open(ine_filename, "wb") as f:
            f.write(await documento_ine.read())

    # Buscar estudiante por matrícula
    estudiante = await fetch_one("SELECT id_estudiante, nombre AS nombre_estudiante FROM estudiante WHERE matricula=%s", (matricula,))
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    nombre_correcto = estudiante.get("nombre_estudiante", "").strip().lower()
    if nombre_correcto != nombre_estudiante.strip().lower():
        raise HTTPException(status_code=400, detail="El nombre no coincide con la matrícula")

    id_estudiante = estudiante["id_estudiante"]

    # Insertar justificante
    insert_query = """
        INSERT INTO justificantes (
            fecha_expedicion,
            matricula,
            nombre_estudiante,
            fecha_inicio,
            fecha_fin,
            gestor,
            numero_gestor,
            situacion,
            documento_pdf,
            documento_ine,
            folio_aprobacion,
            ejecutivo
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    await execute_query(insert_query, (
        fecha_expedicion,
        matricula,
        nombre_estudiante,
        fecha_inicio,
        fecha_fin,
        gestor,
        numero_gestor,
        situacion,
        pdf_filename,
        ine_filename,
        folio_aprobacion,
        ejecutivo
    ))

    # Buscar clases del estudiante en el rango
    clases = await fetch_all("""
        SELECT c.id_clase, c.fecha 
        FROM clase c
        JOIN grupo g ON c.id_grupo = g.id_grupo
        JOIN estudiante e ON e.id_grupo = g.id_grupo
        WHERE e.id_estudiante=%s
        AND c.fecha BETWEEN %s AND %s
    """, (id_estudiante, fecha_inicio, fecha_fin))

    for clase in clases:
        fecha_clase = clase["fecha"]

        asistencia = await fetch_one(
            "SELECT id_asistencia FROM asistencia WHERE id_estudiante=%s AND id_clase=%s AND fecha=%s",
            (id_estudiante, clase["id_clase"], fecha_clase)
        )

        if asistencia:
            await execute_query(
                "UPDATE asistencia SET estado=%s WHERE id_estudiante=%s AND id_clase=%s AND fecha=%s",
                ("justificante", id_estudiante, clase["id_clase"], fecha_clase)
            )
        else:
            await execute_query(
                "INSERT INTO asistencia (id_estudiante, id_clase, estado, fecha) VALUES (%s, %s, %s, %s)",
                (id_estudiante, clase["id_clase"], "justificante", fecha_clase)
            )

    return JSONResponse({"message": "✅ Justificante registrado correctamente y asistencia actualizada"})