import asyncio
import hmac
import hashlib
import time
import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Aeroquant Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BrokerCredentials(BaseModel):
    broker: str
    api_key: str
    api_secret: str

class OrderRequest(BaseModel):
    symbol: str
    side: str  # 'BUY' (LONG) ou 'SELL' (SHORT)
    amount: float
    leverage: int

# Simulação de armazenamento em memória para sessão atual
current_session = {
    "connected": False,
    "broker": None,
    "api_key": None,
    "api_secret": None,
    "positions": []
}

@app.post("/api/connect")
async def connect_broker(creds: BrokerCredentials):
    if not creds.api_key or not creds.api_secret:
        raise HTTPException(status_code=400, detail="API Key e Secret são obrigatórios.")
    
    current_session["connected"] = True
    current_session["broker"] = creds.broker
    current_session["api_key"] = creds.api_key
    current_session["api_secret"] = creds.api_secret

    return {
        "status": "success",
        "message": f"Conectado com sucesso à corretora {creds.broker}",
        "margin_balance": "1,250.40"
    }

@app.post("/api/order")
async def execute_order(order: OrderRequest):
    if not current_session["connected"]:
        raise HTTPException(status_code=401, detail="Robô não conectado a nenhuma corretora.")
    
    # Exemplo de lógica de integração com API de futuros (Bybit/Binance/Bitget)
    new_position = {
        "symbol": order.symbol,
        "side": order.side,
        "amount": order.amount,
        "leverage": order.leverage,
        "entry_price": "65420.00",
        "pnl": "+0.00"
    }
    
    current_session["positions"].append(new_position)
    
    return {
        "status": "success",
        "message": f"Ordem {order.side} executada para {order.symbol}",
        "position": new_position
    }

@app.get("/api/status")
async def get_status():
    return {
        "connected": current_session["connected"],
        "broker": current_session["broker"],
        "positions": current_session["positions"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
