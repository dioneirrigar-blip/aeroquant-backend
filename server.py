import ccxt.async_support as ccxt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AeroQuant Backend Bridge", version="2.5.0")

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
    broker: str
    api_key: str
    api_secret: str
    symbol: str
    side: str  # 'BUY' ou 'SELL'
    amount: float
    leverage: int

def get_exchange_instance(broker_name: str, api_key: str, api_secret: str):
    broker_id = "bybit" if "Bybit" in broker_name else "binance" if "Binance" in broker_name else "bitget"
    exchange_class = getattr(ccxt, broker_id)
    return exchange_class({
        'apiKey': api_key.strip(),
        'secret': api_secret.strip(),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

@app.post("/api/connect")
async def connect_broker(creds: BrokerCredentials):
    exchange = None
    try:
        exchange = get_exchange_instance(creds.broker, creds.api_key, creds.api_secret)
        balance = await exchange.fetch_balance()
        
        # Pega o saldo de USDT disponível na conta de futuros
        usdt_balance = 0.0
        if 'USDT' in balance:
            usdt_balance = balance['USDT'].get('free', 0.0)
        elif 'total' in balance and 'USDT' in balance['total']:
            usdt_balance = balance['total']['USDT']

        return {
            "status": "success",
            "message": f"Conectado com sucesso à corretora {creds.broker}!",
            "margin_balance": round(float(usdt_balance), 2)
        }
    except Exception as e:
        error_msg = str(e)
        if "Invalid" in error_msg or "Signature" in error_msg or "API" in error_msg:
            raise HTTPException(status_code=400, detail="Credenciais inválidas ou sem permissão de futuros/trade.")
        raise HTTPException(status_code=400, detail=f"Erro de comunicação: {error_msg}")
    finally:
        if exchange:
            await exchange.close()

@app.post("/api/order")
async def execute_order(order: OrderRequest):
    exchange = None
    try:
        exchange = get_exchange_instance(order.broker, order.api_key, order.api_secret)
        
        # Configurar alavancagem
        try:
            await exchange.set_leverage(order.leverage, order.symbol)
        except Exception:
            pass # Algumas corretoras gerenciam alavancagem isoladamente na interface ou já configurada

        # Criar ordem de mercado
        order_type = 'market'
        side = 'buy' if order.side == 'BUY' else 'sell'
        
        # Executa ordem na corretora real
        execution = await exchange.create_order(order.symbol, order_type, side, order.amount)

        return {
            "status": "success",
            "message": f"Ordem {order.side} executada com sucesso no par {order.symbol}!",
            "order_id": execution.get('id')
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao executar ordem: {str(e)}")
    finally:
        if exchange:
            await exchange.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
