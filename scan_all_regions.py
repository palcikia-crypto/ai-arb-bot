import requests, re, json, time

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

# Все регионы + запросы
REGIONS = [
    ("Turkey",     "Steam Turkey 10 USD"),
    ("Argentina",  "Steam Argentina 10 USD"),
    ("Brazil",     "Steam Brazil 10 USD"),
    ("India",      "Steam India 10 USD"),
    ("Kazakhstan", "Steam Kazakhstan 10 USD"),
    ("Ukraine",    "Steam Ukraine 10 USD"),
    ("Poland",     "Steam Poland 10 USD"),
    ("Global",     "Steam Wallet 10 USD Global"),
    ("USA",        "Steam Wallet 10 USD USA"),
]

TARGET = 10  # все номиналы по 10 USD
BUYER_RATE = 0.85  # усреднённая ставка скупщика (85%)

def fetch_plati(query):
    """Ищет лоты на Plati."""
    params = {
        "query": query,
        "pagesize": 50,
        "pagenum": 1,
        "visibleOnly": "true",
        "response": "json"
    }
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        return r.json().get("items", [])
    except Exception as e:
        print(f"  ⚠️ API error: {e}")
        return []

def find_best_lot(items, target=10):
    """Фильтрует по минимальному номиналу = target."""
    candidates = []
    for item in items:
        name = (item.get("name_eng","") + " " + item.get("name","")).lower()
        price = item.get("price_usd")
        url = item.get("url")
        if not price or not url: continue
        
        m = re.search(r'(\d+)', name)
        if not m: continue
        if int(m.group(1)) != target: continue
        if price < target * 0.3: continue  # отсев фейков
        
        candidates.append({
            "price": float(price),
            "seller": item.get("seller_name", ""),
            "url": url,
            "name": item.get("name", "")[:60],
        })
    candidates.sort(key=lambda x: x["price"])
    return candidates

def main():
    print("=" * 80)
    print("  🌍 СКАН ВСЕХ РЕГИОНОВ STEAM 10 USD НА PLATI.MARKET")
    print(f"  Ставка скупщика: {BUYER_RATE*100:.0f}% от номинала")
    print("=" * 80)
    
    results = []
    
    for region, query in REGIONS:
        print(f"\n📦 [{region}] {query}")
        items = fetch_plati(query)
        if not items:
            print(f"  ❌ Нет результатов")
            continue
        
        candidates = find_best_lot(items, TARGET)
        if not candidates:
            print(f"  ⚠️ {len(items)} лотов, но ни один не на {TARGET} USD")
            # Показываем что нашли
            for it in items[:3]:
                print(f"     - {it.get('name','')[:60]} | ${it.get('price_usd','?')}")
            continue
        
        best = candidates[0]
        sell = TARGET * BUYER_RATE
        profit = sell - best["price"]
        pct = (profit / best["price"] * 100) if best["price"] > 0 else 0
        marker = "✅" if profit > 0 else "❌"
        
        print(f"  {marker} Дешёвый: {best['seller']} — ${best['price']:.2f}")
        print(f"      Профит при {BUYER_RATE*100:.0f}%: ${profit:+.2f} ({pct:+.1f}%)")
        print(f"      {best['name']}")
        print(f"      {best['url']}")
        
        results.append({
            "region": region,
            "price": round(best["price"], 2),
            "seller": best["seller"],
            "url": best["url"],
            "profit": round(profit, 2),
            "profit_pct": round(pct, 1),
            "marker": marker,
        })
    
    # === ИТОГ ===
    print("\n" + "=" * 80)
    print("  📊 ИТОГ ПО РЕГИОНАМ")
    print("=" * 80)
    
    results.sort(key=lambda x: x["profit_pct"], reverse=True)
    
    print(f"\n{'Регион':<15} {'Цена':<8} {'Профит':<10} {'%':<8} {'Продавец'}")
    print("-" * 80)
    for r in results:
        print(f"{r['region']:<15} ${r['price']:<7} {r['profit']:+<9} {r['profit_pct']:+<7.1f}% {r['seller']}")
    
    # === ЛУЧШИЙ ===
    profitable = [r for r in results if r["profit"] > 0]
    if profitable:
        best = profitable[0]
        print(f"\n🏆 ЛУЧШАЯ СВЯЗКА: {best['region']} — {best['profit_pct']:+.1f}%")
        print(f"   Купить: ${best['price']} у {best['seller']}")
        print(f"   Сдать:  ${TARGET * BUYER_RATE} (при {BUYER_RATE*100:.0f}%)")
        print(f"   Ссылка: {best['url']}")
        
        # Сохраняем
        with open("best_region.json", "w") as f:
            json.dump(best, f, indent=2)
    else:
        print(f"\n❌ ПРИБЫЛЬНЫХ РЕГИОНОВ НЕ НАЙДЕНО при ставке {BUYER_RATE*100:.0f}%")
        print(f"   Все регионы убыточны на Plati.Market")
    
    # Сохраняем всё
    with open("all_regions.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Сохранено в all_regions.json")

if __name__ == "__main__":
    main()
