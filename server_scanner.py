import requests, re, json, os

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}
HF_TOKEN = os.environ.get("HF_TOKEN", "")

CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10),
    ("Steam Global 20", "Steam Global 20 USD", 20),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20),
    ("Xbox USA 10", "Xbox USA 10 USD", 10),
]

def ask_hf_scam(title):
    if not HF_TOKEN: return False
    prompt = f"Текст: '{title}'. Это скам? (Если написано Турция но 'весь мир' - скам). Отвечай 1 словом: ДА или НЕТ."
    try:
        r = requests.post("https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta", 
                          headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": prompt}, timeout=15)
        ans = r.json()[0].get("generated_text", "").upper()
        return "ДА" in ans
    except:
        return False

def get_live_rate():
    try:
        r = requests.get("https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide", headers=HEADERS, timeout=15)
        m = re.search(r'Steam[^0-9%]{0,50}(\d{2})\s*%', r.text, re.IGNORECASE)
        if m: return int(m.group(1)), "HighCardRate"
    except: pass
    return 78, "Fallback"

def fetch_plati(nominal, query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        items = requests.get(API, params=params, headers=HEADERS, timeout=20).json().get("items", [])
    except: return []
    lots = []
    for item in items:
        name = item.get("name", ""); price = item.get("price_usd"); url = item.get("url")
        if not price or not url: continue
        m = re.search(r'(\d+)', name)
        if not m or int(m.group(1)) != nominal: continue
        if price < nominal * 0.4: continue
        region = "Turkey" if "турция" in name.lower() else ("Global" if "global" in name.lower() else "US")
        lots.append({"name": name[:60], "price": float(price), "seller": item.get("seller_name", ""), "url": url, "region": region})
    lots.sort(key=lambda x: x["price"])
    return lots

def main():
    rate_pct, source = get_live_rate()
    results = []
    for cat, query, nominal in CATEGORIES:
        lots = fetch_plati(nominal, query)
        if lots:
            b = lots[0]
            sell = nominal * (rate_pct / 100)
            profit = sell - b["price"]
            if profit > 0:
                is_scam = ask_hf_scam(b["name"])
                results.append({
                    "category": cat, "name": b["name"], "seller": b["seller"], "price": b["price"],
                    "sell_price": round(sell, 2), "profit": round(profit, 2),
                    "pct": round((profit / b["price"] * 100), 1),
                    "rate": rate_pct, "source": source, "url": b["url"], "is_scam": is_scam
                })
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ Скан завершен. Найдено связок: {len(results)}")

if __name__ == "__main__":
    main()
