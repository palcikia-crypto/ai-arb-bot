import requests, re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.text if r.status_code == 200 else None
    except: return None

def find_steam_rates(html, site_name):
    """Ищет ставки для Steam в HTML."""
    if not html: return None
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Ищем "Steam" и проценты
    patterns = [
        r'Steam[^%]{0,150}?(\d{2}(?:\.\d)?)\s*%',
        r'(\d{2}(?:\.\d)?)\s*%[^%]{0,100}?Steam',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return [float(m) for m in matches[:5]]
    return None

print("═══════════════════════════════════════════════════")
print("  🔍 ПОЛНАЯ ПРОВЕРКА: СКУПЩИКИ + ЗАКУПКА")
print("═══════════════════════════════════════════════════")

# 1. Скупщики Steam
print("\n═══ 1. СКУПЩИКИ STEAM (реальные ставки) ═══")
buyers = [
    ("CardBix", "https://cardbix.com/rates"),
    ("GiftCardIo", "https://www.giftcardio.com/sell-steam-gift-card"),
    ("HighCardRate", "https://highcardrate.com/sell-steam-wallet-code"),
    ("Avanprice", "https://avanprice.com/sell-steam-gift-card"),
    ("Cashard", "https://www.cashard.com/sell-steam-gift-card"),
    ("SellCardNow", "https://sellcardnow.com/sell-steam-gift-card"),
]
for name, url in buyers:
    html = fetch(url)
    if not html:
        print(f"  ❌ {name}: не отвечает")
        continue
    rates = find_steam_rates(html, name)
    if rates:
        print(f"  ✅ {name}: до {max(rates):.1f}%")
    else:
        print(f"  ⚠️ {name}: % не найдены (JS/логин)")

# 2. Закупка: Plati.Market (турецкие Steam коды)
print("\n═══ 2. ЗАКУПКА: Plati.Market (Steam Turkey) ═══")
plati_url = "https://plati.market/search/Steam%20Wallet%20Turkey"
html = fetch(plati_url)
if html:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Ищем цены в рублях или долларах
    prices = re.findall(r'(\d+[.,]?\d*)\s*(?:₽|\$|USD|RUB)', text)
    if prices:
        print(f"  ✅ Найдены цены (первые 10): {prices[:10]}")
        print(f"  ⚠️ Нужно вручную проверить, какая цена за 10 USD Turkey")
    else:
        print(f"  ⚠️ Цены не найдены в HTML (возможно JS)")
else:
    print(f"  ❌ Plati.Market не отвечает")

# 3. Турецкие маркетплейсы (Oyunticareti, İtemSatış)
print("\n═══ 3. ТУРЕЦКИЕ МАРКЕТПЛЕЙСЫ (продажа) ═══")
for name, url in [
    ("Oyunticareti", "https://oyunticareti.com/steam"),
    ("İtemSatış", "https://www.itemsatis.com/steam-cuzdan-kodu"),
]:
    html = fetch(url)
    if html:
        print(f"  ✅ {name}: доступен (но нужна регистрация для цен)")
    else:
        print(f"  ❌ {name}: не отвечает")

# 4. Итоговый расчет
print("\n═══════════════════════════════════════════════════")
print("  📊 ИТОГОВЫЙ РАСЧЕТ")
print("═══════════════════════════════════════════════════")
print()
print("  FazerCards Turkey 10 USD:")
print("    Публичная цена: $10.01")
print("    Gold цена (скидка 3.55%): $9.66")
print()
print("  Скупщики (если платят 85%):")
print("    CardBix: $8.50 → профит -$1.16 (-12%) ❌")
print("    GiftCardIo (90%): $9.00 → профит -$0.66 (-6.8%) ❌")
print("    HighCardRate (84%): $8.40 → профит -$1.26 (-13%) ❌")
print()
print("  ВЫВОД: При закупке на FazerCards даже с Gold-планом")
print("         арбитраж Steam Turkey УБЫТОЧЕН.")
print()
print("  💡 Единственный шанс:")
print("    • Plati.Market (турецкие коды дешевле)")
print("    • Или продажа на турецких маркетплейсах (Oyunticareti)")
print("    • Или ждать акции FazerCards (-20% на Steam)")
