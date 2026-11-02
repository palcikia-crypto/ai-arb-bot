import sys, re, requests
from pathlib import Path
from bs4 import BeautifulSoup

# Подключаем наш llm_backend
sys.path.append(str(Path.home() / "quantum_lab_sandbox" / "tools" / "agent_dev"))
try:
    from llm_backend import ask
    HAS_LLM = True
except Exception as e:
    HAS_LLM = False
    print(f"⚠️ LLM не подключен: {e}")

HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

# Что мы знаем о скупщиках (региональные ограничения)
BUYER_REGIONS = {
    "GiftCardIo":  "Принимает global/Turkey Steam gift cards (нужно проверить конкретную ставку)",
    "CardBix":     "Принимает Steam gift cards разных регионов (нужно проверить Turkey)",
    "Cashard":     "Принимает Steam gift cards (нужно проверить Turkey)",
    "SellCardNow": "Принимает Steam gift cards (нужно проверить Turkey)",
    "HighCardRate":"Принимает Steam gift cards (нужно проверить Turkey)",
}

def fetch_description(url):
    """Загружает страницу и извлекает описание товара."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        # Убираем скрипты/стили
        for s in soup(["script", "style", "noscript"]):
            s.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:3500]
    except Exception as e:
        return None

def rule_based_check(description):
    """Быстрая проверка на явные red flags."""
    d = description.lower()
    flags = []
    if "только для региона турция" in d or "только для турции" in d:
        flags.append("⚠️ Только для региона Турция")
    if "только для аккаунтов с валютой" in d and "usd" in d:
        flags.append("⚠️ Только для USD-аккаунтов")
    if "нельзя использовать" in d and "других стран" in d:
        flags.append("⚠️ Не работает в других странах")
    if "регион" in d and "турция" in d:
        if "только" in d or "исключительно" in d:
            flags.append("⚠️ Явное региональное ограничение")
    return flags

def llm_check(description, buyer_platform, nominal):
    """ИИ-проверка: может ли эта карта быть продана на скупщике."""
    if not HAS_LLM:
        return {"verdict": "UNKNOWN", "reason": "LLM не подключен"}
    
    buyer_info = BUYER_REGIONS.get(buyer_platform, "Информации о региональных ограничениях нет")
    
    prompt = f"""Описание товара с Plati.Market:
{description}

Товар: Steam Turkey {nominal} USD gift card.
Покупатель (скупщик): {buyer_platform} — {buyer_info}

Вопрос: 
1. Для какого региона эта карта? (Steam Turkey, USD-аккаунт)
2. Можно ли её продать на {buyer_platform}? Есть ли риск, что {buyer_platform} откажется её принять из-за региональных ограничений?

Ответ строго:
ВЕРДИКТ: SAFE или RISKY или INCOMPATIBLE
РЕГИОН_КАРТЫ: <регион>
ПРИЧИНА: <1 предложение>"""
    
    try:
        ans = ask(prompt, system_prompt="Ты анализируешь совместимость подарочных карт. Отвечай кратко, по шаблону.")
    except Exception as e:
        return {"verdict": "UNKNOWN", "reason": f"LLM ошибка: {e}"}
    
    verdict = "UNKNOWN"
    region = "?"
    reason = ""
    for line in ans.split("\n"):
        if "ВЕРДИКТ:" in line:
            v = line.split(":", 1)[1].strip().upper()
            if "SAFE" in v: verdict = "SAFE"
            elif "RISKY" in v: verdict = "RISKY"
            elif "INCOMPATIBLE" in v: verdict = "INCOMPATIBLE"
        elif "РЕГИОН_КАРТЫ:" in line:
            region = line.split(":", 1)[1].strip()
        elif "ПРИЧИНА:" in line:
            reason = line.split(":", 1)[1].strip()
    
    return {"verdict": verdict, "region": region, "reason": reason, "raw": ans[:300]}

def check_bundle(product_url, buyer_platform, nominal):
    """Полная проверка: правила + ИИ."""
    desc = fetch_description(product_url)
    if not desc:
        return {"verdict": "UNKNOWN", "reason": "Не удалось загрузить описание"}
    
    flags = rule_based_check(desc)
    llm_result = llm_check(desc, buyer_platform, nominal)
    
    # Комбинируем
    final_verdict = llm_result["verdict"]
    if flags and final_verdict == "SAFE":
        final_verdict = "RISKY"
    
    return {
        "verdict": final_verdict,
        "region": llm_result.get("region", "?"),
        "reason": llm_result.get("reason", ""),
        "flags": flags,
        "buyer": buyer_platform,
    }

if __name__ == "__main__":
    # Тест: проверяем текущую связку
    print("═══ ТЕСТ: Plati 10 USD → GiftCardIo ═══")
    result = check_bundle(
        "https://plati.market/itm/4377178",
        "GiftCardIo",
        10
    )
    print(f"\nВердикт:   {result['verdict']}")
    print(f"Регион:    {result['region']}")
    print(f"Причина:   {result['reason']}")
    print(f"Red flags: {result['flags']}")
