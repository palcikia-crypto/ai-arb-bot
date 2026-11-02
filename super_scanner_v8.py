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

# Fallback-ставки (проверенные вручную)
FALLBACK = {
    "GiftCardIo": 0.86,
    "CardBix": 0.85,
    "SellCardNow": 0.85,
    "HighCardRate": 0.78,
    "Cashard": 0.70,
}

# --- 1. SellCardNow: единственный рабочий API ---
def get_sellcardnow_rate():
    try:
        r = requests.get("https://sellcardnow.com/api/rates", headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        # Ищем элементы с category "Steam"
        for item in data.get("items", []):
            if item.get("category", "").lower() == "steam":
                # Пытаемся вычислить процент из ratePerUnitCny и faceValueLabel
                rate_cny = item.get("ratePerUnitCny")
                face = item.get("faceValueLabel")
                if rate_cny and face:
                    try:
                        face_usd = float(face)
                        # ratePerUnitCny — это сколько юаней за 1 единицу номинала
                        # Для приблизительной оценки: 1 USD ≈ 7.2 CNY (можно обновлять)
                        usd_rate = 7.2
                        payout_usd = rate_cny / usd_rate
                        rate = payout_usd / face_usd
                        if 0.5 <= rate <= 1.0:
                            return rate, f"API (SellCardNow, {face} USD → {rate_cny} CNY)"
                    except:
                        pass
        # Если Steam не найден, возвращаем None
        return None, "API (SellCardNow) — Steam не найден в ответе"
    except Exception as e:
        return None, f"Ошибка API: {e}"

# --- 2. HighCardRate: парсим блог (работает) ---
def get_highcardrate_rate():
    url = "https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(["script", "style", "noscript"]): s.decompose()
        text = re.sub(r'\s+', ' ', soup.get_text())
        m = re.search(r'Steam[^0-9]{0,30}(\d{2})\s*%', text, re.IGNORECASE)
        if m and 50 <= int(m.group(1)) <= 95:
            return int(m.group(1)) / 100, f"Regex (HighCardRate, {m.group(1)}%)"
    except:
        pass
    return None

# --- 3. CardBix, GiftCardIo, Cashard: только fallback (API закрыт/отсутствует) ---
def get_fallback(name):
    return FALLBACK[name], "Fallback (ручная ставка)"

# --- 4. Парсинг Plati (без изменений) ---
def fetch_plati(nominal, query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        items = requests.get(API, params=params, headers=HEADERS, timeout=20).json().get("items", [])
    except:
        return []
    lots = []
    for item in items:
        name = item.get("name", "")
        price = item.get("price_usd")
        url = item.get("url")
        seller = item.get("seller_name", "")
        if not price or not url: continue
        m = re.search(r'(\d+)', name)
        if not m or int(m.group(1)) != nominal: continue
        if price < nominal * 0.4: continue
        nl = name.lower()
        region = "Turkey" if "турция" in nl else ("Global" if "global" in nl else "US")
        lots.append({"name": name[:60], "price": float(price), "seller": seller, "url": url, "region": region})
    lots.sort(key=lambda x: x["price"])
    return lots

# === ЗАПУСК ===
print("=" * 80)
print("  🔧 СУПЕР-СКАНЕР v8 (API + FALLBACK)")
print("=" * 80)

print("\n📡 Получаем ставки скупщиков...")
buyer_rates = {}

# SellCardNow
rate, src = get_sellcardnow_rate()
if rate:
    buyer_rates["SellCardNow"] = rate
    print(f"  ✅ SellCardNow: {rate*100:.1f}%  ←  {src}")
else:
    buyer_rates["SellCardNow"] = FALLBACK["SellCardNow"]
    print(f"  ⚠️ SellCardNow: fallback {FALLBACK['SellCardNow']*100:.0f}%  ({src})")

# HighCardRate
rate, src = get_highcardrate_rate()
if rate:
    buyer_rates["HighCardRate"] = rate
    print(f"  ✅ HighCardRate: {rate*100:.0f}%  ←  {src}")
else:
    buyer_rates["HighCardRate"] = FALLBACK["HighCardRate"]
    print(f"  ⚠️ HighCardRate: fallback {FALLBACK['HighCardRate']*100:.0f}%")

# CardBix, GiftCardIo, Cashard — только fallback
for name in ["CardBix", "GiftCardIo", "Cashard"]:
    buyer_rates[name] = FALLBACK[name]
    print(f"  ⚠️ {name}: fallback {FALLBACK[name]*100:.0f}%  (API недоступен)")

print("\n" + "=" * 80)

CATS = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10),
    ("Steam Global 20", "Steam Global 20 USD", 20),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20),
    ("Xbox USA 10", "Xbox USA 10 USD", 10),
]

best_deal = None
for cat, q, nom in CATS:
    print(f"\n📦 [{cat}]")
    lots = fetch_plati(nom, q)
    if not lots:
        print("  ❌ нет лотов")
        continue
    b = lots[0]
    print(f"  📌 {b['name']}")
    print(f"     {b['seller']} | ${b['price']:.2f} | {b['region']}")
    for buyer, r in buyer_rates.items():
        sell = nom * r
        prof = sell - b['price']
        pct = (prof / b['price'] * 100) if b['price'] else 0
        if prof > 0:
            print(f"     ✅ {buyer} ({r*100:.1f}%) → +${prof:.2f} ({pct:+.1f}%)")
            if best_deal is None or prof > best_deal['profit']:
                best_deal = {"buyer": buyer, "profit": prof, "pct": pct, "url": b['url'], "name": b['name']}
        else:
            print(f"     🔻 {buyer} ({r*100:.1f}%) → ${prof:.2f} ({pct:+.1f}%)")

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
