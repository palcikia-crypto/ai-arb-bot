import requests, re, subprocess
from bs4 import BeautifulSoup

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

# (Название, Запрос, Номинал)
CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10),
    ("Steam Global 20", "Steam Global 20 USD", 20),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20),
    ("Xbox USA 10", "Xbox USA 10 USD", 10),
]

# === ПАРСИНГ СКУПЩИКОВ ===
def get_highcardrate_steam():
    """Пытается спарсить реальную ставку Steam с HighCardRate."""
    try:
        url = "https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text()
        # Ищем строку типа "Steam | 78% | $78 in BTC"
        match = re.search(r'Steam\s*\|\s*(\d+)%', text)
        if match:
            rate = int(match.group(1)) / 100.0
            print(f"  ✅ HighCardRate: спарсена ставка Steam {rate*100:.0f}%")
            return rate
    except Exception as e:
        print(f"  ⚠️ HighCardRate: ошибка парсинга ({e})")
    print("  ⚠️ HighCardRate: использую заглушку 78%")
    return 0.78

def get_cardbix_steam():
    """Пытается спарсить ставку CardBix (если не выйдет — заглушка)."""
    # CardBix требует JS/авторизации, поэтому парсинг ненадежен
    # Используем ставку из их описания: до 90%, для Steam обычно 85%
    print("  ⚠️ CardBix: парсинг недоступен (JS/авторизация), использую заглушку 85%")
    return 0.85

def get_sellcardnow_steam():
    """Пытается спарсить калькулятор SellCardNow (сложно, используем заглушку)."""
    print("  ⚠️ SellCardNow: калькулятор требует JS/WhatsApp, использую заглушку 85%")
    return 0.85

# === ПАРСИНГ PLATI ===
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
        
        m = re.search(r'(\d+)', name)
        if not m: continue
        if int(m.group(1)) != nominal: continue
        if price < nominal * 0.4: continue
        
        name_lower = name.lower()
        is_scam = False
        if ("турция" in name_lower or " tr " in name_lower) and ("весь мир" in name_lower or "global" in name_lower):
            is_scam = True
        region = "Turkey" if "турция" in name_lower else ("Global" if "global" in name_lower else "US")
        
        lots.append({
            "name": name[:60], "price": float(price), "seller": seller,
            "url": url, "is_scam": is_scam, "region": region
        })
    lots.sort(key=lambda x: x["price"])
    return lots

# === ОСНОВНОЙ СКАН ===
print("=" * 80)
print("  🔧 СУПЕР-СКАНЕР v2 (ПАРСИНГ СКУПЩИКОВ)")
print("=" * 80)

# Получаем ставки
print("\n📡 Проверяю ставки скупщиков...")
rates = {
    "HighCardRate": get_highcardrate_steam(),
    "CardBix": get_cardbix_steam(),
    "SellCardNow": get_sellcardnow_steam(),
}
# Для Nintendo и Xbox используем те же ставки (примерно)
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
        print("     ⚠️ ВНИМАНИЕ: ИИ обнаружил обман (Турция + 'весь мир')!")
    
    for buyer, rate in rates.items():
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
