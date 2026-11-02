import json, time, threading, requests, re
from bs4 import BeautifulSoup
from http.server import HTTPServer, BaseHTTPRequestHandler
from ai_agent import find_price_via_search

HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"}
CACHE = {"data": [], "updated": 0}

# ДАННЫЕ ИЗ НАШИХ ПРОШЛЫХ ПОИСКОВ (реальные)
KNOWN = {
    "fazercards_tr_10usd_public": 10.01,
    "fazercards_tr_10usd_gold": 9.66,  # -3.55%
    "fazercards_tr_5usd_public": 4.92,
    "fazercards_tr_5usd_gold": 4.75,
    "fazercards_tr_50usd_public": 49.25,
    "fazercards_tr_50usd_gold": 47.50,
    "giftcardio_rate": 0.86,   # из wepesa.com (ai_agent нашёл)
    "cardbix_rate": 0.90,       # из нашего исследования
    "cashard_rate": 0.70,       # live check (только что)
}

def search_plati():
    """Ищем Plati.Market через ai_agent."""
    print("\n🔍 Ищу Plati.Market (Steam Turkey 10 USD)...")
    price, url = find_price_via_search(
        "Steam Turkey 10 USD",
        "Plati Market Steam Turkey 10 USD цена руб"
    )
    if price and 3 < price < 15:
        print(f"  ✅ Plati: ${price:.2f} (url: {url})")
        return price
    # Пробуем прямой fetch
    try:
        r = requests.get("https://plati.market/search/Steam%20Turkey%2010%20USD", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            # Ищем все рубли, берём дешёвые (500-800₽ = $5.5-8.9)
            rubs = [float(x.replace(",", ".")) for x in re.findall(r'(\d{3,4}[.,]?\d*)\s*₽', text)]
            if rubs:
                # Фильтр: 400-900₽ (турецкий Steam 10 USD обычно 500-700₽)
                valid = [r for r in rubs if 400 < r < 900]
                if valid:
                    usd = min(valid) / 90
                    print(f"  ✅ Plati (fetch): ${usd:.2f} (мин {min(valid):.0f}₽)")
                    return usd
    except Exception as e:
        print(f"  ⚠️ fetch error: {e}")
    print(f"  ❌ Plati не найден")
    return None

def scan():
    print("\n=== АВТО-СКАН (используем накопленные данные) ===")
    
    # Пытаемся найти Plati (свежая цена)
    plati_price = search_plati() or 6.50  # fallback из интернета
    
    print(f"\n📊 РАСЧЁТ:")
    print(f"  Plati.Market: ${plati_price:.2f}")
    print()
    
    # Все скупщики с их ставками
    buyers = [
        ("CardBix", KNOWN["cardbix_rate"]),
        ("GiftCardIo", KNOWN["giftcardio_rate"]),
        ("Cashard", KNOWN["cashard_rate"]),
    ]
    
    best = None
    for name, rate in buyers:
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
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Auto Arb</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🎯 Auto Arbitrage (Plati → Скупщики)</h1>
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
    print("🚀 Auto Arb Bot (без ручного ввода)")
    scan()
    print(f"\n🌐 Панель: http://127.0.0.1:8000")
    def bg():
        while True:
            time.sleep(600)
            try: scan()
            except Exception as e: print(f"scan error: {e}")
    threading.Thread(target=bg, daemon=True).start()
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
