import requests, json, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Официальный API Plati.Market (Digiseller)
PLATI_API = "https://plati.io/api/search.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"}

CACHE = {"data": [], "updated": 0}

# Ставки скупщиков (подтверждены ранее)
BUYERS = {
    "CardBix": 0.90,
    "GiftCardIo": 0.86,
    "Cashard": 0.70,
}

def get_plati_price(query):
    """Получает минимальную цену через API Plati в USD."""
    params = {
        "query": query,
        "pagesize": 50,
        "pagenum": 1,
        "response": "json"
    }
    try:
        r = requests.get(PLATI_API, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"Plati API HTTP {r.status_code}")
            return None
        
        data = r.json()
        # Ищем товары с ценой в USD
        prices = []
        for item in data.get("items", []):
            # price_XXX — цена в валюте XXX, нас интересует USD
            price_usd = item.get("price_USD") or item.get("price_usd")
            if price_usd:
                try:
                    prices.append(float(price_usd))
                except: continue
        
        if not prices:
            print("Plati API: цены не найдены в ответе")
            return None
        
        min_price = min(prices)
        print(f"Plati API: найдено {len(prices)} цен, минимум ${min_price:.2f}")
        return min_price
    except Exception as e:
        print(f"Plati API error: {e}")
        return None

def scan():
    print("\n=== АВТО-СКАН (API Plati.Market) ===")
    
    # Ищем Steam Turkey 10 USD
    plati_price = get_plati_price("Steam Turkey 10 USD")
    
    if not plati_price:
        print("❌ Не удалось получить цену с Plati. Использую fallback $6.50")
        plati_price = 6.50
    
    print(f"\n📊 РАСЧЁТ:")
    print(f"  Plati.Market: ${plati_price:.2f}")
    print()
    
    best = None
    for name, rate in BUYERS.items():
        sell = 10 * rate
        profit = sell - plati_price
        pct = (profit / plati_price * 100) if plati_price > 0 else 0
        marker = "✅" if profit > 0 else "❌"
        print(f"  {marker} {name} ({rate*100:.0f}%): продать ${sell:.2f} → профит ${profit:.2f} ({pct:+.1f}%)")
        
        if profit > 0 and (best is None or profit > best["profit"]):
            best = {
                "item": "Steam Turkey $10",
                "buy": "Plati.Market",
                "buy_price": round(plati_price, 2),
                "sell": name,
                "sell_price": round(sell, 2),
                "profit": round(profit, 2),
                "pct": round(pct, 1)
            }
    
    print()
    if best:
        print(f"✅ ЛУЧШАЯ СВЯЗКА: Plati → {best['sell']} ({best['pct']:+.1f}%)")
        CACHE["data"] = [best]
    else:
        print(f"❌ Все связки убыточные")
        CACHE["data"] = []
    
    CACHE["updated"] = time.time()
    return CACHE["data"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>API Arb</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🎯 API Arbitrage (Plati → Скупщики)</h1>
<p>Steam Turkey $10 | Обновлено: <span id="ts">-</span></p>
<table><tr><th>Товар</th><th>Купить</th><th>Цена</th><th>Сдать</th><th>Цена</th><th>Профит</th><th>%</th></tr>
<tbody id="data"><tr><td colspan="7">Скан...</td></tr></tbody></table>
<script>
async function u(){const r=await fetch('/api/spreads');const d=await r.json();
document.getElementById('data').innerHTML=d.length?d.map(s=>{const c=s.profit>0?'profit':'loss';
return `<tr><td>${s.item}</td><td>${s.buy}</td><td>$${s.buy_price}</td><td>${s.sell}</td><td>$${s.sell_price}</td><td class="${c}">$${s.profit}</td><td class="${c}">${s.pct}%</td></tr>`}).join(''):
'<tr><td colspan="7">Нет прибыльных связок</td></tr>';
document.getElementById('ts').textContent=new Date().toLocaleTimeString();}
u();setInterval(u,60000);</script></body></html>"""
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode())
        elif self.path == "/api/spreads":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps(CACHE["data"], ensure_ascii=False).encode())
        else: self.send_response(404); self.end_headers()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("🚀 API Arb Bot (автономный, без ручного ввода)")
    scan()
    print(f"\n🌐 Панель: http://127.0.0.1:8000")
    def bg():
        while True:
            time.sleep(600)
            try: scan()
            except Exception as e: print(f"scan error: {e}")
    threading.Thread(target=bg, daemon=True).start()
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
