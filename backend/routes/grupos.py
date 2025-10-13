from fastapi import APIRouter, HTTPException
import aiomysql
from config.db import fetch_one, fetch_all, execute_query

router = APIRouter()


# Obtener todos los grupos
@router.get("/")
async def obtener_grupos():
    """Obtiene todos los grupos disponibles"""
    query = "SELECT id_grupo, nombre, turno, nivel FROM grupo ORDER BY nombre"
    try:
        grupos = await fetch_all(query)
        return {
            "success": True,
            "data": grupos
        }
    except Exception as e:
        print(f"Error al obtener grupos: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener grupos")

@router.get("/lista")
async def obtener_grupos():
    """Obtiene todos los grupos disponibles"""
    query = "SELECT id_grupo, nombre, turno, nivel FROM grupo ORDER BY nombre"
    try:
        grupos = await fetch_all(query)
        return grupos  # ✅ Devuelve directamente la lista
    except Exception as e:
        print(f"Error al obtener grupos: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener grupos")

# Obtener un grupo por ID
@router.get("/{id_grupo}")
async def obtener_grupo(id_grupo: int):
    """Obtiene un grupo específico por su ID"""
    query = "SELECT * FROM grupo WHERE id_grupo = %s"
    try:
        grupo = await fetch_one(query, (id_grupo,))
        if not grupo:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        return {
            "success": True,
            "data": grupo
        }
    except Exception as e:
        print(f"Error al obtener grupo {id_grupo}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener grupo")


# Obtener estudiantes de un grupo
@router.get("/{id_grupo}/estudiantes")
async def obtener_estudiantes_grupo(id_grupo: int):
    """Obtiene todos los estudiantes de un grupo específico"""
    # Primero verificar que el grupo existe
    grupo_query = "SELECT id_grupo, nombre FROM grupo WHERE id_grupo = %s"
    grupo = await fetch_one(grupo_query, (id_grupo,))
    
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    
    # Obtener estudiantes del grupo
    estudiantes_query = """
        SELECT 
            e.id_estudiante,
            e.matricula,
            e.nombre,
            e.apellido,
            e.correo,
            e.estado_actual,
            e.no_lista
        FROM estudiante e 
        WHERE e.id_grupo = %s 
        ORDER BY e.no_lista, e.apellido, e.nombre
    """
    
    try:
        estudiantes = await fetch_all(estudiantes_query, (id_grupo,))
        return {
            "success": True,
            "data": {
                "grupo": grupo,
                "estudiantes": estudiantes,
                "total": len(estudiantes)
            }
        }
    except Exception as e:
        print(f"Error al obtener estudiantes del grupo {id_grupo}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener estudiantes del grupo")


# Obtener clases de un grupo
@router.get("/{id_grupo}/clases")
async def obtener_clases_grupo(id_grupo: int):
    """Obtiene todas las clases de un grupo específico"""
    # Verificar que el grupo existe
    grupo_query = "SELECT id_grupo, nombre FROM grupo WHERE id_grupo = %s"
    grupo = await fetch_one(grupo_query, (id_grupo,))
    
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    
    # Obtener clases del grupo con información de materia y profesor
    clases_query = """
        SELECT 
            c.id_clase,
            c.nrc,
            c.nombre_clase,
            c.aula,
            m.nombre as materia_nombre,
            m.clave as materia_clave,
            p.nombre as profesor_nombre
        FROM clase c
        JOIN materia m ON c.id_materia = m.id_materia
        JOIN profesor p ON c.id_profesor = p.id_profesor
        WHERE c.id_grupo = %s
        ORDER BY m.nombre
    """
    
    try:
        clases = await fetch_all(clases_query, (id_grupo,))
        return {
            "success": True,
            "data": {
                "grupo": grupo,
                "clases": clases,
                "total": len(clases)
            }
        }
    except Exception as e:
        print(f"Error al obtener clases del grupo {id_grupo}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener clases del grupo")


# Obtener horarios de un grupo
@router.get("/{id_grupo}/horarios")
async def obtener_horarios_grupo(id_grupo: int):
    grupo_query = "SELECT id_grupo, nombre FROM grupo WHERE id_grupo = %s"
    grupo = await fetch_one(grupo_query, (id_grupo,))
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    horarios_query = """
        SELECT 
            h.id_horario,
            h.dia,
            TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hora_inicio,
            TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hora_fin,
            c.nombre_clase,
            c.aula,
            m.nombre AS materia_nombre,
            p.nombre AS profesor_nombre
        FROM horario_clase h
        JOIN clase c   ON h.id_clase = c.id_clase
        JOIN materia m ON c.id_materia = m.id_materia
        JOIN profesor p ON c.id_profesor = p.id_profesor
        WHERE c.id_grupo = %s
        ORDER BY 
            FIELD(h.dia, 'Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'),
            h.hora_inicio
    """

    try:
        horarios = await fetch_all(horarios_query, (id_grupo,))
        return {
            "success": True,
            "data": {
                "grupo": grupo,
                "horarios": horarios,
                "total": len(horarios),
            },
        }
    except Exception as e:
        print(f"Error al obtener horarios del grupo {id_grupo}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener horarios del grupo")