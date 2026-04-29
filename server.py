from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import random
import string
from datetime import datetime, timedelta
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
BACKUP_LICENSES_FILE = "licenses_backup.json"

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
        # أيضا حفظ نسخة احتياطية
        save_backup_licenses(licenses)
        return True
    except:
        return False

def save_backup_licenses(licenses):
    """حفظ نسخة احتياطية من التراخيص"""
    try:
        with open(BACKUP_LICENSES_FILE, 'w') as f:
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
            # انتهت التجربة، نزيلها
            del trials[device_id]
            save_trials(trials)
            return False, None
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
        "status": "active",
        "type": "trial",
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

def create_license_for_device(device_id, license_key=None, expiry_days=30):
    if license_key is None:
        license_key = generate_license_key()
    
    expiry_date = datetime.now() + timedelta(days=expiry_days)
    
    licenses = load_licenses()
    licenses[device_id] = {
        "license_key": license_key,
        "device_id": device_id,
        "created_at": datetime.now().isoformat(),
        "expiry_date": expiry_date.isoformat(),
        "status": "active",
        "type": "paid"
    }
    save_licenses(licenses)
    return license_key

def check_license_validity(license_key, device_id):
    """التحقق من صحة الترخيص - نفس ما يتوقعه ملف التحليل"""
    licenses = load_licenses()
    
    for dev_id, info in licenses.items():
        if info.get('license_key') == license_key:
            # التحقق من تطابق الجهاز
            if dev_id != device_id:
                return False, "هذا المفتاح غير صالح لهذا الجهاز"
            
            # التحقق من الحالة
            if info.get('status') != 'active':
                return False, "الترخيص غير نشط"
            
            # التحقق من صلاحية التاريخ
            expiry_date = info.get('expiry_date')
            if expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date)
                    if expiry < datetime.now():
                        return False, "انتهت صلاحية الترخيص"
                except:
                    pass
            
            # حساب الأيام المتبقية
            if expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date)
                    days_left = (expiry - datetime.now()).days
                    return True, f"ترخيص صالح لمدة {days_left} يوم"
                except:
                    return True, "ترخيص صالح"
            
            return True, "ترخيص صالح"
    
    return False, "مفتاح غير موجود"

# ============================================
# 1. الصفحة الرئيسية
# ============================================
@app.route('/', methods=['GET'])
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
            '/api/health'
        ]
    })

# ============================================
# 2. صفحة الدفع
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
            .btn-primary {{ background: #38bdf8; color: #0f172a; padding: 12px 25px; border-radius: 10px; text-decoration: none; display: inline-block; margin-top: 10px; }}
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
            <p>✅ تحليلات غير محدودة</p>
            <p>✅ دقة عالية في الكشف</p>
            <p>✅ دعم فني على مدار الساعة</p>
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
# 3. صفحة نجاح الدفع
# ============================================
@app.route('/payment-success', methods=['GET'])
def payment_success():
    device_id = request.args.get('device_id')
    subscription_id = request.args.get('subscription_id')
    
    if device_id:
        save_paid_device(device_id)
        license_key = create_license_for_device(device_id, expiry_days=30)
        return f'''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head><meta charset="UTF-8"><title>تم الدفع بنجاح</title>
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; }}
            .container {{ max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }}
            .key {{ background: #334155; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 18px; margin: 20px 0; }}
        </style>
        </head>
        <body>
        <div class="container">
            <h1>✅ تم الدفع بنجاح!</h1>
            <p>🔑 كود التفعيل الخاص بك:</p>
            <div class="key">{license_key}</div>
            <p>📅 صلاحية الترخيص: 30 يوماً</p>
            <a href="/free-trial" style="color:#38bdf8;">🏠 العودة</a>
        </div>
        </body>
        </html>
        '''
    return '<h1>❌ خطأ في الدفع</h1><a href="/buy">المحاولة مرة أخرى</a>'

# ============================================
# 4. صفحة التجربة المجانية
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
            
            function startTrial() {
                var device_id = document.getElementById('device_id').value;
                var email = document.getElementById('email').value;
                
                if(!email) {
                    document.getElementById('result').innerHTML = '<div class="result error">❌ الرجاء إدخال البريد الإلكتروني</div>';
                    return;
                }
                
                document.getElementById('result').innerHTML = '<div class="result">🔄 جاري التفعيل...</div>';
                
                fetch('/api/start-free-trial', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({device_id: device_id, email: email})
                })
                .then(res => res.json())
                .then(data => {
                    if(data.success) {
                        document.getElementById('result').innerHTML = '<div class="result success">✅ تم التفعيل بنجاح!<br>🔑 كود التفعيل: <strong>' + data.license_key + '</strong><br>📅 ينتهي في: ' + new Date(data.expiry).toLocaleString('ar') + '</div>';
                        localStorage.setItem('satellite_license', data.license_key);
                    } else {
                        document.getElementById('result').innerHTML = '<div class="result error">❌ ' + data.error + '</div>';
                    }
                })
                .catch(error => {
                    document.getElementById('result').innerHTML = '<div class="result error">❌ خطأ في الاتصال: ' + error.message + '</div>';
                });
            }
        </script>
    </body>
    </html>
    '''

# ============================================
# 5. API تفعيل الترخيص (نقطة النهاية التي يستخدمها ملف التحليل)
# ============================================
@app.route('/api/activate', methods=['POST'])
def activate():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        
        if not license_key or not device_id:
            return jsonify({'success': False, 'error': 'البيانات غير مكتملة'})
        
        success, message = check_license_validity(license_key, device_id)
        
        if success:
            return jsonify({
                'success': True,
                'status': 'active',
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 6. API التحقق من الترخيص
# ============================================
@app.route('/api/check', methods=['POST'])
def check():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        
        if not license_key or not device_id:
            return jsonify({'success': False, 'error': 'البيانات غير مكتملة'})
        
        success, message = check_license_validity(license_key, device_id)
        
        if success:
            return jsonify({
                'success': True,
                'status': 'active',
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'status': 'invalid',
                'error': message
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 7. API جلب الترخيص (للمستخدمين الذين دفعوا)
# ============================================
@app.route('/api/get-license', methods=['POST'])
def get_license():
    """
    جلب الترخيص من السيرفر - فقط إذا كان الجهاز مدفوعاً
    هذه النقطة يستخدمها ملف التحليل في fetch_license_from_server
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        # التحقق مما إذا كان الجهاز مدفوعاً
        if is_device_paid(device_id):
            licenses = load_licenses()
            if device_id in licenses:
                return jsonify({
                    'success': True,
                    'license_key': licenses[device_id]['license_key'],
                    'message': 'تم استرداد الترخيص بنجاح'
                })
            else:
                # إنشاء ترخيص جديد للجهاز المدفوع
                license_key = create_license_for_device(device_id, expiry_days=30)
                return jsonify({
                    'success': True,
                    'license_key': license_key,
                    'message': 'تم إنشاء ترخيص جديد للجهاز المدفوع'
                })
        
        # التحقق من التجربة المجانية
        has_trial, expiry = has_free_trial(device_id)
        if has_trial and expiry:
            licenses = load_licenses()
            if device_id in licenses:
                return jsonify({
                    'success': True,
                    'license_key': licenses[device_id]['license_key'],
                    'message': 'ترخيص تجريبي نشط',
                    'trial': True,
                    'expiry': expiry
                })
        
        return jsonify({
            'success': False,
            'error': 'لم يتم الدفع أو تفعيل التجربة لهذا الجهاز'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 8. API بدء التجربة المجانية
# ============================================
@app.route('/api/start-free-trial', methods=['POST'])
def start_free_trial_api():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        email = data.get('email')
        
        if not device_id or not email:
            return jsonify({'success': False, 'error': 'جميع الحقول مطلوبة'})
        
        # التحقق من عدم استخدام التجربة مسبقاً
        has_trial, _ = has_free_trial(device_id)
        if has_trial:
            return jsonify({'success': False, 'error': 'لقد استخدمت التجربة المجانية مسبقاً'})
        
        # بدء التجربة
        license_key, expiry_date = start_free_trial(device_id, email)
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'expiry': expiry_date.isoformat(),
            'message': 'تم تفعيل التجربة المجانية بنجاح لمدة 24 ساعة'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 9. API التحقق من الصحة
# ============================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'success': True,
        'status': 'healthy',
        'version': '5.0',
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# 10. API إدارة (للمطور) - توليد مفتاح يدوي
# ============================================
@app.route('/api/admin/generate-key', methods=['POST'])
def admin_generate_key():
    try:
        data = request.get_json()
        admin_secret = data.get('admin_secret')
        device_id = data.get('device_id')
        days = data.get('days', 30)
        
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح'})
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        license_key = create_license_for_device(device_id, expiry_days=days)
        return jsonify({
            'success': True,
            'license_key': license_key,
            'device_id': device_id,
            'expiry_days': days
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 11. API قائمة التراخيص (للمطور)
# ============================================
@app.route('/api/admin/licenses', methods=['GET'])
def admin_list_licenses():
    try:
        admin_secret = request.headers.get('X-Admin-Secret')
        
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح'})
        
        licenses = load_licenses()
        return jsonify({
            'success': True,
            'licenses': licenses,
            'count': len(licenses)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# تشغيل السيرفر
# ============================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 تشغيل سيرفر SatelliteChecking1 API v5.0")
    print("=" * 60)
    print(f"📁 ملف التراخيص: {LICENSES_FILE}")
    print(f"📁 ملف النسخة الاحتياطية: {BACKUP_LICENSES_FILE}")
    print(f"📁 ملف الأجهزة المدفوعة: {PAID_DEVICES_FILE}")
    print(f"📁 ملف التجارب: {TRIALS_FILE}")
    print("=" * 60)
    print("🌐 نقاط النهاية المتاحة:")
    print("   GET  /                    - الصفحة الرئيسية")
    print("   GET  /buy                 - صفحة الدفع")
    print("   GET  /free-trial          - صفحة التجربة المجانية")
    print("   GET  /payment-success     - صفحة نجاح الدفع")
    print("   POST /api/activate        - تفعيل الترخيص")
    print("   POST /api/check           - التحقق من الترخيص")
    print("   POST /api/get-license     - جلب الترخيص")
    print("   POST /api/start-free-trial- بدء التجربة المجانية")
    print("   GET  /api/health          - التحقق من صحة السيرفر")
    print("=" * 60)
    print("✅ السيرفر جاهز للعمل على http://0.0.0.0:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)