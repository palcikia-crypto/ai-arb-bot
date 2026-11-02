import requests, re, json, time, threading
from bs4 import BeautifulSoup
from http.server import HTTPServer, BaseHTTPRequestHandler

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
CACHE = {"data": [], "updated": 0}

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except: return None

def get_plati_price():
    """Парсит минимальную цену Steam Turkey 10 USD на Plati.Market."""
    html = fetch("https://plati.market/search/Steam%20Turkey%2010%20USD")
    if not html: return None
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Ищем цены в рублях рядом с "10 USD"
    prices = []
    for m in re.finditer(r'(\d+[.,]?\d*)\s*₽', text):
        try:
            price_rub = float(m.group(1).replace(",", "."))
            prices.append(price_rub)
        except: continue
    if not prices: return None
    # Берём минимальную цену (обычно она в начале списка)
    min_rub = min(prices)
    # Переводим в USD (курс ~90)
    return round(min_rub / 90, 2)

def get_giftcardio_rate():
    """Парсит ставку GiftCardIo для Steam."""
    html = fetch("https://www.giftcardio.com/sell-steam-gift-card")
    if not html: return 0.90  # fallback
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    m = re.search(r'(\d{2}(?:\.\d)?)\s*%', text)
    if m:
        return float(m.group(1)) / 100
    return 0.90

def scan():
    print("\n=== ФИНАЛЬНЫЙ СКАН: PLATI.MARKET → GIFTCARDIO ===")
    buy_price = get_plati_price()
    rate = get_giftcardio_rate()
    print(f"Plati.Market цена Steam Turkey 10 USD: ${buy_price}")
    print(f"GiftCardIo ставка: {rate*100:.0f}%")
    
    if buy_price and rate:
        sell_price = 10 * rate
        profit = sell_price - buy_price
        profit_pct = (profit / buy_price * 100) if buy_price > 0 else 0
        print(f"Сдача: ${sell_price:.2f}")
        print(f"Профит: ${profit:.2f} ({profit_pct:+.1f}%)")
        
        if profit > 0:
            print("✅ ПРИБЫЛЬНАЯ СВЯЗКА НАЙДЕНА!")
            CACHE["data"] = [{
                "item": "Steam Turkey $10",
                "buy": "Plati.Market",
                "buy_price": round(buy_price, 2),
                "sell": "GiftCardIo",
                "sell_price": round(sell_price, 2),
                "profit": round(profit, 2),
                "pct": round(profit_pct, 1)
            }]
        else:
            print("❌ Связка убыточна. Нужны другие источники.")
            CACHE["data"] = []
    else:
        print("❌ Не удалось получить цены.")
        CACHE["data"] = []
    
    CACHE["updated"] = time.time()
    return CACHE["data"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Final Arb</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🎯 Plati.Market → GiftCardIo</h1>
<p>Steam Turkey $10 | Обновлено: <span id="ts">-</span></p>
<table><tr><th>Товар</th><th>Купить</th><th>Цена</th><th>Сдать</th><th>Цена</th><th>Профит</th><th>%</th></tr>
<tbody id="data"><tr><td colspan="7">Скан...</td></tr></tbody></table>
<script>
async function u(){const r=await fetch('/api/spreads');const d=await r.json();
document.getElementById('data').innerHTML=d.map(s=>{const c=s.profit>0?'profit':'loss';
return `<tr><td>${s.item}</td><td>${s.buy}</td><td>${s.buy_price}</td><td>${s.sell}</td><td>${s.sell_price}</td><td class="${c}">${s.profit}</td><td class="${c}">${s.pct}%</td></tr>`}).join('');
document.getElementById('ts').textContent=new Date().toLocaleTimeString();}
u();setInterval(u,60000);</script></body></html>"""
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode())
        elif self.path == "/api/spreads":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps(CACHE["data"], ensure_ascii=False).encode())
        else: self.send_response(404); self.end_headers()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("🚀 Final Arb Bot")
    result = scan()
    if result:
        print("\n🌐 Панель: http://127.0.0.1:8000")
        def bg():
            while True:
                time.sleep(600)
                try: scan()
                except Exception as e: print(f"scan error: {e}")
        threading.Thread(target=bg, daemon=True).start()
        HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
    else:
        print("❌ Связка не найдена. Бот не запущен.")
