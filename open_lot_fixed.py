import requests, re, subprocess

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
TARGET_NOMINAL = 10  # Ищем карту на 10 USD

params = {
    "query": f"Steam Turkey {TARGET_NOMINAL} USD",
    "pagesize": 50,
    "pagenum": 1,
    "visibleOnly": "true",
    "response": "json"
}

r = requests.get(API, params=params, headers=HEADERS, timeout=20)
items = r.json().get("items", [])

candidates = []
for item in items:
    name = item.get("name_eng", "").lower() + " " + item.get("name", "").lower()
    price = item.get("price_usd")
    if not price: continue
    
    # 1. Извлекаем ПЕРВОЕ число из названия
    m = re.search(r'(\d+)', name)
    if not m: continue
    first_num = int(m.group(1))
    
    # 2. Главный фильтр: первое число должно быть равно целевому номиналу (10)
    if first_num != TARGET_NOMINAL:
        continue
    
    # 3. Дополнительный фильтр: отбрасываем подозрительно дешёвые лоты
    #    (цена не может быть меньше 50% от номинала)
    if price < TARGET_NOMINAL * 0.5:
        print(f"⚠️ Отброшен подозрительно дешёвый лот: ${price:.2f} у {item.get('seller_name', '')}")
        continue
    
    translit = item.get("name_translit_eng") or item.get("name_translit")
    if translit:
        candidates.append({
            "price": float(price),
            "seller": item.get("seller_name", ""),
            "url": f"https://plati.market/itm/{translit}",
            "name": item.get("name", "")[:60]
        })

if candidates:
    candidates.sort(key=lambda x: x["price"])
    best = candidates[0]
    sell_price = TARGET_NOMINAL * 0.90  # CardBix 90%
    profit = sell_price - best["price"]
    profit_pct = (profit / best["price"] * 100) if best["price"] > 0 else 0

    print(f"\n🏆 ЛУЧШИЙ ЛОТ НА {TARGET_NOMINAL} USD (в наличии):")
    print(f"   Продавец:  {best['seller']}")
    print(f"   Цена:      ${best['price']:.2f}")
    print(f"   Название:  {best['name']}")
    print(f"   Ссылка:    {best['url']}")
    print(f"\n📊 Профит (CardBix 90%): +${profit:.2f} ({profit_pct:+.1f}%)")
    print("\n🌐 Открываю в браузере...")
    subprocess.run(["termux-open-url", best["url"]])
else:
    print(f"❌ Не найдено доступных лотов, где {TARGET_NOMINAL} USD — минимальный номинал.")
