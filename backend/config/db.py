import aiomysql
import asyncio
from typing import Optional
import logging
from typing import AsyncGenerator
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pool global
pool: Optional[aiomysql.Pool] = None


async def init_db_pool() -> aiomysql.Pool:
    """Inicializa el pool de conexiones a la base de datos"""
    global pool
    if pool is None:
        try:
            pool = await aiomysql.create_pool(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT")),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                db=os.getenv("DB_NAME"),
                autocommit=True,
                minsize=1,
                maxsize=10,
                echo=False,
                pool_recycle=3600,
                charset='utf8mb4'
            )
            logger.info("✅ Pool de base de datos inicializado correctamente")
            return pool
        except Exception as e:
            logger.error(f"❌ Error al inicializar pool de BD: {e}")
            raise e
    return pool

async def close_db_pool():
    """Cierra el pool de conexiones"""
    global pool
    if pool:
        pool.close()
        await pool.wait_closed()
        pool = None
        logger.info("✅ Pool de base de datos cerrado")

async def get_pool() -> aiomysql.Pool:
    """Obtiene el pool, inicializándolo si es necesario"""
    if pool is None:
        await init_db_pool()
    return pool

# Funciones helper para operaciones comunes
async def fetch_one(query: str, params=None):
    """Ejecuta una query y retorna un solo resultado"""
    pool_instance = await get_pool()
    async with pool_instance.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, params)
            return await cur.fetchone()

async def fetch_all(query: str, params=None):
    """Ejecuta una query y retorna todos los resultados"""
    pool_instance = await get_pool()
    async with pool_instance.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, params)
            results = await cur.fetchall()
            # 🔧 DEBUGGING: Agregar log para verificar tipo
            if results:
                logger.info(f"📊 Tipo de resultado: {type(results[0])}")
                logger.info(f"📊 Primer resultado: {results[0]}")
            return results

async def execute_query(query: str, params=None):
    """Ejecuta una query que no retorna resultados (INSERT, UPDATE, DELETE)"""
    pool_instance = await get_pool()
    async with pool_instance.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            await conn.commit()
            # Para INSERT devuelve lastrowid, para UPDATE/DELETE rowcount
            if query.strip().lower().startswith("insert"):
                return cur.lastrowid
            else:
                return cur.rowcount

async def execute_many(query: str, params_list):
    """Ejecuta una query múltiples veces con diferentes parámetros"""
    pool_instance = await get_pool()
    async with pool_instance.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(query, params_list)
            await conn.commit()
            return cur.rowcount
        

async def get_db_connection() -> AsyncGenerator[aiomysql.Connection, None]:
    """
    Devuelve una conexión de la pool para usar con Depends.
    """
    pool_instance = await get_pool()
    async with pool_instance.acquire() as conn:
        yield conn