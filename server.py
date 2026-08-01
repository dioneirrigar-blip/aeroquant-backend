from flask import Flask, request, jsonify
import os
import ccxt

app = Flask(__name__)

# Armazenamento temporário de credenciais e estado dos bots
user_api_storage = {}
bot_states = {}

@app.route('/api/connect', methods=['POST'])
def connect_exchange():
    try:
        data = request.get_json()
        exchange_id = data.get('exchange')
        api_key = data.get('apiKey')
        api_secret = data.get('apiSecret')
        
        if not exchange_id or not api_key or not api_secret:
            return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400
        
        exchange_class = getattr(ccxt, exchange_id, None)
        if not exchange_class:
            return jsonify({"error": "Corretora não suportada."}), 400
            
        exchange_instance = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        # Validação buscando o saldo
        exchange_instance.fetch_balance()
        
        user_api_storage[exchange_id] = {
            'apiKey': api_key,
            'apiSecret': api_secret,
            'status': 'connected'
        }
        
        return jsonify({
            "status": "success",
            "message": f"Conexão com a {exchange_id.capitalize()} realizada e validada com sucesso!"
        }), 200

    except ccxt.AuthenticationError:
        return jsonify({"error": "Erro de autenticação: Verifique suas chaves de API."}), 401
    except Exception as e:
        return jsonify({"error": f"Erro ao conectar: {str(e)}"}), 500

@app.route('/api/bot/control', methods=['POST'])
def control_bot():
    try:
        data = request.get_json()
        action = data.get('action') # 'start' ou 'stop'
        exchange_id = data.get('exchange', 'bybit')
        symbol = data.get('symbol', 'BTC/USDT')
        
        if exchange_id not in user_api_storage:
            return jsonify({"error": "Nenhuma chave de API conectada para esta corretora."}), 400
            
        creds = user_api_storage[exchange_id]
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': creds['apiKey'],
            'secret': creds['apiSecret'],
            'enableRateLimit': True,
        })
        
        if action == 'start':
            # Ativa o estado do bot e busca preço atual como referência inicial
            ticker = exchange.fetch_ticker(symbol)
            bot_states[symbol] = {
                'status': 'running',
                'last_price': ticker['last']
            }
            return jsonify({"status": "success", "message": f"Bot iniciado para {symbol} na {exchange_id.capitalize()}!"}), 200
            
        elif action == 'stop':
            if symbol in bot_states:
                bot_states[symbol]['status'] = 'stopped'
            return jsonify({"status": "success", "message": f"Bot parado para {symbol}."}), 200
            
        return jsonify({"error": "Ação inválida."}), 400

    except Exception as e:
        return jsonify({"error": f"Erro no controle do bot: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "active", "service": "AeroQuant Backend"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
