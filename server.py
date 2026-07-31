from flask import Flask, request, jsonify
from flask_cors import CORS
import ccxt

app = Flask(__name__)
CORS(app)

def get_exchange_instance(exchange_id, api_key, api_secret):
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({
        'apiKey': "ixdn6tWtjWKuNmUjef",
        'secret': "RMrGoIG8ua4gKIplNw2zIpcCR2gTp9v5nKpt",
        'enableRateLimit': True,
        'options': {
            'defaultType': 'linear',  # USDT Linear Perpetual
        }
    })

@app.route('/api/v1/connect', methods=['POST'])
def test_exchange_connection():
    data = request.json
    try:
        exchange = get_exchange_instance(data.get('exchange'), data.get('apiKey'), data.get('apiSecret'))
        balance = exchange.fetch_balance()
        usdt_total = balance['total'].get('USDT', 0.0)
        return jsonify({'success': True, 'balance': float(usdt_total)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/v1/order', methods=['POST'])
def execute_order():
    data = request.json
    exchange_id = data.get('exchange')
    api_key = data.get('apiKey')
    api_secret = data.get('apiSecret')
    raw_symbol = data.get('symbol', 'BTC/USDT')
    side = data.get('side')
    amount_usdt = float(data.get('amount', 10))
    leverage = int(data.get('leverage', 10))

    try:
        exchange = get_exchange_instance(exchange_id, api_key, api_secret)
        symbol = raw_symbol if ':' in raw_symbol else f"{raw_symbol}:USDT"

        try:
            exchange.set_leverage(leverage, symbol)
        except Exception:
            pass

        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        total_notional_usdt = amount_usdt * leverage
        raw_quantity = total_notional_usdt / current_price
        quantity_formatted = float(exchange.amount_to_precision(symbol, raw_quantity))

        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=quantity_formatted
        )

        return jsonify({
            'success': True,
            'orderId': order.get('id', 'N/A'),
            'price': current_price,
            'filled': quantity_formatted
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/v1/positions', methods=['POST'])
def fetch_positions():
    """Busca apenas as posições ativas (contratos abertos) do usuário."""
    data = request.json
    try:
        exchange = get_exchange_instance(data.get('exchange'), data.get('apiKey'), data.get('apiSecret'))
        positions = exchange.fetch_positions()
        
        # Filtra apenas posições com contrato ativo (contratos > 0)
        active_positions = []
        for pos in positions:
            contracts = float(pos.get('contracts', 0) or 0)
            if contracts > 0:
                active_positions.append({
                    'symbol': pos.get('symbol').split(':')[0], # Exibe como BTC/USDT
                    'rawSymbol': pos.get('symbol'),
                    'side': pos.get('side').upper(),            # LONG ou SHORT
                    'contracts': contracts,
                    'entryPrice': float(pos.get('entryPrice', 0)),
                    'unrealizedPnl': float(pos.get('unrealizedPnl', 0)),
                    'leverage': pos.get('leverage', 1)
                })

        return jsonify({'success': True, 'positions': active_positions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/v1/close-position', methods=['POST'])
def close_position():
    """Fecha uma posição aberta a mercado (reduceOnly)."""
    data = request.json
    try:
        exchange = get_exchange_instance(data.get('exchange'), data.get('apiKey'), data.get('apiSecret'))
        symbol = data.get('symbol')
        side = data.get('side')  # 'LONG' ou 'SHORT'
        amount = float(data.get('contracts'))

        # Para fechar LONG envia SELL, para fechar SHORT envia BUY
        close_side = 'sell' if side == 'LONG' else 'buy'

        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=close_side,
            amount=amount,
            params={'reduceOnly': True}
        )

        return jsonify({'success': True, 'orderId': order.get('id', 'N/A')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Servidor AeroQuant Backend executando na porta {port}")
    app.run(host='0.0.0.0', port=port)