from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from config.db import fetch_one, fetch_all
from typing import List, Optional
import logging
import math

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================
# FUNCIÓN: Calcular ordinario con regla de redondeo
# ============================================
def calcular_ordinario(parcial_1: Optional[int], parcial_2: Optional[int]) -> Optional[float]:
    """
    Calcula el ordinario (promedio de parciales) con regla especial de redondeo:
    - Si la parte decimal >= 0.6 → redondea hacia arriba
    - Si la parte decimal < 0.6 → redondea hacia abajo
    """
    if parcial_1 is None or parcial_2 is None:
        return None
    
    try:
        p1 = float(parcial_1)
        p2 = float(parcial_2)
    except Exception:
        return None

    promedio = (p1 + p2) / 2
    parte_entera = math.floor(promedio)
    parte_decimal = promedio - parte_entera

    if parte_decimal >= 0.6:
        return float(math.ceil(promedio))
    else:
        return float(math.floor(promedio))

# ============================================
# MODELOS PYDANTIC
# ============================================

class CalificacionesEstudianteResponse(BaseModel):
    """Respuesta con calificaciones de un estudiante en una clase"""
    id_estudiante: int
    matricula: str
    nombre_completo: str
    id_clase: int
    nombre_clase: str
    nrc: str
    
    # Calificaciones
    parcial_1: Optional[int] = None
    parcial_2: Optional[int] = None
    ordinario: Optional[float] = None
    promedio_parciales: Optional[float] = None
    
    # Estados y fechas
    estado_parcial_1: str
    estado_parcial_2: str
    fecha_parcial_1: Optional[str] = None
    fecha_parcial_2: Optional[str] = None


# ============================================
# ENDPOINT 1: GET /api/calificaciones/estudiante/{id_estudiante}/clase/{id_clase}
# ============================================

@router.get(
    "/estudiante/{id_estudiante}/clase/{id_clase}",
    response_model=CalificacionesEstudianteResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener calificaciones de parciales de un estudiante",
    description="Retorna SOLO las calificaciones de parcial_1, parcial_2 y ordinario"
)
async def obtener_calificaciones_estudiante(
    id_estudiante: int,
    id_clase: int
):
    """
    Obtiene las calificaciones de parciales de un estudiante en una clase.
    
    **NO incluye actividades** - solo calificaciones de parciales.
    """
    try:
        # Verificar estudiante
        query_estudiante = """
            SELECT e.id_estudiante, e.matricula, 
                   CONCAT(e.nombre, ' ', e.apellido) as nombre_completo,
                   e.id_grupo
            FROM estudiante e
            WHERE e.id_estudiante = %s AND e.estado_actual = 'activo'
        """
        estudiante = await fetch_one(query_estudiante, (id_estudiante,))
        
        if not estudiante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Estudiante con ID {id_estudiante} no encontrado"
            )
        
        # Verificar clase
        query_clase = """
            SELECT c.id_clase, c.nombre_clase, c.nrc, c.id_grupo
            FROM clase c
            WHERE c.id_clase = %s
        """
        clase = await fetch_one(query_clase, (id_clase,))
        
        if not clase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Clase con ID {id_clase} no encontrada"
            )
        
        # Verificar que el estudiante pertenece al grupo
        if estudiante['id_grupo'] != clase['id_grupo']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estudiante no pertenece al grupo de esta clase"
            )
        
        # 🔥 CORREGIDO: Usar IFNULL y CAST para evitar errores de formato
        query_calificaciones = """
            SELECT 
                parcial, 
                CAST(calificacion AS SIGNED) as calificacion,
                IFNULL(DATE_FORMAT(fecha_registro, '%%d %%b %%Y'), '') as fecha_registro
            FROM calificacion_parcial
            WHERE id_estudiante = %s AND id_clase = %s
        """
        calificaciones = await fetch_all(query_calificaciones, (id_estudiante, id_clase))
        
        # Procesar calificaciones
        parcial_1 = None
        parcial_2 = None
        ordinario = None
        fecha_parcial_1 = None
        fecha_parcial_2 = None
        
        for cal in calificaciones:
            if cal['parcial'] == 'parcial_1':
                parcial_1 = int(cal['calificacion']) if cal['calificacion'] is not None else None
                fecha_parcial_1 = cal['fecha_registro'] if cal['fecha_registro'] else None
            elif cal['parcial'] == 'parcial_2':
                parcial_2 = int(cal['calificacion']) if cal['calificacion'] is not None else None
                fecha_parcial_2 = cal['fecha_registro'] if cal['fecha_registro'] else None
            elif cal['parcial'] == 'ordinario':
                ordinario = float(cal['calificacion']) if cal['calificacion'] is not None else None
        
        # Calcular ordinario si no existe pero hay ambos parciales
        if ordinario is None and parcial_1 is not None and parcial_2 is not None:
            ordinario = calcular_ordinario(parcial_1, parcial_2)
        
        # Calcular promedio de parciales
        promedio_parciales = None
        if parcial_1 is not None and parcial_2 is not None:
            promedio_parciales = round((parcial_1 + parcial_2) / 2, 2)
        
        # Estados
        estado_parcial_1 = "calificado" if parcial_1 is not None else "pendiente"
        estado_parcial_2 = "calificado" if parcial_2 is not None else "pendiente"
        
        return CalificacionesEstudianteResponse(
            id_estudiante=estudiante['id_estudiante'],
            matricula=estudiante['matricula'],
            nombre_completo=estudiante['nombre_completo'],
            id_clase=clase['id_clase'],
            nombre_clase=clase['nombre_clase'],
            nrc=clase['nrc'],
            parcial_1=parcial_1,
            parcial_2=parcial_2,
            ordinario=ordinario,
            promedio_parciales=promedio_parciales,
            estado_parcial_1=estado_parcial_1,
            estado_parcial_2=estado_parcial_2,
            fecha_parcial_1=fecha_parcial_1,
            fecha_parcial_2=fecha_parcial_2
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener calificaciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener calificaciones: {str(e)}"
        )


# ============================================
# ENDPOINT 2: GET /api/calificaciones/clase/{id_clase}
# ============================================

@router.get(
    "/clase/{id_clase}",
    response_model=List[CalificacionesEstudianteResponse],
    status_code=status.HTTP_200_OK,
    summary="Obtener calificaciones de parciales de todos los estudiantes de una clase",
    description="Retorna SOLO las calificaciones de parciales (NO actividades)"
)
async def obtener_calificaciones_clase(id_clase: int):
    """
    Obtiene las calificaciones de parciales de todos los estudiantes de una clase.
    
    **NO incluye actividades** - solo calificaciones de parciales.
    Este endpoint es para mostrar en el RecyclerView de Android.
    """
    try:
        # Verificar clase
        query_clase = """
            SELECT c.id_clase, c.nombre_clase, c.nrc, c.id_grupo
            FROM clase c
            WHERE c.id_clase = %s
        """
        clase = await fetch_one(query_clase, (id_clase,))
        
        if not clase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Clase con ID {id_clase} no encontrada"
            )
        
        # Obtener estudiantes del grupo
        query_estudiantes = """
            SELECT e.id_estudiante, e.matricula,
                   CONCAT(e.nombre, ' ', e.apellido) as nombre_completo
            FROM estudiante e
            WHERE e.id_grupo = %s AND e.estado_actual = 'activo'
            ORDER BY e.no_lista, e.apellido, e.nombre
        """
        estudiantes = await fetch_all(query_estudiantes, (clase['id_grupo'],))
        
        if not estudiantes:
            logger.info(f"No hay estudiantes en el grupo de la clase {id_clase}")
            return []
        
        # 🔥 CORREGIDO: Usar %% para escapar el % en DATE_FORMAT
        query_calificaciones = """
            SELECT 
                id_estudiante, 
                parcial, 
                CAST(calificacion AS SIGNED) as calificacion,
                IFNULL(DATE_FORMAT(fecha_registro, '%%d %%b %%Y'), '') as fecha_registro
            FROM calificacion_parcial
            WHERE id_clase = %s
        """
        calificaciones = await fetch_all(query_calificaciones, (id_clase,))
        
        # 🔥 MANEJO DE TABLA VACÍA
        if not calificaciones:
            logger.info(f"No hay calificaciones registradas para la clase {id_clase}")
            # Retornar estudiantes sin calificaciones
            return [
                CalificacionesEstudianteResponse(
                    id_estudiante=est['id_estudiante'],
                    matricula=est['matricula'],
                    nombre_completo=est['nombre_completo'],
                    id_clase=clase['id_clase'],
                    nombre_clase=clase['nombre_clase'],
                    nrc=clase['nrc'],
                    parcial_1=None,
                    parcial_2=None,
                    ordinario=None,
                    promedio_parciales=None,
                    estado_parcial_1="pendiente",
                    estado_parcial_2="pendiente",
                    fecha_parcial_1=None,
                    fecha_parcial_2=None
                )
                for est in estudiantes
            ]
        
        # Organizar calificaciones por estudiante
        calificaciones_por_estudiante = {}
        
        for cal in calificaciones:
            try:
                id_est = int(cal['id_estudiante'])
                
                if id_est not in calificaciones_por_estudiante:
                    calificaciones_por_estudiante[id_est] = {
                        'parcial_1': None,
                        'parcial_2': None,
                        'ordinario': None,
                        'fecha_parcial_1': None,
                        'fecha_parcial_2': None
                    }
                
                # 🔥 CONVERSIÓN SEGURA A NÚMERO
                calificacion_valor = None
                if cal['calificacion'] is not None:
                    try:
                        calificacion_valor = int(cal['calificacion'])
                    except (ValueError, TypeError):
                        logger.warning(f"Calificación inválida: {cal['calificacion']}")
                        continue
                
                if cal['parcial'] == 'parcial_1':
                    calificaciones_por_estudiante[id_est]['parcial_1'] = calificacion_valor
                    calificaciones_por_estudiante[id_est]['fecha_parcial_1'] = cal['fecha_registro'] if cal['fecha_registro'] else None
                elif cal['parcial'] == 'parcial_2':
                    calificaciones_por_estudiante[id_est]['parcial_2'] = calificacion_valor
                    calificaciones_por_estudiante[id_est]['fecha_parcial_2'] = cal['fecha_registro'] if cal['fecha_registro'] else None
                elif cal['parcial'] == 'ordinario':
                    calificaciones_por_estudiante[id_est]['ordinario'] = float(calificacion_valor) if calificacion_valor is not None else None
                    
            except Exception as e:
                logger.warning(f"Error procesando calificación: {e}, datos: {cal}")
                continue
        
        # Construir respuesta para cada estudiante
        estudiantes_response = []
        
        for estudiante in estudiantes:
            id_est = estudiante['id_estudiante']
            cals = calificaciones_por_estudiante.get(id_est, {
                'parcial_1': None,
                'parcial_2': None,
                'ordinario': None,
                'fecha_parcial_1': None,
                'fecha_parcial_2': None
            })
            
            parcial_1 = cals['parcial_1']
            parcial_2 = cals['parcial_2']
            ordinario = cals['ordinario']
            
            # Calcular ordinario si no existe pero hay ambos parciales
            if ordinario is None and parcial_1 is not None and parcial_2 is not None:
                ordinario = calcular_ordinario(parcial_1, parcial_2)
            
            # Calcular promedio de parciales
            promedio_parciales = None
            if parcial_1 is not None and parcial_2 is not None:
                try:
                    promedio_parciales = round((float(parcial_1) + float(parcial_2)) / 2, 2)
                except Exception as e:
                    logger.warning(f"Error calculando promedio para estudiante {id_est}: {e}")
            
            # Estados
            estado_parcial_1 = "calificado" if parcial_1 is not None else "pendiente"
            estado_parcial_2 = "calificado" if parcial_2 is not None else "pendiente"
            
            estudiantes_response.append(CalificacionesEstudianteResponse(
                id_estudiante=estudiante['id_estudiante'],
                matricula=estudiante['matricula'],
                nombre_completo=estudiante['nombre_completo'],
                id_clase=clase['id_clase'],
                nombre_clase=clase['nombre_clase'],
                nrc=clase['nrc'],
                parcial_1=parcial_1,
                parcial_2=parcial_2,
                ordinario=ordinario,
                promedio_parciales=promedio_parciales,
                estado_parcial_1=estado_parcial_1,
                estado_parcial_2=estado_parcial_2,
                fecha_parcial_1=cals['fecha_parcial_1'],
                fecha_parcial_2=cals['fecha_parcial_2']
            ))
        
        return estudiantes_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener calificaciones de la clase: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener calificaciones: {str(e)}"
        )