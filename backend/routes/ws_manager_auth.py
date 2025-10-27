"""
WebSocket Manager para autenticación por QR
Maneja las conexiones WebSocket del dashboard web
"""
from fastapi import WebSocket
from typing import Dict
import logging
import json

logger = logging.getLogger(__name__)


class AuthConnectionManager:
    """
    Gestor de conexiones WebSocket para autenticación.
    Permite notificar a los navegadores cuando una app móvil escanea el QR.
    """
    
    def __init__(self):
        # Diccionario: session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("🔧 AuthConnectionManager inicializado")
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Registra una nueva conexión WebSocket.
        
        Args:
            websocket: La conexión WebSocket del navegador
            session_id: ID de la sesión QR generada
        """
        self.active_connections[session_id] = websocket
        logger.info(f"✅ WebSocket registrado: {session_id}")
        logger.info(f"📊 Conexiones activas: {len(self.active_connections)}")
        
        # Enviar confirmación inicial
        try:
            await websocket.send_json({
                "type": "connected",
                "message": "Conexión establecida correctamente"
            })
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje inicial: {e}")
    
    def disconnect(self, session_id: str):
        """
        Elimina una conexión WebSocket cuando se cierra.
        
        Args:
            session_id: ID de la sesión a desconectar
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"🔴 WebSocket desconectado: {session_id}")
            logger.info(f"📊 Conexiones activas: {len(self.active_connections)}")
        else:
            logger.warning(f"⚠️ Intento de desconectar sesión inexistente: {session_id}")
    
    async def notify_login_success(self, session_id: str, datos: dict) -> bool:
        """
        Notifica al navegador que el login fue exitoso.
        
        Args:
            session_id: ID de la sesión
            datos: Información del login (id_profesor, id_clase, etc.)
            
        Returns:
            bool: True si se notificó exitosamente, False si no hay conexión
        """
        logger.info(f"📤 Intentando notificar login exitoso a: {session_id}")
        logger.info(f"📊 Conexiones disponibles: {list(self.active_connections.keys())}")
        
        if session_id not in self.active_connections:
            logger.warning(f"❌ No hay conexión activa para {session_id}")
            return False
        
        websocket = self.active_connections[session_id]
        
        try:
            # ✅ Formato compatible con Streamlit (español)
            mensaje = {
                "tipo": "login_exitoso",
                "datos": datos
            }
            
            logger.info(f"📨 Enviando mensaje: {json.dumps(mensaje, indent=2)}")
            
            await websocket.send_json(mensaje)
            
            # Esperar un poco para asegurar que el mensaje se envíe
            import asyncio
            await asyncio.sleep(0.5)
            
            logger.info(f"✅ Login exitoso notificado a: {session_id}")
            
            # NO cerrar inmediatamente, dejar que el cliente cierre
            # await websocket.close(code=1000, reason="Login exitoso")
            
            # Limpiar después de un delay
            await asyncio.sleep(1)
            self.disconnect(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error notificando login: {e}")
            self.disconnect(session_id)
            return False
    
    async def notify_error(self, session_id: str, mensaje: str) -> bool:
        """
        Notifica un error al navegador.
        
        Args:
            session_id: ID de la sesión
            mensaje: Mensaje de error a mostrar
            
        Returns:
            bool: True si se notificó exitosamente
        """
        logger.warning(f"⚠️ Notificando error a {session_id}: {mensaje}")
        
        if session_id not in self.active_connections:
            logger.warning(f"❌ No hay conexión activa para {session_id}")
            return False
        
        websocket = self.active_connections[session_id]
        
        try:
            await websocket.send_json({
                "type": "error",
                "message": mensaje
            })
            
            logger.info(f"✅ Error notificado a: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación: {e}")
            self.disconnect(session_id)
            return False
    
    def get_active_sessions_count(self) -> int:
        """
        Retorna el número de sesiones activas.
        
        Returns:
            int: Cantidad de WebSockets conectados
        """
        return len(self.active_connections)
    
    def is_connected(self, session_id: str) -> bool:
        """
        Verifica si una sesión tiene WebSocket activo.
        
        Args:
            session_id: ID de la sesión a verificar
            
        Returns:
            bool: True si está conectado
        """
        return session_id in self.active_connections


# Instancia global del manager
auth_manager = AuthConnectionManager()