"""
AwaazPay Backend — Voice-Based Banking API
==========================================
Flask + SQLite backend for the AwaazPay hackathon project.
Author: AwaazPay Team
"""

from flask import Flask, send_from_directory
from flask_cors import CORS
from database.db import init_db
from routes.auth import auth_bp
from routes.transactions import transactions_bp
from routes.voice import voice_bp
from routes.users import users_bp
import os

app = Flask(__name__)
CORS(app)  # Allow frontend (HTML file) to call API

# ── Config ──────────────────────────────────────────────────────────
app.config['SECRET_KEY']       = os.getenv('SECRET_KEY', 'awaazpay-secret-2026')
app.config['DATABASE']         = os.path.join(os.path.dirname(__file__), 'database', 'awaazpay.db')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit (for audio)

# ── Register Blueprints ──────────────────────────────────────────────
app.register_blueprint(auth_bp,         url_prefix='/api/auth')
app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
app.register_blueprint(voice_bp,        url_prefix='/api/voice')
app.register_blueprint(users_bp,        url_prefix='/api/users')

# ── Serve Frontend ───────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/health')
def health():
    return {'status': 'ok', 'db': 'connected'}

# ── Init DB & Run ────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db(app)
    print("\n" + "="*50)
    print("  🎤  AwaazPay Backend Server Starting...")
    print("="*50)
    print("  URL  : http://localhost:5000")
    print("  DB   : SQLite (database/awaazpay.db)")
    print("="*50 + "\n")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
