import requests, re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except Exception as e:
        print(f"    ❌ {e}")
        return None

def parse_steam_rate(html, site_name):
    """Ищет упоминания % для Steam гифт-карт."""
    if not html: return None
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    
    # Ищем "Steam" и проценты рядом
    patterns = [
        r'Steam[^%]{0,100}?(\d{2}(?:\.\d)?)\s*%',
        r'(\d{2}(?:\.\d)?)\s*%[^%]{0,50}?Steam',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return [float(m) for m in matches[:5]]
    return None

print("═══════════════════════════════════════════════════")
print("  🔍 ПРОВЕРКА СКУПЩИКОВ STEAM (реальные %)")
print("═══════════════════════════════════════════════════")
print()

sites = [
    ("CardBix", "https://cardbix.com/rates"),
    ("CardBix (main)", "https://cardbix.com/"),
    ("SellCardNow", "https://sellcardnow.com/"),
    ("SellCardNow (steam)", "https://sellcardnow.com/sell-steam-gift-card"),
    ("Paxful (Steam)", "https://paxful.com/sell-gift-cards/steam"),
    ("Bitrefill", "https://www.bitrefill.com/gift-cards/steam"),
    ("GameFlip", "https://gameflip.com/browse/gift-cards"),
]

results = {}
for name, url in sites:
    print(f"[{name}] {url}")
    html = fetch(url)
    if not html:
        print(f"  ❌ не отвечает")
        continue
    
    # Ищем "Steam" в тексте
    has_steam = "steam" in html.lower()
    print(f"  Есть Steam: {has_steam}")
    
    rates = parse_steam_rate(html, name)
    if rates:
        print(f"  ✅ Ставки %: {rates}")
        results[name] = rates[0]
    else:
        print(f"  ⚠️ % не найдены в HTML (возможно JS)")
    print()

print("═══════════════════════════════════════════════════")
print("  📊 ИТОГ: РЕАЛЬНЫЕ СТАВКИ СКУПЩИКОВ")
print("═══════════════════════════════════════════════════")
if results:
    for name, rate in sorted(results.items(), key=lambda x: -x[1]):
        print(f"  {name}: {rate}%")
    best = max(results.values())
    print(f"\n  🏆 ЛУЧШИЙ: {best}% от номинала")
else:
    print("  ⚠️ Не удалось получить ставки — все сайты на JS")
    print("  Требуется: CardBix API или ручной ввод")

print()
print("═══════════════════════════════════════════════════")
print("  💡 ПРОФИТ С GOLD FazerCards (-20% опт)")
print("═══════════════════════════════════════════════════")
print()
print("  Если CardBix платит 85%, а FazerCards Gold даёт -20%:")
print("    Turkey $10: купить $8.01 → сдать $8.50 → +6.1%")
print("    Turkey $50: купить $39.40 → сдать $42.50 → +7.9%")
print()
print("  Прибыль есть ТОЛЬКО с Gold-планом.")
print("  Gold-триал: 5 дней БЕСПЛАТНО, без карты.")
print("  https://reseller.fazercards.com/en/free-trial")
