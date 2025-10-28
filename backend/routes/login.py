from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, validator
import bcrypt
import aiomysql 
from aiomysql import Pool  
import logging
from datetime import datetime, timedelta
from config.db import fetch_one, fetch_all, execute_query, get_pool
import uuid
import secrets
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from routes.ws_manager_auth import auth_manager

router = APIRouter()
ws_router = APIRouter()
logger = logging.getLogger(__name__)

# --- Schemas ---
class LoginRequest(BaseModel):
    usuario_login: str
    contrasena: str
    
    @validator('usuario_login')
    def usuario_login_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('El usuario no puede estar vacío')
        return v.strip()
    
    @validator('contrasena')
    def contrasena_must_not_be_empty(cls, v):
        if not v or len(v) < 1:
            raise ValueError('La contraseña no puede estar vacía')
        return v

class LoginResponse(BaseModel):
    success: bool
    message: str
    data: dict = None

class UsuarioCreate(BaseModel):
    nombre_completo: str
    correo: EmailStr
    usuario_login: str
    contrasena: str
    rol: str
    
    @validator('rol')
    def validar_rol(cls, v):
        roles_validos = ['docente', 'estudiante', 'admin']
        if v not in roles_validos:
            raise ValueError(f'Rol debe ser uno de: {", ".join(roles_validos)}')
        return v
    
    @validator('contrasena')
    def validar_contrasena(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v

class ConfirmarSesionRequest(BaseModel):
    session_id: str
    id_profesor: int
    id_clase: int

# ===============================================
# ENDPOINTS DE USUARIO
# ===============================================

@router.post("/usuarios")
async def crear_usuario(usuario: UsuarioCreate):
    pool: Pool = await get_pool() 
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("""
                    SELECT COUNT(*) as count FROM usuario 
                    WHERE correo = %s OR usuario_login = %s
                """, (usuario.correo, usuario.usuario_login))
                
                result = await cur.fetchone()
                if result[0] > 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="Correo o nombre de usuario ya registrado"
                    )

                hashed_password = bcrypt.hashpw(
                    usuario.contrasena.encode("utf-8"), 
                    bcrypt.gensalt()
                ).decode('utf-8')

                await cur.execute("""
                    INSERT INTO usuario (nombre_completo, correo, usuario_login, contrasena, rol)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    usuario.nombre_completo,
                    usuario.correo,
                    usuario.usuario_login,
                    hashed_password,
                    usuario.rol
                ))
                
                id_usuario = cur.lastrowid

                if usuario.rol == "docente":
                    await cur.execute("""
                        INSERT INTO profesor (id_usuario, nombre)
                        VALUES (%s, %s)
                    """, (id_usuario, usuario.nombre_completo))

                await conn.commit()

                return {
                    "message": "Usuario creado exitosamente", 
                    "id_usuario": id_usuario,
                    "rol": usuario.rol
                }

            except aiomysql.MySQLError as e:
                await conn.rollback()
                logger.error(f"Error de MySQL: {e}")
                
                if "Duplicate entry" in str(e):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Correo o usuario ya registrado"
                    )
                elif "Data too long" in str(e):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Algunos datos son demasiado largos"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error interno del servidor"
                    )
            
            except Exception as e:
                await conn.rollback()
                logger.error(f"Error inesperado: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error interno del servidor"
                )

@router.post("/", response_model=LoginResponse)
async def login(data: LoginRequest):
    """Endpoint para autenticación de usuarios"""
    try:
        query = """
            SELECT 
                u.id_usuario,
                u.nombre_completo,
                u.correo,
                u.usuario_login,
                u.contrasena,
                u.rol
            FROM usuario u 
            WHERE u.usuario_login = %s
        """
        
        user = await fetch_one(query, (data.usuario_login,))
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
        
        try:
            if user['contrasena'].startswith('$2b$') or user['contrasena'].startswith('$2a$'):
                valid_password = bcrypt.checkpw(
                    data.contrasena.encode('utf-8'), 
                    user['contrasena'].encode('utf-8')
                )
            else:
                valid_password = data.contrasena == user['contrasena']
                
                if valid_password:
                    hashed_password = bcrypt.hashpw(
                        data.contrasena.encode('utf-8'), 
                        bcrypt.gensalt()
                    ).decode('utf-8')
                    
                    update_query = "UPDATE usuario SET contrasena = %s WHERE id_usuario = %s"
                    await execute_query(update_query, (hashed_password, user['id_usuario']))
                    
        except Exception as password_error:
            print(f"Error validando contraseña: {password_error}")
            valid_password = False
        
        if not valid_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
        
        user_data = {
            "id_usuario": user['id_usuario'],
            "nombre_completo": user['nombre_completo'],
            "correo": user['correo'],
            "usuario_login": user['usuario_login'],
            "rol": user['rol']
        }
        
        if user['rol'] == 'docente':
            profesor_query = """
                SELECT 
                    p.id_profesor,
                    p.nombre as nombre_profesor
                FROM profesor p 
                WHERE p.id_usuario = %s
            """
            profesor_info = await fetch_one(profesor_query, (user['id_usuario'],))
            
            if profesor_info:
                user_data.update({
                    "id_profesor": profesor_info['id_profesor'],
                    "nombre_profesor": profesor_info['nombre_profesor']
                })
        
        return LoginResponse(
            success=True,
            message="Login exitoso",
            data={
                "usuario": user_data,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error interno en login: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")

@router.get("/usuarios")
async def listar_usuarios():
    """Lista todos los usuarios (solo para admins)"""
    try:
        query = """
            SELECT 
                u.id_usuario,
                u.nombre_completo,
                u.correo,
                u.usuario_login,
                u.rol,
                p.id_profesor,
                p.nombre as nombre_profesor
            FROM usuario u
            LEFT JOIN profesor p ON u.id_usuario = p.id_usuario
            ORDER BY u.nombre_completo
        """
        
        usuarios = await fetch_all(query)
        
        return {
            "success": True,
            "data": {
                "usuarios": usuarios,
                "total": len(usuarios)
            }
        }
    
    except Exception as e:
        print(f"Error obteniendo usuarios: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener usuarios")

@router.get("/perfil/{id_usuario}")
async def obtener_perfil(id_usuario: int):
    """Obtiene el perfil completo de un usuario"""
    try:
        query = """
            SELECT 
                u.id_usuario,
                u.nombre_completo,
                u.correo,
                u.usuario_login,
                u.rol,
                p.id_profesor,
                p.nombre as nombre_profesor
            FROM usuario u
            LEFT JOIN profesor p ON u.id_usuario = p.id_usuario
            WHERE u.id_usuario = %s
        """
        
        user = await fetch_one(query, (id_usuario,))
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        
        clases = []
        if user['rol'] == 'docente' and user['id_profesor']:
            clases_query = """
                SELECT 
                    c.id_clase,
                    c.nrc,
                    c.nombre_clase,
                    c.aula,
                    m.nombre as materia_nombre,
                    g.nombre as grupo_nombre
                FROM clase c
                JOIN materia m ON c.id_materia = m.id_materia
                JOIN grupo g ON c.id_grupo = g.id_grupo
                WHERE c.id_profesor = %s
                ORDER BY m.nombre
            """
            clases = await fetch_all(clases_query, (user['id_profesor'],))
        
        return {
            "success": True,
            "data": {
                "usuario": user,
                "clases": clases,
                "total_clases": len(clases)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo perfil: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener perfil")

# ===============================================
# SISTEMA DE LOGIN POR QR (MEJORADO)
# ===============================================

@router.post("/auth/generar-sesion-qr")
async def generar_sesion_qr():
    """
    Genera un session_id único para el QR del dashboard.
    Se guarda en la BD para persistencia.
    """
    try:
        # Generar ID único seguro
        session_id = f"{uuid.uuid4().hex[:8]}-{secrets.token_urlsafe(16)}"
        
        # Guardar en base de datos
        query = """
            INSERT INTO sesiones_dashboard 
            (session_id, estado, fecha_creacion, fecha_expiracion)
            VALUES (%s, 'pendiente', NOW(), DATE_ADD(NOW(), INTERVAL 5 MINUTE))
        """
        
        await execute_query(query, (session_id,))
        
        logger.info(f"🔑 Nueva sesión QR generada: {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "expires_in": 300,  # 5 minutos
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error generando sesión QR: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error generando código QR"
        )

@ws_router.websocket("/ws/login/auth/{session_id}")
async def websocket_auth(websocket: WebSocket, session_id: str):
    """
    WebSocket que el navegador mantiene abierto mientras espera login.
    Acepta primero, valida después.
    """
    # ✅ PRIMERO aceptar la conexión
    await websocket.accept()
    logger.info(f"🔌 WebSocket aceptado: {session_id}")
    
    try:
        # Verificar que la sesión existe en BD
        query = """
            SELECT session_id, estado, fecha_expiracion
            FROM sesiones_dashboard
            WHERE session_id = %s
        """
        
        sesion = await fetch_one(query, (session_id,))
        
        if not sesion:
            logger.warning(f"⚠️ Sesión no encontrada: {session_id}")
            await websocket.send_json({
                "type": "error",
                "message": "Sesión no encontrada. Recarga la página."
            })
            await websocket.close(code=1008)
            return
        
        # Verificar expiración
        if sesion['fecha_expiracion'] < datetime.now():
            logger.warning(f"⚠️ Sesión expirada: {session_id}")
            await websocket.send_json({
                "type": "error",
                "message": "Sesión expirada. Recarga la página."
            })
            await websocket.close(code=1008)
            return
        
        # Conectar al manager
        await auth_manager.connect(websocket, session_id)
        logger.info(f"✅ WebSocket conectado al manager: {session_id}")
        
        # Mantener conexión viva
        while True:
            try:
                data = await websocket.receive_text()
                
                # Verificar estado actualizado
                sesion_actual = await fetch_one(query, (session_id,))
                
                if not sesion_actual:
                    logger.info(f"📤 Sesión eliminada: {session_id}")
                    break
                
                if sesion_actual['estado'] == 'confirmado':
                    logger.info(f"✅ Sesión confirmada, cerrando WS: {session_id}")
                    break
                
                # Responder pings
                if data == "ping":
                    await websocket.send_text("pong")
                
            except WebSocketDisconnect:
                logger.info(f"🔌 Cliente desconectó: {session_id}")
                break
            except Exception as e:
                logger.error(f"❌ Error en WS loop: {e}")
                break
                
    except Exception as e:
        logger.error(f"❌ Error en WebSocket: {e}")
    finally:
        auth_manager.disconnect(session_id)
        logger.info(f"🔴 WebSocket finalizado: {session_id}")

@router.post("/auth/confirmar-sesion")
async def confirmar_sesion(request: ConfirmarSesionRequest):
    """
    Endpoint que llama la APP MÓVIL después de escanear el QR.
    Con validación de BD y manejo de duplicados.
    """
    session_id = request.session_id
    id_profesor = request.id_profesor
    id_clase = request.id_clase
    
    logger.info(f"📱 Confirmación recibida: {session_id}")
    logger.info(f"👤 Profesor: {id_profesor}, Clase: {id_clase}")
    
    try:
        # 1️⃣ Buscar sesión en BD
        query_sesion = """
            SELECT session_id, estado, fecha_expiracion
            FROM sesiones_dashboard
            WHERE session_id = %s
        """
        
        sesion = await fetch_one(query_sesion, (session_id,))
        
        if not sesion:
            logger.warning(f"⚠️ Sesión no encontrada: {session_id}")
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada o ya fue utilizada"
            )
        
        # 2️⃣ Verificar estado
        if sesion['estado'] == 'confirmado':
            logger.warning(f"⚠️ Sesión ya confirmada: {session_id}")
            raise HTTPException(
                status_code=409,
                detail="Sesión ya fue confirmada"
            )
        
        # 3️⃣ Verificar expiración (SIN renovar - crear nueva)
        ahora = datetime.now()
        if sesion['fecha_expiracion'] < ahora:
            logger.warning(f"⚠️ Sesión expirada: {session_id}")
            raise HTTPException(
                status_code=410,
                detail="Sesión expirada. Genera un nuevo QR"
            )
        
        # 4️⃣ Validar clase del profesor
        query_clase = """
            SELECT 
                c.id_clase,
                m.nombre as materia,
                g.nombre as grupo
            FROM clase c
            JOIN materia m ON c.id_materia = m.id_materia
            JOIN grupo g ON c.id_grupo = g.id_grupo
            WHERE c.id_clase = %s AND c.id_profesor = %s
        """
        
        clase = await fetch_one(query_clase, (id_clase, id_profesor))
        
        if not clase:
            logger.error(f"❌ Clase {id_clase} no pertenece a profesor {id_profesor}")
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para esta clase"
            )
        
        # 5️⃣ Obtener nombre del profesor
        query_profesor = """
            SELECT nombre as nombre_completo
            FROM profesor
            WHERE id_profesor = %s
        """
        
        profesor = await fetch_one(query_profesor, (id_profesor,))
        
        if not profesor:
            logger.error(f"❌ Profesor no encontrado: {id_profesor}")
            raise HTTPException(
                status_code=404,
                detail="Profesor no encontrado"
            )
        
        # 6️⃣ CONFIRMAR sesión en BD
        query_confirmar = """
            UPDATE sesiones_dashboard
            SET estado = 'confirmado',
                id_profesor = %s,
                id_clase = %s,
                fecha_confirmacion = NOW()
            WHERE session_id = %s
        """
        
        await execute_query(query_confirmar, (id_profesor, id_clase, session_id))
        
        # 7️⃣ Notificar al navegador vía WebSocket
        datos_login = {
            "id_clase": id_clase,
            "id_profesor": id_profesor,
            "nombre_profesor": profesor['nombre_completo'],
            "materia": clase['materia'],
            "grupo": clase['grupo'],
            "timestamp": datetime.now().isoformat()
        }
        
        await auth_manager.notify_login_success(session_id, datos_login)
        
        logger.info(f"✅ Login confirmado exitosamente")
        logger.info(f"   👤 {profesor['nombre_completo']}")
        logger.info(f"   📚 {clase['materia']} - {clase['grupo']}")
        
        return {
            "success": True,
            "mensaje": f"Login exitoso. Bienvenido {profesor['nombre_completo']}",
            "clase": {
                "id_clase": id_clase,
                "materia": clase['materia'],
                "grupo": clase['grupo']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error confirmando sesión: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
    

@router.get("/auth/sesiones-activas")
async def obtener_sesiones_activas():
    """
    Endpoint de monitoreo: ver sesiones pendientes
    """
    try:
        query = """
            SELECT 
                CONCAT(LEFT(session_id, 16), '...') as session_id_truncado,
                estado,
                fecha_creacion,
                fecha_expiracion,
                id_profesor,
                id_clase
            FROM sesiones_dashboard
            WHERE estado = 'pendiente'
            AND fecha_expiracion > NOW()
            ORDER BY fecha_creacion DESC
        """
        
        sesiones = await fetch_all(query)
        
        return {
            "success": True,
            "total": len(sesiones),
            "sesiones": sesiones,
            "websockets_activos": auth_manager.get_active_sessions_count()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo sesiones: {e}")
        raise HTTPException(status_code=500, detail="Error interno")
    


async def limpiar_sesiones_expiradas():
    """
    Tarea en background que limpia sesiones expiradas cada minuto
    """
    while True:
        try:
            await asyncio.sleep(60)  # Cada 60 segundos
            
            query = """
                DELETE FROM sesiones_dashboard
                WHERE fecha_expiracion < NOW()
                AND estado = 'pendiente'
            """
            
            resultado = await execute_query(query)
            
            if resultado:
                logger.info(f"🗑️ Sesiones expiradas eliminadas")
                
        except Exception as e:
            logger.error(f"❌ Error limpiando sesiones: {e}")

@router.on_event("startup")
async def iniciar_limpieza():
    """Iniciar tarea de limpieza al arrancar el servidor"""
    asyncio.create_task(limpiar_sesiones_expiradas())
    logger.info("✅ Limpiador de sesiones iniciado")