from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import aiomysql
from config.db import fetch_one, fetch_all, execute_query

router = APIRouter()

# ===============================
# 📌 MODELOS DE REQUEST
# ===============================
class EstudianteNuevo(BaseModel):
    matricula: str
    nombre: str
    apellido: str
    email: Optional[str] = None
    grupo: str   # Nombre del grupo (no el id directamente)


# ===============================
# 📌 ENDPOINTS
# ===============================

# Obtener estudiantes por id_grupo
@router.get("/grupo/{id_grupo}")
async def obtener_estudiantes_grupo(id_grupo: int):
    query = """
        SELECT id_estudiante, nombre, apellido, estado_actual, correo, id_grupo, no_lista, matricula
        FROM estudiante
        WHERE id_grupo = %s
        ORDER BY no_lista ASC, apellido ASC
    """
    try:
        rows = await fetch_all(query, (id_grupo,))
        return rows
    except Exception as e:
        print("Error en /grupo/{id_grupo}:", e)
        raise HTTPException(status_code=500, detail="Error al obtener estudiantes")


# Obtener estudiante por matrícula → solo id_estudiante
@router.get("/matricula/{matricula}")
async def obtener_estudiante_por_matricula(matricula: str):
    query = "SELECT id_estudiante FROM estudiante WHERE matricula = %s"
    try:
        row = await fetch_one(query, (matricula,))
        if not row:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
        return {"id_estudiante": row["id_estudiante"]}
    except Exception as e:
        print("Error en /matricula/{matricula}:", e)
        raise HTTPException(status_code=500, detail="Error al obtener estudiante")


# Buscar estudiante por matrícula → devuelve id_estudiante y nombre completo
@router.get("/buscar/{matricula}")
async def buscar_estudiante_por_matricula(matricula: str):
    query = """
        SELECT id_estudiante, CONCAT(nombre, ' ', apellido) AS nombre_completo
        FROM estudiante
        WHERE matricula = %s
    """
    try:
        row = await fetch_one(query, (matricula,))
        if not row:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
        return row
    except Exception as e:
        print("Error en /buscar/{matricula}:", e)
        raise HTTPException(status_code=500, detail="Error al obtener estudiante")


# Crear o actualizar estudiante
# Crear o actualizar estudiante
@router.post("/nuevo")
async def crear_estudiante(data: EstudianteNuevo):
    matricula = data.matricula.strip()
    nombre = data.nombre.strip()
    apellido = data.apellido.strip()
    correo = data.email.strip() if data.email else None
    grupo_nombre = data.grupo.strip()

    try:
        # 1. Buscar id_grupo a partir del nombre del grupo
        query_grupo = "SELECT id_grupo FROM grupo WHERE nombre = %s"
        grupo = await fetch_one(query_grupo, (grupo_nombre,))
        if not grupo:
            raise HTTPException(status_code=400, detail="Grupo no encontrado")
        id_grupo = grupo["id_grupo"]

        # 2. Insertar o actualizar estudiante (usar 0 temporal en no_lista)
        query_insert = """
            INSERT INTO estudiante (matricula, nombre, apellido, correo, id_grupo, estado_actual, foto_url, no_lista)
            VALUES (%s, %s, %s, %s, %s, 'activo', NULL, 0)
            ON DUPLICATE KEY UPDATE
                nombre = VALUES(nombre),
                apellido = VALUES(apellido),
                correo = VALUES(correo),
                id_grupo = VALUES(id_grupo)
        """
        await execute_query(query_insert, (matricula, nombre, apellido, correo, id_grupo))

        # 3. Reordenar lista de estudiantes dentro del grupo
        query_reordenar = """
            WITH ordenados AS (
                SELECT id_estudiante,
                       ROW_NUMBER() OVER (ORDER BY apellido ASC, nombre ASC) AS nuevo_numero
                FROM estudiante
                WHERE id_grupo = %s
            )
            UPDATE estudiante e
            JOIN ordenados o ON e.id_estudiante = o.id_estudiante
            SET e.no_lista = o.nuevo_numero
        """
        await execute_query(query_reordenar, (id_grupo,))

        return {"message": "Estudiante agregado y lista reordenada"}
    except Exception as e:
        print("Error en /nuevo:", e)
        raise HTTPException(status_code=500, detail="Error en el servidor")