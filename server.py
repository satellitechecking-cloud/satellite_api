from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# 🔐 بيانات PayPal الخاصة بك (Live)
# ============================================
PAYPAL_CLIENT_ID = "ATl4-CsC8WLf0yZQw3Hcoiwe9VZ4N2abU8gDET-GGk7CEqIElUECTSbD_Y3EYTcymEey7wvustobI753"
PAYPAL_SECRET = "EN7-2GQ-nWQakjxaWhQqjjooUKcHkSm1Bsu_edITFCsTmNnuKd0SORavMqEe4VNZ7j_aaHgmLo8xaFoS"
PAYPAL_PLAN_ID = "P-60A89529UF070594ENHTVAIY"
PAYPAL_API_BASE = "https://api-m.paypal.com"  # Live

# ============================================
# ملف حفظ التراخيص
# ============================================
LICENSES_FILE = "licenses.json"

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

def generate_license_key():
    """توليد مفتاح ترخيص فريد بصيغة XXXX-XXXX-XXXX-XXXX"""
    import random
    import string
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

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
            .container {{ max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; box-shadow: 0 0 20px rgba(56,189,248,0.2); }}
            h1 {{ color: #facc15; margin-bottom: 10px; }}
            .price {{ font-size: 48px; color: #38bdf8; margin: 20px 0; font-weight: bold; }}
            .features {{ text-align: right; margin: 30px 0; color: #cbd5e1; }}
            .features li {{ margin: 10px 0; }}
            .note {{ font-size: 12px; color: #94a3b8; margin-top: 20px; }}
            .btn-back {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #38bdf8; color: #0f172a; text-decoration: none; border-radius: 8px; }}
        </style>
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
            <a href="/" class="btn-back">🏠 العودة للرئيسية</a>
        </div>
        
        <script>
            paypal.Buttons({{
                style: {{
                    shape: 'rect',
                    color: 'gold',
                    layout: 'vertical',
                    label: 'subscribe'
                }},
                createSubscription: function(data, actions) {{
                    return actions.subscription.create({{
                        plan_id: '{PAYPAL_PLAN_ID}'
                    }});
                }},
                onApprove: function(data, actions) {{
                    window.location.href = '/payment-success?subscription_id=' + data.subscriptionID;
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
# 2. صفحة نجاح الدفع
# ============================================
@app.route('/payment-success', methods=['GET'])
def payment_success():
    subscription_id = request.args.get('subscription_id')
    
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
            .btn-back {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #38bdf8; color: #0f172a; text-decoration: none; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✅</div>
            <h1>تم الدفع بنجاح!</h1>
            <p>تم تفعيل اشتراكك الشهري في SatelliteChecking1</p>
            <p>📧 تم إرسال إيصال الدفع إلى بريدك الإلكتروني</p>
            <p>🔓 الآن ارجع إلى البرنامج واضغط <strong>"تحقق من الدفع"</strong></p>
            <hr style="margin: 20px 0; border-color: #38bdf8;">
            <p style="font-size: 12px; color: #94a3b8;">Subscription ID: {subscription_id}</p>
            <a href="/buy" class="btn-back">🔄 العودة للاشتراك</a>
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
            .btn-back { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #38bdf8; color: #0f172a; text-decoration: none; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ تم إلغاء الدفع</h1>
            <p>لم يتم خصم أي مبلغ من حسابك.</p>
            <p>يمكنك العودة إلى البرنامج والمحاولة مرة أخرى.</p>
            <a href="/buy" class="btn-back">💰 العودة لصفحة الدفع</a>
        </div>
    </body>
    </html>
    '''

# ============================================
# 4. الصفحة الرئيسية
# ============================================
@app.route('/', methods=['GET'])
def home():
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>SatelliteChecking1 API</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; }
            .container { max-width: 600px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }
            h1 { color: #38bdf8; }
            .endpoint { background: #0f172a; padding: 10px; border-radius: 8px; margin: 10px 0; font-family: monospace; }
            .btn { display: inline-block; margin-top: 20px; padding: 12px 30px; background: #facc15; color: #0f172a; text-decoration: none; border-radius: 8px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ SatelliteChecking1 API</h1>
            <p>الخدمة تعمل بشكل طبيعي ✅</p>
            <div class="endpoint">POST /api/activate - تفعيل الترخيص</div>
            <div class="endpoint">POST /api/check - التحقق من الترخيص</div>
            <div class="endpoint">POST /api/get-license - جلب ترخيص جديد</div>
            <div class="endpoint">GET /buy - صفحة الدفع</div>
            <a href="/buy" class="btn">💰 شراء اشتراك</a>
        </div>
    </body>
    </html>
    '''

# ============================================
# 5. API لجلب الترخيص (يستخدمه برنامج العميل)
# ============================================
@app.route('/api/get-license', methods=['POST'])
def get_license():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        # توليد ترخيص جديد
        license_key = generate_license_key()
        
        # حفظ الترخيص
        licenses = load_licenses()
        licenses[device_id] = {
            "license_key": license_key,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        save_licenses(licenses)
        
        return jsonify({
            'success': True,
            'license_key': license_key
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 6. API للتحقق من صحة الترخيص
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
                return jsonify({
                    'success': True,
                    'status': 'active',
                    'message': 'تم التفعيل بنجاح'
                })
        
        return jsonify({
            'success': False,
            'error': 'ترخيص غير صالح أو منتهي الصلاحية'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 7. API للتحقق من حالة الترخيص
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
                return jsonify({
                    'success': True,
                    'status': 'active',
                    'message': 'الترخيص صالح'
                })
        
        return jsonify({
            'success': False,
            'status': 'invalid',
            'error': 'ترخيص غير صالح'
        })
        
    except Exception as e:
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
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# تشغيل السيرفر
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل سيرفر SatelliteChecking1...")
    print(f"📍 http://localhost:5000")
    print(f"📡 الرابط العام: https://satellite-api-mnfw.onrender.com")
    print(f"💰 صفحة الدفع: /buy")
    print(f"📡 API: /api/activate, /api/check, /api/get-license")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)