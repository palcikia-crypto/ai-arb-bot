import requests, re, json, time, threading, os
from bs4 import BeautifulSoup
from http.server import HTTPServer, BaseHTTPRequestHandler

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
CACHE = {"data": [], "updated": 0, "manual_inputs": {}}
MANUAL_FILE = "manual_prices.json"

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except: return None

def load_manual():
    if os.path.exists(MANUAL_FILE):
        try: return json.loads(open(MANUAL_FILE).read())
        except: pass
    return {}

def save_manual(d):
    open(MANUAL_FILE, "w").write(json.dumps(d, indent=2))

def scan():
    print("\n=== ГИБРИДНЫЙ СКАН ===")
    manual = load_manual()
    
    # 1. Пытаемся спарсить Plati.Market
    plati_price = None
    html = fetch("https://plati.market/search/Steam%20Turkey%2010%20USD")
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        # Ищем рубли рядом с "10 USD"
        prices = re.findall(r'(\d+[.,]?\d*)\s*₽', text)
        if prices:
            # Берём минимальную (обычно она самая дешёвая)
            plati_price = min([float(p.replace(",", ".")) for p in prices]) / 90
            print(f"Plati.Market (авто): ${plati_price:.2f}")
    
    if not plati_price and "plati_price" in manual:
        plati_price = manual["plati_price"]
        print(f"Plati.Market (ручной): ${plati_price:.2f}")
    elif not plati_price:
        print("Plati.Market: цена не найдена. Введи вручную.")
        plati_price = float(input("Введи цену Steam Turkey 10 USD в USD (например 6.50): ") or "0")
        manual["plati_price"] = plati_price
        save_manual(manual)
    
    # 2. Пытаемся спарсить GiftCardIo
    gci_rate = None
    html = fetch("https://www.giftcardio.com/sell-steam-gift-card")
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        m = re.search(r'(\d{2}(?:\.\d)?)\s*%', text)
        if m:
            gci_rate = float(m.group(1)) / 100
            print(f"GiftCardIo (авто): {gci_rate*100:.0f}%")
    
    if not gci_rate and "gci_rate" in manual:
        gci_rate = manual["gci_rate"]
        print(f"GiftCardIo (ручной): {gci_rate*100:.0f}%")
    elif not gci_rate:
        print("GiftCardIo: ставка не найдена. Введи вручную.")
        gci_rate = float(input("Введи ставку GiftCardIo в % (например 90): ") or "0") / 100
        manual["gci_rate"] = gci_rate
        save_manual(manual)
    
    # 3. Считаем профит
    if plati_price and gci_rate:
        sell_price = 10 * gci_rate
        profit = sell_price - plati_price
        profit_pct = (profit / plati_price * 100) if plati_price > 0 else 0
        print(f"\nКупить: ${plati_price:.2f}")
        print(f"Сдать: ${sell_price:.2f}")
        print(f"Профит: ${profit:.2f} ({profit_pct:+.1f}%)")
        
        if profit > 0:
            print("✅ ПРИБЫЛЬНАЯ СВЯЗКА!")
            CACHE["data"] = [{
                "item": "Steam Turkey $10",
                "buy": "Plati.Market",
                "buy_price": round(plati_price, 2),
                "sell": "GiftCardIo",
                "sell_price": round(sell_price, 2),
                "profit": round(profit, 2),
                "pct": round(profit_pct, 1)
            }]
        else:
            print("❌ Убыток")
            CACHE["data"] = []
    else:
        CACHE["data"] = []
    
    CACHE["updated"] = time.time()
    return CACHE["data"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Hybrid Arb</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🎯 Hybrid Arbitrage</h1>
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
    print("🚀 Hybrid Arb Bot")
    print("Если авто-парсинг не сработает — введи цену вручную (один раз).")
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
        print("❌ Связка не найдена. Введи цены вручную.")
