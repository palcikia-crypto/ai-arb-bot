import requests, re, json, time  # v3.2 soft-risk

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}
PLATI = "https://plati.io/api/search.ashx"
DIGI = "https://api.digiseller.ru/api/products/search2"

CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10, "TR", ["steam"]),
    ("Steam Global 10", "Steam Global 10 USD", 10, "GLOBAL", ["steam"]),
    ("Steam Global 20", "Steam Global 20 USD", 20, "GLOBAL", ["steam"]),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10, "US", ["nintendo"]),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20, "US", ["nintendo"]),
    ("Xbox USA 10", "Xbox USA 10 USD", 10, "US", ["xbox"]),
]

RISK_WORDS = ["не весь мир", "только для", "конкретн", "уже использов", "used card", "активирован", "пополнение", "пополнени", "баланс", "balance"]

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

def soft_risk(name):
    if re.search(r'\d+\s*[-–]\s*\d+', name):
        return "в названии диапазон номиналов — проверь, что цена именно за нужную сумму"
    return None

def check_lot(it, match_words, nominal, region, sell_max):
    name = (it.get("name") or "")
    price = it.get("price_usd")
    url = it.get("url")
    if not price or not url: return None
    try: p = float(str(price).replace(",", "."))
    except Exception: return None
    nl = name.lower()
    if not all(w in nl for w in match_words): return None
    digits = re.findall(r'(\d+)', name)
    if str(nominal) not in digits and str(nominal) not in nl: return None
    if p < nominal * 0.5 or p > sell_max: return None
    return {"name": name[:70], "price": p, "seller": it.get("seller_name", ""), "url": url}

def fetch_plati(query, match_words, nominal, region, sell_max):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        items = requests.get(PLATI, params=params, headers=HEADERS, timeout=20).json().get("items", [])
    except Exception:
        return None
    best = None
    for it in items:
        lot = check_lot(it, match_words, nominal, region, sell_max)
        if lot and is_risky(lot["name"], region) is None:
            lot["risk"] = soft_risk(lot["name"])
            if best is None or lot["price"] < best["price"]:
                best = lot
    return best

def fetch_digi(query, match_words, nominal, region, sell_max):
    params = {"query": query, "pagesize": 40, "pagenum": 1, "lang": "ru-RU"}
    try:
        data = requests.get(DIGI, params=params, headers=HEADERS, timeout=20).json()
        items = (data.get("items") or {}).get("item", []) or []
    except Exception:
        return None
    best = None
    for it in items:
        if not it.get("url"):
            it["url"] = "https://plati.market/itm/" + str(it.get("id", ""))
        lot = check_lot(it, match_words, nominal, region, sell_max)
        if lot and is_risky(lot["name"], region) is None:
            lot["risk"] = soft_risk(lot["name"])
            if best is None or lot["price"] < best["price"]:
                best = lot
    return best

def main():
    rate_pct, rate_source, live = get_live_rate()
    offers = []
    for cat, query, nominal, region, words in CATEGORIES:
        sell = nominal * rate_pct / 100.0
        cands = []
        p = fetch_plati(query, words, nominal, region, sell * 0.98)
        if p: cands.append((p, "plati.market"))
        time.sleep(1)
        d = fetch_digi(query, words, nominal, region, sell * 0.98)
        if d: cands.append((d, "Digiseller"))
        time.sleep(1)
        if not cands: continue
        b, src = min(cands, key=lambda c: c[0]["price"])
        profit = sell - b["price"]
        if profit <= 0: continue
        offers.append({
            "category": cat, "name": b["name"], "seller": b["seller"],
            "source": src,
            "price": round(b["price"], 2), "nominal": nominal,
            "sell_price": round(sell, 2), "profit": round(profit, 2),
            "pct": round(profit / b["price"] * 100, 1),
            "risk": b.get("risk"),
            "source_rate": rate_source, "url": b["url"],
        })
    offers.sort(key=lambda x: x["pct"], reverse=True)
    data = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rate_pct": rate_pct, "rate_source": rate_source, "rate_live": live,
        "offers": offers[:10],
    }
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("gifts:", len(offers), "| rate:", rate_pct, "| live:", live)

if __name__ == "__main__":
    main()
