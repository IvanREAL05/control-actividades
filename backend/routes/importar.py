from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.excel_utils import leer_excel, convertir_hora_excel
from controllers import importar_controller as ctrl
from datetime import datetime, time
from pydantic import BaseModel
from typing import List, Optional
from config.db import fetch_one, fetch_all, execute_query  # 👈 usamos tus helpers
import logging

router = APIRouter()
logger = logging.getLogger("api_calificaciones")
# ==================== MODELOS ====================
class EstudianteBase(BaseModel):
    matricula: str
    nombre: str
    apellido: str
    correo: Optional[str] = None
    id_grupo: int
    estado_actual: Optional[str] = "activo"
    no_lista: int

class EstudianteEditar(BaseModel):
    matricula: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    correo: Optional[str] = None
    id_grupo: Optional[int] = None
    estado_actual: Optional[str] = None

class EstudianteResponse(BaseModel):
    id_estudiante: int
    matricula: str
    nombre: str
    apellido: str
    correo: Optional[str]
    estado_actual: str
    activo: int  
    id_grupo: int
    nombre_grupo: str
    no_lista: int

@router.post("/{tipo}/archivo")
async def importar_archivo(tipo: str, file: UploadFile = File(...)):
    try:
        # ✅ Validar extensión de archivo antes de leer
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Archivo debe ser Excel")

        contents = await file.read()
        await file.close()
        datos = leer_excel(contents)

        if not datos:
            raise HTTPException(status_code=400, detail="Archivo vacío")

        if tipo == "estudiantes":
            await ctrl.insertar_estudiantes(datos)
        elif tipo == "profesores":
            await ctrl.insertar_profesores(datos)
        elif tipo == "grupos":
            await ctrl.insertar_grupos(datos)
        elif tipo == "clases":
            await ctrl.insertar_clases(datos)
        elif tipo == "materias":
            await ctrl.insertar_materias(datos)
        else:
            raise HTTPException(status_code=400, detail="Tipo no válido")

        return {"message": f"{tipo.capitalize()} importados correctamente."}
    except Exception as e:
        print(f"❌ Error importando {tipo}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al importar {tipo}")
    
# ==================== ENDPOINTS ====================

@router.get("/estudiante/buscar/matricula/{matricula}", response_model=EstudianteResponse)
async def buscar_por_matricula(matricula: str):
    """Busca estudiante por matrícula"""
    query = """
    SELECT e.*, g.nombre as nombre_grupo
    FROM estudiante e
    JOIN grupo g ON e.id_grupo = g.id_grupo
    WHERE e.matricula = %s
    """
    resultado = await fetch_one(query, (matricula,))
    if not resultado:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
        # 🟢 Agregar campo 'activo' según el valor de 'estado_actual'
    resultado["activo"] = 1 if resultado["estado_actual"] == "activo" else 0
    return resultado


@router.get("/estudiante/buscar/nombre", response_model=List[EstudianteResponse])
async def buscar_por_nombre(nombre: str, apellido: Optional[str] = None):
    """Busca estudiantes por nombre y/o apellido"""
    if apellido:
        query = """
        SELECT e.*, g.nombre as nombre_grupo
        FROM estudiante e
        JOIN grupo g ON e.id_grupo = g.id_grupo
        WHERE e.nombre LIKE %s AND e.apellido LIKE %s
        """
        resultados = await fetch_all(query, (f"%{nombre}%", f"%{apellido}%"))
    else:
        query = """
        SELECT e.*, g.nombre as nombre_grupo
        FROM estudiante e
        JOIN grupo g ON e.id_grupo = g.id_grupo
        WHERE e.nombre LIKE %s OR e.apellido LIKE %s
        """
        resultados = await fetch_all(query, (f"%{nombre}%", f"%{nombre}%"))

    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontraron estudiantes")
    return resultados


@router.get("/estudiante/buscar/grupo/{id_grupo}", response_model=List[EstudianteResponse])
async def buscar_por_grupo(id_grupo: int):
    """Lista todos los estudiantes de un grupo"""
    query = """
    SELECT e.*, g.nombre as nombre_grupo
    FROM estudiante e
    JOIN grupo g ON e.id_grupo = g.id_grupo
    WHERE e.id_grupo = %s
    ORDER BY e.no_lista
    """
    resultados = await fetch_all(query, (id_grupo,))
    if not resultados:
        raise HTTPException(status_code=404, detail="No hay estudiantes en este grupo")
    return resultados


@router.put("/estudiante/editar/{id_estudiante}")
async def editar_estudiante(id_estudiante: int, datos: EstudianteEditar):
    """Edita información de un estudiante"""
    # Verificar que existe
    estudiante = await fetch_one("SELECT id_estudiante FROM estudiante WHERE id_estudiante = %s", (id_estudiante,))
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    campos = []
    valores = []

    if datos.matricula:
        # Verificar duplicado
        existe = await fetch_one(
            "SELECT id_estudiante FROM estudiante WHERE matricula = %s AND id_estudiante != %s",
            (datos.matricula, id_estudiante)
        )
        if existe:
            raise HTTPException(status_code=400, detail="La matrícula ya existe")
        campos.append("matricula = %s")
        valores.append(datos.matricula)

    if datos.nombre:
        campos.append("nombre = %s")
        valores.append(datos.nombre)

    if datos.apellido:
        campos.append("apellido = %s")
        valores.append(datos.apellido)

    if datos.correo:
        campos.append("correo = %s")
        valores.append(datos.correo)

    if datos.id_grupo:
        grupo = await fetch_one("SELECT id_grupo FROM grupo WHERE id_grupo = %s", (datos.id_grupo,))
        if not grupo:
            raise HTTPException(status_code=400, detail="El grupo no existe")
        campos.append("id_grupo = %s")
        valores.append(datos.id_grupo)

    if datos.estado_actual:
        if datos.estado_actual not in ['activo', 'inactivo', 'egresado']:
            raise HTTPException(status_code=400, detail="Estado inválido")
        campos.append("estado_actual = %s")
        valores.append(datos.estado_actual)

    if not campos:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

    valores.append(id_estudiante)
    query = f"UPDATE estudiante SET {', '.join(campos)} WHERE id_estudiante = %s"
    await execute_query(query, valores)
    return {"message": "Estudiante actualizado correctamente", "id_estudiante": id_estudiante}


@router.delete("/estudiante/eliminar/{id_estudiante}")
async def eliminar_estudiante(id_estudiante: int):
    """Elimina un estudiante y sus registros relacionados"""
    estudiante = await fetch_one("SELECT matricula, nombre, apellido FROM estudiante WHERE id_estudiante = %s", (id_estudiante,))
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    # Eliminar asistencias primero
    await execute_query("DELETE FROM asistencia WHERE id_estudiante = %s", (id_estudiante,))

    # Eliminar estudiante
    await execute_query("DELETE FROM estudiante WHERE id_estudiante = %s", (id_estudiante,))
    
    return {
        "message": "Estudiante eliminado correctamente",
        "estudiante": estudiante
    }


@router.post("/calificaciones/archivo")
async def importar_calificaciones(file: UploadFile = File(...)):
    """
    Importa calificaciones de parciales desde un archivo Excel.
    
    Estructura esperada del Excel:
    | matricula | nrc | parcial_1 | parcial_2 | ordinario |
    |-----------|-----|-----------|-----------|-----------|
    | 2021001   | 123 | 8.5       | 9.0       |           |
    | 2021002   | 123 | 7.0       | 8.5       |           |
    
    - matricula: Matrícula del estudiante (obligatorio)
    - nrc: NRC de la clase (obligatorio)
    - parcial_1: Calificación del primer parcial (0-10, opcional)
    - parcial_2: Calificación del segundo parcial (0-10, opcional)
    - ordinario: Calificación del examen ordinario (0-10, opcional)
    
    Nota: Al menos una calificación debe estar presente.
    """
    try:
        # ✅ Validar extensión de archivo
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400, 
                detail="El archivo debe ser formato Excel (.xlsx o .xls)"
            )

        # Leer archivo
        contents = await file.read()
        await file.close()
        datos = leer_excel(contents)

        if not datos:
            raise HTTPException(
                status_code=400, 
                detail="El archivo está vacío o no tiene datos válidos"
            )

        # Validar que tenga las columnas mínimas requeridas
        columnas_requeridas = ["matricula", "nrc"]
        columnas_calificaciones = ["parcial_1", "parcial_2", "ordinario"]
        
        primera_fila = datos[0] if datos else {}
        columnas_presentes = list(primera_fila.keys())
        
        # Verificar columnas obligatorias
        faltantes = [col for col in columnas_requeridas if col not in columnas_presentes]
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan columnas obligatorias en el Excel: {', '.join(faltantes)}"
            )
        
        # Verificar que al menos una columna de calificación esté presente
        tiene_calificaciones = any(col in columnas_presentes for col in columnas_calificaciones)
        if not tiene_calificaciones:
            raise HTTPException(
                status_code=400,
                detail=f"El Excel debe contener al menos una columna de calificaciones: {', '.join(columnas_calificaciones)}"
            )

        # Procesar calificaciones
        resultado = await ctrl.insertar_calificaciones(datos)
        
        return {
            "message": "Calificaciones procesadas correctamente",
            "calificaciones_insertadas": resultado["calificaciones_insertadas"],
            "calificaciones_actualizadas": resultado["calificaciones_actualizadas"],
            "total_procesadas": resultado["calificaciones_insertadas"] + resultado["calificaciones_actualizadas"],
            "errores": resultado["errores"],
            "total_errores": len(resultado["errores"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error importando calificaciones: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error al importar calificaciones: {str(e)}"
        )
