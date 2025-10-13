# backend/routes/profesor.py
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, validator
from config.db import fetch_one, fetch_all, execute_query
from utils.fecha import obtener_fecha_hora_cdmx
import aiomysql
import bcrypt
from datetime import datetime, time, timedelta

router = APIRouter()


# ----------------------------
# Modelos
# ----------------------------
class LoginDocenteRequest(BaseModel):
    usuario: str
    contrasena: str
    
    @validator('usuario')
    def usuario_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('El usuario no puede estar vacío')
        return v.strip()
    
    @validator('contrasena')
    def contrasena_must_not_be_empty(cls, v):
        if not v or len(v) < 1:
            raise ValueError('La contraseña no puede estar vacía')
        return v


def convertir_dia_espanol_a_enum(dia_espanol):
    """Convierte día en español al formato enum de la BD"""
    mapeo_dias = {
        'lunes': 'Lunes',
        'martes': 'Martes',
        'miércoles': 'Miércoles',
        'miercoles': 'Miércoles',  # sin acento
        'jueves': 'Jueves',
        'viernes': 'Viernes',
        'sábado': 'Sábado',
        'sabado': 'Sábado'  # sin acento
    }
    return mapeo_dias.get(dia_espanol.lower(), dia_espanol)


# ----------------------------
# Endpoints
# ----------------------------
# Clase actual del profesor
@router.get("/clase-actual")
async def clase_actual(id_profesor: int = Query(..., description="ID del profesor")):
    """Obtiene la clase actual activa del profesor"""
    if not id_profesor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Falta el parámetro id_profesor"
        )

    try:
        # Obtener hora y día actual
        res = obtener_fecha_hora_cdmx()  # retorna {'hora': 'HH:MM:SS', 'dia': 'lunes'}
        hora = res['hora']
        dia = res['dia']

        dia_enum = convertir_dia_espanol_a_enum(dia)
        
        # Convertir hora a objeto time si es string
        if isinstance(hora, str):
            hora_obj = time.fromisoformat(hora)
        else:
            hora_obj = hora

        # Verificar que el profesor existe
        profesor = await fetch_one(
            "SELECT nombre FROM profesor WHERE id_profesor = %s", 
            (id_profesor,)
        )
        
        if not profesor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Profesor no encontrado"
            )
        
        nombre_profesor = profesor['nombre']

        # Buscar clase actual
        clase = await fetch_one("""
            SELECT 
                c.id_clase,
                c.nombre_clase,
                c.nrc,
                c.aula,
                hc.hora_inicio,
                hc.hora_fin,
                hc.dia,
                g.id_grupo,
                g.nombre AS grupo,
                g.turno,
                g.nivel,
                m.nombre AS materia,
                m.clave AS materia_clave
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN materia m ON c.id_materia = m.id_materia
            WHERE c.id_profesor = %s
              AND hc.dia = %s
              AND hc.hora_inicio <= %s
              AND hc.hora_fin >= %s
            LIMIT 1
        """, (id_profesor, dia_enum, hora_obj, hora_obj))

        if clase:
            # Convertir hora_inicio y hora_fin a HH:MM
            clase["hora_inicio"] = clase["hora_inicio"].strftime("%H:%M") if hasattr(clase["hora_inicio"], "strftime") else str(clase["hora_inicio"])
            clase["hora_fin"] = clase["hora_fin"].strftime("%H:%M") if hasattr(clase["hora_fin"], "strftime") else str(clase["hora_fin"])

        if not clase:
            return {
                "success": True,
                "data": {
                    "nombre_profesor": nombre_profesor,
                    "clase_actual": None,
                    "mensaje": "No hay clase activa en este momento"
                }
            }

        return {
            "success": True,
            "data": {
                "nombre_profesor": nombre_profesor,
                "clase_actual": clase,
                "mensaje": "Clase activa encontrada"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error clase_actual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error al obtener clase actual"
        )


# Login docente
@router.post("/login")
async def login_docente(data: LoginDocenteRequest):
    """Login específico para docentes"""
    try:
        # Buscar usuario
        user = await fetch_one(
            "SELECT id_usuario, contrasena, rol FROM usuario WHERE usuario_login = %s", 
            (data.usuario,)
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Credenciales inválidas"
            )
        
        # Verificar que es docente
        if user['rol'] != "docente":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado: No es docente"
            )
        
        # Validar contraseña
        try:
            if user['contrasena'].startswith('$2b$') or user['contrasena'].startswith('$2a$'):
                valid_password = bcrypt.checkpw(
                    data.contrasena.encode('utf-8'), 
                    user['contrasena'].encode('utf-8')
                )
            else:
                valid_password = data.contrasena == user['contrasena']
        except Exception:
            valid_password = False
        
        if not valid_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Credenciales inválidas"
            )

        # Obtener información del profesor
        prof = await fetch_one(
            "SELECT id_profesor, nombre FROM profesor WHERE id_usuario = %s", 
            (user['id_usuario'],)
        )
        
        if not prof:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Información de profesor no encontrada"
            )

        return {
            "success": True,
            "message": "Login exitoso",
            "data": {
                "id_profesor": prof['id_profesor'],
                "nombre": prof['nombre'],
                "rol": user['rol'],
                "id_usuario": user['id_usuario']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error login_docente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor"
        )

# La clase de hoy
@router.get("/clases/profesor/{id_profesor}/hoy")
async def clases_hoy(id_profesor: int):
    """Obtiene las clases del profesor para el día actual"""
    try:
        # Verificar que el profesor existe
        profesor = await fetch_one(
            "SELECT nombre FROM profesor WHERE id_profesor = %s", 
            (id_profesor,)
        )
        if not profesor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profesor no encontrado"
            )

        res = obtener_fecha_hora_cdmx()
        dia = res['dia']
        dia_enum = convertir_dia_espanol_a_enum(dia)

        clases = await fetch_all("""
            SELECT 
                c.id_clase, 
                c.nombre_clase,
                c.nrc,
                c.aula,
                m.nombre AS materia, 
                m.clave AS materia_clave,
                g.nombre AS grupo,
                g.turno,
                g.nivel,
                hc.hora_inicio, 
                hc.hora_fin, 
                hc.dia,
                p.nombre AS nombre_profesor
            FROM clase c
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN horario_clase hc ON c.id_clase = hc.id_clase
            JOIN profesor p ON c.id_profesor = p.id_profesor
            WHERE c.id_profesor = %s AND hc.dia = %s
            ORDER BY hc.hora_inicio
        """, (id_profesor, dia_enum))

        # Convertir hora_inicio y hora_fin a HH:MM
        for clase in clases:
            # hora_inicio
            if hasattr(clase['hora_inicio'], "strftime"):
                clase['hora_inicio'] = clase['hora_inicio'].strftime("%H:%M")
            elif isinstance(clase['hora_inicio'], timedelta):
                total_segundos = clase['hora_inicio'].total_seconds()
                hs = int(total_segundos // 3600)
                ms = int((total_segundos % 3600) // 60)
                clase['hora_inicio'] = f"{hs:02d}:{ms:02d}"
            else:
                clase['hora_inicio'] = str(clase['hora_inicio'])

            # hora_fin
            if hasattr(clase['hora_fin'], "strftime"):
                clase['hora_fin'] = clase['hora_fin'].strftime("%H:%M")
            elif isinstance(clase['hora_fin'], timedelta):
                total_segundos = clase['hora_fin'].total_seconds()
                hs = int(total_segundos // 3600)
                ms = int((total_segundos % 3600) // 60)
                clase['hora_fin'] = f"{hs:02d}:{ms:02d}"
            else:
                clase['hora_fin'] = str(clase['hora_fin'])

        # ✅ Aquí devolvemos la respuesta
        return {
            "success": True,
            "data": {
                "profesor": profesor['nombre'],
                "dia": dia_enum,
                "clases": clases,
                "total": len(clases)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error clases_hoy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo clases del día actual"
        )

# Todas las clases del profesor
@router.get("/clases/profesor/{id_profesor}")
async def todas_clases(id_profesor: int):
    """Obtiene todas las clases del profesor"""
    try:
        # Verificar que el profesor existe
        profesor = await fetch_one(
            "SELECT nombre FROM profesor WHERE id_profesor = %s", 
            (id_profesor,)
        )
        if not profesor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Profesor no encontrado"
            )

        clases = await fetch_all("""
            SELECT 
                c.id_clase, 
                c.nombre_clase,
                c.nrc,
                c.aula,
                m.nombre AS materia, 
                m.clave AS materia_clave,
                g.nombre AS grupo,
                g.turno,
                g.nivel,
                c.id_grupo,   
                hc.hora_inicio, 
                hc.hora_fin, 
                hc.dia,
                p.nombre AS nombre_profesor
            FROM clase c
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN horario_clase hc ON c.id_clase = hc.id_clase
            JOIN profesor p ON c.id_profesor = p.id_profesor
            WHERE c.id_profesor = %s
            ORDER BY 
                FIELD(hc.dia, 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'),
                hc.hora_inicio
        """, (id_profesor,))

        # Convertir hora_inicio y hora_fin a HH:MM
        for clase in clases:
            # hora_inicio
            if hasattr(clase['hora_inicio'], "strftime"):
                clase['hora_inicio'] = clase['hora_inicio'].strftime("%H:%M")
            elif isinstance(clase['hora_inicio'], timedelta):
                total_segundos = clase['hora_inicio'].total_seconds()
                hs = int(total_segundos // 3600)
                ms = int((total_segundos % 3600) // 60)
                clase['hora_inicio'] = f"{hs:02d}:{ms:02d}"
            else:
                # si viene en segundos
                hs = int(clase['hora_inicio'] // 3600)
                ms = int((clase['hora_inicio'] % 3600) // 60)
                clase['hora_inicio'] = f"{hs:02d}:{ms:02d}"

            # hora_fin
            if hasattr(clase['hora_fin'], "strftime"):
                clase['hora_fin'] = clase['hora_fin'].strftime("%H:%M")
            elif isinstance(clase['hora_fin'], timedelta):
                total_segundos = clase['hora_fin'].total_seconds()
                hs = int(total_segundos // 3600)
                ms = int((total_segundos % 3600) // 60)
                clase['hora_fin'] = f"{hs:02d}:{ms:02d}"
            else:
                # si viene en segundos
                hs = int(clase['hora_fin'] // 3600)
                ms = int((clase['hora_fin'] % 3600) // 60)
                clase['hora_fin'] = f"{hs:02d}:{ms:02d}"

        # Agrupar clases por día
        clases_por_dia = {}
        for clase in clases:
            dia = clase['dia']
            if dia not in clases_por_dia:
                clases_por_dia[dia] = []
            clases_por_dia[dia].append(clase)

        return {
            "success": True,
            "data": {
                "profesor": profesor['nombre'],
                "clases_por_dia": clases_por_dia,
                "total_clases": len(clases)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error todas_clases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error obteniendo todas las clases"
        )
    

    
# Obtener estudiantes de una clase específica
@router.get("/clase/{id_clase}/estudiantes")
async def obtener_estudiantes_clase(id_clase: int):
    """Obtiene los estudiantes de una clase específica"""
    try:
        # Verificar que la clase existe
        clase = await fetch_one("""
            SELECT 
                c.id_clase,
                c.nombre_clase,
                m.nombre AS materia,
                g.nombre AS grupo,
                p.nombre AS profesor
            FROM clase c
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN grupo g ON c.id_grupo = g.id_grupo
            JOIN profesor p ON c.id_profesor = p.id_profesor
            WHERE c.id_clase = %s
        """, (id_clase,))
        
        if not clase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Clase no encontrada"
            )

        # Obtener estudiantes del grupo de la clase
        estudiantes = await fetch_all("""
            SELECT 
                e.id_estudiante,
                e.matricula,
                e.nombre,
                e.apellido,
                e.correo,
                e.estado_actual,
                e.no_lista
            FROM estudiante e
            JOIN clase c ON e.id_grupo = c.id_grupo
            WHERE c.id_clase = %s
            ORDER BY e.no_lista, e.apellido, e.nombre
        """, (id_clase,))

        return {
            "success": True,
            "data": {
                "clase": clase,
                "estudiantes": estudiantes,
                "total_estudiantes": len(estudiantes)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error obtener_estudiantes_clase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error obteniendo estudiantes de la clase"
        )