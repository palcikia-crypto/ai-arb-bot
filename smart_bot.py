import requests, json, time, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler

PLATI_API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
CACHE = {"data": [], "updated": 0}
BUYERS = {"CardBix": 0.90, "GiftCardIo": 0.86, "Cashard": 0.70}

def get_plati_price_for_10usd():
    """Ищет цену за 10 USD Turkey (фильтрует диапазоны)."""
    params = {"query": "Steam Turkey 10 USD", "pagesize": 50, "pagenum": 1, "response": "json"}
    try:
        r = requests.get(PLATI_API, params=params, headers=HEADERS, timeout=20)
        data = r.json()
        items = data.get("items", [])
        
        candidates = []
        for item in items:
            name = item.get("name_eng", "").lower() + " " + item.get("name", "").lower()
            price = item.get("price_usd")
            if not price: continue
            
            # ВАЖНО: извлекаем ПЕРВОЕ число из названия
            m = re.search(r'(\d+)', name)
            if not m: continue
            first_num = int(m.group(1))
            
            # Берём только лоты, где ПЕРВЫЙ номинал = 10
            # (значит цена за 10 USD, а не за 5)
            if first_num == 10:
                candidates.append({
                    "name": item.get("name", "")[:60],
                    "price_usd": float(price),
                    "seller": item.get("seller_name", ""),
                    "first_num": first_num,
                })
        
        if not candidates:
            print("❌ Нет лотов с первым номиналом 10 USD")
            return None
        
        # Сортируем по цене
        candidates.sort(key=lambda x: x["price_usd"])
        print(f"\n✅ Найдено {len(candidates)} лотов с номиналом 10 USD:")
        for c in candidates[:5]:
            print(f"  ${c['price_usd']:.2f} — {c['seller']} — {c['name']}")
        
        return candidates[0]["price_usd"]
    except Exception as e:
        print(f"API error: {e}")
        return None

def scan():
    print("\n=== SMART СКАН (только 10 USD лоты) ===")
    plati_price = get_plati_price_for_10usd()
    
    if not plati_price:
        print("❌ Не нашли, пропускаем")
        CACHE["data"] = []
        return []
    
    print(f"\n📊 РАСЧЁТ (Plati: ${plati_price:.2f})")
    
    best = None
    for name, rate in BUYERS.items():
        sell = 10 * rate
        profit = sell - plati_price
        pct = (profit / plati_price * 100) if plati_price > 0 else 0
        marker = "✅" if profit > 0 else "❌"
        print(f"  {marker} {name} ({rate*100:.0f}%): ${sell:.2f} → профит ${profit:.2f} ({pct:+.1f}%)")
        
        if profit > 0 and (best is None or profit > best["profit"]):
            best = {
                "item": "Steam Turkey $10", "buy": "Plati.Market",
                "buy_price": round(plati_price, 2), "sell": name,
                "sell_price": round(sell, 2), "profit": round(profit, 2), "pct": round(pct, 1)
            }
    
    if best:
        print(f"\n✅ ЛУЧШАЯ СВЯЗКА: Plati → {best['sell']} ({best['pct']:+.1f}%)")
        CACHE["data"] = [best]
    else:
        print("\n❌ Убыток")
        CACHE["data"] = []
    
    CACHE["updated"] = time.time()
    return CACHE["data"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Smart Arb</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🎯 Smart Arb (только 10 USD лоты)</h1><p>Обновлено: <span id="ts">-</span></p>
<table><tr><th>Товар</th><th>Купить</th><th>Цена</th><th>Сдать</th><th>Цена</th><th>Профит</th><th>%</th></tr>
<tbody id="data"><tr><td colspan="7">Скан...</td></tr></tbody></table>
<script>async function u(){const r=await fetch('/api/spreads');const d=await r.json();
document.getElementById('data').innerHTML=d.length?d.map(s=>{const c=s.profit>0?'profit':'loss';
return `<tr><td>${s.item}</td><td>${s.buy}</td><td>$${s.buy_price}</td><td>${s.sell}</td><td>$${s.sell_price}</td><td class="${c}">$${s.profit}</td><td class="${c}">${s.pct}%</td></tr>`}).join(''):
'<tr><td colspan="7">Нет связок</td></tr>';
document.getElementById('ts').textContent=new Date().toLocaleTimeString();}
u();setInterval(u,60000);</script></body></html>"""
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode())
        elif self.path == "/api/spreads":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps(CACHE["data"], ensure_ascii=False).encode())
        else: self.send_response(404); self.end_headers()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("🚀 Smart Arb Bot")
    scan()
    def bg():
        while True:
            time.sleep(300)
            try: scan()
            except Exception as e: print(f"error: {e}")
    threading.Thread(target=bg, daemon=True).start()
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
