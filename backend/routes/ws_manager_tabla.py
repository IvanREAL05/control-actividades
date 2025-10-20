from typing import Dict, List
from fastapi import WebSocket

class TableConnectionManager:
    """
    Manager de WebSockets para dashboards de tabla dinámica.
    Cada conexión se asigna a un id_clase (NRC), así los docentes
    solo reciben actualizaciones de su grupo.
    """
    def __init__(self):
        # Diccionario: id_clase -> lista de WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, id_clase: int):
        """Aceptar conexión y asignarla al id_clase correspondiente"""
        if id_clase not in self.active_connections:
            self.active_connections[id_clase] = []
        self.active_connections[id_clase].append(websocket)
        print(f"✅ Cliente conectado a clase {id_clase}. Total: {len(self.active_connections[id_clase])}")

    def disconnect(self, websocket: WebSocket, id_clase: int):
        """Remover conexión de un id_clase específico"""
        if id_clase in self.active_connections and websocket in self.active_connections[id_clase]:
            self.active_connections[id_clase].remove(websocket)
        print(f"❌ Cliente desconectado de clase {id_clase}. Total: {len(self.active_connections.get(id_clase, []))}")

    async def broadcast(self, message: str, id_clase: int):
        """
        Enviar mensaje solo a los clientes conectados a esta clase.
        """
        if id_clase not in self.active_connections:
            return
        disconnected = []
        for connection in self.active_connections[id_clase]:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error enviando a cliente de clase {id_clase}: {e}")
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn, id_clase)

# Instancia global que usarán los routers
tabla_manager = TableConnectionManager()