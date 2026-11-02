import json, re, sys
from pathlib import Path

sys.path.append(str(Path.home() / "quantum_lab_sandbox" / "tools" / "agent_dev"))
from llm_backend import ask

def find_context(text, keywords, window=300):
    """Ищет ключевые слова и возвращает контекст."""
    results = []
    text_lower = text.lower()
    for kw in keywords:
        idx = 0
        while True:
            idx = text_lower.find(kw, idx)
            if idx == -1: break
            context = text[max(0, idx-window):idx+window]
            # Чистим от HTML-тегов
            context = re.sub(r'<[^>]+>', ' ', context)
            context = re.sub(r'\s+', ' ', context).strip()
            if len(context) > 50:
                results.append(f"[{kw}] {context}")
            idx += len(kw)
            if len(results) > 10: break
        if len(results) > 10: break
    return results

def analyze_file(filename, platform):
    print(f"\n{'='*60}")
    print(f"  📦 {platform} — {filename}")
    print(f"{'='*60}")
    
    try:
        data = json.load(open(filename))
    except:
        print(f"  ❌ Файл не найден")
        return
    
    # Собираем весь текст из всех полей
    all_text = ""
    for key, val in data.items():
        if key == "platform": continue
        if isinstance(val, str):
            all_text += f"\n\n=== {key} ===\n{val}"
        elif isinstance(val, dict):
            for k, v in val.items():
                all_text += f"\n\n=== {key}.{k} ===\n{v}"
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    all_text += f"\n{item.get('title','')} — {item.get('snippet','')}"
    
    print(f"  📊 Всего текста: {len(all_text)} символов")
    
    # Ищем ключевые слова
    keywords = ["turkey", "turkish", "steam turkey", "85%", "86%", "rate", "steam"]
    contexts = find_context(all_text, keywords)
    
    if contexts:
        print(f"\n  🔍 Найдено {len(contexts)} контекстов:")
        for c in contexts[:8]:
            print(f"  {c[:200]}")
    else:
        print(f"  ⚠️ Ничего не найдено")
    
    # ИИ анализирует
    if contexts:
        prompt = f"""Площадка: {platform}
Вот фрагменты текста с их сайта (найденные по ключевым словам):

{chr(10).join(contexts[:10])[:3000]}

ВОПРОС: Принимает ли {platform} подарочные карты Steam Turkey (турецкий регион)?

Ответ СТРОГО:
ПРИНИМАЕТ_TURKEY: ДА / НЕТ / НЕИЗВЕСТНО
СТАВКА: <число %> или НЕИЗВЕСТНО
ЦИТАТА: <цитата из текста>"""
        
        try:
            ans = ask(prompt, system_prompt="Анализируй текст. Отвечай по шаблону.")
            print(f"\n  🤖 ИИ-вердикт:")
            print(f"  {ans[:500]}")
        except Exception as e:
            print(f"  ⚠️ ИИ ошибка: {e}")

def main():
    files = [
        ("deep_giftcardio.json", "GiftCardIo"),
        ("deep_cashard.json", "Cashard"),
        ("deep_sellcardnow.json", "SellCardNow"),
        ("deep_cardbix.json", "CardBix"),
    ]
    for fn, name in files:
        if Path(fn).exists():
            analyze_file(fn, name)

if __name__ == "__main__":
    main()
