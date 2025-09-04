# backend/routes/qr.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, validator
from config.db import fetch_one, fetch_all, execute_query
from utils.fernet import decrypt_qr, encrypt_qr
from utils.fecha import obtener_fecha_hora_cdmx
import aiomysql
import qrcode
import base64
from io import BytesIO
from datetime import datetime, time

router = APIRouter()


# ----------------------------
# Modelos
# ----------------------------
class AsistenciaQRRequest(BaseModel):
    qrData: str
    estado: str = "presente"
    
    @validator('qrData')
    def qrdata_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Los datos del QR no pueden estar vacíos')
        return v.strip()
    
    @validator('estado')
    def estado_must_be_valid(cls, v):
        estados_validos = ['presente', 'ausente', 'justificante']
        if v.lower() not in estados_validos:
            raise ValueError(f'Estado debe ser uno de: {", ".join(estados_validos)}')
        return v.lower()


class QRInfoRequest(BaseModel):
    qrData: str
    
    @validator('qrData')
    def qrdata_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Los datos del QR no pueden estar vacíos')
        return v.strip()


def convertir_dia_espanol_a_enum(dia_espanol):
    """Convierte día en español al formato enum de la BD"""
    mapeo_dias = {
        'lunes': 'Lunes',
        'martes': 'Martes',
        'miércoles': 'Miércoles',
        'miercoles': 'Miércoles',
        'jueves': 'Jueves',
        'viernes': 'Viernes',
        'sábado': 'Sábado',
        'sabado': 'Sábado'
    }
    return mapeo_dias.get(dia_espanol.lower(), dia_espanol)


# ----------------------------
# Endpoints
# ----------------------------

# Registrar asistencia vía QR
@router.post("/asistencia-qr")
async def registrar_asistencia(req: AsistenciaQRRequest):
    """Registra asistencia usando datos de QR encriptado"""
    try:
        # Desencriptar QR
        try:
            texto_plano = decrypt_qr(req.qrData)
        except Exception as decrypt_error:
            print(f"Error desencriptando QR: {decrypt_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR inválido o corrupto"
            )

        # Validar formato: "NOMBRE|MATRICULA|GRUPO|CLAVE"
        partes = [s.strip() for s in texto_plano.split("|")]
        if len(partes) != 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de QR inválido"
            )
        
        nombre_completo, matricula, grupo_qr, clave_unica = partes

        # Buscar estudiante y validar grupo
        estudiante = await fetch_one("""
            SELECT 
                e.id_estudiante, 
                e.id_grupo,
                e.nombre,
                e.apellido,
                g.nombre as grupo_nombre
            FROM estudiante e
            JOIN grupo g ON e.id_grupo = g.id_grupo
            WHERE e.matricula = %s
        """, (matricula,))
        
        if not estudiante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estudiante no encontrado"
            )

        # Validar que el grupo del QR coincida con el de la BD
        if grupo_qr.upper() != estudiante['grupo_nombre'].upper():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El grupo en el QR no coincide con el registrado"
            )

        id_estudiante = estudiante["id_estudiante"]
        id_grupo = estudiante["id_grupo"]

        # Obtener fecha y hora actual
        datos_fecha = obtener_fecha_hora_cdmx()
        fecha = datos_fecha["fecha"]
        hora = datos_fecha["hora"]
        dia = datos_fecha["dia"]

        print(f"DEBUG => fecha: {fecha}, hora: {hora}, dia: {dia}")
        # Convertir hora a objeto time si es string
        if isinstance(hora, str):
            try:
                # Aseguramos que tenga segundos
                if len(hora.split(":")) == 2:
                    hora = hora + ":00"
                hora_obj = time.fromisoformat(hora)
            except Exception as e:
                print(f"Error convirtiendo hora: {hora} -> {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Formato de hora inválido: {hora}"
                )
        else:
            hora_obj = hora

        # Buscar clase activa CORREGIDA
        clase = await fetch_one("""
            SELECT 
                c.id_clase,
                c.nombre_clase,
                m.nombre as materia,
                hc.hora_inicio,
                hc.hora_fin
            FROM horario_clase hc
            JOIN clase c ON hc.id_clase = c.id_clase
            JOIN materia m ON c.id_materia = m.id_materia
            WHERE c.id_grupo = %s
              AND hc.dia = %s
              AND hc.hora_inicio <= %s
              AND hc.hora_fin > %s
            LIMIT 1
        """, (id_grupo, dia, hora_obj, hora_obj))
        
        if not clase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay clase activa para este grupo en este horario"
            )

        id_clase = clase["id_clase"]

        # Verificar si ya existe asistencia para hoy
        asistencia_existente = await fetch_one("""
            SELECT id_asistencia, estado 
            FROM asistencia 
            WHERE id_estudiante = %s AND id_clase = %s AND fecha = %s
        """, (id_estudiante, id_clase, fecha))

        if asistencia_existente:
            # Actualizar estado existente
            await execute_query("""
                UPDATE asistencia 
                SET estado = %s, hora_entrada = %s 
                WHERE id_asistencia = %s
            """, (req.estado, hora_obj, asistencia_existente['id_asistencia']))
            
            accion = "actualizada"
        else:
            # Insertar nueva asistencia
            await execute_query("""
                INSERT INTO asistencia (id_estudiante, id_clase, estado, fecha, hora_entrada) 
                VALUES (%s, %s, %s, %s, %s)
            """, (id_estudiante, id_clase, req.estado, fecha, hora_obj))
            
            accion = "registrada"

        return {
            "success": True,
            "message": f"Asistencia {accion} correctamente",
            "data": {
                "estudiante": f"{estudiante['nombre']} {estudiante['apellido']}",
                "matricula": matricula,
                "grupo": estudiante['grupo_nombre'],
                "clase": clase['materia'],
                "estado": req.estado,
                "fecha": fecha.isoformat() if hasattr(fecha, 'isoformat') else str(fecha),
                "hora": hora_obj.isoformat() if hasattr(hora_obj, 'isoformat') else str(hora_obj),
                "accion": accion
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error registrar_asistencia: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al procesar el QR"
        )


# Generar QR por matrícula
@router.get("/por-matricula/{matricula}")
async def generar_qr(matricula: str):
    """Genera un QR encriptado para un estudiante"""
    matricula = matricula.strip()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula requerida"
        )

    try:
        # Buscar estudiante
        alumno = await fetch_one("""
            SELECT 
                e.nombre, 
                e.apellido, 
                e.matricula, 
                g.nombre AS grupo,
                e.estado_actual
            FROM estudiante e
            JOIN grupo g ON e.id_grupo = g.id_grupo
            WHERE e.matricula = %s
        """, (matricula,))
        
        if not alumno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estudiante no encontrado"
            )

        # Verificar que el estudiante esté activo
        if alumno['estado_actual'] != 'activo':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El estudiante está {alumno['estado_actual']}, no se puede generar QR"
            )

        nombre_completo = f"{alumno['nombre']} {alumno['apellido']}"
        grupo = alumno["grupo"]

        # Generar datos para QR con clave única
        try:
            from utils.fernet import STATIC_UNIQUE_ID
            clave_unica = STATIC_UNIQUE_ID
        except ImportError:
            # Fallback si no existe STATIC_UNIQUE_ID
            clave_unica = "DEFAULT_KEY"

        datos = f"{nombre_completo}|{alumno['matricula']}|{grupo}|{clave_unica}"

        # Encriptar con Fernet
        try:
            encrypted = encrypt_qr(datos)
        except Exception as encrypt_error:
            print(f"Error encriptando datos: {encrypt_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al generar QR encriptado"
            )

        # Generar QR visual en base64
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10, 
                border=4
            )
            qr.add_data(encrypted)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_base64 = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        except Exception as qr_error:
            print(f"Error generando imagen QR: {qr_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al generar imagen QR"
            )

        return {
            "success": True,
            "data": {
                "estudiante": {
                    "nombre": nombre_completo,
                    "matricula": alumno["matricula"],
                    "grupo": grupo,
                    "estado": alumno['estado_actual']
                },
                "qr": {
                    "imagen": qr_base64,
                    "texto_encriptado": encrypted,
                    "datos_originales": datos
                },
                "generado": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generar_qr: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al generar el QR"
        )


# Obtener información del QR
@router.post("/info")
async def info_qr(req: QRInfoRequest):
    """Obtiene información decodificada de un QR sin registrar asistencia"""
    try:
        # Desencriptar QR
        try:
            texto_plano = decrypt_qr(req.qrData)
        except Exception as decrypt_error:
            print(f"Error desencriptando QR: {decrypt_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR inválido o corrupto"
            )

        # Validar formato
        partes = [s.strip() for s in texto_plano.split("|")]
        if len(partes) != 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de QR inválido"
            )
        
        nombre_completo, matricula, grupo_qr, clave_unica = partes

        # Validar en BD
        alumno = await fetch_one("""
            SELECT 
                e.nombre, 
                e.apellido, 
                e.matricula, 
                e.estado_actual,
                e.correo,
                e.no_lista,
                g.nombre AS grupo,
                g.turno,
                g.nivel
            FROM estudiante e
            JOIN grupo g ON e.id_grupo = g.id_grupo
            WHERE e.matricula = %s
        """, (matricula,))
        
        if not alumno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estudiante no encontrado en la base de datos"
            )

        # Verificar consistencia de grupo
        grupo_coincide = grupo_qr.upper() == alumno["grupo"].upper()

        nombre_bd = f"{alumno['nombre']} {alumno['apellido']}"
        
        return {
            "success": True,
            "data": {
                "qr_valido": True,
                "datos_qr": {
                    "nombre": nombre_completo,
                    "matricula": matricula,
                    "grupo": grupo_qr,
                    "clave": clave_unica
                },
                "datos_bd": {
                    "nombre": nombre_bd,
                    "matricula": alumno["matricula"],
                    "grupo": alumno["grupo"],
                    "turno": alumno["turno"],
                    "nivel": alumno["nivel"],
                    "estado": alumno["estado_actual"],
                    "correo": alumno["correo"],
                    "no_lista": alumno["no_lista"]
                },
                "validacion": {
                    "grupo_coincide": grupo_coincide,
                    "estudiante_activo": alumno["estado_actual"] == "activo"
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error info_qr: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al procesar el QR"
        )


# Validar QR sin procesar
@router.post("/validar")
async def validar_qr(req: QRInfoRequest):
    """Valida si un QR es válido sin procesar ni guardar información"""
    try:
        # Intentar desencriptar
        try:
            texto_plano = decrypt_qr(req.qrData)
            partes = [s.strip() for s in texto_plano.split("|")]
            
            return {
                "success": True,
                "data": {
                    "qr_valido": True,
                    "formato_correcto": len(partes) == 4,
                    "partes": len(partes),
                    "estructura": partes if len(partes) == 4 else None
                }
            }
        except Exception:
            return {
                "success": True,
                "data": {
                    "qr_valido": False,
                    "formato_correcto": False,
                    "error": "No se pudo desencriptar el QR"
                }
            }

    except Exception as e:
        print(f"Error validar_qr: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al validar QR"
        )