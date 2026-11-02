import requests, re, json, time, threading
from bs4 import BeautifulSoup
from http.server import HTTPServer, BaseHTTPRequestHandler

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
CARDBIX_PCT = 0.85
CACHE = {"data": [], "updated": 0}

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except: return None

def parse_fazercards_region(region_name, url):
    """Парсит пакеты: "X USD $Y" — номинал X USD, цена Y USD."""
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    
    # Паттерн: "5 USD $ 4.92" или "5 USD $4.92"
    pairs = re.findall(r'(\d+)\s*USD\s*\$\s*([\d.]+)', text)
    results = []
    seen = set()
    for nominal_str, price_str in pairs:
        try:
            nominal = float(nominal_str)
            price = float(price_str)
        except: continue
        
        key = (nominal, price)
        if key in seen: continue
        seen.add(key)
        
        # Сколько CardBix платит (85% от номинала Steam)
        cardbix_pays = nominal * CARDBIX_PCT
        profit = cardbix_pays - price
        profit_pct = (profit / price * 100) if price > 0 else 0
        
        results.append({
            "region": region_name,
            "nominal_usd": nominal,
            "price_usd": round(price, 2),
            "cardbix_pays": round(cardbix_pays, 2),
            "profit": round(profit, 2),
            "profit_pct": round(profit_pct, 1)
        })
    
    return results

def scan():
    print("\n=== СКАН STEAM РЕГИОНОВ ===")
    all_packages = []
    
    regions = [
        ("Turkey", "https://reseller.fazercards.com/en/catalog/steam/turkey"),
        ("Argentina", "https://reseller.fazercards.com/en/catalog/steam/argentina"),
        ("Brazil", "https://reseller.fazercards.com/en/catalog/steam/brazil"),
        ("India", "https://reseller.fazercards.com/en/catalog/steam/india"),
    ]
    
    for name, url in regions:
        print(f"\n[{name}] {url}")
        packages = parse_fazercards_region(name, url)
        print(f"  Найдено пакетов: {len(packages)}")
        all_packages.extend(packages)
        for p in packages[:5]:
            marker = "✅" if p["profit"] > 0 else "❌"
            print(f"  {marker} ${p['nominal_usd']:.0f} → buy ${p['price_usd']:.2f} → sell ${p['cardbix_pays']:.2f} ({p['profit_pct']:+.1f}%)")
    
    all_packages.sort(key=lambda x: x["profit_pct"], reverse=True)
    profitable = [p for p in all_packages if p["profit"] > 0]
    print(f"\n✅ ПРИБЫЛЬНЫХ: {len(profitable)} из {len(all_packages)}")
    
    CACHE["data"] = all_packages
    CACHE["updated"] = time.time()
    return all_packages

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Steam Regions</title>
<style>body{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #0f0;padding:8px}th{background:#1a1a1a}.profit{color:#0f0;font-weight:bold}.loss{color:#f00}</style></head>
<body><h1>🌍 Steam Regions Arbitrage</h1>
<p>FazerCards → CardBix (85%) | Обновлено: <span id="ts">-</span></p>
<table><tr><th>Регион</th><th>Номинал</th><th>Купить</th><th>Сдать</th><th>Профит</th><th>%</th></tr>
<tbody id="data"><tr><td colspan="6">Скан...</td></tr></tbody></table>
<script>
async function u(){const r=await fetch('/api/spreads');const d=await r.json();
document.getElementById('data').innerHTML=d.map(s=>{const c=s.profit>0?'profit':'loss';
return `<tr><td>${s.region}</td><td>$${s.nominal_usd}</td><td>$${s.price_usd}</td><td>$${s.cardbix_pays}</td><td class="${c}">$${s.profit}</td><td class="${c}">${s.profit_pct}%</td></tr>`}).join('');
document.getElementById('ts').textContent=new Date().toLocaleTimeString();}
u();setInterval(u,60000);</script></body></html>"""
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html.encode())
        elif self.path == "/api/spreads":
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps(CACHE["data"], ensure_ascii=False).encode())
        else: self.send_response(404); self.end_headers()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("🚀 Steam Regions Arb Bot")
    scan()
    print("\n🌐 Панель: http://127.0.0.1:8000")
    
    def bg():
        while True:
            time.sleep(600)
            try: scan()
            except Exception as e: print(f"scan error: {e}")
    
    threading.Thread(target=bg, daemon=True).start()
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
