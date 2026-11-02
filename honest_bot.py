import requests, re, json, time, threading, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
CACHE = {"data": [], "updated": 0, "summary": ""}

# Ставки скупщиков (консервативные — чтобы не врать)
BUYERS = {
    "CardBix":   0.85,  # 85% (реалистичнее, чем 90%)
    "GiftCardIo": 0.86,
    "Cashard":   0.70,
}

# Все номиналы для проверки
NOMINALS = [5, 10, 20, 50, 100]

def get_lots_for_nominal(nominal):
    """Возвращает ВСЕ доступные лоты для номинала, где nominal = минимальный."""
    params = {
        "query": f"Steam Turkey {nominal} USD",
        "pagesize": 50,
        "pagenum": 1,
        "visibleOnly": "true",
        "response": "json"
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
        if not price or not url:
            continue
        
        # Первое число в названии
        m = re.search(r'(\d+)', name)
        if not m:
            continue
        first_num = int(m.group(1))
        
        # Только если первый номинал = искомый
        if first_num != nominal:
            continue
        
        # Отсеиваем подозрительно дешёвые (обычно цена за минимальный в диапазоне)
        if price < nominal * 0.4:
            continue
        
        lots.append({
            "nominal": nominal,
            "price": float(price),
            "seller": item.get("seller_name", ""),
            "url": url,
            "name": item.get("name", "")[:60],
        })
    
    lots.sort(key=lambda x: x["price"])
    return lots

def scan():
    print("\n" + "="*60)
    print("  🔍 ПОЛНЫЙ СКАН ВСЕХ НОМИНАЛОВ")
    print("="*60)
    
    all_results = []
    summary_lines = []
    
    for nominal in NOMINALS:
        lots = get_lots_for_nominal(nominal)
        if not lots:
            print(f"\n[{nominal} USD] ❌ Нет лотов в наличии")
            summary_lines.append(f"{nominal} USD: нет лотов")
            continue
        
        cheapest = lots[0]
        print(f"\n[{nominal} USD] Найдено {len(lots)} лотов. Дешёвый: {cheapest['seller']} за ${cheapest['price']:.2f}")
        
        # Считаем для каждого скупщика
        best_for_nominal = None
        for buyer_name, buyer_rate in BUYERS.items():
            sell = nominal * buyer_rate
            profit = sell - cheapest["price"]
            pct = (profit / cheapest["price"] * 100) if cheapest["price"] > 0 else 0
            marker = "✅" if profit > 0 else "❌"
            print(f"   {marker} {buyer_name} ({buyer_rate*100:.0f}%): ${sell:.2f} → {profit:+.2f} ({pct:+.1f}%)")
            
            if profit > 0 and (best_for_nominal is None or profit > best_for_nominal["profit"]):
                best_for_nominal = {
                    "nominal": nominal,
                    "buy_price": cheapest["price"],
                    "buy_seller": cheapest["seller"],
                    "buy_url": cheapest["url"],
                    "sell_platform": buyer_name,
                    "sell_rate": buyer_rate,
                    "sell_price": round(sell, 2),
                    "profit": round(profit, 2),
                    "profit_pct": round(pct, 1),
                }
        
        if best_for_nominal:
            summary_lines.append(f"{nominal} USD: ✅ {best_for_nominal['profit_pct']:+.1f}% через {best_for_nominal['sell_platform']}")
            all_results.append(best_for_nominal)
        else:
            summary_lines.append(f"{nominal} USD: ❌ убыток")
    
    # Сортируем по профиту
    all_results.sort(key=lambda x: x["profit_pct"], reverse=True)
    
    print("\n" + "="*60)
    print("  📊 ИТОГ")
    print("="*60)
    for line in summary_lines:
        print(f"  {line}")
    
    if all_results:
        best = all_results[0]
        print(f"\n🏆 ЛУЧШАЯ СВЯЗКА:")
        print(f"   Номинал:  {best['nominal']} USD")
        print(f"   Купить:   ${best['buy_price']:.2f} у {best['buy_seller']}")
        print(f"   Сдать:    ${best['sell_price']:.2f} в {best['sell_platform']}")
        print(f"   Профит:   +${best['profit']:.2f} ({best['profit_pct']:+.1f}%)")
        print(f"   Ссылка:   {best['buy_url']}")
        CACHE["data"] = all_results
        CACHE["summary"] = " | ".join(summary_lines)
        
        # Открываем в браузере только если профит > 5%
        if best["profit_pct"] > 5:
            print(f"\n🌐 Профит {best['profit_pct']:+.1f}% > 5% — открываю в браузере...")
            try:
                subprocess.run(["termux-open-url", best["buy_url"]], timeout=10)
            except:
                pass
        else:
            print(f"\n⚠️ Профит {best['profit_pct']:+.1f}% слишком мал, не открываю")
    else:
        print(f"\n❌ ПРИБЫЛЬНЫХ СВЯЗОК НЕТ при текущих ставках скупщиков")
        CACHE["data"] = []
        CACHE["summary"] = " | ".join(summary_lines)
    
    CACHE["updated"] = time.time()
    return all_results

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Honest Arb</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%;margin-top:20px}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}.warn{color:#fa0}</style></head>
<body><h1>🎯 Honest Arbitrage Scanner</h1>
<p>Проверяет ВСЕ номиналы | Обновлено: <span id="ts">-</span></p>
<p style="color:#fa0">Ставки: CardBix 85% | GiftCardIo 86% | Cashard 70%</p>
<p id="summary" style="color:#0af"></p>
<table><tr><th>Номинал</th><th>Купить</th><th>Цена</th><th>Сдать</th><th>Цена</th><th>Профит</th><th>%</th><th>Ссылка</th></tr>
<tbody id="data"><tr><td colspan="8">Скан...</td></tr></tbody></table>
<script>
async function u(){
  try{
    const r = await fetch('/api/spreads');
    const d = await r.json();
    document.getElementById('data').innerHTML = d.length ? d.map(s=>{
      const c = s.profit>0?'profit':'loss';
      return `<tr><td>$${s.nominal}</td><td>${s.buy_seller}</td><td>$${s.buy_price}</td><td>${s.sell_platform}</td><td>$${s.sell_price}</td><td class="${c}">$${s.profit}</td><td class="${c}">${s.profit_pct}%</td><td><a href="${s.buy_url}" target="_blank" style="color:#0af">открыть</a></td></tr>`;
    }).join('') : '<tr><td colspan="8" class="loss">Прибыльных связок нет</td></tr>';
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
    print("🚀 Honest Arb Scanner")
    print("   Проверяет номиналы: " + str(NOMINALS))
    scan()
    def bg():
        while True:
            time.sleep(600)
            try: scan()
            except Exception as e: print(f"scan error: {e}")
    threading.Thread(target=bg, daemon=True).start()
    print(f"\n🌐 Панель: http://127.0.0.1:8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
