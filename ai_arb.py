import json, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from ai_agent import find_price_via_search

CACHE = {"data": [], "updated": 0}

def scan():
    global CACHE
    print("\n=== СКАН ЗАПУЩЕН ===")
    spreads = []

    # ROBUX
    print("[1/2] FazerCards Robux...")
    buy, _ = find_price_via_search("Robux", "FazerCards Robux wholesale price per 1 Robux")
    print(f"  → buy={buy}")
    
    print("[2/2] RBXSTOCK bid...")
    sell_1000, _ = find_price_via_search("Robux", "RBXSTOCK Robux buy rate per 1 robux")
    sell = sell_1000 if sell_1000 else 0.0125  # LLM уже дала за 1 единицу
    print(f"  → sell_per_unit={sell}")
    
    if buy and sell:
        profit = (sell * 0.95) - buy
        spreads.append({"item":"Robux","buy":"FazerCards","buy_price":round(buy,5),"sell":"RBXSTOCK","sell_price":round(sell,5),"profit":round(profit,5),"pct":round(profit/buy*100,2)})
    
    # STEAM
    print("[3/4] FazerCards Steam...")
    buy, _ = find_price_via_search("Steam Gift $10", "FazerCards Steam gift card 10 USD wholesale price")
    print(f"  → buy={buy}")
    
    print("[4/4] CardBix rate...")
    rate_pct, _ = find_price_via_search("Steam Gift $10", "CardBix Steam gift card buy rate")
    rate = (rate_pct / 100) if rate_pct and rate_pct > 10 else 0.90
    sell = 10 * rate
    print(f"  → sell={sell}")
    
    if buy and sell:
        profit = sell - buy
        spreads.append({"item":"Steam $10","buy":"FazerCards","buy_price":round(buy,2),"sell":"CardBix","sell_price":round(sell,2),"profit":round(profit,2),"pct":round(profit/buy*100,2)})
    
    # STARS
    print("[5/6] FazerCards Stars...")
    buy_star, _ = find_price_via_search("Telegram Star", "FazerCards Telegram Stars wholesale price per star")
    print(f"  → buy_per_star={buy_star}")
    
    print("[6/6] Starsei bid...")
    sell_star, _ = find_price_via_search("Telegram Star", "Starsei Telegram Stars buy rate per star")
    print(f"  → sell_per_star={sell_star}")
    
    if buy_star and sell_star:
        buy = buy_star * 100
        sell = sell_star * 100 * 0.95
        profit = sell - buy
        spreads.append({"item":"Stars (100)","buy":"FazerCards","buy_price":round(buy,2),"sell":"Starsei","sell_price":round(sell,2),"profit":round(profit,2),"pct":round(profit/buy*100,2)})
    
    CACHE["data"] = spreads
    CACHE["updated"] = time.time()
    print(f"\n✅ Скан завершён. Связок: {len(spreads)}")
    return spreads

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>AI Arb</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🎯 AI Arbitrage</h1><p>Скан каждые 5 мин</p>
<table><tr><th>Товар</th><th>Купить</th><th>Цена</th><th>Сдать</th><th>Цена</th><th>Профит</th><th>%</th></tr>
<tbody id="data"><tr><td colspan="7">Первый скан...</td></tr></tbody></table>
<script>async function u(){const r=await fetch('/api/spreads');const d=await r.json();
document.getElementById('data').innerHTML=d.map(s=>{const c=s.profit>0?'profit':'loss';
return `<tr><td>${s.item}</td><td>${s.buy}</td><td>${s.buy_price}</td><td>${s.sell}</td><td>${s.sell_price}</td><td class="${c}">${s.profit}</td><td class="${c}">${s.pct}%</td></tr>`}).join('')}
u();setInterval(u,30000);</script></body></html>"""
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode())
        elif self.path == "/api/spreads":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps(CACHE["data"], ensure_ascii=False).encode())
        else: self.send_response(404); self.end_headers()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("🚀 Запуск синхронного скана...")
    scan()
    print("\n🌐 Веб-панель: http://127.0.0.1:8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
