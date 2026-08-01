from flask import Flask, request, jsonify
import os
import sqlite3
import ccxt

app = Flask(__name__)

DB_NAME = "aeroquant.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabela de credenciais de API
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_credentials (
            exchange TEXT PRIMARY KEY,
            api_key TEXT,
            api_secret TEXT,
            status TEXT
        )
    ''')
    # Tabela de saldo e transações de gás
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gas_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            amount REAL,
            tx_hash TEXT,
            status TEXT
        )
    ''')
    # Tabela de estado do bot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_states (
            symbol TEXT PRIMARY KEY,
            status TEXT,
            last_price REAL
        )
    ''')
    conn.commit()
    conn.close()

# Inicializa o banco ao iniciar o app
init_db()

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
        
        # Validação buscando saldo real
        exchange_instance.fetch_balance()
        
        # Salva no banco de dados SQLite
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO api_credentials (exchange, api_key, api_secret, status)
            VALUES (?, ?, ?, ?)
        ''', (exchange_id, api_key, api_secret, 'connected'))
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Conexão com a {exchange_id.capitalize()} realizada e salva com sucesso!"
        }), 200

    except ccxt.AuthenticationError:
        return jsonify({"error": "Erro de autenticação: Verifique suas chaves de API."}), 401
    except Exception as e:
        return jsonify({"error": f"Erro ao conectar: {str(e)}"}), 500

@app.route('/api/bot/control', methods=['POST'])
def control_bot():
    try:
        data = request.get_json()
        action = data.get('action')
        exchange_id = data.get('exchange', 'bybit')
        symbol = data.get('symbol', 'BTC/USDT')
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT api_key, api_secret FROM api_credentials WHERE exchange = ?', (exchange_id,))
        creds = cursor.fetchone()
        
        if not creds:
            conn.close()
            return jsonify({"error": "Nenhuma chave de API conectada para esta corretora."}), 400
            
        api_key, api_secret = creds
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        if action == 'start':
            ticker = exchange.fetch_ticker(symbol)
            last_price = ticker['last']
            cursor.execute('''
                INSERT OR REPLACE INTO bot_states (symbol, status, last_price)
                VALUES (?, ?, ?)
            ''', (symbol, 'running', last_price))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": f"Bot iniciado para {symbol}!"}), 200
            
        elif action == 'stop':
            cursor.execute('''
                INSERT OR REPLACE INTO bot_states (symbol, status, last_price)
                VALUES (?, ?, ?)
            ''', (symbol, 'stopped', 0.0))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": f"Bot parado para {symbol}."}), 200
            
        conn.close()
        return jsonify({"error": "Ação inválida."}), 400

    except Exception as e:
        return jsonify({"error": f"Erro no controle do bot: {str(e)}"}), 500

@app.route('/api/gas/balance', methods=['GET'])
def get_gas_balance():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(amount) FROM gas_transactions WHERE status = "Aprovado"')
    total = cursor.fetchone()[0]
    current_balance = 998.0 + (total if total else 0.0)
    
    cursor.execute('SELECT type, amount, tx_hash, status FROM gas_transactions')
    rows = cursor.fetchall()
    transactions = [{"type": r[0], "amount": r[1], "txHash": r[2], "status": r[3]} for r in rows]
    conn.close()
    
    return jsonify({
        "gas_balance": current_balance,
        "transactions": transactions
    }), 200

@app.route('/api/gas/deposit', methods=['POST'])
def register_deposit():
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        tx_hash = data.get('txHash')
        
        if amount <= 0 or not tx_hash:
            return jsonify({"error": "Informe um valor válido e o comprovante (TxHash)."}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gas_transactions (type, amount, tx_hash, status)
            VALUES (?, ?, ?, ?)
        ''', ('Gás', amount, tx_hash, 'Aprovado'))
        conn.commit()
        
        cursor.execute('SELECT SUM(amount) FROM gas_transactions WHERE status = "Aprovado"')
        total = cursor.fetchone()[0]
        new_balance = 998.0 + (total if total else 0.0)
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Depósito de {amount} USDT registrado com sucesso!",
            "new_balance": new_balance
        }), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao registrar depósito: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "active", "service": "AeroQuant Backend DB Connected"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
