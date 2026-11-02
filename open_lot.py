import requests, re, subprocess

API = "https://plati.io/api/search.ashx"
params = {"query": "Steam Turkey 10 USD", "pagesize": 50, "pagenum": 1, "response": "json"}
r = requests.get(API, params=params, timeout=20)
items = r.json().get("items", [])

candidates = []
for item in items:
    name = item.get("name_eng", "").lower() + " " + item.get("name", "").lower()
    price = item.get("price_usd")
    if not price: continue
    m = re.search(r"(\d+)", name)
    if not m: continue
    if int(m.group(1)) == 10:
        translit = item.get("name_translit_eng") or item.get("name_translit")
        if translit:
            candidates.append({
                "price": float(price), 
                "url": f"https://plati.market/itm/{translit}", 
                "seller": item.get("seller_name", ""),
                "name": item.get("name", "")[:60]
            })

if candidates:
    candidates.sort(key=lambda x: x["price"])
    best = candidates[0]
    print(f"🏆 Лучший лот: {best['seller']} за ${best['price']:.2f}")
    print(f"📦 Название: {best['name']}")
    print(f"🔗 Ссылка: {best['url']}")
    print(f"📊 Профит (CardBix 90%): +${9.00 - best['price']:.2f} ({(9.00 - best['price'])/best['price']*100:.1f}%)")
    print()
    print("🌐 Открываю в браузере...")
    subprocess.run(["termux-open-url", best["url"]])
else:
    print("❌ Активных лотов на 10 USD Turkey не найдено.")
