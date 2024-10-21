from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from passlib.context import CryptContext
import uvicorn
import json

app = FastAPI()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fake database for users and sales
fake_users_db = {}
sales_data_db = []

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str

class Sale(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str

# User management functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_user(username: str, password: str):
    hashed_password = get_password_hash(password)
    fake_users_db[username] = UserInDB(username=username, hashed_password=hashed_password)

def get_user(username: str):
    user = fake_users_db.get(username)
    if user:
        return UserInDB(**user.dict())
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = get_user(token)  # Replace with a proper token verification in production
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

# This class will manage multiple WebSocket connections.
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.sales_data: List[str] = []  # List to store sales data

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send existing sales data to new connections
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
        sales_data_db.append(sale)  # Store in fake database for persistence

manager = ConnectionManager()

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": user.username, "token_type": "bearer"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, current_user: User = Depends(get_current_user)):
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

@app.get("/")
async def get():
    return {"message": "Sales Board WebSocket Server is running!"}

@app.get("/sales", response_model=List[str])
async def get_sales():
    """Retrieve all sales data."""
    return manager.sales_data

@app.post("/sales")
async def create_sale(sale: Sale, current_user: User = Depends(get_current_user)):
    """Create a new sale."""
    sale_message = f"Salesperson reports a sale: {sale.message}"
    manager.record_sale(sale_message)
    await manager.broadcast(sale_message)
    return {"message": "Sale recorded successfully!"}

# Create an initial user for testing
create_user("testuser", "password123")  # You can register more users as needed.

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
