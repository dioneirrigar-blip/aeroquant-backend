import ccxt.async_support as ccxt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AeroQuant Backend Bridge", version="2.7.0")

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
    side: str
    amount: float
    leverage: int

@app.post("/api/connect")
async def connect_broker(creds: BrokerCredentials):
    broker_lower = creds.broker.lower()
    broker_id = "bybit" if "bybit" in broker_lower else "binance" if "binance" in broker_lower else "bitget"
    
    exchange_class = getattr(ccxt, broker_id)
    exchange = exchange_class({
        'apiKey': creds.api_key.strip(),
        'secret': creds.api_secret.strip(),
        'enableRateLimit': True,
        'timeout': 5000,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True
        }
    })

    try:
        # Executa a chamada sem carregar mercados pesados para responder instantaneamente
        balance = await exchange.fetch_balance()
        
        usdt_balance = 0.0
        if isinstance(balance, dict):
            if 'USDT' in balance:
                usdt_balance = balance['USDT'].get('free', 0.0)
            elif 'total' in balance and isinstance(balance['total'], dict):
                usdt_balance = balance['total'].get('USDT', 0.0)

        return {
            "status": "success",
            "message": f"Conectado com sucesso à corretora {creds.broker}!",
            "margin_balance": round(float(usdt_balance), 2)
        }
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=400, detail=f"Erro de autenticação: {error_msg}")
    finally:
        await exchange.close()

@app.post("/api/order")
async def execute_order(order: OrderRequest):
    broker_lower = order.broker.lower()
    broker_id = "bybit" if "bybit" in broker_lower else "binance" if "binance" in broker_lower else "bitget"
    
    exchange_class = getattr(ccxt, broker_id)
    exchange = exchange_class({
        'apiKey': order.api_key.strip(),
        'secret': order.api_secret.strip(),
        'enableRateLimit': True,
        'timeout': 7000,
        'options': {'defaultType': 'future'}
    })

    try:
        try:
            await exchange.set_leverage(order.leverage, order.symbol)
        except Exception:
            pass

        side = 'buy' if order.side.upper() == 'BUY' else 'sell'
        execution = await exchange.create_order(order.symbol, 'market', side, order.amount)

        return {
            "status": "success",
            "message": f"Ordem {order.side} executada com sucesso!",
            "order_id": execution.get('id')
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao executar ordem: {str(e)}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
