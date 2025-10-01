import websocket

def on_open(ws):
    print("Conectado al WebSocket!")
    # envía un mensaje de prueba al servidor
    ws.send("Hola servidor!")

def on_message(ws, msg):
    print("Mensaje recibido:", msg)

ws = websocket.WebSocketApp(
    "ws://127.0.0.1:8000/api/clases/ws/attendances",
    on_open=on_open,
    on_message=on_message
)

ws.run_forever()