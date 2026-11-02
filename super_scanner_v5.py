import requests, re, subprocess, sys
from pathlib import Path
from bs4 import BeautifulSoup

# --- ПОДКЛЮЧАЕМ ТВОЙ РАБОЧИЙ ИИ ---
sys.path.append(str(Path.home() / 'quantum_lab_sandbox' / 'tools' / 'agent_dev'))
try:
    from llm_backend import ask
    HAS_LLM = True
    print("✅ Локальный ИИ (DeepSeek-V3 через llm7.io) подключен!")
except ImportError:
    HAS_LLM = False
    print("⚠️ ИИ не найден, будем использовать заглушки.")

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

BASE_RATES = {
    "GiftCardIo": 0.86,
    "CardBix": 0.85,
    "SellCardNow": 0.85,
    "HighCardRate": 0.84,
    "Cashard": 0.70,
}

def aggressive_fetch(url):
    print(f"    ⏳ Загрузка: {url}")
    if HAS_CFFI:
        try:
            r = cffi_requests.get(url, impersonate="chrome120", timeout=15)
            if r.status_code == 200 and len(r.text) > 500:
                print("      ✅ curl_cffi успех!")
                return r.text
        except Exception: pass
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            print("      ✅ requests успех!")
            return r.text
    except Exception: pass
    print("      ❌ Не удалось загрузить.")
    return None

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "noscript"]): s.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r'\s+', ' ', text)

def get_rate_with_ai(urls, site_name):
    for url in urls:
        html = aggressive_fetch(url)
        if not html: continue
        text = extract_text(html)
        
        # 1. Пробуем Regex (быстро)
        match = re.search(r'Steam.*?(\d{1,3})\s*%', text, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            if 50 <= val <= 95: return val/100, f"✅ Regex на {url}"
                
        # 2. Если Regex не сработал — зовем ИИ!
        if HAS_LLM:
            print(f"      🤖 Отправляю текст на анализ DeepSeek-V3...")
            prompt = f"Найди в этом тексте ставку (в процентах) для Steam gift cards. Если ставки нет, напиши 'NO RATE'. Ответь только числом или NO RATE.\n\nТекст:\n{text[:4000]}"
            try:
                ans = ask(prompt, system_prompt="Ты извлекаешь числа из текста. Отвечай только числом или NO RATE.")
                match_llm = re.search(r'(\d{1,2})', ans)
                if match_llm:
                    val = int(match_llm.group(1))
                    if 50 <= val <= 95: return val/100, f"✅ ИИ (DeepSeek) на {url}"
                print(f"      🤖 ИИ не нашел ставку (ответ: {ans[:30]}...)")
            except Exception as e:
                print(f"      ⚠️ Ошибка ИИ: {e}")
            
    return None, None

def fetch_plati_lots(nominal, query):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        items = r.json().get("items", [])
    except Exception: return []

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

        lots.append({"name": name[:60], "price": float(price), "seller": seller, "url": url, "is_scam": is_scam, "region": region})
    lots.sort(key=lambda x: x["price"])
    return lots

# === ЗАПУСК ===
print("=" * 80)
print("  🔧 СУПЕР-СКАНЕР v5 (РЕАЛЬНЫЙ ПАРСИНГ + ИИ DeepSeek-V3)")
print("=" * 80)

print("\n📡 Ищем ставки на сайтах скупщиков...")
buyer_rates = {}
sites_to_parse = [
    ("GiftCardIo", ["https://giftcardio.com/", "https://giftcardio.com/sell-gift-cards"]),
    ("CardBix", ["https://cardbix.com/", "https://cardbix.com/rates"]),
    ("SellCardNow", ["https://sellcardnow.com/", "https://sellcardnow.com/steam"]),
    ("HighCardRate", ["https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide", "https://highcardrate.com/"]),
    ("Cashard", ["https://cashard.com/", "https://cashard.com/rates"])
]

for name, urls in sites_to_parse:
    print(f"\n🔍 Скупщик: {name}")
    rate, status = get_rate_with_ai(urls, name)
    if rate:
        buyer_rates[name] = rate
        print(f"  🏆 Итоговая ставка {name}: {rate*100:.0f}% ({status})")
    else:
        buyer_rates[name] = BASE_RATES[name]
        print(f"  ⚠️ Не удалось достать. Fallback: {BASE_RATES[name]*100:.0f}%")

print("\n" + "=" * 80)

best_deal = None
CATEGORIES = [
    ("Steam Turkey 10", "Steam Turkey 10 USD", 10),
    ("Steam Global 20", "Steam Global 20 USD", 20),
    ("Nintendo 10", "Nintendo eShop 10 USD", 10),
    ("Nintendo 20", "Nintendo eShop 20 USD", 20),
    ("Xbox USA 10", "Xbox USA 10 USD", 10),
]

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
    try: subprocess.run(["termux-open-url", best_deal['url']], timeout=5)
    except: print("   ⚠️ Не удалось открыть браузер")
else:
    print("❌ Прибыльных связок не найдено.")
print("=" * 80)
