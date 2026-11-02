import requests, json, re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
}

def try_ep(method, url, payload=None, ref=None):
    h = dict(HEADERS)
    if ref:
        base = "https://" + url.split("/")[2]
        h["Origin"] = base
        h["Referer"] = base + "/"
    try:
        if method == "GET":
            r = requests.get(url, headers=h, timeout=10)
        else:
            r = requests.post(url, headers=h, json=payload, timeout=10)
        s = r.status_code
        size = len(r.text)
        snippet = r.text[:120].replace("\n", " ")
        ok = s == 200 and size > 15 and "not found" not in snippet.lower() and "<html" not in snippet.lower()[:50]
        mark = "✅" if ok else "❌"
        print(f"    {mark} [{s}] {size}b  {method} {url}")
        if ok:
            print(f"       → {snippet}")
        return (url, r.text) if ok else None
    except Exception as e:
        print(f"    ❌ ERR {method} {url}  ({type(e).__name__})")
        return None

def probe(name, base, eps):
    print(f"\n{'='*60}\n🔍 {name}  ({base})\n{'='*60}")
    hits = []
    for m, p, pl in eps:
        res = try_ep(m, base + p, pl, ref=base)
        if res: hits.append(res)
    print(f"\n  {'🏆 Найдено: ' + str(len(hits)) if hits else '⚠️ 0 эндпоинтов'}")
    return hits

# === CARDBIX ===
cb = [
    ("GET", "/api/rates", None),
    ("GET", "/api/v1/rates", None),
    ("GET", "/api/rates/steam", None),
    ("GET", "/api/v1/rates/steam", None),
    ("GET", "/api/calculator/steam", None),
    ("POST", "/api/rates", {"card": "steam", "amount": 10}),
    ("POST", "/api/v1/rate", {"brand": "steam", "value": 10}),
    ("POST", "/api/calc", {"brand": "steam", "amount": 10, "currency": "USD"}),
    ("POST", "/api/calculator", {"brand": "steam", "amount": 10}),
    ("POST", "/api/price", {"product": "steam_10"}),
    ("POST", "/api/quote", {"product": "steam", "denom": 10}),
]

# === SELLCARDNOW ===
sn = [
    ("GET", "/api/rates", None),
    ("GET", "/api/v1/rates", None),
    ("GET", "/api/rates/steam", None),
    ("GET", "/api/calc?card=steam&amount=10&country=US", None),
    ("POST", "/api/rate", {"card_type": "steam", "amount": 10, "country": "US"}),
    ("POST", "/api/calc", {"card": "steam", "amount": 10, "region": "US"}),
    ("POST", "/api/quote", {"card": "steam", "amount": 10}),
    ("POST", "/api/v1/quote", {"brand": "steam", "denomination": 10}),
    ("POST", "/api/payout", {"card": "steam", "amount": 10}),
]

# === GIFTCARDIO ===
gi = [
    ("GET", "/api/rates", None),
    ("GET", "/api/offers?brand=steam", None),
    ("GET", "/api/search?q=steam", None),
    ("GET", "/api/v1/products?brand=steam", None),
]

# === CASHARD ===
ch = [
    ("GET", "/api/rates", None),
    ("GET", "/api/rate?brand=steam", None),
    ("GET", "/api/v1/rates", None),
]

print("="*60)
print("  🔬 API PROBER — ищу JSON-эндпоинты скупщиков")
print("="*60)

all_hits = {
    "CardBix":     probe("CardBix",     "https://cardbix.com",     cb),
    "SellCardNow": probe("SellCardNow", "https://sellcardnow.com", sn),
    "GiftCardIo":  probe("GiftCardIo",  "https://giftcardio.com",  gi),
    "Cashard":     probe("Cashard",     "https://cashard.com",     ch),
}

# === ИТОГ + СОХРАНЕНИЕ ===
print(f"\n{'='*60}\n📊 ИТОГ\n{'='*60}")
summary = {}
for name, hits in all_hits.items():
    if hits:
        url, text = hits[0]
        print(f"✅ {name}: {url}")
        print(f"   {text[:300]}")
        summary[name] = {"url": url, "sample": text[:1000]}
    else:
        print(f"❌ {name}: 0 эндпоинтов")

with open("api_probe_results.json", "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(f"\n💾 Сохранено в api_probe_results.json")
