import requests, re, json, time, threading, subprocess
from bs4 import BeautifulSoup
from http.server import HTTPServer, BaseHTTPRequestHandler

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
CACHE = {"data": [], "summary": "", "updated": 0}

# === СКУПЩИКИ (реальные ставки) ===
BUYERS = {
    "CardBix":    0.85,  # проверено
    "GiftCardIo": 0.86,  # проверено
    "Cashard":    0.70,
    "SellCardNow": 0.85,  # предположительно
    "HighCardRate": 0.84,
}

# === НОМИНАЛЫ ===
NOMINALS = [5, 10, 20, 50, 100]

def fetch_plati_lots(nominal):
    """Все доступные лоты на Plati для номинала (где nominal = минимальный)."""
    params = {
        "query": f"Steam Turkey {nominal} USD",
        "pagesize": 50, "pagenum": 1,
        "visibleOnly": "true", "response": "json"
    }
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=20)
        items = r.json().get("items", [])
    except Exception as e:
        print(f"  ⚠️ API error {nominal}: {e}")
        return []
    
    lots = []
    for item in items:
        name = item.get("name_eng", "").lower() + " " + item.get("name", "").lower()
        price = item.get("price_usd")
        url = item.get("url")
        if not price or not url: continue
        m = re.search(r'(\d+)', name)
        if not m: continue
        if int(m.group(1)) != nominal: continue
        if price < nominal * 0.4: continue  # отсев фейков
        lots.append({
            "nominal": nominal,
            "price": float(price),
            "seller": item.get("seller_name", ""),
            "url": url,
            "name": item.get("name", "")[:50],
        })
    lots.sort(key=lambda x: x["price"])
    return lots

def fetch_fazercards_turkey():
    """Публичные цены FazerCards Turkey (HTML)."""
    try:
        r = requests.get("https://reseller.fazercards.com/en/catalog/steam/turkey", 
                         headers=HEADERS, timeout=20)
        if r.status_code != 200: return []
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        # Ищем пары "X USD $Y"
        pairs = re.findall(r'(\d+)\s*USD\s*\$\s*([\d.]+)', text)
        seen = set()
        lots = []
        for nominal_str, price_str in pairs:
            nominal = int(nominal_str)
            price = float(price_str)
            if nominal < 5: continue
            key = (nominal, price)
            if key in seen: continue
            seen.add(key)
            # Применяем скидку Gold (3.55%) — предполагаем, что она есть
            price_gold = round(price * 0.9645, 2)
            lots.append({
                "source": "FazerCards",
                "nominal": nominal,
                "price": price_gold,
                "price_public": price,
                "url": "https://reseller.fazercards.com/en/catalog/steam/turkey",
            })
        return lots
    except Exception as e:
        print(f"FazerCards error: {e}")
        return []

def scan():
    print("\n" + "="*70)
    print("  🚀 SUPER SCAN: PLATI + FAZERCARDS + 5 СКУПЩИКОВ")
    print("="*70)
    
    all_spreads = []
    summary_lines = []
    
    # === 1. Plati.Market ===
    print("\n📡 Сканирую Plati.Market...")
    plati_lots = {}
    for nom in NOMINALS:
        lots = fetch_plati_lots(nom)
        if lots:
            plati_lots[nom] = lots
            print(f"  [{nom} USD] {len(lots)} лотов, дешёвый: {lots[0]['seller']} ${lots[0]['price']:.2f}")
        else:
            print(f"  [{nom} USD] нет лотов")
    
    # === 2. FazerCards ===
    print("\n📡 Сканирую FazerCards Turkey...")
    fc_lots = fetch_fazercards_turkey()
    fc_by_nominal = {}
    for lot in fc_lots:
        if lot["nominal"] not in fc_by_nominal or lot["price"] < fc_by_nominal[lot["nominal"]]["price"]:
            fc_by_nominal[lot["nominal"]] = lot
    for nom, lot in sorted(fc_by_nominal.items()):
        print(f"  [{nom} USD] ${lot['price']} (public ${lot['price_public']})")
    
    # === 3. Считаем связки ===
    print("\n" + "="*70)
    print("  📊 РАСЧЁТ ВСЕХ СВЯЗОК")
    print("="*70)
    
    sources = []
    for nom, lots in plati_lots.items():
        sources.append((f"Plati {nom} USD", nom, lots[0]["price"], lots[0]["url"], lots[0]["seller"]))
    for nom, lot in fc_by_nominal.items():
        sources.append((f"FazerCards {nom} USD", nom, lot["price"], lot["url"], "FazerCards"))
    
    for source_name, nominal, buy_price, buy_url, buy_seller in sources:
        print(f"\n📦 {source_name} — купить ${buy_price:.2f} у {buy_seller}")
        best_for_source = None
        for buyer_name, buyer_rate in BUYERS.items():
            sell = nominal * buyer_rate
            profit = sell - buy_price
            pct = (profit / buy_price * 100) if buy_price > 0 else 0
            marker = "✅" if profit > 0 else "❌"
            print(f"   {marker} {buyer_name} ({buyer_rate*100:.0f}%): ${sell:.2f} → {profit:+.2f} ({pct:+.1f}%)")
            if profit > 0 and (best_for_source is None or profit > best_for_source["profit"]):
                best_for_source = {
                    "source": source_name,
                    "nominal": nominal,
                    "buy_price": round(buy_price, 2),
                    "buy_url": buy_url,
                    "buy_seller": buy_seller,
                    "sell_platform": buyer_name,
                    "sell_rate": buyer_rate,
                    "sell_price": round(sell, 2),
                    "profit": round(profit, 2),
                    "profit_pct": round(pct, 1),
                }
        if best_for_source:
            all_spreads.append(best_for_source)
            summary_lines.append(f"{source_name}: ✅ {best_for_source['profit_pct']:+.1f}% через {best_for_source['sell_platform']}")
        else:
            summary_lines.append(f"{source_name}: ❌ убыток")
    
    # === 4. Сортируем и выводим ===
    all_spreads.sort(key=lambda x: x["profit_pct"], reverse=True)
    
    print("\n" + "="*70)
    print("  🏆 ТОП-5 ЛУЧШИХ СВЯЗОК")
    print("="*70)
    for i, s in enumerate(all_spreads[:5], 1):
        print(f"  {i}. {s['source']} → {s['sell_platform']}")
        print(f"     Купить: ${s['buy_price']} у {s['buy_seller']}")
        print(f"     Сдать:  ${s['sell_price']} ({s['sell_rate']*100:.0f}%)")
        print(f"     Профит: +${s['profit']} ({s['profit_pct']:+.1f}%)")
        print(f"     Ссылка: {s['buy_url']}")
        print()
    
    print("  📋 ИТОГ:")
    for line in summary_lines:
        print(f"    {line}")
    
    CACHE["data"] = all_spreads
    CACHE["summary"] = " | ".join(summary_lines)
    CACHE["updated"] = time.time()
    
    # === 5. Автооткрытие лучшей ===
    if all_spreads:
        best = all_spreads[0]
        if best["profit_pct"] > 5:
            print(f"\n🌐 ЛУЧШАЯ СВЯЗКА: {best['source']} → {best['sell_platform']} ({best['profit_pct']:+.1f}%)")
            print(f"   Открываю в браузере: {best['buy_url']}")
            try:
                subprocess.run(["termux-open-url", best["buy_url"]], timeout=10)
            except Exception as e:
                print(f"   ⚠️ Не удалось открыть: {e}")
        else:
            print(f"\n⚠️ Лучшая связка {best['profit_pct']:+.1f}% < 5% — не открываю")
    else:
        print(f"\n❌ Прибыльных связок нет")
    
    return all_spreads

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Super Scanner</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%;margin-top:20px}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🚀 SUPER SCANNER: Plati + FazerCards + 5 скупщиков</h1>
<p>Обновлено: <span id="ts">-</span></p>
<p id="summary" style="color:#0af"></p>
<table><tr><th>#</th><th>Источник</th><th>Номинал</th><th>Купить</th><th>Цена</th><th>Сдать</th><th>Цена</th><th>Профит</th><th>%</th><th>Ссылка</th></tr>
<tbody id="data"><tr><td colspan="10">Скан...</td></tr></tbody></table>
<script>
async function u(){
  try{
    const r = await fetch('/api/spreads');
    const d = await r.json();
    document.getElementById('data').innerHTML = d.length ? d.map((s,i)=>{
      const c = s.profit>0?'profit':'loss';
      return `<tr><td>${i+1}</td><td>${s.source}</td><td>$${s.nominal}</td><td>${s.buy_seller}</td><td>$${s.buy_price}</td><td>${s.sell_platform}</td><td>$${s.sell_price}</td><td class="${c}">$${s.profit}</td><td class="${c}">${s.profit_pct}%</td><td><a href="${s.buy_url}" target="_blank" style="color:#0af">открыть</a></td></tr>`;
    }).join('') : '<tr><td colspan="10" class="loss">Нет прибыльных связок</td></tr>';
  }catch(e){}
}
async function s(){
  try{
    const r = await fetch('/api/summary');
    const d = await r.json();
    document.getElementById('summary').textContent = d.summary || '';
    document.getElementById('ts').textContent = new Date().toLocaleTimeString();
  }catch(e){}
}
u(); s(); setInterval(u, 60000); setInterval(s, 60000);
</script></body></html>"""
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode())
        elif self.path == "/api/spreads":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps(CACHE["data"], ensure_ascii=False).encode())
        elif self.path == "/api/summary":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"summary": CACHE["summary"]}, ensure_ascii=False).encode())
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *args): pass

if __name__ == "__main__":
    print("🚀 SUPER SCANNER")
    print("   Источники: Plati.Market, FazerCards")
    print("   Скупщики: " + ", ".join(BUYERS.keys()))
    print("   Номиналы: " + str(NOMINALS))
    scan()
    def bg():
        while True:
            time.sleep(600)
            try: scan()
            except Exception as e: print(f"scan error: {e}")
    threading.Thread(target=bg, daemon=True).start()
    print(f"\n🌐 Панель: http://127.0.0.1:8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
