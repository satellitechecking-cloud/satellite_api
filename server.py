from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import os
import random
import string
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# ============================================
# إعدادات حفظ الإيصالات
# ============================================
UPLOAD_FOLDER = "payment_receipts"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================
# ملفات التخزين
# ============================================
LICENSES_FILE = "licenses.json"
PAID_DEVICES_FILE = "paid_devices.json"
TRIAL_USED_FILE = "trial_used.json"
PENDING_PAYMENTS_FILE = "pending_payments.json"
FAILED_ATTEMPTS_FILE = "failed_attempts.json"
CRYPTO_PAYMENTS_FILE = "crypto_payments.json"

# ============================================
# إعدادات الحماية
# ============================================
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
ADMIN_SECRET = "SAT-ADMIN-2024"

# ============================================
# عنوان المحفظة الرقمية
# ============================================
CRYPTO_WALLET_ADDRESS = "0x8dae6262f49407ab6aee40de10ca458f526b7dd04c1dcd3f733621c83738d071"
CRYPTO_NETWORK = "ERC20"
CRYPTO_CURRENCY = "USDT"

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
        with open("licenses_backup.json", 'w') as f:
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

def load_trial_used():
    try:
        if os.path.exists(TRIAL_USED_FILE):
            with open(TRIAL_USED_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except:
        return set()

def save_trial_used(device_id):
    trial_used = load_trial_used()
    trial_used.add(device_id)
    with open(TRIAL_USED_FILE, 'w') as f:
        json.dump(list(trial_used), f)

def has_used_trial(device_id):
    return device_id in load_trial_used()

def generate_license_key():
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_server_time():
    try:
        import requests
        response = requests.get("https://worldtimeapi.org/api/timezone/Asia/Jerusalem", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return datetime.fromisoformat(data['datetime'].replace('Z', '+00:00'))
    except:
        pass
    return datetime.now()

def record_failed_attempt(device_id):
    try:
        attempts = {}
        if os.path.exists(FAILED_ATTEMPTS_FILE):
            with open(FAILED_ATTEMPTS_FILE, 'r') as f:
                attempts = json.load(f)
        
        now = datetime.now().isoformat()
        if device_id not in attempts:
            attempts[device_id] = {'count': 1, 'last_attempt': now, 'locked_until': None}
        else:
            attempts[device_id]['count'] += 1
            attempts[device_id]['last_attempt'] = now
        
        if attempts[device_id]['count'] >= MAX_FAILED_ATTEMPTS:
            lock_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            attempts[device_id]['locked_until'] = lock_until
        
        with open(FAILED_ATTEMPTS_FILE, 'w') as f:
            json.dump(attempts, f, indent=2)
    except:
        pass

def is_device_locked(device_id):
    try:
        if os.path.exists(FAILED_ATTEMPTS_FILE):
            with open(FAILED_ATTEMPTS_FILE, 'r') as f:
                attempts = json.load(f)
            
            if device_id in attempts and attempts[device_id].get('locked_until'):
                lock_until = datetime.fromisoformat(attempts[device_id]['locked_until'])
                if lock_until > datetime.now():
                    return True
    except:
        pass
    return False

def reset_failed_attempts(device_id):
    try:
        if os.path.exists(FAILED_ATTEMPTS_FILE):
            with open(FAILED_ATTEMPTS_FILE, 'r') as f:
                attempts = json.load(f)
            if device_id in attempts:
                del attempts[device_id]
            with open(FAILED_ATTEMPTS_FILE, 'w') as f:
                json.dump(attempts, f, indent=2)
    except:
        pass

# ============================================
# صفحات الويب
# ============================================

@app.route('/buy', methods=['GET'])
def buy_page():
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>SatelliteChecking1 - اشتراك شهري</title>
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; }}
            .container {{ max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }}
            h1 {{ color: #facc15; }}
            .price {{ font-size: 48px; color: #38bdf8; margin: 20px 0; }}
            .bank-info, .crypto-info {{ background: #0f172a; padding: 15px; border-radius: 10px; margin: 20px 0; text-align: right; direction: ltr; }}
            .crypto-info {{ border: 1px solid #facc15; }}
            .copy-btn {{ background: #38bdf8; color: #0f172a; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }}
            .note {{ font-size: 12px; color: #94a3b8; margin-top: 20px; }}
        </style>
        <script>
            function copyAddress() {{
                navigator.clipboard.writeText('{CRYPTO_WALLET_ADDRESS}');
                alert('✅ تم نسخ عنوان المحفظة!');
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ SatelliteChecking1</h1>
            <p>نظام كشف الفراغات والمعادن والذهب عبر الأقمار الصناعية</p>
            <div class="price">$20 <span style="font-size:18px">/ شهرياً</span></div>
            
            <div class="bank-info">
                <strong>🏦 التحويل البنكي:</strong><br>
                البنك: البنك الإسلامي الفلسطيني<br>
                اسم المستفيد: هيثم غازي محمد بزراوي<br>
                رقم الحساب: 0842/1610058/003/3101/000<br>
                رقم IBAN: PS30PIBC084216100580033101000
            </div>
            
            <div class="crypto-info">
                <strong>💸 الدفع بالعملة الرقمية (USDT):</strong><br>
                العملة: {CRYPTO_CURRENCY}<br>
                الشبكة: {CRYPTO_NETWORK}<br>
                العنوان: <code style="font-size: 11px;">{CRYPTO_WALLET_ADDRESS}</code>
                <button class="copy-btn" onclick="copyAddress()">📋 نسخ</button><br>
                المبلغ: 20 USDT
            </div>
            
            <p>⚠️ بعد التحويل، يرجى العودة إلى البرنامج وإرسال إشعار الدفع مع رقم العملية أو هاش المعاملة</p>
            <div class="note">🔒 سيتم تفعيل اشتراكك خلال 24 ساعة من استلام إشعار الدفع</div>
        </div>
    </body>
    </html>
    '''

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
            button { background: #34d399; color: #0f172a; padding: 12px 30px; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; }
            .result { margin-top: 20px; padding: 15px; border-radius: 10px; }
            .success { background: #34d399; color: #0f172a; }
            .error { background: #ef4444; color: white; }
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
            <button onclick="startTrial()">ابدأ التجربة الآن</button>
            <div id="result"></div>
            <hr style="margin: 20px 0;">
            <p>أو يمكنك</p>
            <a href="/buy" style="background:#38bdf8; color:#0f172a; padding:12px 30px; border-radius:10px; text-decoration:none; display:inline-block;">💰 شراء اشتراك شهري (20$)</a>
        </div>
        <script>
            document.getElementById('device_id').value = localStorage.getItem('satellite_device_id');
            
            async function startTrial() {
                var device_id = document.getElementById('device_id').value;
                var email = document.getElementById('email').value;
                
                if(!email) {
                    document.getElementById('result').innerHTML = '<div class="result error">❌ الرجاء إدخال البريد الإلكتروني</div>';
                    return;
                }
                
                document.getElementById('result').innerHTML = '<div class="result">🔄 جاري التفعيل...</div>';
                
                try {
                    const response = await fetch('/api/start-free-trial', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({device_id: device_id, email: email})
                    });
                    const data = await response.json();
                    
                    if(data.success) {
                        document.getElementById('result').innerHTML = '<div class="result success">✅ تم التفعيل بنجاح!<br>🔑 كود التفعيل: <strong>' + data.license_key + '</strong><br>📅 ينتهي في: ' + new Date(data.expiry).toLocaleString('ar') + '</div>';
                        localStorage.setItem('satellite_license', data.license_key);
                    } else {
                        document.getElementById('result').innerHTML = '<div class="result error">❌ ' + data.error + '</div>';
                    }
                } catch(error) {
                    document.getElementById('result').innerHTML = '<div class="result error">❌ خطأ في الاتصال: ' + error.message + '</div>';
                }
            }
        </script>
    </body>
    </html>
    '''

# ============================================
# API الرئيسية
# ============================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'SatelliteChecking1 API',
        'version': '5.0',
        'price': '20 USD',
        'crypto_wallet': CRYPTO_WALLET_ADDRESS,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/start-free-trial', methods=['POST'])
def start_free_trial_api():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        email = data.get('email')
        
        if not device_id or not email:
            return jsonify({'success': False, 'error': 'جميع الحقول مطلوبة'})
        
        if is_device_locked(device_id):
            return jsonify({'success': False, 'error': f'الجهاز مقفل مؤقتاً. حاول بعد {LOCKOUT_MINUTES} دقيقة'})
        
        if has_used_trial(device_id):
            record_failed_attempt(device_id)
            return jsonify({'success': False, 'error': 'لقد استخدمت التجربة المجانية مسبقاً'})
        
        save_trial_used(device_id)
        
        server_time = get_server_time()
        expiry_date = server_time + timedelta(hours=24)  # 24 ساعة = يوم واحد
        
        trial_key = f"TRIAL_{device_id[:8]}_{random.randint(1000,9999)}"
        
        licenses = load_licenses()
        if device_id in licenses:
            del licenses[device_id]
        
        licenses[device_id] = {
            "license_key": trial_key,
            "device_id": device_id,
            "email": email,
            "created_at": server_time.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "status": "active",
            "type": "trial"
        }
        save_licenses(licenses)
        
        print(f"🎁 تم تفعيل التجربة المجانية للجهاز {device_id[:20]}... البريد: {email} (تنتهي بعد 24 ساعة)")
        
        return jsonify({
            'success': True,
            'license_key': trial_key,
            'expiry': expiry_date.isoformat(),
            'message': 'تم تفعيل التجربة المجانية بنجاح لمدة 24 ساعة'
        })
        
    except Exception as e:
        print(f"❌ خطأ في بدء التجربة: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get-license', methods=['POST'])
def get_license():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        if is_device_paid(device_id):
            licenses = load_licenses()
            if device_id in licenses and licenses[device_id].get('type') == 'paid':
                return jsonify({
                    'success': True,
                    'license_key': licenses[device_id]['license_key'],
                    'type': 'paid'
                })
            else:
                license_key = generate_license_key()
                expiry_date = get_server_time() + timedelta(days=30)
                licenses[device_id] = {
                    "license_key": license_key,
                    "device_id": device_id,
                    "created_at": datetime.now().isoformat(),
                    "expiry_date": expiry_date.isoformat(),
                    "status": "active",
                    "type": "paid"
                }
                save_licenses(licenses)
                return jsonify({
                    'success': True,
                    'license_key': license_key,
                    'type': 'paid'
                })
        
        if has_used_trial(device_id):
            licenses = load_licenses()
            if device_id in licenses and licenses[device_id].get('type') == 'trial':
                expiry_date = licenses[device_id].get('expiry_date')
                if expiry_date:
                    server_time = get_server_time()
                    expiry = datetime.fromisoformat(expiry_date)
                    if server_time > expiry:
                        return jsonify({
                            'success': False,
                            'error': 'انتهت صلاحية النسخة التجريبية',
                            'trial_expired': True
                        })
                return jsonify({
                    'success': True,
                    'license_key': licenses[device_id]['license_key'],
                    'type': 'trial'
                })
        
        return jsonify({
            'success': False,
            'error': 'لم يتم العثور على ترخيص لهذا الجهاز'
        })
        
    except Exception as e:
        print(f"❌ خطأ في get_license: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/activate', methods=['POST'])
def activate():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        
        if not license_key or not device_id:
            return jsonify({'success': False, 'error': 'بيانات ناقصة'})
        
        if is_device_locked(device_id):
            return jsonify({'success': False, 'error': f'تم قفل الجهاز مؤقتاً. حاول بعد {LOCKOUT_MINUTES} دقيقة'})
        
        if not license_key.startswith('TRIAL_') and not (len(license_key) == 19 and license_key.count('-') == 3):
            record_failed_attempt(device_id)
            return jsonify({'success': False, 'error': 'صيغة مفتاح غير صالحة'})
        
        licenses = load_licenses()
        
        for dev_id, info in licenses.items():
            if info.get('license_key') == license_key:
                if dev_id != device_id:
                    record_failed_attempt(device_id)
                    return jsonify({'success': False, 'error': 'هذا المفتاح غير صالح لهذا الجهاز'})
                
                if info.get('status') != 'active':
                    record_failed_attempt(device_id)
                    return jsonify({'success': False, 'error': 'الترخيص غير نشط'})
                
                if info.get('type') == 'trial':
                    expiry_date = info.get('expiry_date')
                    if expiry_date:
                        server_time = get_server_time()
                        expiry = datetime.fromisoformat(expiry_date)
                        if server_time > expiry:
                            record_failed_attempt(device_id)
                            return jsonify({'success': False, 'error': 'انتهت صلاحية النسخة التجريبية'})
                
                reset_failed_attempts(device_id)
                
                days_left = "غير محدد"
                if info.get('expiry_date'):
                    try:
                        server_time = get_server_time()
                        expiry = datetime.fromisoformat(info['expiry_date'])
                        days_left_num = (expiry - server_time).days
                        days_left = f"{max(0, days_left_num)} يوم"
                    except:
                        pass
                
                return jsonify({
                    'success': True,
                    'status': 'active',
                    'type': info.get('type', 'paid'),
                    'message': f'ترخيص صالح - {days_left}'
                })
        
        record_failed_attempt(device_id)
        return jsonify({'success': False, 'error': 'مفتاح الترخيص غير صالح'})
        
    except Exception as e:
        print(f"❌ خطأ في activate: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check', methods=['POST'])
def check():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        
        if not license_key:
            return jsonify({'success': False, 'status': 'invalid', 'error': 'لا يوجد مفتاح'})
        
        if is_device_locked(device_id):
            return jsonify({'success': False, 'status': 'locked', 'error': 'الجهاز مقفل مؤقتاً'})
        
        licenses = load_licenses()
        
        for dev_id, info in licenses.items():
            if info.get('license_key') == license_key:
                if dev_id != device_id:
                    record_failed_attempt(device_id)
                    return jsonify({'success': False, 'status': 'invalid', 'error': 'جهاز غير مصرح'})
                
                if info.get('type') == 'trial':
                    expiry_date = info.get('expiry_date')
                    if expiry_date:
                        server_time = get_server_time()
                        expiry = datetime.fromisoformat(expiry_date)
                        if server_time > expiry:
                            return jsonify({'success': False, 'status': 'expired', 'error': 'انتهت التجربة'})
                
                reset_failed_attempts(device_id)
                return jsonify({'success': True, 'status': 'active'})
        
        record_failed_attempt(device_id)
        return jsonify({'success': False, 'status': 'invalid', 'error': 'مفتاح غير صالح'})
        
    except Exception as e:
        return jsonify({'success': False, 'status': 'error', 'error': str(e)})

# ============================================
# API لإدارة التراخيص (للمطور)
# ============================================

@app.route('/api/admin/create-license', methods=['POST'])
def admin_create_license():
    try:
        data = request.get_json()
        admin_secret = data.get('admin_secret')
        
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح'})
        
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        expiry_date_str = data.get('expiry_date')
        license_type = data.get('type', 'paid')
        
        if not license_key or not device_id:
            return jsonify({'success': False, 'error': 'بيانات ناقصة'})
        
        # التحقق من صحة expiry_date
        if expiry_date_str:
            expiry_date = datetime.fromisoformat(expiry_date_str)
        else:
            if license_type == 'paid':
                expiry_date = get_server_time() + timedelta(days=30)
            else:
                expiry_date = get_server_time() + timedelta(hours=24)
        
        licenses = load_licenses()
        licenses[device_id] = {
            "license_key": license_key,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "status": "active",
            "type": license_type
        }
        save_licenses(licenses)
        
        if license_type == 'paid':
            save_paid_device(device_id)
        
        days_left = (expiry_date - get_server_time()).days if license_type == 'paid' else 1
        print(f"✅ تم إنشاء ترخيص {license_type} للجهاز {device_id[:20]}... ينتهي في {expiry_date.strftime('%Y-%m-%d')}")
        
        return jsonify({
            'success': True,
            'message': f'تم إنشاء الترخيص ({license_type})',
            'expiry_date': expiry_date.isoformat(),
            'days_left': max(0, days_left)
        })
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الترخيص: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/licenses', methods=['GET'])
def admin_get_licenses():
    try:
        admin_secret = request.headers.get('X-Admin-Secret')
        
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح'})
        
        licenses = load_licenses()
        server_time = get_server_time()
        
        result = {}
        for device_id, info in licenses.items():
            result[device_id] = {
                **info,
                "remaining_days": max(0, (datetime.fromisoformat(info['expiry_date']) - server_time).days) if info.get('expiry_date') else None
            }
        
        return jsonify({'success': True, 'licenses': result, 'count': len(result)})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/extend-license', methods=['POST'])
def admin_extend_license():
    try:
        data = request.get_json()
        admin_secret = data.get('admin_secret')
        
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح'})
        
        device_id = data.get('device_id')
        extra_days = data.get('extra_days', 30)
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        licenses = load_licenses()
        
        if device_id not in licenses:
            return jsonify({'success': False, 'error': 'الجهاز غير مسجل'})
        
        current_expiry = licenses[device_id].get('expiry_date')
        server_time = get_server_time()
        
        if current_expiry:
            new_expiry = datetime.fromisoformat(current_expiry) + timedelta(days=extra_days)
        else:
            new_expiry = server_time + timedelta(days=extra_days)
        
        licenses[device_id]['expiry_date'] = new_expiry.isoformat()
        licenses[device_id]['status'] = 'active'
        save_licenses(licenses)
        
        print(f"✅ تم تمديد ترخيص الجهاز {device_id[:20]}... بـ {extra_days} يوماً")
        
        return jsonify({
            'success': True,
            'message': f'تم تمديد الترخيص {extra_days} يوماً',
            'new_expiry_date': new_expiry.isoformat(),
            'new_remaining_days': max(0, (new_expiry - server_time).days)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# API للمدفوعات
# ============================================

@app.route('/api/submit_payment', methods=['POST'])
def submit_payment():
    try:
        device_id = request.form.get('device_id')
        ref_number = request.form.get('ref_number')
        
        if not device_id or not ref_number:
            return jsonify({'success': False, 'error': 'بيانات ناقصة'})
        
        if 'receipt' not in request.files:
            return jsonify({'success': False, 'error': 'لم يتم رفع إيصال'})
        
        file = request.files['receipt']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'لم يتم اختيار ملف'})
        
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{ref_number}.{ext}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
        else:
            return jsonify({'success': False, 'error': 'نوع الملف غير مدعوم'})
        
        pending = []
        if os.path.exists(PENDING_PAYMENTS_FILE):
            with open(PENDING_PAYMENTS_FILE, 'r') as f:
                pending = json.load(f)
        
        pending.append({
            "device_id": device_id,
            "ref_number": ref_number,
            "receipt_path": filepath,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "type": "bank"
        })
        
        with open(PENDING_PAYMENTS_FILE, 'w') as f:
            json.dump(pending, f, indent=2)
        
        print(f"📩 طلب دفع بنكي جديد من جهاز {device_id[:30]}... رقم العملية: {ref_number}")
        
        return jsonify({'success': True, 'message': 'تم استلام طلب الدفع، سيتم تفعيل البرنامج بعد التحقق خلال 24 ساعة'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/submit_crypto_payment', methods=['POST'])
def submit_crypto_payment():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        transaction_hash = data.get('transaction_hash')
        
        if not device_id or not transaction_hash:
            return jsonify({'success': False, 'error': 'بيانات ناقصة'})
        
        if not transaction_hash.startswith('0x') or len(transaction_hash) != 66:
            return jsonify({'success': False, 'error': 'صيغة هاش المعاملة غير صالحة'})
        
        pending = []
        if os.path.exists(PENDING_PAYMENTS_FILE):
            with open(PENDING_PAYMENTS_FILE, 'r') as f:
                pending = json.load(f)
        
        pending.append({
            "device_id": device_id,
            "transaction_hash": transaction_hash,
            "amount": 20,
            "currency": CRYPTO_CURRENCY,
            "network": CRYPTO_NETWORK,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "type": "crypto"
        })
        
        with open(PENDING_PAYMENTS_FILE, 'w') as f:
            json.dump(pending, f, indent=2)
        
        print(f"💸 طلب دفع بالعملة الرقمية من جهاز {device_id[:30]}... الهاش: {transaction_hash[:20]}...")
        
        return jsonify({'success': True, 'message': 'تم استلام طلب الدفع، سيتم تفعيل البرنامج بعد التحقق من المعاملة'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# لوحة تحكم الدفع
# ============================================

@app.route('/admin/payments', methods=['GET'])
def admin_payments():
    pending = []
    if os.path.exists(PENDING_PAYMENTS_FILE):
        with open(PENDING_PAYMENTS_FILE, 'r') as f:
            pending = json.load(f)
    
    html = '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>لوحة تحكم الدفع - SatelliteChecking1</title>
        <style>
            body { font-family: Arial; background: #0f172a; color: white; padding: 20px; }
            table { width: 100%; border-collapse: collapse; background: #1e293b; }
            th, td { border: 1px solid #38bdf8; padding: 10px; text-align: center; }
            th { background: #facc15; color: #0f172a; }
            .approve-btn { background: #34d399; color: #0f172a; padding: 5px 10px; border: none; cursor: pointer; border-radius: 5px; }
            .approve-btn:hover { background: #10b981; }
            .receipt-link { color: #38bdf8; text-decoration: none; }
            .status-pending { color: #facc15; }
            .status-approved { color: #34d399; }
        </style>
    </head>
    <body>
        <h1>📋 طلبات الدفع</h1>
        <p>⚠️ تأكد من صحة الدفع ثم اضغط "تفعيل الترخيص"</p>
        <table>
            <tr>
                <th>رقم العملية / الهاش</th>
                <th>معرف الجهاز</th>
                <th>التاريخ</th>
                <th>نوع الدفع</th>
                <th>الإيصال</th>
                <th>الحالة</th>
                <th>إجراء</th>
            </tr>
    '''
    
    for p in pending:
        status_class = "status-approved" if p['status'] == 'approved' else "status-pending"
        display_id = p.get('ref_number', p.get('transaction_hash', 'N/A'))[:30]
        payment_type = "🏦 بنكي" if p.get('type') == 'bank' else "💸 عملة رقمية"
        
        receipt_link = ''
        if p.get('type') == 'bank' and p.get('receipt_path'):
            receipt_link = f"<a href='/admin/receipt/{p['receipt_path']}' class='receipt-link' target='_blank'>عرض الإيصال</a>"
        else:
            receipt_link = p.get('transaction_hash', 'N/A')[:20] + '...'
        
        html += f'''
             <tr>
                 <td>{display_id}</td>
                 <td>{p['device_id'][:30]}...</td>
                 <td>{p['timestamp'][:19]}</td>
                 <td>{payment_type}</td>
                 <td>{receipt_link}</td>
                 <td class="{status_class}">{p['status']}</td>
                 <td>
        '''
        if p['status'] != 'approved':
            html += f'<button class="approve-btn" onclick=\'approve("{p["device_id"]}")\'>تفعيل الترخيص</button>'
        else:
            html += 'تم التفعيل'
        html += '</td></tr>'
    
    html += '''
           </table>
        <script>
        function approve(deviceId) {
            if(confirm('هل تريد تفعيل الترخيص لهذا الجهاز؟')) {
                fetch('/admin/approve', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({device_id: deviceId})
                }).then(r => r.json()).then(data => {
                    if(data.success) alert('✅ تم تفعيل الترخيص!');
                    else alert('❌ فشل: ' + data.error);
                    location.reload();
                });
            }
        }
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/admin/receipt/<path:filepath>')
def admin_receipt(filepath):
    return send_file(filepath)

@app.route('/admin/approve', methods=['POST'])
def approve_payment():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        save_paid_device(device_id)
        
        pending = []
        if os.path.exists(PENDING_PAYMENTS_FILE):
            with open(PENDING_PAYMENTS_FILE, 'r') as f:
                pending = json.load(f)
        
        updated = []
        for p in pending:
            if p['device_id'] == device_id:
                p['status'] = 'approved'
            updated.append(p)
        
        with open(PENDING_PAYMENTS_FILE, 'w') as f:
            json.dump(updated, f, indent=2)
        
        licenses = load_licenses()
        if device_id in licenses and licenses[device_id].get('type') == 'trial':
            del licenses[device_id]
        
        license_key = generate_license_key()
        expiry_date = get_server_time() + timedelta(days=30)
        licenses[device_id] = {
            "license_key": license_key,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "status": "active",
            "type": "paid"
        }
        save_licenses(licenses)
        
        print(f"✅ تم تفعيل الترخيص المدفوع للجهاز {device_id[:20]}... (30 يوم)")
        
        return jsonify({'success': True, 'license_key': license_key, 'expiry_days': 30})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# الصفحة الرئيسية
# ============================================

@app.route('/')
def home():
    return jsonify({
        'service': 'SatelliteChecking1 API',
        'status': 'online',
        'version': '5.0',
        'endpoints': [
            '/buy',
            '/free-trial',
            '/api/activate',
            '/api/check',
            '/api/get-license',
            '/api/start-free-trial',
            '/api/submit_payment',
            '/api/submit_crypto_payment',
            '/api/health',
            '/admin/payments',
            '/api/admin/create-license',
            '/api/admin/licenses',
            '/api/admin/extend-license'
        ],
        'crypto_wallet': CRYPTO_WALLET_ADDRESS
    })

# ============================================
# تشغيل السيرفر
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 تشغيل سيرفر SatelliteChecking1 API v5.0")
    print("💰 الاشتراك الشهري: 20 دولار")
    print("🎁 تجربة مجانية: 24 ساعة (يوم واحد)")
    print("💸 الدفع بالعملة الرقمية: USDT (ERC20)")
    print(f"   عنوان المحفظة: {CRYPTO_WALLET_ADDRESS}")
    print("📡 API متاحة:")
    print("   POST /api/activate")
    print("   POST /api/check")
    print("   POST /api/get-license")
    print("   POST /api/start-free-trial")
    print("   POST /api/submit_payment (بنكي)")
    print("   POST /api/submit_crypto_payment (رقمي)")
    print("   GET  /api/health")
    print("🏦 نظام الدفع: تحويل بنكي + عملات رقمية")
    print("🔧 لوحة التحكم: /admin/payments")
    print("🔐 API المطور:")
    print("   POST /api/admin/create-license (إنشاء ترخيص)")
    print("   GET  /api/admin/licenses (عرض التراخيص)")
    print("   POST /api/admin/extend-license (تمديد ترخيص)")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)