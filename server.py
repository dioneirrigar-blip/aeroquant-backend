from flask import Flask, request, jsonify
import os
import ccxt

app = Flask(__name__)

# Armazenamento temporário em memória (em produção, usaremos banco de dados)
user_api_storage = {}

@app.route('/api/connect', methods=['POST'])
def connect_exchange():
    try:
        data = request.get_json()
        
        exchange_id = data.get('exchange')
        api_key = data.get('apiKey')
        api_secret = data.get('apiSecret')
        
        if not exchange_id or not api_key or not api_secret:
            return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400
        
        # Validação e teste de conexão real usando CCXT
        exchange_class = getattr(ccxt, exchange_id, None)
        if not exchange_class:
            return jsonify({"error": "Corretora não suportada."}), 400
            
        exchange_instance = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        # Testando a autenticação buscando o saldo da conta
        # (Isso garante que as chaves são válidas antes de salvar)
        balance = exchange_instance.fetch_balance()
        
        # Salvando as credenciais validadas
        user_api_storage[exchange_id] = {
            'apiKey': api_key,
            'apiSecret': api_secret,
            'status': 'connected'
        }
        
        print(f"Sucesso ao conectar com {exchange_id}!")
        
        return jsonify({
            "status": "success",
            "message": f"Conexão com a {exchange_id.capitalize()} realizada e validada com sucesso!"
        }), 200

    except ccxt.AuthenticationError:
        return jsonify({"error": "Erro de autenticação: Verifique se sua API Key e Secret estão corretas."}), 401
    except Exception as e:
        return jsonify({"error": f"Erro ao conectar: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "active", "service": "AeroQuant Backend"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
