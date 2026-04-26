"""
Transaction Routes — /api/transactions
=======================================
POST /api/transactions/send        — Send money via UPI
GET  /api/transactions/history     — Get transaction history
GET  /api/transactions/<txn_id>    — Get single transaction
GET  /api/transactions/balance     — Get current balance
"""

from flask import Blueprint, request, jsonify, current_app
from services.upi_service import (
    execute_upi_transfer, get_transaction_history,
    get_balance, get_user_by_upi
)

transactions_bp = Blueprint('transactions', __name__)


# ── POST /api/transactions/send ──────────────────────────────────────
@transactions_bp.route('/send', methods=['POST'])
def send_money():
    """
    Body: {
      "sender_id":     1,
      "receiver_upi":  "ravi@okhdfcbank",
      "receiver_name": "Ravi Kumar",
      "amount":        500,
      "pin":           "1234",
      "voice_command": "Send 500 to Ravi",
      "language":      "en"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['sender_id', 'receiver_upi', 'amount', 'pin']
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400

    db_path = current_app.config['DATABASE']

    # If receiver_name not provided, try to look up
    receiver_name = data.get('receiver_name', '')
    if not receiver_name:
        receiver = get_user_by_upi(db_path, data['receiver_upi'])
        receiver_name = receiver['name'] if receiver else data['receiver_upi']

    result = execute_upi_transfer(
        db_path       = db_path,
        sender_id     = data['sender_id'],
        receiver_upi  = data['receiver_upi'],
        receiver_name = receiver_name,
        amount        = float(data['amount']),
        pin           = str(data['pin']),
        voice_command = data.get('voice_command', ''),
        lang          = data.get('language', 'en'),
    )

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


# ── GET /api/transactions/history ────────────────────────────────────
@transactions_bp.route('/history', methods=['GET'])
def history():
    """
    Query params: user_id, limit (default 20)
    """
    user_id = request.args.get('user_id', 1, type=int)
    limit   = request.args.get('limit', 20, type=int)

    db_path = current_app.config['DATABASE']
    txns    = get_transaction_history(db_path, user_id, limit)

    return jsonify({
        'transactions': txns,
        'count':        len(txns),
        'user_id':      user_id,
    })


# ── GET /api/transactions/balance ─────────────────────────────────────
@transactions_bp.route('/balance', methods=['GET'])
def balance():
    """
    Query params: user_id
    """
    user_id = request.args.get('user_id', 1, type=int)
    db_path = current_app.config['DATABASE']
    bal     = get_balance(db_path, user_id)

    if bal is None:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user_id': user_id,
        'balance': bal,
        'formatted': f'₹{bal:,.2f}',
        'currency': 'INR',
    })


# ── GET /api/transactions/<txn_id> ───────────────────────────────────
@transactions_bp.route('/<txn_id>', methods=['GET'])
def get_transaction(txn_id):
    import sqlite3
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM transactions WHERE txn_id = ?", (txn_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Transaction not found'}), 404
    return jsonify(dict(row))
