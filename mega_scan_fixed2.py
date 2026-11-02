import requests, re, time

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

# Категории: (Название, Запрос, Номинал, Реальный процент скупщика)
CATEGORIES = [
    ("Steam Turkey 10",   "Steam Turkey 10 USD",      10,   0.45), # Турция берут максимум за 45%!
    ("Steam Global 20",   "Steam Global 20 USD",      20,   0.86), # Global берут за 86%
    ("Nintendo 10",       "Nintendo eShop 10 USD",    10,   0.85),
    ("Nintendo 20",       "Nintendo eShop 20 USD",    20,   0.85),
    ("Xbox USA 10",       "Xbox USA 10 USD",          10,   0.85),
    ("V-Bucks 1000",      "V-Bucks 1000 Fortnite",    1000, 0.60), # V-Bucks = 1000 шт = ~$10
]

def ai_analyze(title):
    """ИИ проверяет название на обман и кардинг"""
    text = title.lower()
    is_scam = False
    reason = ""
    
    # Если это Турция, но пишут "весь мир" или "Global" - это скам
    if any(w in text for w in ["турция", " tr ", " try "]):
        if any(w in text for w in ["весь мир", "global", "world"]):
            is_scam = True
            reason = "Турецкая карта не может быть Global/весь мир"
            
    return is_scam, reason

def fetch_plati(query):
    params = {"query": query, "pagesize": 50, "pagenum": 1,
              "visibleOnly": "true", "response": "json"}
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        return r.json().get("items", [])
    except Exception as e:
        return []

def find_real_lot(items, target, rate, cat_name):
    candidates = []
    for item in items:
        name = item.get("name", "")
        price = item.get("price_usd")
        url = item.get("url")
        
        if not price or not url: continue
        
        # Очистка названия от скидок типа [-10%]
        name_clean = re.sub(r'\[\s*-?\d+%?\s*\]', '', name.lower())
        name_clean = re.sub(r'-\d+%', '', name_clean)
        
        # Ищем числа в названии
        numbers = re.findall(r'\b(\d+)\b', name_clean)
        if not numbers: continue
        
        first_num = int(numbers[0])
        if first_num != target: continue
        
        # Определяем стоимость в долларах для расчета профита
        usd_value = target if target < 100 else (target * 0.01)
        
        # ИИ-проверка
        is_scam, scam_reason = ai_analyze(name)
        
        # Проверка на кардинг (цена ниже 65% от номинала)
        carding_risk = (float(price) / usd_value) < 0.65
        
        sell_price = usd_value * rate
        profit = sell_price - float(price)
        pct = (profit / float(price) * 100) if float(price) > 0 else 0
        
        # Статус
        if is_scam:
            status = "⚠️ СКАМ"
        elif carding_risk:
            status = "❌ РИСК (Кардинг)"
        elif profit > 0:
            status = "✅ ПРОФИТ"
        else:
            status = "🔻 УБЫТОК"
            
        candidates.append({
            "price": float(price),
            "seller": item.get("seller_name", ""),
            "url": url,
            "name": name[:70],
            "profit": profit,
            "pct": pct,
            "status": status,
            "reason": scam_reason
        })
    
    # Сортируем: сначала профитные, потом по цене
    candidates.sort(key=lambda x: (x["status"] != "✅ ПРОФИТ", x["price"]))
    return candidates

print("=" * 80)
print("  🔧 СКАН PLATI API + ИИ ПРОВЕРКА")
print("=" * 80)

all_deals = []
for name, query, target, rate in CATEGORIES:
    print(f"\n📦 [{name}]")
    items = fetch_plati(query)
    
    if not items:
        print(f"  ❌ API вернул 0 лотов")
        continue
    
    lots = find_real_lot(items, target, rate, name)
    if not lots:
        print(f"  ⚠️ Найдено {len(items)} лотов, но ни один не подошел под номинал {target}")
        continue
    
    print(f"  🔍 Найдено {len(lots)} подходящих лотов (Номинал: {target}):")
    for i, lot in enumerate(lots[:5], 1):
        if lot["status"] == "✅ ПРОФИТ":
            print(f"    {lot['status']} | ${lot['price']:.2f} у {lot['seller']} → +${lot['profit']:.2f} ({lot['pct']:+.1f}%)")
            print(f"       {lot['name']}")
            print(f"       {lot['url']}")
            all_deals.append({
                "category": name,
                "price": round(lot["price"], 2),
                "seller": lot["seller"],
                "profit": round(lot["profit"], 2),
                "profit_pct": round(lot["pct"], 1),
                "url": lot["url"],
            })
        elif lot["status"] == "⚠️ СКАМ":
            print(f"    {lot['status']} | ${lot['price']:.2f} у {lot['seller']} ({lot['reason']})")
        elif lot["status"] == "❌ РИСК (Кардинг)":
            print(f"    {lot['status']} | ${lot['price']:.2f} у {lot['seller']} (Слишком дешево)")
        else:
            pass # Убыточные не выводим, чтобы не засорять эфир

print("\n" + "=" * 80)
print("  📊 ИТОГ: ЛУЧШИЕ СВЯЗКИ")
print("=" * 80)
if all_deals:
    all_deals.sort(key=lambda x: x["profit_pct"], reverse=True)
    for d in all_deals:
        print(f"  🏆 {d['category']}: купить за ${d['price']} → +${d['profit']} ({d['profit_pct']:+.1f}%)")
        print(f"     {d['url']}")
else:
    print("  ❌ Прибыльных и безопасных связок не найдено (ИИ отсеял риски).")
