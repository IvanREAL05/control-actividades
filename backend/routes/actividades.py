from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
from config.db import fetch_one, fetch_all, execute_query

router = APIRouter()

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
        fecha_entrega_completa = f"{data.fecha_entrega} {data.hora_entrega}"

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