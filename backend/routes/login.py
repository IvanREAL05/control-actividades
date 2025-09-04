from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, validator
import bcrypt
import aiomysql 
from aiomysql import Pool  
import logging  # ← IMPORTACIÓN FALTANTE PARA LOGGER
from datetime import datetime
from config.db import fetch_one, fetch_all, execute_query, get_pool

router = APIRouter()
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


