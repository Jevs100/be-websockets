from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

# This class will manage multiple WebSocket connections.
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.sales_data: List[str] = []  # List to store sales data

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # When a new client connects, send them the existing sales data.
        if self.sales_data:
            await self.send_existing_sales(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def send_existing_sales(self, websocket: WebSocket):
        """Send all previous sales to a newly connected client."""
        for sale in self.sales_data:
            await websocket.send_text(sale)

    def record_sale(self, sale: str):
        """Store the sale information."""
        self.sales_data.append(sale)


manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Format the sale update
            sale_message = f"Salesperson #{client_id} reports a sale: {data}"
            
            # Store the sale in the manager's sales data
            manager.record_sale(sale_message)
            
            # Broadcast the sale message to all clients
            await manager.broadcast(sale_message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Salesperson #{client_id} left the board.")

# A basic HTTP endpoint for testing the FastAPI server
@app.get("/")
async def get():
    return {"message": "Sales Board WebSocket Server is running!"}
