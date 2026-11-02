import requests

TOKEN = "cfat_W6Hnr0wDz0rrypFhtQ2UbwLq9xSThsA5HXNN1GPrcbebf6bd"
ACCOUNT_ID = "a914f12cfed55cd028f76ed14fd6f789"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Проверка токена
print("=== 1. ПРОВЕРКА ТОКЕНА ===")
r = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=headers)
print(f"HTTP статус: {r.status_code}")
if r.json().get("success"):
    print("✅ Токен рабочий! (status: active)")
else:
    print(f"❌ Ошибка токена: {r.json().get('errors')}")
    exit()

# 2. Проверка R2 (Облачное хранилище)
print("\n=== 2. ДОСТУП К R2 ===")
url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/r2/buckets"
r = requests.get(url, headers=headers)
print(f"HTTP статус: {r.status_code}")
if r.json().get("success"):
    buckets = r.json().get("result", {}).get("buckets", [])
    print(f"✅ Доступ к R2 есть! Созданных бакетов (папок): {len(buckets)}")
    for b in buckets:
        print(f"  - {b['name']}")
    print("\n👉 Термукс официально подключен к твоему Cloudflare!")
else:
    print(f"⚠️ Ошибка R2: {r.json().get('errors')}")

