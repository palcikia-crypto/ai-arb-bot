import requests, re, subprocess
from bs4 import BeautifulSoup

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10),
    ("Steam Global 20", "Steam Global 20 USD", 20),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20),
    ("Xbox USA 10", "Xbox USA 10 USD", 10),
]

# === БАЗОВЫЕ СТАВКИ (из твоего первого лога, как fallback) ===
BASE_RATES = {
    "GiftCardIo": 0.86,
    "CardBix": 0.85,
    "SellCardNow": 0.85,
    "HighCardRate": 0.84,
    "Cashard": 0.70,
}

# === ПАРСЕРЫ СКУПЩИКОВ ===
def parse_rate_site(url, patterns):
    """Универсальный парсер: пробует URL, ищет regex-паттерны, возвращает ставку или None."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return None
        text = BeautifulSoup(r.text, "html.parser").get_text()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = float(match.group(1))
                rate = val / 100 if val > 1 else val
                if 0.5 <= rate <= 1.0:
                    return rate
    except Exception:
        pass
    return None

def get_rate_giftcardio():
    urls = ["https://giftcardio.com/", "https://giftcardio.com/sell-gift-cards"]
    patterns = [r'Steam[^\d]*(\d{2})\s*%', r'Steam[^\d]*0\.(\d{2})']
    for url in urls:
        rate = parse_rate_site(url, patterns)
        if rate: return rate, "спарсено", url
    return BASE_RATES["GiftCardIo"], "fallback", None

def get_rate_cardbix():
    urls = ["https://cardbix.com/", "https://cardbix.com/rates"]
    patterns = [r'Steam[^\d]*(\d{2})\s*%', r'Steam[^\d]*0\.(\d{2})']
    for url in urls:
        rate = parse_rate_site(url, patterns)
        if rate: return rate, "спарсено", url
    return BASE_RATES["CardBix"], "fallback", None

def get_rate_sellcardnow():
    urls = ["https://sellcardnow.com/", "https://sellcardnow.com/steam"]
    patterns = [r'Steam[^\d]*(\d{2})\s*%', r'Steam[^\d]*0\.(\d{2})']
    for url in urls:
        rate = parse_rate_site(url, patterns)
        if rate: return rate, "спарсено", url
    return BASE_RATES["SellCardNow"], "fallback", None

def get_rate_highcardrate():
    urls = [
        "https://highcardrate.com/",
        "https://highcardrate.com/rates",
        "https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide",
    ]
    patterns = [r'Steam[^\d]*(\d{2})\s*%', r'Steam[^\d]*0\.(\d{2})']
    for url in urls:
        rate = parse_rate_site(url, patterns)
        if rate: return rate, "спарсено", url
    return BASE_RATES["HighCardRate"], "fallback", None

def get_rate_cashard():
    urls = ["https://cashard.com/", "https://cashard.com/rates"]
    patterns = [r'Steam[^\d]*(\d{2})\s*%', r'Steam[^\d]*0\.(\d{2})']
    for url in urls:
        rate = parse_rate_site(url, patterns)
        if rate: return rate, "спарсено", url
    return BASE_RATES["Cashard"], "fallback", None

# === ПАРСИНГ PLATI (как в твоем первом скрипте) ===
def fetch_plati_lots(nominal, query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        items = r.json().get("items", [])
    except Exception:
        return []

    lots = []
    for item in items:
        name = item.get("name", "")
        price = item.get("price_usd")
        url = item.get("url")
        seller = item.get("seller_name", "")
        if not price or not url: continue
        m = re.search(r'(\d+)', name)
        if not m: continue
        if int(m.group(1)) != nominal: continue
        if price < nominal * 0.4: continue

        name_lower = name.lower()
        is_scam = ("турция" in name_lower or " tr " in name_lower) and ("весь мир" in name_lower or "global" in name_lower)
        region = "Turkey" if "турция" in name_lower else ("Global" if "global" in name_lower else "US")

        lots.append({
            "name": name[:60], "price": float(price), "seller": seller,
            "url": url, "is_scam": is_scam, "region": region
        })
    lots.sort(key=lambda x: x["price"])
    return lots

# === ОСНОВНОЙ СКАН ===
print("=" * 80)
print("  🔧 СУПЕР-СКАНЕР v3 (5 СКУПЩИКОВ + РЕАЛЬНЫЙ ПАРСИНГ)")
print("=" * 80)

print("\n📡 Проверяю ставки скупщиков (реальный парсинг)...")
buyer_rates = {}
for name, func in [
    ("GiftCardIo", get_rate_giftcardio),
    ("CardBix", get_rate_cardbix),
    ("SellCardNow", get_rate_sellcardnow),
    ("HighCardRate", get_rate_highcardrate),
    ("Cashard", get_rate_cashard),
]:
    rate, status, url = func()
    buyer_rates[name] = rate
    tag = "✅" if status == "спарсено" else "⚠️"
    print(f"  {tag} {name}: {rate*100:.0f}% [{status}]" + (f" <- {url}" if url else ""))

print("\n" + "=" * 80)

best_deal = None

for cat_name, query, nominal in CATEGORIES:
    print(f"\n📦 [{cat_name}] Ищем номинал {nominal} USD...")
    lots = fetch_plati_lots(nominal, query)
    if not lots:
        print("  ❌ Нет подходящих лотов.")
        continue

    best = lots[0]
    print(f"  📌 {best['name']}")
    print(f"     Продавец: {best['seller']} | Цена: ${best['price']:.2f} | Регион: {best['region']}")
    if best['is_scam']:
        print("     ⚠️ ИИ: обнаружен обман (Турция + 'весь мир')!")

    for buyer, rate in buyer_rates.items():
        sell = nominal * rate
        profit = sell - best['price']
        pct = (profit / best['price'] * 100) if best['price'] > 0 else 0
        if profit > 0:
            print(f"     ✅ {buyer} ({rate*100:.0f}%) → ${sell:.2f} | Профит: +${profit:.2f} ({pct:+.1f}%)")
            if best_deal is None or profit > best_deal['profit']:
                best_deal = {"buyer": buyer, "profit": profit, "pct": pct, "url": best['url'], "name": best['name']}
        else:
            print(f"     🔻 {buyer} ({rate*100:.0f}%) → Убыток: ${profit:.2f} ({pct:+.1f}%)")

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
        print("   ⚠️ Не удалось открыть браузер")
else:
    print("❌ Прибыльных связок не найдено.")
print("=" * 80)
