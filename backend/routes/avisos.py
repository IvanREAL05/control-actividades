# routes/avisos.py (pulido y optimizado)
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, Dict, Any
from config.db import fetch_one, fetch_all, execute_query
from pydantic import BaseModel, Field, HttpUrl, validator
from utils.fecha import obtener_fecha_hora_cdmx, obtener_fecha_hora_cdmx_completa
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# 📌 Modelos mejorados
class AvisoCreate(BaseModel):
    nombre_evento: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Nombre del evento o aviso"
    )
    fecha: str = Field(
        ..., 
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Fecha en formato YYYY-MM-DD"
    )
    descripcion: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Descripción detallada del aviso"
    )
    enlace: HttpUrl = Field(
        ...,
        description="URL del enlace relacionado al aviso"
    )
    
    @validator('fecha')
    def validar_fecha(cls, v):
        try:
            fecha_obj = datetime.strptime(v, "%Y-%m-%d").date()
            fecha_actual = date.today()
            if fecha_obj < fecha_actual:
                raise ValueError("La fecha no puede ser anterior a la fecha actual")
            return v
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError("La fecha debe tener formato YYYY-MM-DD")
            raise e

class AvisoUpdate(BaseModel):
    nombre_evento: Optional[str] = Field(None, min_length=1, max_length=255)
    fecha: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    descripcion: Optional[str] = Field(None, min_length=1, max_length=2000)
    enlace: Optional[HttpUrl] = None
    
    @validator('fecha')
    def validar_fecha(cls, v):
        if v is not None:
            try:
                fecha_obj = datetime.strptime(v, "%Y-%m-%d").date()
                fecha_actual = date.today()
                if fecha_obj < fecha_actual:
                    raise ValueError("La fecha no puede ser anterior a la fecha actual")
            except ValueError as e:
                if "does not match format" in str(e):
                    raise ValueError("La fecha debe tener formato YYYY-MM-DD")
                raise e
        return v

# 📌 Funciones de validación
async def validar_aviso_existe(aviso_id: int) -> Dict[str, Any]:
    """Valida que un aviso exista y lo retorna - SIN DATE_FORMAT problemático"""
    if aviso_id <= 0:
        raise HTTPException(
            status_code=400, 
            detail="El ID debe ser un número entero positivo"
        )
    
    # SOLUCIÓN: Usar CAST o formato simple, NO DATE_FORMAT
    aviso = await fetch_one("""
        SELECT id, nombre_evento, 
               fecha,
               descripcion, enlace,
               fecha_creacion
        FROM avisos WHERE id = %s
    """, (aviso_id,))
    
    if not aviso:
        raise HTTPException(
            status_code=404,
            detail=f"No existe un aviso con el ID {aviso_id}"
        )
    
    # Formatear fechas en Python en lugar de MySQL
    if aviso:
        # Convertir fecha a string si es necesario
        if hasattr(aviso['fecha'], 'strftime'):
            aviso['fecha'] = aviso['fecha'].strftime('%Y-%m-%d')
        if hasattr(aviso['fecha_creacion'], 'strftime'):
            aviso['fecha_creacion'] = aviso['fecha_creacion'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Asegurar que sean strings
        aviso['fecha'] = str(aviso['fecha'])
        aviso['fecha_creacion'] = str(aviso['fecha_creacion'])
    
    return aviso

# ✅ POST - Ver todos los avisos
@router.get("/")
async def get_avisos(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Elementos por página"),
    search: Optional[str] = Query(None, description="Buscar en nombre o descripción"),
    fecha_desde: Optional[str] = Query(None, pattern=r'^\d{4}-\d{2}-\d{2}$'),
    fecha_hasta: Optional[str] = Query(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
):
    """
    Obtiene todos los avisos con paginación y filtros opcionales
    """
    try:
        offset = (page - 1) * limit
        
        # Construir query con filtros
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("(nombre_evento LIKE %s OR descripcion LIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        if fecha_desde:
            where_conditions.append("fecha >= %s")
            params.append(fecha_desde)
            
        if fecha_hasta:
            where_conditions.append("fecha <= %s")
            params.append(fecha_hasta)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Query principal
        avisos = await fetch_all("""
            SELECT id, 
                   nombre_evento, 
                   DATE_FORMAT(fecha, '%%Y-%%m-%%d') AS fecha,
                   descripcion, 
                   enlace,
                   DATE_FORMAT(fecha_creacion, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_creacion
            FROM avisos 
            {where_clause}
            ORDER BY fecha_creacion DESC 
            LIMIT %s OFFSET %s
        """.format(where_clause=where_clause), params + [limit, offset])
        
        # Query para contar total
        total_result = await fetch_one("""
            SELECT COUNT(*) AS total 
            FROM avisos {where_clause}
        """.format(where_clause=where_clause), params)
        
        total_items = total_result["total"]
        total_pages = (total_items + limit - 1) // limit
        
        return {
            "success": True,
            "data": avisos,
            "pagination": {
                "totalItems": total_items,
                "totalPages": total_pages,
                "currentPage": page,
                "itemsPerPage": limit,
                "hasNextPage": page < total_pages,
                "hasPrevPage": page > 1,
            },
            "filters": {
                "search": search,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error al obtener avisos: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al obtener los avisos"
        )
    
# ✅ POST - Crear un nuevo aviso
@router.post("/")
async def create_aviso(aviso: AvisoCreate):
    print("➡️ Petición recibida en create_aviso")
    print("Datos recibidos:", aviso.dict())

    try:
        fecha_creacion = obtener_fecha_hora_cdmx_completa()

        # Insertar aviso en MySQL
        insert_sql = """
            INSERT INTO avisos (nombre_evento, fecha, descripcion, enlace, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s)
        """

        params = (
            aviso.nombre_evento.strip(),
            aviso.fecha,
            aviso.descripcion.strip(),
            aviso.enlace,   # ya validado por Pydantic
            fecha_creacion
        )

        new_id = await execute_query(insert_sql, params)

        # Recuperar aviso recién insertado
        select_sql = """
            SELECT id, 
                   nombre_evento,
                   DATE_FORMAT(fecha, '%%Y-%%m-%%d') as fecha,
                   descripcion, 
                   enlace,
                   DATE_FORMAT(fecha_creacion, '%%Y-%%m-%%d %%H:%%i:%%s') as fecha_creacion
            FROM avisos
            WHERE id = %s
        """

        new_aviso = await fetch_one(select_sql, (new_id,))

        logger.info(f"✅ Aviso creado con ID: {new_id}")

        return {
            "success": True,
            "message": "Aviso creado exitosamente",
            "data": new_aviso,
            "links": {
                "view": f"/api/avisos/{new_id}",
                "all": "/api/avisos"
            }
        }

    except Exception as e:
        print("❌ Error al crear aviso:", e)
        logger.error(f"Error al crear aviso: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al crear el aviso"
        )


# ✅ PUT - Actualizar aviso
@router.put("/{aviso_id}")
async def update_aviso(aviso_id: int, aviso_update: AvisoUpdate):
    """Actualiza un aviso existente - CORREGIDO ✅"""
    try:
        # Verificar que el aviso exists
        await validar_aviso_existe(aviso_id)
        
        # Construir query dinámicamente
        updates = []
        params = []
        
        if aviso_update.nombre_evento is not None:
            updates.append("nombre_evento = %s")
            params.append(aviso_update.nombre_evento.strip())
            
        if aviso_update.fecha is not None:
            updates.append("fecha = %s")
            params.append(aviso_update.fecha)
            
        if aviso_update.descripcion is not None:
            updates.append("descripcion = %s")
            params.append(aviso_update.descripcion.strip())
            
        if aviso_update.enlace is not None:
            updates.append("enlace = %s")
            params.append(str(aviso_update.enlace))
        
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No se proporcionaron campos para actualizar"
            )
        
        # Ejecutar actualización - SIN f-strings problemáticos
        params.append(aviso_id)
        update_query = "UPDATE avisos SET " + ", ".join(updates) + " WHERE id = %s"
        
        await execute_query(update_query, params)
        
        # Obtener aviso actualizado - CON parámetros separados para DATE_FORMAT
        aviso_actualizado = await fetch_one("""
            SELECT id, nombre_evento,
                   DATE_FORMAT(fecha, %s) AS fecha,
                   descripcion, enlace,
                   DATE_FORMAT(fecha_creacion, %s) AS fecha_creacion
            FROM avisos
            WHERE id = %s
        """, ('%Y-%m-%d', '%Y-%m-%d %H:%i:%s', aviso_id))
        
        logger.info(f"✅ Aviso {aviso_id} actualizado")
        
        return {
            "success": True,
            "message": "Aviso actualizado exitosamente",
            "data": aviso_actualizado,
            "changes": len(updates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al actualizar aviso {aviso_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar el aviso"
        )


# ✅ DELETE - Eliminar aviso
@router.delete("/{aviso_id}")
async def delete_aviso(aviso_id: int):
    """
    Elimina un aviso específico
    """
    try:
        # Verificar que el aviso existe
        aviso = await validar_aviso_existe(aviso_id)
        
        # Eliminar aviso
        await execute_query("DELETE FROM avisos WHERE id = %s", (aviso_id,))
        
        logger.info(f"✅ Aviso {aviso_id} eliminado")
        
        return {
            "success": True,
            "message": f"Aviso '{aviso['nombre_evento']}' eliminado exitosamente",
            "deleted_data": {
                "id": aviso_id,
                "nombre_evento": aviso['nombre_evento']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar aviso {aviso_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al eliminar el aviso"
        )

