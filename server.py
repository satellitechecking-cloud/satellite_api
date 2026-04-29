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
# 🔐 بيانات PayPal الجديدة
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
# دوال مساعدة للتخزين
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
    """التحقق إذا كان الجهاز استخدم التجربة المجانية من قبل"""
    trials = load_trials()
    if device_id in trials:
        expiry = datetime.fromisoformat(trials[device_id]['expiry'])
        if expiry > datetime.now():
            return True, trials[device_id]['expiry']
        else:
            # انتهت صلاحية التجربة، نعتبر أنه استخدمها من قبل
            return True, None
    return False, None

def start_free_trial(device_id, email):
    """بدء تجربة مجانية لمدة 24 ساعة"""
    trials = load_trials()
    
    # حساب وقت انتهاء التجربة (بعد 24 ساعة)
    expiry = datetime.now() + timedelta(hours=24)
    
    trials[device_id] = {
        'email': email,
        'started': datetime.now().isoformat(),
        'expiry': expiry.isoformat(),
        'used': True
    }
    
    save_trials(trials)
    
    # إنشاء ترخيص مؤقت
    license_key = generate_trial_license(device_id, expiry)
    
    return license_key, expiry

def generate_trial_license(device_id, expiry_date):
    """توليد كود ترخيص تجريبي"""
    raw = f"TRIAL_{device_id}_{expiry_date.strftime('%Y%m%d%H%M')}"
    return base64.b64encode(raw.encode()).decode()[:20]

def generate_license_key():
    """توليد مفتاح ترخيص فريد"""
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def create_license_for_device(device_id, license_key=None):
    """إنشاء ترخيص لجهاز معين"""
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
# 1. صفحة الدفع الرئيسية
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
            .features {{ text-align: right; margin: 30px 0; }}
            .note {{ font-size: 12px; color: #94a3b8; margin-top: 20px; }}
            .trial-btn {{ background: #34d399; color: #0f172a; padding: 12px 25px; border-radius: 10px; text-decoration: none; display: inline-block; margin-top: 20px; font-weight: bold; }}
            #paypal-button-container {{ margin: 30px 0; }}
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
            <p>نظام كشف الفراغات والمعادن والذهب عبر الأقمار الصناعية</p>
            <div class="price">$20 <span style="font-size:18px">/ شهرياً</span></div>
            <ul class="features">
                <li>✅ تحليلات غير محدودة</li>
                <li>✅ دقة عالية (حتى 10 متر)</li>
                <li>✅ تقارير شاملة (PDF, KML, JSON)</li>
                <li>✅ دعم فني 24/7</li>
            </ul>
            <div id="paypal-button-container"></div>
            <div class="note">🔒 دفع آمن عبر PayPal | يتم التجديد تلقائياً شهرياً</div>
            <hr>
            <a href="/free-trial" class="trial-btn">🎁 جرب مجاناً لمدة 24 ساعة</a>
        </div>
        
        <script>
            var deviceId = localStorage.getItem('satellite_device_id');
            
            paypal.Buttons({{
                style: {{
                    shape: 'rect',
                    color: 'gold',
                    layout: 'vertical',
                    label: 'subscribe'
                }},
                createSubscription: function(data, actions) {{
                    return actions.subscription.create({{
                        plan_id: '{PAYPAL_PLAN_ID}',
                        custom_id: deviceId
                    }});
                }},
                onApprove: function(data, actions) {{
                    window.location.href = '/payment-success?subscription_id=' + data.subscriptionID + '&device_id=' + deviceId;
                }},
                onError: function(err) {{
                    console.error(err);
                    alert('حدث خطأ في الدفع. يرجى المحاولة مرة أخرى.');
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
        <title>SatelliteChecking1 - تجربة مجانية 24 ساعة</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; direction: rtl; }
            .container { max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }
            input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 8px; border: none; background: #334155; color: white; }
            button { background: #34d399; color: #0f172a; padding: 12px 30px; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 16px; }
            .trial-info { color: #facc15; margin: 20px 0; }
            .back-link { color: #38bdf8; text-decoration: none; display: inline-block; margin-top: 20px; }
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
            <h1>🛰️ SatelliteChecking1</h1>
            <h2>🎁 تجربة مجانية 24 ساعة</h2>
            <p class="trial-info">❗ تجربة واحدة لكل جهاز (24 ساعة)</p>
            <input type="text" id="device_id" placeholder="معرف الجهاز (device_id)">
            <input type="email" id="email" placeholder="بريدك الإلكتروني">
            <button onclick="startTrial()">🚀 ابدأ التجربة المجانية</button>
            <div id="result" style="margin-top: 20px;"></div>
            <hr>
            <a href="/buy" class="back-link">💰 العودة لصفحة الاشتراك الشهري</a>
        </div>
        
        <script>
            var storedId = localStorage.getItem('satellite_device_id');
            if(storedId) {
                document.getElementById('device_id').value = storedId;
            }
            
            function startTrial() {
                var device_id = document.getElementById('device_id').value.trim();
                var email = document.getElementById('email').value.trim();
                
                if(!device_id) {
                    alert('الرجاء إدخال معرف الجهاز');
                    return;
                }
                
                if(!email) {
                    alert('الرجاء إدخال البريد الإلكتروني');
                    return;
                }
                
                fetch('/api/start-free-trial', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ device_id: device_id, email: email })
                })
                .then(res => res.json())
                .then(data => {
                    if(data.success) {
                        document.getElementById('result').innerHTML = `
                            <div style="background:#34d399; padding:15px; border-radius:10px;">
                                ✅ <strong>تم تفعيل التجربة المجانية!</strong><br>
                                🔑 كود التفعيل: <strong style="font-size:18px;">${data.license_key}</strong><br>
                                ⏰ تنتهي التجربة بعد 24 ساعة (${data.expiry})<br>
                                📧 تم إرسال الكود إلى بريدك الإلكتروني
                            </div>
                        `;
                        localStorage.setItem('satellite_license', data.license_key);
                    } else {
                        document.getElementById('result').innerHTML = `
                            <div style="background:#ef4444; padding:15px; border-radius:10px;">
                                ❌ ${data.error}
                            </div>
                        `;
                    }
                })
                .catch(err => {
                    document.getElementById('result').innerHTML = `
                        <div style="background:#ef4444; padding:15px; border-radius:10px;">
                            ❌ خطأ في الاتصال بالخادم
                        </div>
                    `;
                });
            }
        </script>
    </body>
    </html>
    '''

# ============================================
# 3. API لبدء التجربة المجانية
# ============================================
@app.route('/api/start-free-trial', methods=['POST'])
def start_free_trial_api():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        email = data.get('email')
        
        if not device_id or not email:
            return jsonify({'success': False, 'error': 'الرجاء إدخال جميع البيانات'})
        
        # التحقق إذا كان الجهاز استخدم التجربة من قبل
        has_trial, expiry = has_free_trial(device_id)
        
        if has_trial:
            if expiry:
                return jsonify({
                    'success': False, 
                    'error': f'لقد استخدمت التجربة المجانية مسبقاً (تنتهي في {expiry})'
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': 'لقد استخدمت التجربة المجانية مسبقاً ولم يتبقى لك وقت'
                })
        
        # بدء تجربة جديدة
        license_key, expiry_date = start_free_trial(device_id, email)
        
        # حفظ الترخيص التجريبي في ملف التراخيص
        licenses = load_licenses()
        licenses[device_id] = {
            "license_key": license_key,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "status": "trial",
            "email": email
        }
        save_licenses(licenses)
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'expiry': expiry_date.strftime('%Y-%m-%d %H:%M:%S'),
            'message': 'تم تفعيل التجربة المجانية لمدة 24 ساعة'
        })
        
    except Exception as e:
        print(f"❌ خطأ في API التجربة: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 4. صفحة نجاح الدفع
# ============================================
@app.route('/payment-success', methods=['GET'])
def payment_success():
    subscription_id = request.args.get('subscription_id')
    device_id = request.args.get('device_id')
    
    if not device_id:
        return "❌ خطأ: لا يوجد device_id"
    
    # تسجيل الجهاز كمدفوع
    save_paid_device(device_id)
    print(f"✅ تم تسجيل جهاز {device_id[:30]}... كمدفوع")
    
    # توليد ترخيص تلقائي للجهاز فوراً بعد الدفع
    license_key = create_license_for_device(device_id)
    print(f"✅ تم توليد ترخيص تلقائي: {license_key}")
    
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تم الدفع بنجاح - SatelliteChecking1</title>
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; }}
            .container {{ max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }}
            h1 {{ color: #34d399; }}
            .checkmark {{ font-size: 80px; }}
            .license-code {{ background: #0f172a; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 18px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✅</div>
            <h1>تم الدفع بنجاح!</h1>
            <p>تم تفعيل اشتراكك الشهري في SatelliteChecking1</p>
            <div class="license-code">
                🔑 كود التفعيل الخاص بك:<br>
                <strong style="color: #facc15;">{license_key}</strong>
            </div>
            <p>🔓 يمكنك الآن العودة إلى البرنامج واستخدام هذا الكود</p>
            <hr>
            <p style="font-size: 12px; color: #94a3b8;">Subscription ID: {subscription_id}</p>
        </div>
    </body>
    </html>
    '''

# ============================================
# 5. صفحة إلغاء الدفع
# ============================================
@app.route('/payment-cancel', methods=['GET'])
def payment_cancel():
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تم الإلغاء - SatelliteChecking1</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; }
            .container { max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }
            h1 { color: #facc15; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ تم إلغاء الدفع</h1>
            <p>لم يتم خصم أي مبلغ من حسابك.</p>
            <a href="/buy" style="color:#38bdf8;">💰 العودة لصفحة الدفع</a>
        </div>
    </body>
    </html>
    '''

# ============================================
# 6. API لجلب الترخيص
# ============================================
@app.route('/api/get-license', methods=['POST'])
def get_license():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        # التحقق من وجود ترخيص مدفوع
        if is_device_paid(device_id):
            licenses = load_licenses()
            if device_id in licenses and licenses[device_id].get('status') == 'active':
                return jsonify({'success': True, 'license_key': licenses[device_id]['license_key']})
        
        # التحقق من وجود ترخيص تجريبي
        licenses = load_licenses()
        if device_id in licenses:
            license_data = licenses[device_id]
            if license_data.get('status') == 'trial':
                expiry = datetime.fromisoformat(license_data.get('expiry_date', '2000-01-01'))
                if expiry > datetime.now():
                    return jsonify({'success': True, 'license_key': license_data['license_key']})
        
        return jsonify({'success': False, 'error': 'لا يوجد ترخيص نشط لهذا الجهاز'})
        
    except Exception as e:
        print(f"❌ خطأ في get_license: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 7. API للتحقق من صحة الترخيص
# ============================================
@app.route('/api/activate', methods=['POST'])
def activate():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        
        licenses = load_licenses()
        
        # البحث عن الترخيص
        for dev_id, info in licenses.items():
            if info.get('license_key') == license_key:
                if info.get('status') in ['active', 'trial']:
                    # التحقق من صلاحية الترخيص التجريبي
                    if info.get('status') == 'trial' and info.get('expiry_date'):
                        expiry = datetime.fromisoformat(info['expiry_date'])
                        if expiry < datetime.now():
                            return jsonify({'success': False, 'error': 'انتهت صلاحية الترخيص التجريبي'})
                    return jsonify({'success': True, 'status': info.get('status')})
        
        return jsonify({'success': False, 'error': 'ترخيص غير صالح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 8. API للتحقق من حالة الترخيص
# ============================================
@app.route('/api/check', methods=['POST'])
def check():
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
                            return jsonify({'success': False, 'status': 'expired'})
                    return jsonify({'success': True, 'status': 'active'})
        
        return jsonify({'success': False, 'status': 'invalid'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 9. API لتوليد مفتاح يدوي (للمطور فقط)
# ============================================
@app.route('/api/admin/generate-key', methods=['POST'])
def admin_generate_key():
    try:
        data = request.get_json()
        admin_secret = data.get('admin_secret')
        device_id = data.get('device_id')
        
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح به'})
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        if not is_device_paid(device_id):
            save_paid_device(device_id)
            print(f"✅ تم تسجيل الجهاز {device_id[:30]}... كمدفوع (يدوي)")
        
        license_key = create_license_for_device(device_id)
        
        return jsonify({
            'success': True, 
            'license_key': license_key,
            'device_id': device_id,
            'message': 'تم توليد المفتاح بنجاح'
        })
        
    except Exception as e:
        print(f"❌ خطأ في admin_generate_key: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 10. API للتحقق من صحة السيرفر
# ============================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'success': True,
        'status': 'healthy',
        'secure': True,
        'service': 'SatelliteChecking1 API',
        'version': '4.0',
        'features': ['paypal', 'free_trial'],
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# تشغيل السيرفر
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل سيرفر SatelliteChecking1...")
    print("💰 صفحة الدفع: /buy")
    print("🎁 صفحة التجربة المجانية: /free-trial")
    print("📡 API: /api/activate, /api/check, /api/get-license")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)