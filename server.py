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
    """توليد مفتاح ترخيص فريد بصيغة XXXX-XXXX-XXXX-XXXX"""
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================
# 1. صفحة الدفع الرئيسية (معلومات الحساب البنكي - 30 دولار)
# ============================================
@app.route('/buy', methods=['GET'])
def buy_page():
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>SatelliteChecking1 - اشتراك شهري</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white; }
            .container { max-width: 500px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; }
            h1 { color: #facc15; }
            .price { font-size: 48px; color: #38bdf8; margin: 20px 0; }
            .bank-info { background: #0f172a; padding: 15px; border-radius: 10px; margin: 20px 0; text-align: right; direction: ltr; }
            .note { font-size: 12px; color: #94a3b8; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ SatelliteChecking1</h1>
            <p>نظام كشف الفراغات والمعادن والذهب عبر الأقمار الصناعية</p>
            <div class="price">$30 <span style="font-size:18px">/ شهرياً</span></div>
            <div class="bank-info">
                <strong>🏦 بيانات الحساب البنكي:</strong><br>
                البنك: البنك الإسلامي الفلسطيني<br>
                اسم المستفيد: هيثم غازي محمد بزراوي<br>
                رقم IBAN: PS30PIBC084216100580033101000
            </div>
            <p>⚠️ بعد التحويل، يرجى العودة إلى البرنامج وإرسال إشعار الدفع مع رقم العملية وصورة الإيصال</p>
            <div class="note">🔒 سيتم تفعيل اشتراكك خلال 24 ساعة من استلام إشعار الدفع</div>
        </div>
    </body>
    </html>
    '''

# ============================================
# 2. استقبال إشعار الدفع (رفع الإيصال ورقم العملية)
# ============================================
@app.route('/api/submit_payment', methods=['POST'])
def submit_payment():
    try:
        device_id = request.form.get('device_id')
        ref_number = request.form.get('ref_number')
        
        if not device_id or not ref_number:
            return jsonify({'success': False, 'error': 'بيانات ناقصة'})
        
        # التحقق من وجود ملف الإيصال
        if 'receipt' not in request.files:
            return jsonify({'success': False, 'error': 'لم يتم رفع إيصال'})
        
        file = request.files['receipt']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'لم يتم اختيار ملف'})
        
        # حفظ الإيصال
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{ref_number}.{ext}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
        else:
            return jsonify({'success': False, 'error': 'نوع الملف غير مدعوم (يدعم: png, jpg, jpeg, gif, bmp, pdf)'})
        
        # حفظ الطلب في قائمة الانتظار
        pending = []
        if os.path.exists(PENDING_PAYMENTS_FILE):
            with open(PENDING_PAYMENTS_FILE, 'r') as f:
                pending = json.load(f)
        
        pending.append({
            "device_id": device_id,
            "ref_number": ref_number,
            "receipt_path": filepath,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        })
        
        with open(PENDING_PAYMENTS_FILE, 'w') as f:
            json.dump(pending, f, indent=2)
        
        print(f"📩 طلب دفع جديد من جهاز {device_id[:30]}... رقم العملية: {ref_number}")
        
        return jsonify({'success': True, 'message': 'تم استلام طلب الدفع، سيتم تفعيل البرنامج بعد التحقق خلال 24 ساعة'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 3. API لجلب الترخيص (للأجهزة المدفوعة أو التجربة المجانية)
# ============================================
@app.route('/api/get-license', methods=['POST'])
def get_license():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        # 1. هل هذا الجهاز دفع؟
        if is_device_paid(device_id):
            license_key = generate_license_key()
            licenses = load_licenses()
            # حذف أي ترخيص قديم
            if device_id in licenses:
                del licenses[device_id]
            licenses[device_id] = {
                "license_key": license_key,
                "device_id": device_id,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "type": "paid"
            }
            save_licenses(licenses)
            print(f"✅ تم إصدار ترخيص مدفوع للجهاز {device_id[:30]}...")
            return jsonify({'success': True, 'license_key': license_key, 'type': 'paid'})
        
        # 2. هل استخدم هذا الجهاز النسخة التجريبية من قبل؟
        if has_used_trial(device_id):
            return jsonify({'success': False, 'error': 'انتهت النسخة التجريبية. يرجى شراء اشتراك', 'trial_expired': True})
        
        # 3. لم يدفع ولم يستخدم التجربة - نعطيه تجربة مجانية
        save_trial_used(device_id)
        trial_license = "TRIAL_" + datetime.now().strftime('%Y%m%d')
        
        licenses = load_licenses()
        if device_id in licenses:
            del licenses[device_id]
        licenses[device_id] = {
            "license_key": trial_license,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "status": "trial",
            "type": "trial",
            "expires_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        save_licenses(licenses)
        
        print(f"🎁 تم إصدار ترخيص تجريبي للجهاز {device_id[:30]}...")
        return jsonify({'success': True, 'license_key': trial_license, 'type': 'trial', 'trial_days': 1})
        
    except Exception as e:
        print(f"❌ خطأ في get_license: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 4. API للتحقق من صحة الترخيص
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
                # التحقق من صلاحية الترخيص التجريبي
                if info.get('type') == 'trial':
                    expires_at = info.get('expires_at')
                    if expires_at:
                        expiry_date = datetime.fromisoformat(expires_at)
                        if datetime.now() > expiry_date:
                            return jsonify({'success': False, 'error': 'انتهت صلاحية النسخة التجريبية'})
                
                if info.get('status') == 'active' or info.get('type') == 'trial':
                    return jsonify({'success': True, 'status': 'active', 'type': info.get('type', 'paid')})
        
        return jsonify({'success': False, 'error': 'ترخيص غير صالح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 5. API للتحقق من حالة الترخيص
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
                if info.get('type') == 'trial':
                    expires_at = info.get('expires_at')
                    if expires_at:
                        expiry_date = datetime.fromisoformat(expires_at)
                        if datetime.now() > expiry_date:
                            return jsonify({'success': False, 'status': 'expired', 'error': 'انتهت التجربة'})
                
                return jsonify({'success': True, 'status': 'active', 'type': info.get('type', 'paid')})
        
        return jsonify({'success': False, 'status': 'invalid'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 6. API للتجربة المجانية (مرة واحدة لكل جهاز)
# ============================================
@app.route('/api/request_free_trial', methods=['POST'])
def request_free_trial():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id مطلوب'})
        
        if has_used_trial(device_id):
            return jsonify({'success': False, 'error': 'لقد استخدمت النسخة التجريبية مسبقاً'})
        
        save_trial_used(device_id)
        trial_license = "TRIAL_" + datetime.now().strftime('%Y%m%d')
        
        licenses = load_licenses()
        if device_id in licenses:
            del licenses[device_id]
        licenses[device_id] = {
            "license_key": trial_license,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "status": "trial",
            "type": "trial",
            "expires_at": (datetime.now() + timedelta(days=1)).isoformat()
        }
        save_licenses(licenses)
        
        return jsonify({'success': True, 'license_key': trial_license, 'message': 'تم تفعيل النسخة التجريبية لمدة 24 ساعة'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 7. لوحة تحكم بسيطة لعرض طلبات الدفع وتفعيلها يدوياً
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
        <h1>📋 طلبات الدفع البنكي</h1>
        <p>⚠️ تأكد من صحة الدفع ثم اضغط "تفعيل الترخيص"</p>
         <table>
             <tr>
                 <th>رقم العملية</th>
                 <th>معرف الجهاز</th>
                 <th>التاريخ</th>
                 <th>الإيصال</th>
                 <th>الحالة</th>
                 <th>إجراء</th>
             </tr>
    '''
    
    for p in pending:
        status_class = "status-approved" if p['status'] == 'approved' else "status-pending"
        html += f'''
             <tr>
                 <td>{p['ref_number']}</td>
                 <td>{p['device_id'][:30]}...</td>
                 <td>{p['timestamp'][:19]}</td>
                 <td><a href='/admin/receipt/{p['receipt_path']}' class='receipt-link' target='_blank'>عرض الإيصال</a></td>
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
        
        # تسجيل الجهاز كمدفوع
        save_paid_device(device_id)
        
        # تحديث حالة الطلب
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
        
        # حذف الترخيص التجريبي القديم إن وجد
        licenses = load_licenses()
        if device_id in licenses:
            del licenses[device_id]
        
        # إصدار ترخيص جديد مدفوع
        license_key = generate_license_key()
        licenses[device_id] = {
            "license_key": license_key,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "type": "paid"
        }
        save_licenses(licenses)
        
        print(f"✅ تم تفعيل الترخيص للجهاز {device_id[:20]}...")
        return jsonify({'success': True, 'license_key': license_key})
        
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
        'service': 'SatelliteChecking1 Bank Transfer API',
        'version': '2.0',
        'price': '30 USD',
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# تشغيل السيرفر
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل سيرفر SatelliteChecking1 (نظام بنكي)")
    print("💰 الاشتراك الشهري: 30 دولار")
    print("📡 API: /api/activate, /api/check, /api/get-license, /api/request_free_trial")
    print("🏦 نظام الدفع: تحويل بنكي + إشعار يدوي")
    print("🔧 لوحة التحكم: /admin/payments")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)