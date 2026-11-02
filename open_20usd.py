import requests, re, subprocess

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
TARGET = 20  # Ищем карту на 20 USD

params = {
    "query": f"Steam Turkey {TARGET} USD",
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
    url = item.get("url")
    if not price or not url: continue

    m = re.search(r'(\d+)', name)
    if not m: continue
    first_num = int(m.group(1))

    # Ищем лоты, где 20 USD — минимальный номинал
    if first_num != TARGET: continue
    if price < TARGET * 0.5: continue

    candidates.append({
        "price": float(price),
        "seller": item.get("seller_name", ""),
        "url": url,
        "name": item.get("name", "")[:60]
    })

if candidates:
    candidates.sort(key=lambda x: x["price"])
    best = candidates[0]
    sell_price = TARGET * 0.90  # CardBix 90%
    profit = sell_price - best["price"]
    profit_pct = (profit / best["price"] * 100) if best["price"] > 0 else 0

    print(f"\n🏆 ЛУЧШИЙ ЛОТ НА {TARGET} USD (в наличии):")
    print(f"   Продавец:  {best['seller']}")
    print(f"   Цена:      ${best['price']:.2f} (~{best['price']*90:.0f}₽)")
    print(f"   Ссылка:    {best['url']}")
    print(f"\n📊 Расчёт связки:")
    print(f"   Купить:   ${best['price']:.2f}")
    print(f"   Сдать:    ${sell_price:.2f} (CardBix 90%)")
    print(f"   Профит:   +${profit:.2f} ({profit_pct:+.1f}%)")
    print("\n🌐 Открываю в браузере...")
    subprocess.run(["termux-open-url", best["url"]])
else:
    print(f"❌ Нет лотов на {TARGET} USD. Попробуй 50 USD или подожди.")
