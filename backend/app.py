# app.py (mejorado)
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.db import init_db_pool, close_db_pool
import time
import json
from dotenv import load_dotenv
import os

load_dotenv()  # Esto carga todas las variables del .env
from routes import (
    actividades, avisos,login, clases, estadisticas,
    estudiantes, grupos, profesor, qr, asistencias, 
    importar, reportes, justificantes, observaciones,
    info
)

# Manejo del ciclo de vida de la aplicación
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando aplicación...")
    await init_db_pool()
    print("✅ Base de datos conectada")
    
    yield
    
    # Shutdown
    print("🔄 Cerrando aplicación...")
    await close_db_pool()
    print("✅ Aplicación cerrada correctamente")

app = FastAPI(
    title="Control de Actividades",
    description="API para control de actividades académicas",
    version="1.0.0",
    lifespan=lifespan
)

# 🛠 Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging mejorado
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log de request
    if request.method == "GET":
        query_params = dict(request.query_params)
        print(f"🔍 [{request.method}] {request.url.path} - query: {query_params}")
    else:
        try:
            body = await request.body()
            if body:
                body_str = body.decode('utf-8')
                # Truncar body muy largo para logs
                if len(body_str) > 500:
                    body_str = body_str[:500] + "..."
                print(f"📝 [{request.method}] {request.url.path} - body: {body_str}")
            else:
                print(f"📝 [{request.method}] {request.url.path} - (sin body)")
        except Exception as e:
            print(f"📝 [{request.method}] {request.url.path} - (error leyendo body: {e})")
    
    # Procesar request
    response = await call_next(request)
    
    # Log de response
    process_time = time.time() - start_time
    print(f"⚡ Completado en {process_time:.3f}s - Status: {response.status_code}")
    
    return response

# Manejo global de errores
@app.exception_handler(500)
async def internal_server_error(request: Request, exc: Exception):
    print(f"❌ Error interno: {exc}")
    return HTTPException(
        status_code=500,
        detail="Error interno del servidor"
    )

# 📦 Montar routers
app.include_router(actividades.router, prefix="/api/actividades", tags=["Actividades"])
app.include_router(avisos.router, prefix="/api/avisos", tags=["Avisos"])
app.include_router(login.router, prefix='/api/login', tags=["Login"])
app.include_router(clases.router, prefix='/api/clases', tags=["Clases"])
app.include_router(estadisticas.router, prefix='/api/estadisticas', tags=["Estadisticas"])
app.include_router(estudiantes.router, prefix='/api/estudiantes', tags=["Estudiantes"])
app.include_router(grupos.router, prefix='/api/grupos', tags=["Grupos"])
app.include_router(profesor.router, prefix='/api/profesor', tags=["Profesor"])
app.include_router(qr.router, prefix='/api/qr', tags=["QR"])
app.include_router(asistencias.router, prefix='/api/asistencias', tags=["Asistencias"])
app.include_router(importar.router, prefix='/api/importar', tags=["Importar"])
app.include_router(reportes.router, prefix='/api/reportes', tags=["Reportes"])
app.include_router(justificantes.router, prefix="/api/justificantes", tags=["Justificantes"])
app.include_router(observaciones.router, prefix='/api/observaciones', tags=["Observaciones"])
app.include_router(info.router, prefix='/api/helpers', tags=["Helpers"])

# ✅ Ruta health check mejorada
@app.get("/")
async def root():
    return {
        "status": "OK",
        "message": "API Control de Actividades funcionando correctamente",
        "version": "1.0.0",
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    """Endpoint para verificar el estado de la aplicación y BD"""
    try:
        # Verificar conexión a BD
        from config.db import fetch_one
        result = await fetch_one("SELECT 1 as test")
        
        return {
            "status": "healthy",
            "database": "connected" if result else "disconnected",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": time.time()
        }
