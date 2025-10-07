from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Cliente conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ Cliente desconectado. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        print(f"📡 Broadcasting a {len(self.active_connections)} clientes: {message[:100]}...")
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error enviando a cliente: {e}")
                disconnected.append(connection)
        
        # Limpia conexiones muertas
        for conn in disconnected:
            self.disconnect(conn)

# Instancia global
manager = ConnectionManager()