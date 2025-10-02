from fastapi import APIRouter, HTTPException
from config.db import fetch_all

router = APIRouter()

# ==================== OBTENER GRUPOS ====================
@router.get("/grupos")
async def obtener_grupos():
    """Obtiene lista de grupos con formato legible"""
    try:
        grupos = await fetch_all("""
            SELECT id_grupo, nombre, turno, nivel
            FROM grupo
            ORDER BY nivel, nombre, turno
        """)
        
        return [
            {
                "id": g["id_grupo"],
                "label": f"{g['nombre']} - {g['turno'].capitalize()} ({g['nivel'] or 'N/A'})",
                "nombre": g["nombre"]
            }
            for g in grupos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== OBTENER ESTUDIANTES ====================
@router.get("/estudiantes")
async def obtener_estudiantes():
    """Obtiene lista de estudiantes con matrícula y nombre"""
    try:
        estudiantes = await fetch_all("""
            SELECT e.id_estudiante, e.matricula, e.nombre, e.apellido, g.nombre as grupo
            FROM estudiante e
            LEFT JOIN grupo g ON e.id_grupo = g.id_grupo
            WHERE e.estado_actual = 'activo'
            ORDER BY e.apellido, e.nombre
        """)
        
        return [
            {
                "id": e["id_estudiante"],
                "label": f"{e['matricula']} - {e['apellido']} {e['nombre']} ({e['grupo'] or 'Sin grupo'})",
                "matricula": e["matricula"]
            }
            for e in estudiantes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== OBTENER CLASES ====================
@router.get("/clases")
async def obtener_clases():
    """Obtiene lista de clases con materia y grupo"""
    try:
        clases = await fetch_all("""
            SELECT 
                c.id_clase,
                c.nrc,
                m.nombre as materia,
                m.num_curso,
                g.nombre as grupo,
                p.nombre as profesor
            FROM clase c
            LEFT JOIN materia m ON c.id_materia = m.id_materia
            LEFT JOIN grupo g ON c.id_grupo = g.id_grupo
            LEFT JOIN profesor p ON c.id_profesor = p.id_profesor
            ORDER BY m.nombre, g.nombre
        """)
        
        return [
            {
                "id": c["id_clase"],
                "label": f"{c['materia']} - {c['grupo']} (NRC: {c['nrc']})",
                "nrc": c["nrc"],
                "materia": c["materia"],
                "grupo": c["grupo"]
            }
            for c in clases
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== OBTENER PROFESORES ====================
@router.get("/profesores")
async def obtener_profesores():
    """Obtiene lista de profesores"""
    try:
        profesores = await fetch_all("""
            SELECT p.id_profesor, p.nombre
            FROM profesor p
            ORDER BY p.nombre
        """)
        
        return [
            {
                "id": p["id_profesor"],
                "label": f"{p['nombre']} (ID: {p['id_profesor']})",
                "nombre": p["nombre"]
            }
            for p in profesores
        ]
    except Exception as e:
        print(f"Error en obtener_profesores: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== OBTENER CLASES POR PROFESOR ====================
@router.get("/profesores/{id_profesor}/clases")
async def obtener_clases_profesor(id_profesor: int):
    """Obtiene las clases de un profesor específico"""
    try:
        clases = await fetch_all("""
            SELECT 
                c.id_clase,
                c.nrc,
                m.nombre as materia,
                g.nombre as grupo
            FROM clase c
            LEFT JOIN materia m ON c.id_materia = m.id_materia
            LEFT JOIN grupo g ON c.id_grupo = g.id_grupo
            WHERE c.id_profesor = %s
            ORDER BY m.nombre, g.nombre
        """, (id_profesor,))
        
        return [
            {
                "id": c["id_clase"],
                "label": f"{c['materia']} - {c['grupo']}",
                "nrc": c["nrc"]
            }
            for c in clases
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))