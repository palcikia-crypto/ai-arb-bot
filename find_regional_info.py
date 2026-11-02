import sys, re, json, requests
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.append(str(Path.home() / "quantum_lab_sandbox" / "tools" / "agent_dev"))
from llm_backend import ask
from ai_agent import web_search

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

# ===== СТРАНИЦЫ СКУПЩИКОВ (FAQ, terms, supported cards) =====
PAGES = {
    "GiftCardIo": [
        "https://www.giftcardio.com/",
        "https://www.giftcardio.com/faq",
        "https://www.giftcardio.com/sell-steam-gift-card",
        "https://www.giftcardio.com/terms",
    ],
    "CardBix": [
        "https://cardbix.com/",
        "https://cardbix.com/faq",
        "https://cardbix.com/supported-cards",
    ],
    "Cashard": [
        "https://www.cashard.com/",
        "https://www.cashard.com/faq",
    ],
    "SellCardNow": [
        "https://sellcardnow.com/",
        "https://sellcardnow.com/faq",
    ],
}

def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200:
            return None, r.status_code
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(["script", "style", "noscript"]):
            s.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:4000], 200
    except Exception as e:
        return None, str(e)[:50]

def search_platform_info(platform):
    """DuckDuckGo: ищет инфо про Turkey в этом скупщике."""
    query = f"{platform} Steam Turkey gift card accepted rate"
    print(f"\n  🔍 Поиск: {query}")
    try:
        result = web_search(query, max_results=5)
        return result
    except Exception as e:
        return f"search_error: {e}"

def analyze_with_llm(platform, fetched_text, search_text):
    """ИИ анализирует всё найденное и делает вердикт."""
    prompt = f"""Площадка: {platform}

Текст с их сайта (первые 4000 символов):
{fetched_text[:3000] if fetched_text else "(сайт не отвечает)"}

Результаты поиска в интернете:
{search_text[:2500]}

ВОПРОС: Принимает ли {platform} подарочные карты Steam Turkey (Turkish region, USD wallet) для выкупа?

Ответ СТРОГО по шаблону:
ПРИНИМАЕТ_TURKEY: ДА / НЕТ / НЕИЗВЕСТНО
СТАВКА: <число %> или НЕИЗВЕСТНО
ДОКАЗАТЕЛЬСТВО: <цитата из текста или поиска, 1-2 предложения>"""

    try:
        ans = ask(prompt, system_prompt="Ты анализируешь инфо о gift card скупщиках. Отвечай по шаблону.")
    except Exception as e:
        return {"accepts": "ERROR", "rate": "?", "reason": str(e)[:100]}

    result = {"accepts": "НЕИЗВЕСТНО", "rate": "НЕИЗВЕСТНО", "reason": ""}
    for line in ans.split("\n"):
        if "ПРИНИМАЕТ_TURKEY:" in line:
            v = line.split(":", 1)[1].strip().upper()
            if "ДА" in v: result["accepts"] = "ДА"
            elif "НЕТ" in v: result["accepts"] = "НЕТ"
            else: result["accepts"] = "НЕИЗВЕСТНО"
        elif "СТАВКА:" in line:
            result["rate"] = line.split(":", 1)[1].strip()
        elif "ДОКАЗАТЕЛЬСТВО:" in line:
            result["reason"] = line.split(":", 1)[1].strip()
    return result

def main():
    print("=" * 70)
    print("  🕵️ ИИ-ДЕТЕКТИВ: ищем кто принимает Steam Turkey")
    print("=" * 70)

    results = {}

    for platform, urls in PAGES.items():
        print(f"\n{'='*50}")
        print(f"  📦 {platform}")
        print(f"{'='*50}")

        # 1. Прямой fetch всех страниц
        combined_text = ""
        for url in urls:
            text, status = fetch(url)
            if text:
                print(f"  ✅ {url[:60]} — {len(text)} символов")
                combined_text += f"\n\n[{url}]\n{text[:1500]}"
            else:
                print(f"  ⚠️ {url[:60]} — {status}")

        # 2. Поиск в интернете
        search_text = search_platform_info(platform)
        print(f"  🔍 Найдено сниппетов: {len(search_text)} символов")

        # 3. ИИ-анализ
        print(f"  🤖 ИИ анализирует...")
        verdict = analyze_with_llm(platform, combined_text, search_text)
        results[platform] = verdict

        print(f"\n  📊 ВЕРДИКТ для {platform}:")
        print(f"     Принимает Turkey: {verdict['accepts']}")
        print(f"     Ставка:           {verdict['rate']}")
        print(f"     Доказательство:   {verdict['reason'][:200]}")

    # ===== ИТОГ =====
    print("\n" + "=" * 70)
    print("  📋 ИТОГ: кто принимает Turkey")
    print("=" * 70)
    for platform, verdict in results.items():
        marker = "✅" if verdict["accepts"] == "ДА" else "❌" if verdict["accepts"] == "НЕТ" else "❓"
        print(f"  {marker} {platform:15} — Turkey: {verdict['accepts']:12} | Ставка: {verdict['rate']}")

    # Сохраняем
    with open("regional_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Сохранено в regional_results.json")

if __name__ == "__main__":
    main()
