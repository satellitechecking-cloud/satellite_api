from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import uuid
import hashlib
import time

app = Flask(__name__)
CORS(app)

SECRET_KEY = "SUPER_SECRET_KEY_2024"
ADMIN_SECRET = "SATELLITE_SECRET_KEY_2024"

def init_db():
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_key TEXT UNIQUE NOT NULL,
        plan TEXT DEFAULT 'pro',
        device_id TEXT,
        max_devices INTEGER DEFAULT 1,
        expiry_date TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        activated_at TEXT
    )''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

def generate_license():
    return f"SAT-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"

def hash_device(device_id):
    return hashlib.sha256(device_id.encode()).hexdigest()

def generate_signature(status, license_key, device_id):
    data = f"{status}{license_key}{device_id}{SECRET_KEY}"
    return hashlib.sha256(data.encode()).hexdigest()

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'service': 'SatelliteChecking1 API',
        'version': '2.0',
        'secure': True
    })

@app.route('/api/check', methods=['POST'])
def check_license():
    try:
        data = request.get_json()
        license_key = data.get('license_key', '').upper().strip()
        device_id = hash_device(data.get('device_id', ''))
        timestamp = data.get('timestamp', 0)
        
        current_time = int(time.time())
        if abs(current_time - timestamp) > 60:
            return jsonify({'success': False, 'status': 'error', 'error': 'طلب منتهي الصلاحية'})
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        c.execute("SELECT * FROM licenses WHERE license_key = ? AND device_id = ?", 
                  (license_key, device_id))
        license_data = c.fetchone()
        
        if not license_data:
            conn.close()
            return jsonify({'success': False, 'status': 'invalid', 'error': 'ترخيص غير صالح'})
        
        expiry_date = license_data[5]
        is_active = license_data[6]
        
        if not is_active:
            conn.close()
            return jsonify({'success': False, 'status': 'inactive', 'error': 'الترخيص غير نشط'})
        
        if expiry_date:
            expiry = datetime.datetime.fromisoformat(expiry_date)
            if expiry < datetime.datetime.now():
                c.execute("UPDATE licenses SET is_active = 0 WHERE license_key = ?", (license_key,))
                conn.commit()
                conn.close()
                return jsonify({'success': False, 'status': 'expired', 'error': 'انتهت صلاحية الترخيص'})
        
        conn.close()
        
        return jsonify({
            'success': True,
            'status': 'active',
            'license_key': license_key,
            'device_id': device_id,
            'expiry_date': expiry_date,
            'plan': license_data[2],
            'signature': generate_signature('active', license_key, device_id)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'status': 'error', 'error': str(e)})

@app.route('/api/activate', methods=['POST'])
def activate():
    try:
        data = request.get_json()
        license_key = data.get('license_key', '').upper().strip()
        device_id = hash_device(data.get('device_id', ''))
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        c.execute("SELECT * FROM licenses WHERE license_key = ?", (license_key,))
        license_data = c.fetchone()
        
        if not license_data:
            conn.close()
            return jsonify({'success': False, 'error': 'كود التفعيل غير صالح'})
        
        if license_data[3] and license_data[3] != device_id:
            conn.close()
            return jsonify({'success': False, 'error': 'هذا الكود مستخدم على جهاز آخر'})
        
        expiry_date = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
        
        c.execute("""UPDATE licenses 
                     SET device_id = ?, expiry_date = ?, activated_at = ? 
                     WHERE license_key = ?""",
                  (device_id, expiry_date, datetime.datetime.now().isoformat(), license_key))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'status': 'active',
            'plan': license_data[2],
            'expiry_date': expiry_date,
            'signature': generate_signature('active', license_key, device_id)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/create_license', methods=['POST'])
def create_license():
    try:
        data = request.get_json()
        secret = data.get('secret', '')
        
        if secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'غير مصرح'})
        
        license_key = generate_license()
        created_at = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        c.execute("""INSERT INTO licenses (license_key, plan, max_devices, is_active, created_at) 
                     VALUES (?, 'pro', 1, 1, ?)""",
                  (license_key, created_at))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'license_key': license_key})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)