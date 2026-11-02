import requests, re

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

CATEGORIES = [
    ("Steam Turkey 10",   "Steam Turkey 10 USD",      10,   0.85, 5, 10),
    ("Nintendo 10",       "Nintendo eShop 10 USD",    10,   0.85, 7, 10),
    ("Nintendo 20",       "Nintendo eShop 20 USD",    20,   0.85, 14, 20),
    ("V-Bucks 1000",      "V-Bucks 1000 Fortnite",    1000, 0.60, 4, 8),
    ("Xbox USA 10",       "Xbox USA 10 USD",          10,   0.85, 7, 10),
]

def fetch_plati(query):
    params = {"query": query, "pagesize": 50, "pagenum": 1,
              "visibleOnly": "true", "response": "json"}
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        return r.json().get("items", [])
    except: return []

def find_sane_lot(items, target, price_min, price_max):
    """Ищет лот, где target в названии И цена в разумных пределах."""
    candidates = []
    for item in items:
        name = (item.get("name_eng","") + " " + item.get("name","")).lower()
        price = item.get("price_usd")
        url = item.get("url")
        if not price or not url: continue
        
        # Убираем мусор
        name_clean = re.sub(r'\[\s*-?\d+%?\s*\]', '', name)
        name_clean = re.sub(r'-\d+%', '', name_clean)
        
        # Ищем target в названии (как отдельное число)
        if not re.search(rf'\b{target}\b', name_clean):
            continue
        
        # ЦЕНА в разумных пределах
        if not (price_min <= price <= price_max):
            print(f"  ⚠️ Отброшен: {name[:50]} | ${price:.2f} (цена не в {price_min}-{price_max})")
            continue
        
        candidates.append({
            "price": float(price),
            "seller": item.get("seller_name", ""),
            "url": url,
            "name": item.get("name", "")[:60],
        })
    candidates.sort(key=lambda x: x["price"])
    return candidates

for name, query, target, rate, pmin, pmax in CATEGORIES:
    print(f"\n📦 [{name}]")
    items = fetch_plati(query)
    if not items:
        print(f"  ❌ пусто")
        continue
    
    lots = find_sane_lot(items, target, pmin, pmax)
    if not lots:
        print(f"  ❌ нет лотов с target={target} и ценой {pmin}-{pmax}")
        continue
    
    best = lots[0]
    usd_value = target if target < 100 else target * 0.01
    sell = usd_value * rate
    profit = sell - best["price"]
    pct = (profit / best["price"] * 100) if best["price"] > 0 else 0
    marker = "✅" if profit > 0 else "❌"
    print(f"  {marker} {best['seller']} — ${best['price']:.2f} → {profit:+.2f} ({pct:+.1f}%)")
    print(f"     {best['name']}")
    print(f"     {best['url']}")
