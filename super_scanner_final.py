import requests, re, subprocess

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

# (Название, Запрос, Номинал)
CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10),
    ("Steam Global 20", "Steam Global 20 USD", 20),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20),
    ("Xbox USA 10", "Xbox USA 10 USD", 10),
]

# ТВОИ СКУПЩИКИ (ровно как в первом скрипте super_scanner.py)
BUYERS = {
    "CardBix": 0.85,
    "GiftCardIo": 0.86,
    "Cashard": 0.70,
    "HighCardRate": 0.84
}

def fetch_plati_lots(nominal, query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        items = r.json().get("items", [])
    except Exception as e:
        return []

    lots = []
    for item in items:
        name = item.get("name", "")
        price = item.get("price_usd")
        url = item.get("url")
        seller = item.get("seller_name", "")
        
        if not price or not url: continue
        
        # ТВОЯ РАБОЧАЯ ЛОГИКА: Берем первое число. Если это не номинал - отсеиваем.
        m = re.search(r'(\d+)', name)
        if not m: continue
        if int(m.group(1)) != nominal: continue
        
        # Отсев кардинга (цена меньше 40% от номинала)
        if price < nominal * 0.4: continue
        
        # ИИ-ПРЕДУПРЕЖДЕНИЕ (не блокирует расчет!)
        name_lower = name.lower()
        is_scam = False
        if ("турция" in name_lower or " tr " in name_lower) and ("весь мир" in name_lower or "global" in name_lower):
            is_scam = True
            
        region = "Turkey" if "турция" in name_lower else ("Global" if "global" in name_lower else "US")
        
        lots.append({
            "name": name[:60],
            "price": float(price),
            "seller": seller,
            "url": url,
            "is_scam": is_scam,
            "region": region
        })
        
    lots.sort(key=lambda x: x["price"])
    return lots

print("=" * 80)
print("  🔧 СУПЕР-СКАНЕР (ЛОГИКА ИЗ ПЕРВОГО СКРИПТА)")
print("=" * 80)

best_deal = None

for cat_name, query, nominal in CATEGORIES:
    print(f"\n📦 [{cat_name}] Ищем номинал {nominal} USD...")
    lots = fetch_plati_lots(nominal, query)
    
    if not lots:
        print("  ❌ Нет подходящих лотов (или все отсеяны как мульти-лоты).")
        continue
        
    # Берем самый дешевый
    best = lots[0]
    
    print(f"  📌 Найден: {best['name']}")
    print(f"     Продавец: {best['seller']} | Цена: ${best['price']:.2f} | Регион: {best['region']}")
    
    if best['is_scam']:
        print("     ⚠️ ВНИМАНИЕ: ИИ обнаружил обман! Продавец пишет 'весь мир', но это ТУРЦИЯ!")
        
    for buyer, rate in BUYERS.items():
        sell = nominal * rate
        profit = sell - best['price']
        pct = (profit / best['price'] * 100) if best['price'] > 0 else 0
        
        if profit > 0:
            print(f"     ✅ {buyer} ({rate*100}%) → Сдать за ${sell:.2f} | Профит: +${profit:.2f} ({pct:+.1f}%)")
            if best_deal is None or profit > best_deal['profit']:
                best_deal = {"buyer": buyer, "profit": profit, "pct": pct, "url": best['url'], "name": best['name']}
        else:
            print(f"     🔻 {buyer} ({rate*100}%) → Убыток: ${profit:.2f} ({pct:+.1f}%)")

print("\n" + "=" * 80)
if best_deal:
    print(f"🏆 ЛУЧШАЯ СВЯЗКА: {best_deal['name']}")
    print(f"   Скупщик: {best_deal['buyer']}")
    print(f"   Профит: +${best_deal['profit']:.2f} ({best_deal['pct']:+.1f}%)")
    print(f"   Ссылка: {best_deal['url']}")
    print("\n🌐 Открываю в браузере...")
    try:
        subprocess.run(["termux-open-url", best_deal['url']], timeout=5)
    except:
        print("   ⚠️ Не удалось открыть браузер (нет termux-api)")
else:
    print("❌ Прибыльных связок не найдено.")
print("=" * 80)
