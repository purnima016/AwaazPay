"""
Voice Routes — /api/voice
==========================
POST /api/voice/process   — Parse voice command text → intent + entities
POST /api/voice/execute   — Parse + execute in one shot (with PIN)
GET  /api/voice/languages — Get supported languages
"""

import sqlite3
from flask import Blueprint, request, jsonify, current_app
from services.nlp_service import process_voice_command, detect_language
from services.upi_service  import get_contacts, execute_upi_transfer, get_balance

voice_bp = Blueprint('voice', __name__)


# ── POST /api/voice/process ───────────────────────────────────────────
@voice_bp.route('/process', methods=['POST'])
def process_voice():
    """
    Parse a voice command into structured data.

    Body: {
      "text":    "Send 500 to Ravi",
      "user_id": 1              (optional, for contact lookup)
    }

    Returns: {
      "intent":        "send_money",
      "amount":        500.0,
      "recipient":     {"name": "Ravi Kumar", "upi_id": "ravi@okhdfcbank"},
      "language":      "en",
      "confidence":    0.92,
      "response_text": "Do you want to send ₹500 to Ravi Kumar?",
      "ready_to_send": true
    }
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'text field is required'}), 400

    text    = data['text'].strip()
    user_id = data.get('user_id', 1)

    # Load contacts for recipient matching
    db_path  = current_app.config['DATABASE']
    contacts = get_contacts(db_path, user_id)

    # Run NLP
    result = process_voice_command(text, contacts)

    # Log the voice command
    _log_voice(db_path, user_id, text, result)

    # If it's a balance check, include actual balance
    if result['intent'] == 'check_balance':
        bal = get_balance(db_path, user_id)
        result['balance'] = bal
        result['balance_formatted'] = f'₹{bal:,.2f}' if bal else None

    return jsonify(result)


# ── POST /api/voice/execute ────────────────────────────────────────────
@voice_bp.route('/execute', methods=['POST'])
def execute_voice():
    """
    Full pipeline: voice text → parse → execute transaction.

    Body: {
      "text":    "Send 500 to Ravi",
      "user_id": 1,
      "pin":     "1234"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    text    = data.get('text', '').strip()
    user_id = data.get('user_id', 1)
    pin     = data.get('pin', '')

    if not text:
        return jsonify({'error': 'text is required'}), 400
    if not pin:
        return jsonify({'error': 'pin is required'}), 400

    db_path  = current_app.config['DATABASE']
    contacts = get_contacts(db_path, user_id)
    parsed   = process_voice_command(text, contacts)

    if parsed['intent'] != 'send_money':
        return jsonify({'error': 'Could not detect send intent', 'parsed': parsed}), 400
    if not parsed.get('amount'):
        return jsonify({'error': 'Could not detect amount', 'parsed': parsed}), 400
    if not parsed.get('recipient'):
        return jsonify({'error': 'Could not detect recipient', 'parsed': parsed}), 400

    recipient = parsed['recipient']
    result = execute_upi_transfer(
        db_path       = db_path,
        sender_id     = user_id,
        receiver_upi  = recipient.get('upi_id') or f"{recipient['name'].lower().replace(' ','')}@upi",
        receiver_name = recipient['name'],
        amount        = parsed['amount'],
        pin           = str(pin),
        voice_command = text,
        lang          = parsed['language'],
    )

    return jsonify({**result, 'parsed_command': parsed})


# ── GET /api/voice/languages ──────────────────────────────────────────
@voice_bp.route('/languages', methods=['GET'])
def languages():
    return jsonify({
        'supported': [
            {'code': 'en', 'name': 'English',  'native': 'English',  'example': 'Send 500 to Ravi'},
            {'code': 'hi', 'name': 'Hindi',    'native': 'हिंदी',     'example': 'रवि को 500 भेजो'},
            {'code': 'te', 'name': 'Telugu',   'native': 'తెలుగు',    'example': 'రవికి 500 పంపండి'},
            {'code': 'ta', 'name': 'Tamil',    'native': 'தமிழ்',     'example': 'ரவிக்கு 500 அனுப்பு'},
        ],
        'default': 'en',
        'auto_detect': True,
    })


# ── Helper: log voice commands ────────────────────────────────────────
def _log_voice(db_path, user_id, text, result):
    import json
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO voice_logs (user_id, raw_text, detected_lang, intent, extracted_data) VALUES (?,?,?,?,?)",
            (user_id, text, result['language'], result['intent'], json.dumps({
                'amount': result.get('amount'),
                'recipient': result.get('recipient'),
            }))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Logging failure should never crash the API
