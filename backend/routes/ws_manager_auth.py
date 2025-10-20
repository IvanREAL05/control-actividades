# backend/routes/ws_manager_auth.py
"""
Manager de WebSockets para autenticación por QR.
Gestiona las sesiones de login pendientes.
"""

from typing import Dict
from fastapi import WebSocket
import logging
import json

logger = logging.getLogger(__name__)

class AuthConnectionManager:
    """
    Manager de WebSockets para login por QR.
    Mapea session_id → WebSocket del navegador esperando login.
    """
    def __init__(self):
        # Diccionario: session_id -> WebSocket del navegador
        self.pending_sessions: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Registrar conexión de un navegador esperando login"""
        # ✅ NO llamar accept() aquí, ya se hizo en el endpoint
        self.pending_sessions[session_id] = websocket
        logger.info(f"✅ Sesión de login registrada: {session_id}")
        logger.info(f"📊 Total sesiones pendientes: {len(self.pending_sessions)}")
    
    def disconnect(self, session_id: str):
        """Remover sesión al cerrar navegador o completar login"""
        if session_id in self.pending_sessions:
            del self.pending_sessions[session_id]
            logger.info(f"❌ Sesión removida: {session_id}")
            logger.info(f"📊 Total sesiones pendientes: {len(self.pending_sessions)}")
    
    async def notify_login_success(self, session_id: str, data: dict) -> bool:
        """
        Notificar al navegador que el login fue exitoso.
        Envía los datos de la clase para redirección automática.
        
        Args:
            session_id: ID de la sesión QR
            data: Diccionario con id_clase, id_profesor, nombre_profesor, materia, grupo
            
        Returns:
            bool: True si se envió exitosamente, False si no hay conexión
        """
        if session_id not in self.pending_sessions:
            logger.warning(f"⚠️ Session {session_id} no encontrada o ya expiró")
            return False
        
        websocket = self.pending_sessions[session_id]
        
        # ✅ IMPORTANTE: Usar "datos" (no "data") para coincidir con el frontend
        mensaje = {
            "tipo": "login_exitoso",
            "datos": data
        }
        
        try:
            logger.info(f"📤 Enviando notificación de login a sesión: {session_id}")
            logger.info(f"📦 Mensaje completo: {json.dumps(mensaje, indent=2, ensure_ascii=False)}")
            
            await websocket.send_json(mensaje)
            
            logger.info(f"✅ Notificación enviada exitosamente a {session_id}")
            logger.info(f"🎯 Datos enviados: Profesor {data.get('id_profesor')} → Clase {data.get('id_clase')}")
            
            # ⏳ Esperar un momento antes de cerrar para asegurar entrega
            import asyncio
            await asyncio.sleep(0.5)
            
            # Cerrar websocket después de notificar
            await websocket.close(code=1000, reason="Login completado")
            self.disconnect(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error notificando login a {session_id}: {type(e).__name__}: {e}")
            self.disconnect(session_id)
            return False
    
    async def notify_error(self, session_id: str, mensaje: str):
        """Notificar error al navegador"""
        if session_id not in self.pending_sessions:
            logger.warning(f"⚠️ No se puede notificar error: sesión {session_id} no existe")
            return
        
        websocket = self.pending_sessions[session_id]
        
        try:
            await websocket.send_json({
                "tipo": "error",
                "mensaje": mensaje
            })
            logger.warning(f"⚠️ Error enviado a sesión {session_id}: {mensaje}")
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje de error: {e}")
            self.disconnect(session_id)
    
    def is_session_active(self, session_id: str) -> bool:
        """Verificar si una sesión está esperando login"""
        return session_id in self.pending_sessions
    
    def get_active_sessions_count(self) -> int:
        """Obtener cantidad de sesiones pendientes"""
        return len(self.pending_sessions)

# Instancia global
auth_manager = AuthConnectionManager()