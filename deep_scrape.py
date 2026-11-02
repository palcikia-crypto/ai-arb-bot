import requests, re, json, time
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
MOBILE_HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"}

PLATFORMS = {
    "GiftCardIo": {
        "url": "https://www.giftcardio.com/sell-steam-gift-card",
        "domains": ["www.giftcardio.com", "giftcardio.com"],
    },
    "CardBix": {
        "url": "https://cardbix.com/rates",
        "domains": ["cardbix.com", "www.cardbix.com"],
    },
    "Cashard": {
        "url": "https://www.cashard.com/",
        "domains": ["www.cashard.com", "cashard.com"],
    },
    "SellCardNow": {
        "url": "https://sellcardnow.com/",
        "domains": ["sellcardnow.com", "www.sellcardnow.com"],
    },
}

def try_jina_reader(url):
    """ЛАЙФХАК 1: Jina AI Reader — рендерит JS на сервере, отдаёт markdown."""
    print(f"  [Jina] {url}")
    try:
        r = requests.get(f"https://r.jina.ai/{url}", headers=HEADERS, timeout=40)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception as e:
        print(f"    ⚠️ {e}")
    return None

def try_mobile_ua(url):
    """ЛАЙФХАК 2: мобильный User-Agent — часто отдаёт простой HTML."""
    print(f"  [Mobile] {url}")
    try:
        r = requests.get(url, headers=MOBILE_HEADERS, timeout=15)
        if r.status_code == 200:
            return r.text
    except: pass
    return None

def try_wayback(url):
    """ЛАЙФХАК 3: Wayback Machine — архивные копии (обход 403)."""
    print(f"  [Wayback] {url}")
    try:
        r = requests.get(f"http://archive.org/wayback/available?url={url}", timeout=15)
        data = r.json()
        snapshot = data.get("archived_snapshots", {}).get("closest", {})
        if snapshot.get("url"):
            print(f"    → snapshot: {snapshot['url']}")
            r2 = requests.get(snapshot["url"], headers=HEADERS, timeout=15)
            if r2.status_code == 200:
                return r2.text
    except Exception as e:
        print(f"    ⚠️ {e}")
    return None

def find_next_data(html):
    """ЛАЙФХАК 4: __NEXT_DATA__ (Next.js) — данные встроены в HTML."""
    if not html: return None
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except: pass
    return None

def find_api_endpoints(html):
    """ЛАЙФХАК 5: поиск API endpoints в JS-бандлах."""
    if not html: return []
    endpoints = set()
    # 1. Из HTML
    for m in re.finditer(r'["\'](/(?:api|v\d+)/[\w/\-\.]+)["\']', html):
        endpoints.add(m.group(1))
    # 2. Из JS-файлов
    js_urls = re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)
    for js in js_urls[:3]:
        if not js.startswith("http"):
            js = "https://" + js.lstrip("/")
        try:
            r = requests.get(js, headers=HEADERS, timeout=10)
            for m in re.finditer(r'["\'](/(?:api|v\d+)/[\w/\-\.]+)["\']', r.text):
                endpoints.add(m.group(1))
        except: pass
    return list(endpoints)[:10]

def try_api_endpoints(domain, endpoints):
    """ЛАЙФХАК 6: пробуем найденные API endpoints на Turkey."""
    results = {}
    for ep in endpoints:
        for proto in ["https://"]:
            for dom in [domain]:
                url = f"{proto}{dom}{ep}"
                try:
                    r = requests.get(url, headers=HEADERS, timeout=10)
                    if r.status_code == 200 and len(r.text) > 100:
                        # Ищем Turkey
                        text_lower = r.text.lower()
                        if "turkey" in text_lower or "turkish" in text_lower or "steam" in text_lower:
                            results[url] = r.text[:1500]
                except: continue
    return results

def search_indexed(platform, domains):
    """ЛАЙФХАК 7: поиск индексированных страниц с Turkey через DuckDuckGo."""
    found = []
    for dom in domains:
        q = f"site:{dom} turkey steam"
        try:
            r = requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for res in soup.select(".result")[:5]:
                    a = res.select_one(".result__a")
                    snip = res.select_one(".result__snippet")
                    if a and snip:
                        found.append({
                            "title": a.get_text(strip=True)[:100],
                            "snippet": snip.get_text(strip=True)[:200],
                            "url": a.get("href", "")
                        })
        except: pass
    return found

def main():
    print("=" * 70)
    print("  🕵️ DEEP SCRAPE: 7 ЛАЙФХАКОВ")
    print("=" * 70)

    for name, cfg in PLATFORMS.items():
        print(f"\n{'='*60}")
        print(f"  📦 {name}")
        print(f"{'='*60}")

        results = {"platform": name}

        # 1. Jina Reader
        jina = try_jina_reader(cfg["url"])
        if jina:
            print(f"  ✅ Jina: {len(jina)} символов")
            results["jina"] = jina[:3000]
        else:
            print(f"  ❌ Jina не сработал")

        # 2. Мобильный UA
        mobile = try_mobile_ua(cfg["url"])
        if mobile:
            print(f"  ✅ Mobile: {len(mobile)} символов")
            results["mobile"] = mobile[:3000]

        # 3. Wayback
        wayback = try_wayback(cfg["url"])
        if wayback:
            print(f"  ✅ Wayback: {len(wayback)} символов")
            results["wayback"] = wayback[:3000]

        # 4. __NEXT_DATA__
        for html_src_name, html_src in [("main", mobile), ("wayback", wayback)]:
            if not html_src: continue
            nd = find_next_data(html_src)
            if nd:
                print(f"  ✅ __NEXT_DATA__ найден ({html_src_name}), {len(str(nd))} символов")
                json_str = json.dumps(nd, ensure_ascii=False)
                # Ищем Turkey
                if "turkey" in json_str.lower() or "turkish" in json_str.lower():
                    idx = json_str.lower().find("turkey")
                    print(f"     🎯 TURKEY НАЙДЕН: ...{json_str[max(0,idx-100):idx+100]}...")
                    results["next_data_turkey"] = json_str[max(0,idx-200):idx+500]
                else:
                    results["next_data"] = json_str[:2000]

        # 5. API endpoints
        source_html = mobile or wayback or jina
        endpoints = find_api_endpoints(source_html)
        if endpoints:
            print(f"  🔍 Найдено {len(endpoints)} API endpoints: {endpoints[:5]}")
            api_results = try_api_endpoints(cfg["domains"][0], endpoints)
            if api_results:
                print(f"  ✅ API нашёл данные: {list(api_results.keys())}")
                results["api"] = {k: v[:500] for k, v in list(api_results.items())[:3]}
            else:
                print(f"  ⚠️ API endpoints не дали данных с Turkey")

        # 6. Поиск индексированных
        print(f"  🔍 Ищем индексированные страницы...")
        indexed = search_indexed(name, cfg["domains"])
        if indexed:
            print(f"  ✅ Найдено {len(indexed)} результатов:")
            for item in indexed[:3]:
                print(f"     - {item['title'][:60]}")
                print(f"       {item['snippet'][:100]}")
            results["indexed"] = indexed[:5]

        # 7. Финальный ИИ-анализ по всем данным
        with open(f"deep_{name.lower()}.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("  📋 ИТОГ: файлы сохранены")
    print("=" * 70)
    for name in PLATFORMS:
        fn = f"deep_{name.lower()}.json"
        try:
            data = json.load(open(fn))
            sources = [k for k in data.keys() if k != "platform"]
            print(f"  {name}: {sources}")
        except:
            print(f"  {name}: не сохранено")

if __name__ == "__main__":
    main()
