from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, validator
import bcrypt
import aiomysql 
from aiomysql import Pool  
import logging  # ← IMPORTACIÓN FALTANTE PARA LOGGER
from datetime import datetime, timedelta
from config.db import fetch_one, fetch_all, execute_query, get_pool
import uuid
import secrets
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from routes.ws_manager_auth import auth_manager

router = APIRouter()
ws_router = APIRouter()
# Configurar logger
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

# Schema de entrada
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

@router.post("/usuarios")
async def crear_usuario(usuario: UsuarioCreate):
    pool: Pool = await get_pool() 
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # Verificar si el usuario o correo ya existen
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

                # Encriptar contraseña
                hashed_password = bcrypt.hashpw(
                    usuario.contrasena.encode("utf-8"), 
                    bcrypt.gensalt()
                ).decode('utf-8')  # ← Convertir a string para almacenar en BD

                # Insertar en tabla usuario
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
                
                # Obtener el id insertado
                id_usuario = cur.lastrowid

                # Si es docente, insertar en tabla profesor
                if usuario.rol == "docente":
                    await cur.execute("""
                        INSERT INTO profesor (id_usuario, nombre)
                        VALUES (%s, %s)
                    """, (id_usuario, usuario.nombre_completo))

                # Commit al final de todas las operaciones
                await conn.commit()

                return {
                    "message": "Usuario creado exitosamente", 
                    "id_usuario": id_usuario,
                    "rol": usuario.rol
                }

            except aiomysql.MySQLError as e:
                await conn.rollback()
                logger.error(f"Error de MySQL: {e}")
                
                # Manejo más específico de errores
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
            
# --- Endpoints ---
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
        
        # Validar contraseña
        try:
            if user['contrasena'].startswith('$2b$') or user['contrasena'].startswith('$2a$'):
                # Contraseña bcrypt
                valid_password = bcrypt.checkpw(
                    data.contrasena.encode('utf-8'), 
                    user['contrasena'].encode('utf-8')
                )
            else:
                # Contraseña legacy (texto plano)
                valid_password = data.contrasena == user['contrasena']
                
                if valid_password:
                    # Migrar a bcrypt
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
        
        # Datos base del usuario
        user_data = {
            "id_usuario": user['id_usuario'],
            "nombre_completo": user['nombre_completo'],
            "correo": user['correo'],
            "usuario_login": user['usuario_login'],
            "rol": user['rol']
        }
        
        # Si es profesor, obtener info extra
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
        
        # Si es profesor, obtener sus clases
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
#NUEVOS ENDPOINTS


    """Modelo para sesiones de login por QR"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(minutes=2)
        self.is_used = False
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired()


class ConfirmarSesionRequest(BaseModel):
    """Datos que envía la app móvil al escanear el QR"""
    session_id: str
    id_profesor: int
    id_clase: int

class SesionQR:
    """Modelo para sesiones de login por QR"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(minutes=2)
        self.is_used = False
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired()
# ===============================================
# ALMACENAMIENTO TEMPORAL DE SESIONES
# ===============================================
# En producción, usar Redis. Para desarrollo, dict en memoria
active_qr_sessions: dict[str, SesionQR] = {}

def limpiar_sesiones_expiradas():
    """Eliminar sesiones expiradas (llamar periódicamente)"""
    global active_qr_sessions
    now = datetime.now()
    expired = [sid for sid, sesion in active_qr_sessions.items() if sesion.is_expired()]
    
    for sid in expired:
        del active_qr_sessions[sid]
        auth_manager.disconnect(sid)
    
    if expired:
        logger.info(f"🧹 Limpiadas {len(expired)} sesiones expiradas")


# ===============================================
# ENDPOINTS
# ===============================================

@router.post("/auth/generar-sesion-qr")
async def generar_sesion_qr():
    """
    Genera un session_id único para el QR del dashboard.
    El navegador llamará este endpoint al cargar app.py
    
    URL: POST /api/login/auth/generar-sesion-qr
    
    Response:
    {
        "session_id": "abc-123-def-456",
        "expires_in": 120  // segundos
    }
    """
    # Limpiar sesiones viejas
    limpiar_sesiones_expiradas()
    
    # Generar ID único seguro
    session_id = f"{uuid.uuid4().hex[:8]}-{secrets.token_urlsafe(16)}"
    
    # Crear sesión
    sesion = SesionQR(session_id)
    active_qr_sessions[session_id] = sesion
    
    logger.info(f"🔑 Nueva sesión QR generada: {session_id}")
    logger.info(f"📊 Sesiones activas: {len(active_qr_sessions)}")
    
    return {
        "success": True,
        "session_id": session_id,
        "expires_in": 120,  # 2 minutos
        "created_at": sesion.created_at.isoformat()
    }


@ws_router.websocket("/ws/login/auth/{session_id}")
async def websocket_auth(websocket: WebSocket, session_id: str):
    """
    WebSocket que el navegador mantiene abierto mientras espera login.
    Cuando la app móvil escanea el QR y confirma, este WS notifica al navegador.
    
    URL: ws://localhost:8000/ws/login/auth/{session_id}
    """
    # ✅ PRIMERO aceptar, LUEGO validar
    await websocket.accept()
    logger.info(f"🔌 WebSocket aceptado para sesión: {session_id}")
    
    # Verificar que la sesión existe
    if session_id not in active_qr_sessions:
        logger.warning(f"⚠️ Sesión no encontrada: {session_id}")
        await websocket.close(code=1008, reason="Sesión no encontrada")
        return
    
    sesion = active_qr_sessions[session_id]
    
    # Verificar que no esté expirada
    if sesion.is_expired():
        logger.warning(f"⚠️ Sesión expirada: {session_id}")
        await websocket.close(code=1008, reason="Sesión expirada")
        del active_qr_sessions[session_id]
        return
    
    # Conectar al manager
    await auth_manager.connect(websocket, session_id)
    
    try:
        # Mantener conexión viva
        while True:
            try:
                # Esperar mensajes del cliente (pings)
                data = await websocket.receive_text()
                
                # Verificar si la sesión sigue válida
                if session_id not in active_qr_sessions:
                    logger.info(f"📤 Sesión {session_id} ya fue usada")
                    break
                
                if active_qr_sessions[session_id].is_expired():
                    logger.warning(f"⏱️ Sesión {session_id} expiró")
                    await auth_manager.notify_error(session_id, "Sesión expirada. Genera un nuevo QR.")
                    break
                
            except WebSocketDisconnect:
                logger.info(f"🔌 Cliente desconectó sesión: {session_id}")
                break
                
    except Exception as e:
        logger.error(f"❌ Error en WebSocket auth {session_id}: {e}")
    finally:
        auth_manager.disconnect(session_id)
        logger.info(f"🔴 WebSocket auth cerrado: {session_id}")


@router.post("/auth/confirmar-sesion")
async def confirmar_sesion(request: ConfirmarSesionRequest):
    """
    Endpoint que llama la APP MÓVIL después de escanear el QR.
    Valida los datos y notifica al navegador para redirección automática.
    
    Body:
    {
        "session_id": "abc-123-def-456",
        "id_profesor": 4,
        "id_clase": 6
    }
    """
    session_id = request.session_id
    id_profesor = request.id_profesor
    id_clase = request.id_clase
    
    logger.info(f"📱 Confirmación de sesión recibida: {session_id}")
    logger.info(f"👤 Profesor: {id_profesor}, Clase: {id_clase}")
    
    # 1️⃣ Verificar que la sesión existe
    if session_id not in active_qr_sessions:
        raise HTTPException(
            status_code=404, 
            detail="Sesión no encontrada o ya fue utilizada"
        )
    
    sesion = active_qr_sessions[session_id]
    
    # 2️⃣ Verificar que no esté expirada
    if sesion.is_expired():
        del active_qr_sessions[session_id]
        auth_manager.disconnect(session_id)
        raise HTTPException(
            status_code=410, 
            detail="Sesión expirada. El docente debe generar un nuevo QR."
        )
    
    # 3️⃣ Verificar que no haya sido usada
    if sesion.is_used:
        raise HTTPException(
            status_code=409, 
            detail="Esta sesión ya fue utilizada"
        )
    
    # 4️⃣ Validar que el profesor tenga permisos para esa clase
    from config.db import fetch_one  # Importar tu helper de DB
    
    clase = await fetch_one(
        """
        SELECT c.id_clase, c.id_profesor, m.nombre as materia, g.nombre as grupo
        FROM clase c
        JOIN materia m ON c.id_materia = m.id_materia
        JOIN grupo g ON c.id_grupo = g.id_grupo
        WHERE c.id_clase = %s AND c.id_profesor = %s
        """,
        (id_clase, id_profesor)
    )
    
    if not clase:
        await auth_manager.notify_error(
            session_id, 
            "No tienes permisos para acceder a esta clase"
        )
        raise HTTPException(
            status_code=403,
            detail="El profesor no tiene asignada esta clase"
        )
    
    # 5️⃣ Marcar sesión como usada
    sesion.is_used = True
    
    # 6️⃣ Obtener datos del profesor
    profesor = await fetch_one(
        "SELECT id_profesor, nombre, apellido FROM profesor WHERE id_profesor = %s",
        (id_profesor,)
    )
    
    # 7️⃣ Notificar al navegador
    datos_login = {
        "id_clase": id_clase,
        "id_profesor": id_profesor,
        "nombre_profesor": f"{profesor['nombre']} {profesor['apellido']}",
        "materia": clase["materia"],
        "grupo": clase["grupo"],
        "timestamp": datetime.now().isoformat()
    }
    
    success = await auth_manager.notify_login_success(session_id, datos_login)
    
    if not success:
        raise HTTPException(
            status_code=408,
            detail="El navegador ya no está esperando. Intenta nuevamente."
        )
    
    # 8️⃣ Limpiar sesión
    del active_qr_sessions[session_id]
    
    logger.info(f"✅ Login exitoso: Profesor {id_profesor} → Clase {id_clase}")
    
    return {
        "success": True,
        "mensaje": f"Login exitoso. Bienvenido {profesor['nombre']}",
        "clase": {
            "id_clase": id_clase,
            "materia": clase["materia"],
            "grupo": clase["grupo"]
        }
    }


@router.get("/auth/sesiones-activas")
async def obtener_sesiones_activas():
    """
    Endpoint de monitoreo (opcional).
    Ver cuántas sesiones de login están pendientes.
    """
    limpiar_sesiones_expiradas()
    
    sesiones = [
        {
            "session_id": sid[:16] + "...",  # Ocultar parte del ID
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "is_expired": s.is_expired(),
            "is_used": s.is_used
        }
        for sid, s in active_qr_sessions.items()
    ]
    
    return {
        "total": len(sesiones),
        "sesiones": sesiones,
        "websockets_conectados": auth_manager.get_active_sessions_count()
    }