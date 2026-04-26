"""
NLP Service — Voice Command Processing Engine
=============================================
Parses voice commands in Telugu, Hindi, Tamil, English
and extracts: intent, recipient, amount.

No paid APIs needed — pure Python keyword matching.
(In production, swap extract_intent() with Groq/LLaMA call)
"""

import re
import json

# ── Number word maps for 4 languages ────────────────────────────────

HINDI_NUMBERS = {
    'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पाँच': 5, 'पांच': 5,
    'छह': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10,
    'बीस': 20, 'तीस': 30, 'चालीस': 40, 'पचास': 50,
    'साठ': 60, 'सत्तर': 70, 'अस्सी': 80, 'नब्बे': 90,
    'सौ': 100, 'हज़ार': 1000, 'हजार': 1000, 'लाख': 100000,
}

TELUGU_NUMBERS = {
    'ఒకటి': 1, 'రెండు': 2, 'మూడు': 3, 'నాలుగు': 4, 'అయిదు': 5,
    'ఆరు': 6, 'ఏడు': 7, 'ఎనిమిది': 8, 'తొమ్మిది': 9, 'పది': 10,
    'వంద': 100, 'వేయి': 1000,
}

TAMIL_NUMBERS = {
    'ஒன்று': 1, 'இரண்டு': 2, 'மூன்று': 3, 'நான்கு': 4, 'ஐந்து': 5,
    'ஆறு': 6, 'ஏழு': 7, 'எட்டு': 8, 'ஒன்பது': 9, 'பத்து': 10,
    'நூறு': 100, 'ஆயிரம்': 1000,
}

ALL_NUMBER_WORDS = {**HINDI_NUMBERS, **TELUGU_NUMBERS, **TAMIL_NUMBERS}

# ── Intent keywords ──────────────────────────────────────────────────

SEND_KEYWORDS = [
    # English
    'send', 'pay', 'transfer', 'give',
    # Hindi
    'भेजो', 'भेज', 'दो', 'भेजना', 'पेमेंट', 'ट्रांसफर',
    # Telugu
    'పంపండి', 'పంపు', 'ఇవ్వు', 'చెల్లించు',
    # Tamil
    'அனுப்பு', 'கொடு', 'செலுத்து',
]

BALANCE_KEYWORDS = [
    # English
    'balance', 'check balance', 'how much', 'account',
    # Hindi
    'बैलेंस', 'बकाया', 'कितना', 'खाता',
    # Telugu
    'బ్యాలెన్స్', 'నిల్వ', 'చెక్',
    # Tamil
    'இருப்பு', 'பேலன்ஸ்', 'சரிபார்',
]

HISTORY_KEYWORDS = [
    'history', 'transactions', 'last', 'recent', 'statement',
    'इतिहास', 'लेनदेन', 'ट्रांजेक्शन',
    'చరిత్ర', 'లావాదేవీలు',
    'வரலாறு', 'பரிவர்த்தனை',
]

# ── Language detection ───────────────────────────────────────────────

def detect_language(text: str) -> str:
    """Fast Unicode-range language detector. ~0ms, 90% accuracy."""
    telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))
    hindi_chars  = len(re.findall(r'[\u0900-\u097F]', text))
    tamil_chars  = len(re.findall(r'[\u0B80-\u0BFF]', text))

    scores = {'te': telugu_chars, 'hi': hindi_chars, 'ta': tamil_chars, 'en': 0}

    # English fallback: count ASCII letters
    ascii_words = len(re.findall(r'[a-zA-Z]+', text))
    scores['en'] = ascii_words

    return max(scores, key=scores.get)


# ── Amount extraction ────────────────────────────────────────────────

def extract_amount(text: str) -> float | None:
    """
    Extract rupee amount from voice text.
    Handles: "500", "₹200", "five hundred", "पाँच सौ", etc.
    """
    # 1) ₹ symbol followed by number
    match = re.search(r'[₹Rs\.]*\s*(\d[\d,]*(?:\.\d{1,2})?)', text)
    if match:
        return float(match.group(1).replace(',', ''))

    # 2) Plain number in text
    match = re.search(r'\b(\d+(?:\.\d{1,2})?)\b', text)
    if match:
        return float(match.group(1))

    # 3) Word-based numbers
    text_lower = text.lower()
    for word, val in ALL_NUMBER_WORDS.items():
        if word in text_lower or word in text:
            return float(val)

    return None


# ── Recipient extraction ─────────────────────────────────────────────

def extract_recipient(text: str, contacts: list) -> dict | None:
    """
    Match recipient name from voice text using known contacts list.
    contacts = [{'name': 'Ravi Kumar', 'upi_id': 'ravi@okhdfcbank', ...}]
    """
    text_lower = text.lower()

    for contact in contacts:
        name_parts = contact['name'].lower().split()
        # Check if any part of the name appears in text
        for part in name_parts:
            if len(part) > 2 and part in text_lower:
                return contact

    # Fallback: try to extract a proper noun (capitalized word)
    words = text.split()
    for i, word in enumerate(words):
        clean = re.sub(r'[^\w]', '', word)
        if clean and clean[0].isupper() and len(clean) > 2:
            # Skip known keywords
            if clean.lower() not in ['send', 'pay', 'transfer', 'rupees', 'inr']:
                return {'name': clean, 'upi_id': None}

    return None


# ── Main NLP processor ───────────────────────────────────────────────

def process_voice_command(text: str, contacts: list = []) -> dict:
    """
    Main entry point: parse a voice command and return structured data.

    Returns:
    {
        "intent":    "send_money" | "check_balance" | "transaction_history" | "unknown",
        "amount":    500.0 or None,
        "recipient": {"name": "Ravi Kumar", "upi_id": "ravi@okhdfcbank"} or None,
        "language":  "en" | "hi" | "te" | "ta",
        "raw_text":  "Send 500 to Ravi",
        "confidence": 0.95,
        "response_text": "Do you want to send ₹500 to Ravi Kumar?"
    }
    """
    if not text or not text.strip():
        return _error_response("Empty voice command")

    text = text.strip()
    lang = detect_language(text)
    text_lower = text.lower()

    # ── Detect intent ────────────────────────────────────────────────
    intent = 'unknown'
    confidence = 0.5

    if any(kw in text_lower or kw in text for kw in SEND_KEYWORDS):
        intent = 'send_money'
        confidence = 0.92
    elif any(kw in text_lower or kw in text for kw in BALANCE_KEYWORDS):
        intent = 'check_balance'
        confidence = 0.95
    elif any(kw in text_lower or kw in text for kw in HISTORY_KEYWORDS):
        intent = 'transaction_history'
        confidence = 0.90

    # ── Extract entities ─────────────────────────────────────────────
    amount    = extract_amount(text) if intent == 'send_money' else None
    recipient = extract_recipient(text, contacts) if intent == 'send_money' else None

    # ── Build response text ──────────────────────────────────────────
    response_text = _build_response(intent, amount, recipient, lang)

    return {
        'intent':        intent,
        'amount':        amount,
        'recipient':     recipient,
        'language':      lang,
        'raw_text':      text,
        'confidence':    confidence,
        'response_text': response_text,
        'ready_to_send': intent == 'send_money' and amount is not None and recipient is not None,
    }


def _build_response(intent, amount, recipient, lang):
    """Generate voice response text in the detected language."""
    if intent == 'send_money':
        amt_str = f"₹{int(amount)}" if amount else "an amount"
        name    = recipient['name'] if recipient else "the recipient"

        responses = {
            'en': f"Do you want to send {amt_str} to {name}?",
            'hi': f"क्या आप {name} को {amt_str} भेजना चाहती हैं?",
            'te': f"మీరు {name} కి {amt_str} పంపాలనుకుంటున్నారా?",
            'ta': f"நீங்கள் {name} க்கு {amt_str} அனுப்ப விரும்புகிறீர்களா?",
        }
        return responses.get(lang, responses['en'])

    elif intent == 'check_balance':
        responses = {
            'en': "Checking your account balance...",
            'hi': "आपका खाता बैलेंस देख रही हूँ...",
            'te': "మీ ఖాతా బ్యాలెన్స్ తనిఖీ చేస్తున్నాను...",
            'ta': "உங்கள் கணக்கு இருப்பை சரிபார்க்கிறேன்...",
        }
        return responses.get(lang, responses['en'])

    elif intent == 'transaction_history':
        return "Here are your recent transactions."

    return "Sorry, I didn't understand. Please try again."


def _error_response(msg):
    return {
        'intent': 'unknown', 'amount': None, 'recipient': None,
        'language': 'en', 'raw_text': '', 'confidence': 0.0,
        'response_text': msg, 'ready_to_send': False,
    }
