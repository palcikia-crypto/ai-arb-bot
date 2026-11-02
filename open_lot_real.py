import requests, re, subprocess

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
TARGET_NOMINAL = 10

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
    url = item.get("url")  # <-- БЕРЁМ ГОТОВЫЙ URL ИЗ API
    if not price or not url: continue

    m = re.search(r'(\d+)', name)
    if not m: continue
    if int(m.group(1)) != TARGET_NOMINAL: continue
    if price < TARGET_NOMINAL * 0.5: continue

    candidates.append({
        "price": float(price),
        "seller": item.get("seller_name", ""),
        "url": url,  # уже прямой URL
        "name": item.get("name", "")[:60]
    })

if candidates:
    candidates.sort(key=lambda x: x["price"])
    best = candidates[0]
    sell_price = TARGET_NOMINAL * 0.90
    profit = sell_price - best["price"]
    profit_pct = (profit / best["price"] * 100) if best["price"] > 0 else 0

    print(f"\n🏆 ЛУЧШИЙ ЛОТ НА {TARGET_NOMINAL} USD (в наличии):")
    print(f"   Продавец:  {best['seller']}")
    print(f"   Цена:      ${best['price']:.2f}")
    print(f"   Ссылка:    {best['url']}")
    print(f"\n📊 Профит (CardBix 90%): +${profit:.2f} ({profit_pct:+.1f}%)")
    print("\n🌐 Открываю в браузере...")
    subprocess.run(["termux-open-url", best["url"]])
else:
    print("❌ Нет доступных лотов, где 10 USD — минимальный номинал. Попробуйте позже.")
