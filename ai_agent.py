import re, json, requests, sys, time
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

sys.path.append('/data/data/com.termux/files/home/quantum_lab_sandbox/tools/agent_dev')
try:
    from llm_backend import ask
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    print("⚠️ llm_backend не найден")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

def web_search(query, max_results=5):
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=HEADERS, timeout=15)
        if r.status_code != 200: return f"SEARCH_ERROR: HTTP {r.status_code}"
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for res in soup.select(".result")[:max_results]:
            a = res.select_one(".result__a")
            snip = res.select_one(".result__snippet")
            if a:
                href = a.get("href", "")
                m = re.search(r'uddg=([^&]+)', href)
                if m: href = unquote(m.group(1))
                title = a.get_text(strip=True)
                body = snip.get_text(strip=True) if snip else ""
                results.append(f"URL: {href}\n  {title}: {body[:150]}")
        return "\n".join(results) if results else "НЕТ РЕЗУЛЬТАТОВ"
    except Exception as e:
        return f"SEARCH_ERROR: {e}"

def web_fetch(url, max_chars=4000):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return f"FETCH_ERROR: HTTP {r.status_code}"
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(["script", "style", "noscript"]): s.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:max_chars]
    except Exception as e:
        return f"FETCH_ERROR: {e}"

def llm_extract_unit_price(text, item_name):
    """LLM извлекает цену ЗА 1 ЕДИНИЦУ (делит цену пакета на количество)."""
    if not HAS_LLM: return None
    prompt = f"""Текст страницы:
{text[:4000]}

ЗАДАЧА: найди цену за 1 единицу товара '{item_name}' в USD.
Если на странице есть пакеты (например "200 Robux = $2.25"), вычисли цену за 1 Robux: 2.25 / 200 = 0.01125.
Если цены в рублях — переведи в USD по курсу 90.
Если цены нет — ответь NONE.

Ответ: ТОЛЬКО число (например 0.01125) или NONE."""
    try:
        ans = ask(prompt, system_prompt="Отвечай только числом или NONE.")
        ans = ans.strip().replace(",", ".")
        m = re.search(r'\d+\.\d+', ans)
        return float(m.group(0)) if m else None
    except: return None

def find_price_via_search(item_name, search_query):
    """Поиск + fetch + LLM extraction. Возвращает (price_usd, url)."""
    print(f"  🔍 Поиск: {search_query}")
    search_result = web_search(search_query)
    urls = re.findall(r'URL: (\S+)', search_result)
    print(f"  → Найдено URL: {len(urls)}")
    
    for i, url in enumerate(urls[:3]):
        print(f"  📥 Читаем [{i+1}/3]: {url[:80]}")
        page_text = web_fetch(url)
        if page_text.startswith("FETCH_ERROR"): continue
        
        price = llm_extract_unit_price(page_text, item_name)
        if price and 0.0001 < price < 100:
            print(f"    ✅ Цена: ${price:.5f}")
            return price, url
        else:
            print(f"    ❌ Цена не найдена")
    return None, None

# --- ПОИСК ЦЕН ---
def find_fazercards_robux():
    return find_price_via_search("Robux", "FazerCards Robux wholesale price per 1 Robux")

def find_fazercards_steam():
    return find_price_via_search("Steam Gift $10", "FazerCards Steam gift card $10 wholesale price")

def find_fazercards_stars():
    return find_price_via_search("Telegram Star", "FazerCards Telegram Stars wholesale price per star")

def find_rbxstock_bid():
    return find_price_via_search("Robux", "RBXSTOCK Robux buy rate per 1000")

def find_cardbix_steam_rate():
    return find_price_via_search("Steam Gift $10", "CardBix Steam gift card buy rate")

def find_starsei_bid():
    return find_price_via_search("Telegram Star", "Starsei Telegram Stars buy rate per star")

if __name__ == "__main__":
    t0 = time.time()
    print("\n═══════════ ТЕСТ: FAZERCARDS ROBUX ═══════════")
    price, url = find_fazercards_robux()
    print(f"\nРезультат: price=${price}, url={url}")
    print(f"Время: {time.time()-t0:.1f}с")
