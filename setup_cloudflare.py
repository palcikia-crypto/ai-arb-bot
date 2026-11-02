import requests
import json
import getpass

print("=" * 50)
print("  НАСТРОЙКА CLOUDFLARE В TERMUX")
print("=" * 50)

# 1. Безопасный ввод токена (он не будет отображаться на экране)
token = getpass.getpass("Вставь сюда свой API-токен (он скроется): ").strip()
account_id = "a914f12cfed55cd028f76ed14fd6f789" # Из твоего скриншота

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. Проверка токена
print("\n⏳ Проверяю токен...")
r = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=headers)

if not r.json().get("success"):
    print(f"❌ Ошибка: Токен невалиден. Возможно, скопировал криво.")
    print(f"Детали: {r.json().get('errors')}")
    exit()

print("✅ Токен рабочий!")

# 3. Проверка и создание R2 бакета
print("\n⏳ Проверяю доступ к облаку R2...")
bucket_name = "ai-arb-backup"
url_list = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/buckets"
r_list = requests.get(url_list, headers=headers)

if not r_list.json().get("success"):
    print(f"❌ Ошибка доступа к R2: {r_list.json().get('errors')}")
    print("Возможно, у токена нет прав на R2.")
    exit()

buckets = [b['name'] for b in r_list.json().get("result", {}).get("buckets", [])]
print(f"✅ Доступ к R2 есть. Найдено бакетов: {len(buckets)}")

if bucket_name not in buckets:
    print(f"⏳ Создаю бакет (папку) '{bucket_name}'...")
    r_create = requests.post(url_list, headers=headers, json={"name": bucket_name})
    if r_create.json().get("success"):
        print(f"✅ Бакет '{bucket_name}' успешно создан!")
    else:
        print(f"❌ Ошибка создания: {r_create.json().get('errors')}")
else:
    print(f"✅ Бакет '{bucket_name}' уже существует!")

print("\n" + "=" * 50)
print("  🎉 ГОТОВО! CLOUDFLARE ПОДКЛЮЧЕН К TERMUX")
print("=" * 50)
