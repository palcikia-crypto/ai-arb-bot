import platform, re, json

print("="*70)
print(f"  🔬 PROBER v2 | arch={platform.machine()} | py={platform.python_version()}")
print("="*70)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}

try:
    import cloudscraper; HAS_CS = True; print("✅ cloudscraper установлен")
except ImportError: HAS_CS = False; print("❌ cloudscraper НЕТ")

try:
    from curl_cffi import requests as cffi; HAS_CFFI = True; print("✅ curl_cffi установлен")
except ImportError: HAS_CFFI = False; print("❌ curl_cffi НЕТ")

def try_cs(url):
    try:
        s = cloudscraper.create_scraper()
        r = s.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            print(f"    ✅ [{r.status_code}] {len(r.text)}b  cloudscraper")
            return r.text
        print(f"    ❌ [{r.status_code}] cloudscraper")
    except Exception as e:
        print(f"    ❌ cloudscraper ERR: {type(e).__name__}")
    return None

def try_cffi(url, imp):
    try:
        r = cffi.get(url, impersonate=imp, timeout=20)
        if r.status_code == 200:
            print(f"    ✅ [{r.status_code}] {len(r.text)}b  curl_cffi({imp})")
            return r.text
        print(f"    ❌ [{r.status_code}] curl_cffi({imp})")
    except Exception as e:
        print(f"    ❌ curl_cffi({imp}) ERR: {type(e).__name__}")
    return None

def probe(name, urls):
    print(f"\n{'='*70}\n  🔍 {name}\n{'='*70}")
    for url in urls:
        print(f"  → {url}")
        body = try_cs(url) if HAS_CS else None
        if not body and HAS_CFFI:
            for imp in ["chrome131", "chrome124", "chrome120", "safari17_0", "firefox133"]:
                body = try_cffi(url, imp)
                if body: break
        if body:
            m = re.search(r'Steam[^0-9%]{0,50}(\d{1,3})\s*%', body, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                if 50 <= val <= 95:
                    print(f"    🎯 СТАВКА STEAM НАЙДЕНА: {val}%")
                    return url, val
            else:
                # Поиск в JSON-полях
                m2 = re.search(r'"(?:rate|percent|payout)"\s*:\s*"?(\d{1,2})', body)
                if m2:
                    val = int(m2.group(1))
                    if 50 <= val <= 95:
                        print(f"    🎯 СТАВКА В JSON: {val}%")
                        return url, val
            print("    ⚠️  Загрузилось, но ставки в HTML нет (нужен JS-рендер)")
            return url, None
    return None, None

results = {}
for name, urls in [
    ("CardBix", ["https://cardbix.com/", "https://cardbix.com/rates"]),
    ("GiftCardIo", ["https://giftcardio.com/", "https://giftcardio.com/sell-gift-cards"]),
    ("Cashard", ["https://cashard.com/"]),
    ("HighCardRate", ["https://highcardrate.com/blog/sell-gift-cards-for-bitcoin-btc-guide"]),
]:
    url, rate = probe(name, urls)
    results[name] = {"url": url, "rate": rate}

print(f"\n{'='*70}\n  📊 ИТОГ\n{'='*70}")
for name, r in results.items():
    if r["url"] and r["rate"]:
        print(f"✅ {name}: {r['rate']}% (живая ставка!)")
    elif r["url"]:
        print(f"⚠️  {name}: HTML грузится, но ставка только через JS")
    else:
        print(f"❌ {name}: не пробился")

with open("prober_v2_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
