from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from config.db import execute_query, fetch_all, fetch_one
from datetime import datetime

router = APIRouter()

# ---------------------------
# Modelos Pydantic inline
# ---------------------------
class ObservacionBase(BaseModel):
    estudiante_id: int
    profesor_id: int
    estado: Optional[int] = Field(0, ge=0, le=6)

class ObservacionCreate(ObservacionBase):
    pass

class ObservacionUpdate(BaseModel):
    estado: Optional[int] = Field(None, ge=0, le=6)

class ObservacionResponse(BaseModel):
    id: int
    estudiante_id: int
    profesor_id: int
    estado: int
    fecha: str
    nombre_estudiante: Optional[str] = None
    apellido_estudiante: Optional[str] = None
    nombre_profesor: Optional[str] = None
    apellido_profesor: Optional[str] = None

    class Config:
        orm_mode = True

class ObservacionResponseList(BaseModel):
    success: bool = True
    mensaje: Optional[str] = None
    observacion: Optional[ObservacionResponse] = None
    observaciones: Optional[List[ObservacionResponse]] = None

# ---------------------------
# CRUD endpoints
# ---------------------------

# Crear observación
@router.post("/", response_model=ObservacionResponseList)
async def crear_observacion(obs: ObservacionCreate):
    if obs.estado is not None and (obs.estado < 0 or obs.estado > 6):
        raise HTTPException(status_code=400, detail="Estado inválido")

    query = "INSERT INTO observaciones (estudiante_id, profesor_id, estado) VALUES (%s, %s, %s)"
    last_id = await execute_query(query, (obs.estudiante_id, obs.profesor_id, obs.estado))
    created = await fetch_one("SELECT * FROM observaciones WHERE id = %s", (last_id,))

    # Convertir fecha a string
    if isinstance(created["fecha"], datetime):
        created["fecha"] = created["fecha"].strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "observacion": created}

# Obtener todas las observaciones
@router.get("/", response_model=ObservacionResponseList)
async def obtener_observaciones():
    query = """
        SELECT o.*, 
               e.nombre AS nombre_estudiante, 
               e.apellido AS apellido_estudiante, 
               p.nombre AS nombre_profesor
        FROM observaciones o
        JOIN estudiante e ON o.estudiante_id = e.id_estudiante
        JOIN profesor p ON o.profesor_id = p.id_profesor
        ORDER BY o.fecha DESC
    """
    observaciones = await fetch_all(query)

    # Convertir fecha a string
    for obs in observaciones:
        if isinstance(obs["fecha"], datetime):
            obs["fecha"] = obs["fecha"].strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "observaciones": observaciones}

# Obtener observaciones por estudiante
@router.get("/estudiante/{estudiante_id}", response_model=ObservacionResponseList)
async def obtener_por_estudiante(estudiante_id: int):
    query = """
        SELECT o.*, p.nombre AS nombre_profesor
        FROM observaciones o
        JOIN profesor p ON o.profesor_id = p.id_profesor
        WHERE o.estudiante_id = %s
        ORDER BY o.fecha DESC
    """
    observaciones = await fetch_all(query, (estudiante_id,))

    for obs in observaciones:
        if isinstance(obs["fecha"], datetime):
            obs["fecha"] = obs["fecha"].strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "observaciones": observaciones}

# Actualizar observación
@router.put("/{id}", response_model=ObservacionResponseList)
async def actualizar_observacion(id: int, obs: ObservacionUpdate):
    if obs.estado is not None and (obs.estado < 0 or obs.estado > 6):
        raise HTTPException(status_code=400, detail="Estado inválido")

    query = "UPDATE observaciones SET estado=%s, fecha=CURRENT_TIMESTAMP WHERE id=%s"
    rowcount = await execute_query(query, (obs.estado, id))
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Observación no encontrada")

    updated = await fetch_one("SELECT * FROM observaciones WHERE id=%s", (id,))
    if isinstance(updated["fecha"], datetime):
        updated["fecha"] = updated["fecha"].strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "observacion": updated}

# Eliminar observación
@router.delete("/{id}", response_model=ObservacionResponseList)
async def eliminar_observacion(id: int):
    obs = await fetch_one("SELECT * FROM observaciones WHERE id=%s", (id,))
    if not obs:
        raise HTTPException(status_code=404, detail="Observación no encontrada")

    await execute_query("DELETE FROM observaciones WHERE id=%s", (id,))

    if isinstance(obs["fecha"], datetime):
        obs["fecha"] = obs["fecha"].strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "observacion": obs}
