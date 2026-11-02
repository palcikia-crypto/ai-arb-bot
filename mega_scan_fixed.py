import requests, re, json

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

CATEGORIES = [
    ("Steam Turkey 10",     "Steam Turkey 10 USD",     10,  0.85),
    ("Nintendo 10",         "Nintendo eShop 10 USD",   10,  0.85),
    ("Nintendo 20",         "Nintendo eShop 20 USD",   20,  0.85),
    ("V-Bucks 1000",        "V-Bucks 1000 Fortnite",   1000, 0.60),
]

def fetch_plati(query):
    params = {"query": query, "pagesize": 50, "pagenum": 1,
              "visibleOnly": "true", "response": "json"}
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        return r.json().get("items", [])
    except: return []

def find_exact_lot(items, target):
    """Ищет лоты с ТОЧНЫМ совпадением 'target USD' или 'target$' в названии."""
    candidates = []
    for item in items:
        name = (item.get("name_eng","") + " " + item.get("name","")).lower()
        price = item.get("price_usd")
        url = item.get("url")
        if not price or not url: continue
        
        # Строгая проверка: '10 usd' или '10$' или '10 $'
        pattern = rf'\b{target}\s*(?:usd|\$)'
        if not re.search(pattern, name):
            continue
        
        # Дополнительная защита: если в названии есть диапазон (5-10), пропускаем
        if re.search(rf'\d+\s*-\s*{target}', name) or re.search(rf'{target}\s*-\s*\d+', name):
            continue
        
        if price < target * 0.3: continue
        
        candidates.append({
            "price": float(price),
            "seller": item.get("seller_name", ""),
            "url": url,
            "name": item.get("name", "")[:60],
        })
    candidates.sort(key=lambda x: x["price"])
    return candidates

for name, query, target, rate in CATEGORIES:
    print(f"\n📦 [{name}]")
    items = fetch_plati(query)
    lots = find_exact_lot(items, target)
    if not lots:
        print(f"  ❌ Нет точных лотов на {target} USD")
        continue
    
    best = lots[0]
    sell = target * rate
    profit = sell - best["price"]
    pct = (profit / best["price"] * 100) if best["price"] > 0 else 0
    marker = "✅" if profit > 0 else "❌"
    
    print(f"  {marker} {best['seller']} — ${best['price']:.2f}")
    print(f"     Профит (при {rate*100:.0f}%): ${profit:+.2f} ({pct:+.1f}%)")
    print(f"     {best['name']}")
    print(f"     {best['url']}")
