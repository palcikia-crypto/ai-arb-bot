import requests, re, json, time

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}

CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10, "TR"),
    ("Steam Global 10", "Steam Global 10 USD", 10, "GLOBAL"),
    ("Steam Global 20", "Steam Global 20 USD", 20, "GLOBAL"),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10, "US"),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20, "US"),
    ("Xbox USA 10", "Xbox USA 10 USD", 10, "US"),
]

RISK_WORDS = ["не весь мир", "только для", "конкретн", "уже использов", "used card", "активирован"]

def get_live_rate():
    try:
        r = requests.get("https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide", headers=HEADERS, timeout=15)
        m = re.search(r'Steam[^0-9%]{0,50}(\d{2})\s*%', r.text, re.IGNORECASE)
        if m: return int(m.group(1)), "HighCardRate (живой курс)", True
    except Exception:
        pass
    return 78, "запасная оценка: сайт скупщика не ответил", False

def is_risky(name, region):
    n = name.lower()
    if region == "GLOBAL" and ("турция" in n or "turkey" in n):
        return "регион лота не совпадает с категорией"
    for w in RISK_WORDS:
        if w in n: return "подозрительное описание"
    return None

def fetch_plati(nominal, query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        items = requests.get(API, params=params, headers=HEADERS, timeout=20).json().get("items", [])
    except Exception:
        return []
    lots = []
    for item in items:
        name = item.get("name", ""); price = item.get("price_usd"); url = item.get("url")
        if not price or not url: continue
        m = re.search(r'(\d+)', name)
        if not m or int(m.group(1)) != nominal: continue
        if price < nominal * 0.5: continue
        lots.append({"name": name[:70], "price": float(price), "seller": item.get("seller_name", ""), "url": url})
    lots.sort(key=lambda x: x["price"])
    return lots

def main():
    rate_pct, rate_source, live = get_live_rate()
    offers = []
    for cat, query, nominal, region in CATEGORIES:
        lots = fetch_plati(nominal, query)
        if not lots: continue
        b = lots[0]
        sell = nominal * rate_pct / 100.0
        profit = sell - b["price"]
        if profit <= 0: continue
        offers.append({
            "category": cat, "name": b["name"], "seller": b["seller"],
            "price": round(b["price"], 2), "nominal": nominal,
            "sell_price": round(sell, 2), "profit": round(profit, 2),
            "pct": round(profit / b["price"] * 100, 1),
            "risk": is_risky(b["name"], region),
            "source": rate_source, "url": b["url"],
        })
    offers.sort(key=lambda x: x["pct"], reverse=True)
    data = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rate_pct": rate_pct, "rate_source": rate_source, "rate_live": live,
        "offers": offers[:8],
    }
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("offers:", len(offers), "| rate:", rate_pct, "| live:", live)

if __name__ == "__main__":
    main()