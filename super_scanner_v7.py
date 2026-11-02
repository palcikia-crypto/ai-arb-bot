import requests, re, subprocess, sys
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.append(str(Path.home() / 'quantum_lab_sandbox' / 'tools' / 'agent_dev'))
try:
    from llm_backend import ask
    HAS_LLM = True
    print("✅ ИИ (DeepSeek-V3) подключен!")
except ImportError:
    HAS_LLM = False
    print("⚠️ ИИ не найден.")

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

BASE_RATES = {
    "GiftCardIo": 0.86, "CardBix": 0.85, "SellCardNow": 0.85,
    "HighCardRate": 0.78, "Cashard": 0.70,
}

# РАБОЧИЕ URL (проверенные, где ставки есть в HTML)
SITES = [
    ("GiftCardIo", [
        "https://giftcardio.com/sell-gift-cards",
        "https://giftcardio.com/blog/sell-steam-gift-cards",
    ]),
    ("CardBix", [
        "https://cardbix.com/blog",
        "https://cardbix.com/sell-steam",
    ]),
    ("SellCardNow", [
        "https://sellcardnow.com/blog",
        "https://sellcardnow.com/how-it-works",
    ]),
    ("HighCardRate", [
        "https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide",  # ← РАБОТАЕТ (78%)
        "https://highcardrate.com/blog",
    ]),
    ("Cashard", [
        "https://cashard.com/blog",
    ]),
]

def fetch_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return None
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(["script", "style", "noscript"]): s.decompose()
        return re.sub(r'\s+', ' ', soup.get_text(separator=" ", strip=True))[:4000]
    except: return None

def web_search(query):
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for res in soup.select(".result")[:3]:
            t = res.select_one(".result__a"); s = res.select_one(".result__snippet")
            if t: out.append(f"{t.get_text(strip=True)}: {(s.get_text(strip=True) if s else '')[:200]}")
        return " | ".join(out)
    except: return ""

def extract_rate(text):
    """Regex + AI: ищет ставку Steam."""
    m = re.search(r'Steam[^0-9]{0,30}(\d{2})\s*%', text, re.IGNORECASE)
    if m and 50 <= int(m.group(1)) <= 95: return int(m.group(1))/100, "Regex"
    
    if HAS_LLM:
        try:
            ans = ask(
                f"Текст:\n{text[:2500]}\n\nНайди ставку для Steam в %. Ответь ТОЛЬКО числом или NO RATE.",
                system_prompt="Ты извлекаешь проценты. Отвечай числом или NO RATE."
            )
            m2 = re.search(r'(\d{1,2})', ans)
            if m2 and 50 <= int(m2.group(1)) <= 95: return int(m2.group(1))/100, "AI"
        except: pass
    return None, None

def get_rate(name, urls):
    for url in urls:
        print(f"    ⏳ {url}")
        text = fetch_text(url)
        if not text: 
            print("      ❌ не загрузилось")
            continue
        rate, method = extract_rate(text)
        if rate: 
            print(f"      ✅ {method}: {rate*100:.0f}%")
            return rate, url
    
    # AI поиск в интернете как последний шанс
    if HAS_LLM:
        print(f"      🌐 Ищу в поиске...")
        results = web_search(f"{name} Steam gift card rate")
        if results:
            rate, method = extract_rate(results)
            if rate:
                print(f"      ✅ AI-поиск: {rate*100:.0f}%")
                return rate, "web-search"
    
    return None, None

def fetch_plati(nominal, query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        items = requests.get(API, params=params, headers=HEADERS, timeout=20).json().get("items", [])
    except: return []
    lots = []
    for item in items:
        name = item.get("name", ""); price = item.get("price_usd"); url = item.get("url"); seller = item.get("seller_name", "")
        if not price or not url: continue
        m = re.search(r'(\d+)', name)
        if not m or int(m.group(1)) != nominal: continue
        if price < nominal * 0.4: continue
        nl = name.lower()
        region = "Turkey" if "турция" in nl else ("Global" if "global" in nl else "US")
        lots.append({"name": name[:60], "price": float(price), "seller": seller, "url": url, "region": region})
    lots.sort(key=lambda x: x["price"])
    return lots

# === СКАН ===
print("="*80); print("  🔧 СУПЕР-СКАНЕР v7"); print("="*80)

print("\n📡 Ставки скупщиков:")
buyer_rates = {}
for name, urls in SITES:
    print(f"\n🔍 {name}")
    rate, src = get_rate(name, urls)
    if rate:
        buyer_rates[name] = rate
        print(f"  🏆 {rate*100:.0f}%  ←  {src}")
    else:
        buyer_rates[name] = BASE_RATES[name]
        print(f"  ⚠️ Fallback: {BASE_RATES[name]*100:.0f}%")

print("\n" + "="*80)

CATS = [("Steam Turkey 10","Steam Turkey 10 USD",10), ("Steam Global 20","Steam Global 20 USD",20),
        ("Nintendo 10","Nintendo eShop 10 USD",10), ("Nintendo 20","Nintendo eShop 20 USD",20),
        ("Xbox USA 10","Xbox USA 10 USD",10)]

best_deal = None
for cat, q, nom in CATS:
    print(f"\n📦 [{cat}]")
    lots = fetch_plati(nom, q)
    if not lots: print("  ❌ пусто"); continue
    b = lots[0]
    print(f"  📌 {b['name']}\n     {b['seller']} | ${b['price']:.2f} | {b['region']}")
    for buyer, r in buyer_rates.items():
        sell = nom * r; prof = sell - b['price']; pct = (prof / b['price'] * 100) if b['price'] else 0
        if prof > 0:
            print(f"     ✅ {buyer} ({r*100:.0f}%) → +${prof:.2f} ({pct:+.1f}%)")
            if best_deal is None or prof > best_deal['profit']:
                best_deal = {"buyer": buyer, "profit": prof, "pct": pct, "url": b['url'], "name": b['name']}
        else:
            print(f"     🔻 {buyer} ({r*100:.0f}%) → ${prof:.2f} ({pct:+.1f}%)")

print("\n" + "="*80)
if best_deal:
    print(f"🏆 {best_deal['name']}")
    print(f"   {best_deal['buyer']} | +${best_deal['profit']:.2f} ({best_deal['pct']:+.1f}%)")
    print(f"   {best_deal['url']}")
    try: subprocess.run(["termux-open-url", best_deal['url']], timeout=5)
    except: pass
else:
    print("❌ нет связок")
print("="*80)
