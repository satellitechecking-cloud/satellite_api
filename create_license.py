import requests

API_URL = "https://satellite-api.onrender.com/api"

def create_license():
    response = requests.post(f"{API_URL}/create_license", json={
        'secret': 'SATELLITE_SECRET_KEY_2024'
    })
    result = response.json()
    if result.get('success'):
        print(f"✅ كود الترخيص: {result['license_key']}")
    else:
        print(f"❌ خطأ: {result.get('error')}")

if __name__ == '__main__':
    create_license()