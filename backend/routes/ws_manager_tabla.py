from fastapi import WebSocket
from typing import Dict, List
import json

class TableConnectionManager:
    """Manager de WebSockets para dashboards de tabla dinámica"""
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, id_clase: int):
        """Aceptar conexión y asignarla al id_clase correspondiente"""
        await websocket.accept()
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
        Enviar mensaje (string JSON) solo a los clientes conectados a esta clase
        
        Args:
            message: String JSON con el mensaje a enviar
            id_clase: ID de la clase
        """
        if id_clase not in self.active_connections:
            print(f"⚠️ No hay conexiones activas para clase {id_clase}")
            return
        
        disconnected = []
        
        for connection in self.active_connections[id_clase]:
            try:
                await connection.send_text(message)
                
                # Log del tipo de mensaje (parsear el JSON solo para logging)
                try:
                    mensaje_dict = json.loads(message)
                    tipo = mensaje_dict.get('tipo', 'desconocido')
                    print(f"📤 Mensaje '{tipo}' enviado a clase {id_clase}")
                except:
                    print(f"📤 Mensaje enviado a clase {id_clase}")
                    
            except Exception as e:
                print(f"❌ Error enviando a cliente de clase {id_clase}: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones rotas
        for conn in disconnected:
            self.disconnect(conn, id_clase)

# Instancia global
tabla_manager = TableConnectionManager()