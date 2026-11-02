import requests, re

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

# (Название, Запрос, Номинал в USD для расчета)
CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10),
    ("Steam Global 20", "Steam Global 20 USD", 20),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20),
    ("Xbox USA 10", "Xbox USA 10 USD", 10),
    ("V-Bucks 1000", "V-Bucks 1000 Fortnite", 10), # 1000 V-Bucks ~ $10
]

# РЕАЛЬНЫЕ СКУПЩИКИ (ставки, которые платят СРАЗУ)
BUYERS = {
    "CardBix": {"Global": 0.85, "US": 0.85, "Turkey": 0.0},
    "GiftCardIo": {"Global": 0.86, "US": 0.86, "Turkey": 0.45},
}

def fetch_plati(query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        return r.json().get("items", [])
    except: return []

def process_lot(item, target_usd):
    name = item.get("name", "")
    price = item.get("price_usd")
    url = item.get("url")
    seller = item.get("seller_name", "Unknown")
    
    if not price or not url: return None
    
    # Ищем все числа в названии
    numbers = re.findall(r'\b(\d+)\b', name)
    if not numbers: return None
    
    # Определяем регион по названию
    name_lower = name.lower()
    if "турция" in name_lower or " tr " in name_lower: region = "Turkey"
    elif "global" in name_lower or "весь мир" in name_lower or "world" in name_lower: region = "Global"
    elif "usa" in name_lower or " us " in name_lower or "сша" in name_lower: region = "US"
    else: region = "UNKNOWN"
    
    # Проверка на скам (Турция + весь мир)
    is_scam = (region == "Turkey" and ("global" in name_lower or "весь мир" in name_lower))
    
    results = []
    for buyer, rates in BUYERS.items():
        rate = rates.get(region, 0)
        if rate == 0: continue
        
        sell_price = target_usd * rate
        profit = sell_price - float(price)
        pct = (profit / float(price) * 100) if float(price) > 0 else 0
        
        results.append({
            "buyer": buyer,
            "rate": rate,
            "sell_price": sell_price,
            "profit": profit,
            "pct": pct,
            "is_scam": is_scam
        })
        
    return {
        "name": name[:60],
        "price": float(price),
        "url": url,
        "seller": seller,
        "region": region,
        "results": results
    }

print("=" * 80)
print("  🔧 ПОЛНЫЙ СКАН PLATI API (БЕЗ ФИЛЬТРОВ)")
print("=" * 80)

for cat_name, query, target_usd in CATEGORIES:
    print(f"\n📦 [{cat_name}] (Номинал: ${target_usd})")
    items = fetch_plati(query)
    
    if not items:
        print("  ❌ API вернул 0")
        continue
        
    found_any = False
    for item in items:
        lot = process_lot(item, target_usd)
        if not lot: continue
        
        # Выводим только если есть совпадение по номиналу (хотя бы одно число)
        # Для V-Bucks 1000 ищем "1000"
        if str(target_usd) not in lot["name"] and target_usd != 10: continue 
        
        found_any = True
        print(f"\n  📌 {lot['name']}")
        print(f"     Продавец: {lot['seller']} | Цена: ${lot['price']:.2f} | Регион: {lot['region']}")
        if lot['region'] == "UNKNOWN":
            print("     ⚠️ Регион не определен, ставка скупщика может быть 0%")
            
        for res in lot["results"]:
            status = ""
            if res["is_scam"]: status = "⚠️ СКАМ"
            elif res["profit"] > 0: status = "✅ ПРОФИТ"
            else: status = "🔻 УБЫТОК"
            
            print(f"       {status} | Скупщик: {res['buyer']} ({res['rate']*100}%) → Сдать за ${res['sell_price']:.2f} | Профит: {res['profit']:+.2f} ({res['pct']:+.1f}%)")
            
        print(f"     Ссылка: {lot['url']}")
        
    if not found_any:
        print("  ⚠️ Ничего не найдено по этому запросу (или все отфильтровано по номиналу).")

print("\n" + "=" * 80)
print("  ✅ СКАН ЗАВЕРШЕН")
print("=" * 80)
