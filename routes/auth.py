"""
Auth Routes — /api/auth
=======================
POST /api/auth/login    — Login with phone + PIN
POST /api/auth/register — Register new user
GET  /api/auth/me       — Get current user info
"""

import hashlib
import sqlite3
from flask import Blueprint, request, jsonify, current_app

auth_bp = Blueprint('auth', __name__)


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# ── POST /api/auth/login ─────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Body: { "phone": "9876543210", "pin": "1234" }
    Returns user info + token (simple user_id for demo)
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    phone = data.get('phone', '').strip()
    pin   = data.get('pin', '').strip()

    if not phone or not pin:
        return jsonify({'error': 'Phone and PIN are required'}), 400

    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        "SELECT * FROM users WHERE phone = ? AND is_active = 1", (phone,)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user['pin_hash'] != hash_pin(pin):
        return jsonify({'error': 'Incorrect PIN'}), 401

    return jsonify({
        'success':  True,
        'user_id':  user['id'],
        'name':     user['name'],
        'phone':    user['phone'],
        'upi_id':   user['upi_id'],
        'balance':  user['balance'],
        'language': user['language'],
        'token':    f"demo_token_{user['id']}"   # In production: use JWT
    })


# ── POST /api/auth/register ──────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Body: { "name": "Priya", "phone": "9876543210", "pin": "1234", "language": "en" }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name     = data.get('name', '').strip()
    phone    = data.get('phone', '').strip()
    pin      = data.get('pin', '').strip()
    language = data.get('language', 'en')

    if not all([name, phone, pin]):
        return jsonify({'error': 'Name, phone, and PIN are required'}), 400
    if len(pin) < 4:
        return jsonify({'error': 'PIN must be at least 4 digits'}), 400
    if len(phone) != 10:
        return jsonify({'error': 'Phone must be 10 digits'}), 400

    # Generate UPI ID
    first_name = name.split()[0].lower()
    upi_id     = f"{first_name}{phone[-4:]}@awaazpay"

    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)

    try:
        conn.execute(
            "INSERT INTO users (name, phone, upi_id, pin_hash, language) VALUES (?,?,?,?,?)",
            (name, phone, upi_id, hash_pin(pin), language)
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        return jsonify({
            'success':  True,
            'user_id':  user_id,
            'name':     name,
            'upi_id':   upi_id,
            'message':  f'Welcome to AwaazPay, {name}! Your UPI ID: {upi_id}'
        }), 201

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Phone number already registered'}), 409


# ── GET /api/auth/me ─────────────────────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
def me():
    """Get user info. Pass user_id as query param for demo."""
    user_id = request.args.get('user_id', 1)
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        "SELECT id, name, phone, upi_id, balance, language, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(dict(user))
