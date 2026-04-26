"""
Users Routes — /api/users
==========================
GET  /api/users/<id>/contacts  — Get contacts list
POST /api/users/<id>/contacts  — Add contact
GET  /api/users/<id>/stats     — Get spending stats
"""

import sqlite3
from flask import Blueprint, request, jsonify, current_app

users_bp = Blueprint('users', __name__)


@users_bp.route('/<int:user_id>/contacts', methods=['GET'])
def get_contacts(user_id):
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM contacts WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return jsonify({'contacts': [dict(r) for r in rows]})


@users_bp.route('/<int:user_id>/contacts', methods=['POST'])
def add_contact(user_id):
    data = request.get_json()
    if not data or not data.get('name') or not data.get('upi_id'):
        return jsonify({'error': 'name and upi_id required'}), 400

    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO contacts (user_id, name, upi_id, phone, nickname) VALUES (?,?,?,?,?)",
        (user_id, data['name'], data['upi_id'], data.get('phone',''), data.get('nickname',''))
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f"Contact {data['name']} added"}), 201


@users_bp.route('/<int:user_id>/stats', methods=['GET'])
def get_stats(user_id):
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total_sent = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as total FROM transactions WHERE sender_id=? AND status='success'",
        (user_id,)
    ).fetchone()['total']

    txn_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE sender_id=? AND status='success'",
        (user_id,)
    ).fetchone()['cnt']

    balance = conn.execute(
        "SELECT balance FROM users WHERE id=?", (user_id,)
    ).fetchone()['balance']

    conn.close()
    return jsonify({
        'user_id':    user_id,
        'balance':    balance,
        'total_sent': total_sent,
        'txn_count':  txn_count,
    })
