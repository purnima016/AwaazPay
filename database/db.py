"""
Database — SQLite schema & initialization
"""

import sqlite3
import hashlib
import os
from flask import g

DATABASE = None  # set via app.config


def get_db(app=None):
    """Get a database connection. Uses Flask's app context if available."""
    if 'db' not in g:
        db_path = app.config['DATABASE'] if app else DATABASE
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row  # rows act like dicts
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """Create all tables and seed demo data."""
    global DATABASE
    DATABASE = app.config['DATABASE']

    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    with app.app_context():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # ── USERS TABLE ─────────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                phone       TEXT    UNIQUE NOT NULL,
                upi_id      TEXT    UNIQUE NOT NULL,
                pin_hash    TEXT    NOT NULL,
                balance     REAL    DEFAULT 24580.00,
                language    TEXT    DEFAULT 'en',
                created_at  TEXT    DEFAULT (datetime('now')),
                is_active   INTEGER DEFAULT 1
            )
        ''')

        # ── TRANSACTIONS TABLE ───────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                txn_id          TEXT    UNIQUE NOT NULL,
                sender_id       INTEGER NOT NULL,
                receiver_upi    TEXT    NOT NULL,
                receiver_name   TEXT    NOT NULL,
                amount          REAL    NOT NULL,
                status          TEXT    DEFAULT 'pending',
                txn_type        TEXT    DEFAULT 'IMPS',
                voice_command   TEXT,
                language_used   TEXT    DEFAULT 'en',
                created_at      TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
        ''')

        # ── VOICE LOGS TABLE ─────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER,
                raw_text        TEXT,
                detected_lang   TEXT,
                intent          TEXT,
                extracted_data  TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        ''')

        # ── CONTACTS TABLE ───────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                name        TEXT    NOT NULL,
                upi_id      TEXT    NOT NULL,
                phone       TEXT,
                nickname    TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ── SEED DEMO DATA ───────────────────────────────────────────
        def hash_pin(pin):
            return hashlib.sha256(pin.encode()).hexdigest()

        # Check if already seeded
        existing = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing == 0:
            demo_users = [
                ('Priya Sharma',  '9876543210', 'priya@awaazpay',  hash_pin('1234'), 24580.00, 'en'),
                ('Ravi Kumar',    '9876543211', 'ravi@okhdfcbank', hash_pin('5678'), 15000.00, 'hi'),
                ('Anita Devi',    '9876543212', 'anita@ybl',       hash_pin('9012'), 8200.00,  'te'),
                ('Sunita Bai',    '9876543213', 'sunita@oksbi',    hash_pin('3456'), 5400.00,  'ta'),
                ('Meena Kumari',  '9876543214', 'meena@okaxis',    hash_pin('7890'), 12000.00, 'hi'),
            ]
            cursor.executemany(
                "INSERT INTO users (name, phone, upi_id, pin_hash, balance, language) VALUES (?,?,?,?,?,?)",
                demo_users
            )

            # Seed demo transactions
            demo_txns = [
                ('AWZ-001', 1, 'ravi@okhdfcbank',  'Ravi Kumar',   340.0,  'success', 'IMPS', 'Ravi ko 340 bhejo', 'hi'),
                ('AWZ-002', 1, 'anita@ybl',         'Anita Devi',   1200.0, 'success', 'IMPS', 'Send 1200 to Anita', 'en'),
                ('AWZ-003', 1, 'sunita@oksbi',      'Sunita Bai',   120.0,  'success', 'IMPS', 'சுனிதாவுக்கு 120 அனுப்பு', 'ta'),
                ('AWZ-004', 1, 'meena@okaxis',      'Meena Kumari', 500.0,  'success', 'IMPS', 'మీనాకి 500 పంపండి', 'te'),
                ('AWZ-005', 1, 'ravi@okhdfcbank',   'Ravi Kumar',   840.0,  'success', 'IMPS', 'Pay 840 to Ravi for electricity', 'en'),
            ]
            cursor.executemany(
                "INSERT INTO transactions (txn_id, sender_id, receiver_upi, receiver_name, amount, status, txn_type, voice_command, language_used) VALUES (?,?,?,?,?,?,?,?,?)",
                demo_txns
            )

            # Seed contacts for user 1 (Priya)
            demo_contacts = [
                (1, 'Ravi Kumar',   'ravi@okhdfcbank',  '9876543211', 'Ravi bhai'),
                (1, 'Anita Devi',   'anita@ybl',         '9876543212', 'Anita ji'),
                (1, 'Sunita Bai',   'sunita@oksbi',      '9876543213', 'Sunita'),
                (1, 'Meena Kumari', 'meena@okaxis',      '9876543214', 'Meena'),
            ]
            cursor.executemany(
                "INSERT INTO contacts (user_id, name, upi_id, phone, nickname) VALUES (?,?,?,?,?)",
                demo_contacts
            )

            conn.commit()
            print("✅  Database initialized with demo data.")
        else:
            print("✅  Database already initialized.")

        conn.close()
    app.teardown_appcontext(close_db)
