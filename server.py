from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import random
import string
from datetime import datetime, timedelta
import base64
import secrets

app = Flask(__name__)
CORS(app)

# ============================================
# 🔐 بيانات PayPal
# ============================================
PAYPAL_CLIENT_ID = "Ab84fn5Z-fuDvANlGASLbDIkWhPA9J4d3fBtGqt98_Qp6l9fkgvTpZIrc_kwbCNxBMHjUuBCnetcINVa"
PAYPAL_SECRET = "EEi9D6sGO9n4Jhd0Dvk0t2-aIKEwW5fNYXOZ9T8nfcRCmEBElTz8kyhpq9dKiHB4a5wDApxW55UPCnDp"
PAYPAL_PLAN_ID = "P-26497072CJ312830WNHY54PY"

# ============================================
# ملفات التخزين
# ============================================
LICENSES_FILE = "licenses.json"
PAID_DEVICES_FILE = "paid_devices.json"
TRIALS_FILE = "free_trials.json"

# ============================================
# كلمة سر لتوليد المفاتيح يدوياً
# ============================================
ADMIN_SECRET = "SAT-ADMIN-KEY-2024"

# ============================================
# دوال مساعدة
# ============================================

def load_licenses():
    try:
        if os.path.exists(LICENSES_FILE):
            with open(LICENSES_FILE, 'r') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_licenses(licenses):
    try:
        with open(LICENSES_FILE, 'w') as f:
            json.dump(licenses, f, indent=2)
        return True
    except:
        return False

def load_paid_devices():
    try:
        if os.path.exists(PAID_DEVICES_FILE):
            with open(PAID_DEVICES_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except:
        return set()

def save_paid_device(device_id):
    paid = load_paid_devices()
    paid.add(device_id)
    with open(PAID_DEVICES_FILE, 'w') as f:
        json.dump(list(paid), f)

def is_device_paid(device_id):
    return device_id in load_paid_devices()

def load_trials():
    try:
        if os.path.exists(TRIALS_FILE):
            with open(TRIALS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_trials(trials):
    with open(TRIALS_FILE, 'w') as f:
        json.dump(trials, f, indent=2)

def has_free_trial(device_id):
    trials = load_trials()
    if device_id in trials:
        expiry = datetime.fromisoformat(trials[device_id]['expiry'])
        if expiry > datetime.now():
            return True, trials[device_id]['expiry']
        else:
            return True, None
    return False, None

def start_free_trial(device_id, email):
    trials = load_trials()
    expiry = datetime.now() + timedelta(hours=24)
    
    trials[device_id] = {
        'email': email,
        'started': datetime.now().isoformat(),
        'expiry': expiry.isoformat(),
        'used': True
    }
    save_trials(trials)
    
    # توليد كود ترخيص تجريبي
    license_key = f"TRIAL_{device_id[:8]}_{secrets.token_hex(4)}".upper()
    
    # حفظ الترخيص التجريبي
    licenses = load_licenses()
    licenses[device_id] = {
        "license_key": license_key,
        "device_id": device_id,
        "created_at": datetime.now().isoformat(),
        "expiry_date": expiry.isoformat(),
        "status": "trial",
        "email": email
    }
    save_licenses(licenses)
    
    return license_key, expiry

def generate_license_key():
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def create_license_for_device(device_id, license_key=None):
    if license_key is None:
        license_key = generate_license_key()
    
    licenses = load_licenses()
    licenses[device_id] = {
        "license_key": license_key,
        "device_id": device_id,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    save_licenses(licenses)
    return license_key

# ============================================
# 1. صفحة الدفع
# ============================================
@app.route('/buy', methods=['GET'])
def buy_page():
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>SatelliteChecking1 - اشتراك شهري</title>
        <script src="https://www.paypal.com/sdk/js?client-id={PAYPAL_CLIENT_ID}&vault=true&intent=subscription"></script>
        <style>
            body {{ font-family: 'Segoe UI', Arial; text-align: center; padding: 50px; background: #0f172a; color: white; direction: rtl; }}
            .container {{ max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }}
            h1 {{ color: #facc15; }}
            .price {{ font-size: 48px; color: #38bdf8; margin: 20px 0; }}
            .trial-btn {{ background: #34d399; color: #0f172a; padding: 12px 25px; border-radius: 10px; text-decoration: none; display: inline-block; margin-top: 20px; }}
        </style>
        <script>
            if(!localStorage.getItem('satellite_device_id')) {{
                var deviceId = 'DEV_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('satellite_device_id', deviceId);
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ SatelliteChecking1</h1>
            <div class="price">$20 <span style="font-size:18px">/ شهرياً</span></div>
            <div id="paypal-button-container"></div>
            <a href="/free-trial" class="trial-btn">🎁 جرب مجاناً لمدة 24 ساعة</a>
            <a href="/" style="display:block; margin-top:20px; color:#38bdf8;">🏠 الرئيسية</a>
        </div>
        <script>
            var deviceId = localStorage.getItem('satellite_device_id');
            paypal.Buttons({{
                createSubscription: function(data, actions) {{
                    return actions.subscription.create({{
                        plan_id: '{PAYPAL_PLAN_ID}',
                        custom_id: deviceId
                    }});
                }},
                onApprove: function(data, actions) {{
                    window.location.href = '/payment-success?subscription_id=' + data.subscriptionID + '&device_id=' + deviceId;
                }}
            }}).render('#paypal-button-container');
        </script>
    </body>
    </html>
    '''

# ============================================
# 2. صفحة التجربة المجانية
# ============================================
@app.route('/free-trial', methods=['GET'])
def free_trial_page():
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تجربة مجانية - SatelliteChecking1</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; }
            .container { max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }
            input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 8px; background: #334155; color: white; border: none; }
            button { background: #34d399; color: #0f172a; padding: 12px 30px; border: none; border-radius: 10px; cursor: pointer; }
        </style>
        <script>
            if(!localStorage.getItem('satellite_device_id')) {
                var deviceId = 'DEV_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('satellite_device_id', deviceId);
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🎁 تجربة مجانية 24 ساعة</h1>
            <input type="text" id="device_id" placeholder="معرف الجهاز">
            <input type="email" id="email" placeholder="بريدك الإلكتروني">
            <button onclick="startTrial()">ابدأ التجربة</button>
            <div id="result"></div>
            <a href="/buy" style="color:#38bdf8; display:block; margin-top:20px;">💰 شراء اشتراك</a>
        </div>
        <script>
            document.getElementById('device_id').value = localStorage.getItem('satellite_device_id');
            
            function startTrial() {
                var device_id = document.getElementById('device_id').value;
                var email = document.getElementById('email').value;
                
                fetch('/api/start-free-trial', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({device_id: device_id, email: email})
                })
                .then(res => res.json())
                .then(data => {
                    if(data.success) {
                        document.getElementById('result').innerHTML = '<div style="background:#34d399;padding:15px;border-radius:10px;">✅ تم التفعيل<br>🔑 كودك: ' + data.license_key + '</div>';
                        localStorage.setItem('satellite_license', data.license_key);
                    } else {
                        document.getElementById('result').innerHTML = '<div style="background:#ef4444;padding:15px;border-radius:10px;">❌ ' + data.error + '</div>';
                    }
                });
            }
        </script>
    </body>
    </html>
    '''

# ============================================
# 3. API بدء التجربة
# ============================================
@app.route('/api/start-free-trial', methods=['POST'])
def start_free_trial_api():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        email = data.get('email')
        
        if not device_id or not email:
            return jsonify({'success': False, 'error': 'جميع الحقول مطلوبة'})
        
        has_trial, expiry = has_free_trial(device_id)
        if has_trial:
            return jsonify({'success': False, 'error': 'لقد استخدمت التجربة مسبقاً'})
        
        license_key, expiry_date = start_free_trial(device_id, email)
        return jsonify({'success': True, 'license_key': license_key, 'expiry': expiry_date.isoformat()})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 4. صفحة نجاح الدفع
# ============================================
@app.route('/payment-success', methods=['GET'])
def payment_success():
    device_id = request.args.get('device_id')
    if device_id:
        save_paid_device(device_id)
        license_key = create_license_for_device(device_id)
        return f'<h1>✅ تم الدفع بنجاح!</h1><p>🔑 كود التفعيل: {license_key}</p><a href="/">العودة</a>'
    return '❌ خطأ'

# ============================================
# 5. API جلب الترخيص
# ============================================
@app.route('/api/get-license', methods=['POST'])
def get_license():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        licenses = load_licenses()
        if device_id in licenses:
            return jsonify({'success': True, 'license_key': licenses[device_id]['license_key']})
        
        return jsonify({'success': False, 'error': 'لا يوجد ترخيص'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 6. API تفعيل الترخيص
# ============================================
@app.route('/api/activate', methods=['POST'])
def activate():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        
        licenses = load_licenses()
        
        for dev_id, info in licenses.items():
            if info.get('license_key') == license_key:
                if info.get('status') in ['active', 'trial']:
                    if info.get('status') == 'trial' and info.get('expiry_date'):
                        expiry = datetime.fromisoformat(info['expiry_date'])
                        if expiry < datetime.now():
                            return jsonify({'success': False, 'error': 'انتهت التجربة'})
                    return jsonify({'success': True, 'status': info.get('status')})
        
        return jsonify({'success': False, 'error': 'ترخيص غير صالح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 7. API التحقق من الترخيص
# ============================================
@app.route('/api/check', methods=['POST'])
def check():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        
        licenses = load_licenses()
        for info in licenses.values():
            if info.get('license_key') == license_key:
                if info.get('status') == 'trial' and info.get('expiry_date'):
                    expiry = datetime.fromisoformat(info['expiry_date'])
                    if expiry < datetime.now():
                        return jsonify({'success': False, 'status': 'expired'})
                return jsonify({'success': True, 'status': 'active'})
        
        return jsonify({'success': False, 'status': 'invalid'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 8. API توليد مفتاح يدوي (للمطور)
# ============================================
@app.route('/api/admin/generate-key', methods=['POST'])
def admin_generate_key():
    try:
        data = request.get_json()
        admin_secret = data.get('admin_secret')
        device_id = data.get('device_id')
        
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح'})
        
        license_key = create_license_for_device(device_id)
        return jsonify({'success': True, 'license_key': license_key})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 9. الصفحة الرئيسية
# ============================================
@app.route('/', methods=['GET'])
def home():
    return jsonify({'service': 'SatelliteChecking1 API', 'status': 'online', 'endpoints': ['/buy', '/free-trial', '/api/activate', '/api/check', '/api/get-license']})

# ============================================
# 10. API الصحة
# ============================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'status': 'healthy', 'version': '4.0'})

# ============================================
# تشغيل السيرفر
# ============================================
if __name__ == '__main__':
    print("🚀 تشغيل السيرفر...")
    app.run(host='0.0.0.0', port=5000, debug=True)