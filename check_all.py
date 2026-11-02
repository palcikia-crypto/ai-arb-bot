import requests, re, subprocess

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

# Проверяем несколько номиналов
nominals = [5, 10, 20, 50]
best_lot = None

for nominal in nominals:
    print(f"\n🔍 Проверяю Steam Turkey {nominal} USD (только в наличии)...")
    params = {
        "query": f"Steam Turkey {nominal} USD",
        "pagesize": 50,
        "pagenum": 1,
        "visibleOnly": "true",  # ВАЖНО: только доступные товары
        "response": "json"
    }
    
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        data = r.json()
        items = data.get("items", [])
        
        candidates = []
        for item in items:
            name = item.get("name_eng", "").lower() + " " + item.get("name", "").lower()
            price = item.get("price_usd")
            if not price: continue
            
            # Извлекаем первое число из названия
            m = re.search(r'(\d+)', name)
            if not m: continue
            first_num = int(m.group(1))
            
            # Проверяем, что номинал совпадает
            if first_num == nominal:
                translit = item.get("name_translit_eng") or item.get("name_translit")
                if translit:
                    candidates.append({
                        "nominal": nominal,
                        "price": float(price),
                        "seller": item.get("seller_name", ""),
                        "url": f"https://plati.market/itm/{translit}",
                        "name": item.get("name", "")[:60]
                    })
        
        if candidates:
            # Сортируем по цене
            candidates.sort(key=lambda x: x["price"])
            best_for_nominal = candidates[0]
            print(f"  ✅ Найдено {len(candidates)} лотов. Лучший: {best_for_nominal['seller']} за ${best_for_nominal['price']:.2f}")
            
            # Сравниваем с текущим лучшим
            if best_lot is None or best_for_nominal["price"] < best_lot["price"]:
                best_lot = best_for_nominal
        else:
            print(f"  ❌ Нет доступных лотов на {nominal} USD")
            
    except Exception as e:
        print(f"  ⚠️ Ошибка: {e}")

# Выводим итог и открываем лучший лот
print("\n" + "="*50)
if best_lot:
    print(f"🏆 ЛУЧШИЙ ЛОТ В НАЛИЧИИ:")
    print(f"   Номинал:   {best_lot['nominal']} USD")
    print(f"   Продавец:  {best_lot['seller']}")
    print(f"   Цена:      ${best_lot['price']:.2f}")
    print(f"   Название:  {best_lot['name']}")
    print(f"   Ссылка:    {best_lot['url']}")
    print()
    print(f"📊 Профит при сдаче в CardBix (90%): +${best_lot['nominal'] * 0.90 - best_lot['price']:.2f} ({(best_lot['nominal'] * 0.90 - best_lot['price'])/best_lot['price']*100:.1f}%)")
    print()
    print("🌐 Открываю в браузере...")
    subprocess.run(["termux-open-url", best_lot["url"]])
else:
    print("❌ Не найдено ни одного доступного лота. Попробуйте позже.")
