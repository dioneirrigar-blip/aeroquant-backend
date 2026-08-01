from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/api/connect', methods=['POST'])
def connect_exchange():
    try:
        data = request.get_json()
        
        exchange = data.get('exchange')
        api_key = data.get('apiKey')
        api_secret = data.get('apiSecret')
        
        if not exchange or not api_key or not api_secret:
            return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400
        
        # Aqui você insere a lógica de conexão com a corretora escolhida 
        # (ex: usando ccxt para validar as chaves de Bybit, Binance, etc.)
        print(f"Recebida tentativa de conexão para a corretora: {exchange}")
        
        # Retorno de sucesso para o frontend
        return jsonify({
            "status": "success",
            "message": f"Conexão com a {exchange.capitalize()} realizada com sucesso!"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "active", "service": "AeroQuant Backend"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
