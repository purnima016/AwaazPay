"""
UPI Service — Transaction Processing Engine
==========================================
Simulates UPI payment gateway integration.
In production: replace execute_upi_transfer() with
actual Razorpay / PayU / NPCI UPI SDK calls.
"""

import sqlite3
import uuid
import hashlib
from datetime import datetime


def generate_txn_id() -> str:
    """Generate a unique transaction ID like real UPI IDs."""
    uid = str(uuid.uuid4()).replace('-', '').upper()[:8]
    return f"AWZ{uid}"


def verify_pin(stored_hash: str, entered_pin: str) -> bool:
    """Verify PIN against stored hash."""
    return stored_hash == hashlib.sha256(entered_pin.encode()).hexdigest()


def get_user_by_id(db_path: str, user_id: int) -> dict | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_upi(db_path: str, upi_id: str) -> dict | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE upi_id = ? AND is_active = 1", (upi_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_contacts(db_path: str, user_id: int) -> list:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM contacts WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def execute_upi_transfer(db_path: str, sender_id: int, receiver_upi: str,
                          receiver_name: str, amount: float,
                          pin: str, voice_command: str = '', lang: str = 'en') -> dict:
    """
    Core transaction function.
    1. Validate sender & PIN
    2. Check balance
    3. Deduct from sender, add to receiver (if on platform)
    4. Record transaction
    5. Return result
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # ── 1. Get sender ────────────────────────────────────────────
        sender = conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1", (sender_id,)
        ).fetchone()

        if not sender:
            return {'success': False, 'error': 'Sender account not found'}

        # ── 2. Verify PIN ────────────────────────────────────────────
        if not verify_pin(sender['pin_hash'], pin):
            return {'success': False, 'error': 'Incorrect PIN. Transaction declined.'}

        # ── 3. Validate amount ───────────────────────────────────────
        if amount <= 0:
            return {'success': False, 'error': 'Invalid amount'}
        if amount > 100000:
            return {'success': False, 'error': 'Amount exceeds UPI limit of ₹1,00,000'}
        if sender['balance'] < amount:
            return {
                'success': False,
                'error': f'Insufficient balance. Available: ₹{sender["balance"]:.2f}'
            }

        # ── 4. Process transfer ──────────────────────────────────────
        txn_id = generate_txn_id()

        # Deduct from sender
        conn.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (amount, sender_id)
        )

        # Credit to receiver if they're on AwaazPay
        receiver = conn.execute(
            "SELECT * FROM users WHERE upi_id = ?", (receiver_upi,)
        ).fetchone()
        if receiver:
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (amount, receiver['id'])
            )

        # ── 5. Record transaction ────────────────────────────────────
        conn.execute('''
            INSERT INTO transactions
            (txn_id, sender_id, receiver_upi, receiver_name, amount, status, txn_type, voice_command, language_used)
            VALUES (?, ?, ?, ?, ?, 'success', 'IMPS', ?, ?)
        ''', (txn_id, sender_id, receiver_upi, receiver_name, amount, voice_command, lang))

        conn.commit()

        # ── 6. Return success ────────────────────────────────────────
        new_balance = conn.execute(
            "SELECT balance FROM users WHERE id = ?", (sender_id,)
        ).fetchone()['balance']

        return {
            'success':       True,
            'txn_id':        txn_id,
            'amount':        amount,
            'receiver_name': receiver_name,
            'receiver_upi':  receiver_upi,
            'new_balance':   new_balance,
            'timestamp':     datetime.now().strftime('%d %b %Y • %I:%M %p'),
            'txn_type':      'IMPS / Instant Transfer',
            'message':       f'₹{amount:.0f} sent successfully to {receiver_name}!'
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': f'Transaction failed: {str(e)}'}
    finally:
        conn.close()


def get_transaction_history(db_path: str, user_id: int, limit: int = 20) -> list:
    """Fetch transaction history for a user."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT * FROM transactions
        WHERE sender_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_balance(db_path: str, user_id: int) -> float | None:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None
