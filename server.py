from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import random
import string
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# 🔐 بيانات PayPal الخاصة بك (Live)
# ============================================
PAYPAL_CLIENT_ID = "ATl4-CsC8WLf0yZQw3Hcoiwe9VZ4N2abU8gDET-GGk7CEqIElUECTSbD_Y3EYTcymEey7wvustobI753"
PAYPAL_SECRET = "EN7-2GQ-nWQakjxaWhQqjjooUKcHkSm1Bsu_edITFCsTmNnuKd0SORavMqEe4VNZ7j_aaHgmLo8xaFoS"
PAYPAL_PLAN_ID = "P-60A89529UF070594ENHTVAIY"

# ============================================
# ملفات التخزين
# ============================================
LICENSES_FILE = "licenses.json"
PAID_DEVICES_FILE = "paid_devices.json"

# ============================================
# كلمة سر لتوليد المفاتيح يدوياً (غيرها بما يناسبك)
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
    """التحقق: هل هذا الجهاز دفع فعلاً؟"""
    return device_id in load_paid_devices()

def generate_license_key():
    """توليد مفتاح ترخيص فريد بصيغة XXXX-XXXX-XXXX-XXXX"""
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def create_license_for_device(device_id, license_key=None):
    """إنشاء ترخيص لجهاز معين (داخلي)"""
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
            <div class="price">$100 <span style="font-size:18px">/ شهرياً</span></div>
            <ul class="features">
                <li>✅ تحليلات غير محدودة</li>
                <li>✅ دقة عالية (حتى 10 متر)</li>
                <li>✅ تقارير شاملة (PDF, KML, JSON)</li>
                <li>✅ دعم فني 24/7</li>
            </ul>
            <div id="paypal-button-container"></div>
            <div class="note">🔒 دفع آمن عبر PayPal | يتم التجديد تلقائياً شهرياً</div>
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
# 2. صفحة نجاح الدفع (تسجيل الجهاز كمدفوع + توليد ترخيص تلقائي)
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
    
    # 🔥 توليد ترخيص تلقائي للجهاز فوراً بعد الدفع
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
# 3. صفحة إلغاء الدفع
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
# 4. API لجلب الترخيص (فقط للأجهزة المدفوعة)
# ============================================
@app.route('/api/get-license', methods=['POST'])
def get_license():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        # 🔴 شرط واحد فقط: هل هذا الجهاز دفع؟
        if not is_device_paid(device_id):
            return jsonify({'success': False, 'error': 'لم يتم الدفع من هذا الجهاز. يرجى شراء اشتراك أولاً'})
        
        # التحقق: هل يوجد ترخيص لهذا الجهاز بالفعل؟
        licenses = load_licenses()
        if device_id in licenses and licenses[device_id].get('status') == 'active':
            license_key = licenses[device_id]['license_key']
            print(f"✅ إعادة إرسال الترخيص الموجود للجهاز {device_id[:30]}...")
        else:
            # الجهاز دفع لكن ليس لديه ترخيص - ننشئ له ترخيص جديد
            license_key = create_license_for_device(device_id)
            print(f"✅ تم إنشاء ترخيص جديد للجهاز المدفوع {device_id[:30]}...")
        
        return jsonify({'success': True, 'license_key': license_key})
        
    except Exception as e:
        print(f"❌ خطأ في get_license: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 5. API للتحقق من صحة الترخيص
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
            if info.get('license_key') == license_key and info.get('status') == 'active':
                return jsonify({'success': True, 'status': 'active'})
        
        return jsonify({'success': False, 'error': 'ترخيص غير صالح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 6. API للتحقق من حالة الترخيص
# ============================================
@app.route('/api/check', methods=['POST'])
def check():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        
        licenses = load_licenses()
        
        for dev_id, info in licenses.items():
            if info.get('license_key') == license_key and info.get('status') == 'active':
                return jsonify({'success': True, 'status': 'active'})
        
        return jsonify({'success': False, 'status': 'invalid'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 7. API لتوليد مفتاح يدوي (للمطور فقط)
# ============================================
@app.route('/api/admin/generate-key', methods=['POST'])
def admin_generate_key():
    try:
        data = request.get_json()
        admin_secret = data.get('admin_secret')
        device_id = data.get('device_id')
        
        # التحقق من كلمة السر
        if admin_secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح به'})
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        # تسجيل الجهاز كمدفوع (إذا لم يكن مسجلاً)
        if not is_device_paid(device_id):
            save_paid_device(device_id)
            print(f"✅ تم تسجيل الجهاز {device_id[:30]}... كمدفوع (يدوي)")
        
        # إنشاء ترخيص جديد للجهاز
        license_key = create_license_for_device(device_id)
        
        print(f"✅ تم توليد مفتاح يدوي للجهاز {device_id[:30]}...: {license_key}")
        
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
# 8. API للتحقق من صحة السيرفر
# ============================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'success': True,
        'status': 'healthy',
        'secure': True,
        'service': 'SatelliteChecking1 API',
        'version': '3.0',
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# تشغيل السيرفر
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل سيرفر SatelliteChecking1...")
    print("💰 صفحة الدفع: /buy")
    print("📡 API: /api/activate, /api/check, /api/get-license")
    print("🔐 Admin API: /api/admin/generate-key (للتوليد اليدوي)")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)