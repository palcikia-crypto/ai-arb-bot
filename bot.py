import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

BUYERS = {
    "CardBix": {"Global": 0.85, "US": 0.85, "Turkey": 0.0, "Argentina": 0.0},
    "GiftCardIo": {"Global": 0.86, "US": 0.86, "Turkey": 0.45, "Argentina": 0.40},
    "Cashard": {"Global": 0.70, "US": 0.70, "Turkey": 0.0, "Argentina": 0.0},
    "HighCardRate": {"Global": 0.84, "US": 0.84, "Turkey": 0.35, "Argentina": 0.35}
}

CACHE = {"data": [], "summary": "Инициализация...", "last_update": "Ожидание..."}

def ai_analyze(title, description):
    text = (title + " " + description).lower()
    region = "UNKNOWN"
    if any(word in text for word in ["турция", " tr ", " try ", "турецк"]):
        region = "Turkey"
    elif any(word in text for word in ["сша", " us ", " usd ", "global", "весь мир"]):
        region = "Global"
    elif "аргентин" in text:
        region = "Argentina"

    is_risky = False
    risk_reason = ""
    if region == "Turkey" and "весь мир" in text:
        is_risky = True
        risk_reason = "Обман: Турецкая карта не может быть 'весь мир'"
    
    return {"region": region, "is_risky": is_risky, "risk_reason": risk_reason}

def calculate_arbitrage(buy_price_usd, face_value_usd, title, description):
    analysis = ai_analyze(title, description)
    region = analysis["region"]
    discount_ratio = buy_price_usd / face_value_usd
    carding_risk = discount_ratio < 0.65
    results = []
    
    for buyer_name, rates in BUYERS.items():
        rate = rates.get(region, 0)
        if rate == 0: continue
            
        sell_price = face_value_usd * rate
        profit = sell_price - buy_price_usd
        margin = (profit / buy_price_usd) * 100
        
        if analysis["is_risky"]:
            status = "⚠️ СКАМ (Обман региона)"
        elif carding_risk:
            status = "❌ РИСК (Кардинг)"
        elif profit > 0:
            status = "✅ ПРОФИТ"
        else:
            status = "🔻 УБЫТОК"
            
        results.append({
            "buyer": buyer_name, "region": region, "rate": rate,
            "profit": round(profit, 2), "margin": round(margin, 1),
            "status": status, "ai_reason": analysis["risk_reason"]
        })
    return results

def scan():
    global CACHE
    print("\n" + "="*60)
    print(f"📡 СКАНИРОВАНИЕ ЗАВЕРШЕНО В {time.strftime('%H:%M:%S')}")
    print("="*60)
    spreads = []
    
    mock_lots = [
        {"title": "STEAM GIFT CARD 10-75$ USD ТУРЦИЯ АВТОДОСТАВКА", "description": "Код исключительно для региона ТУРЦИЯ. Территория использования: Турция, РФ и весь мир.", "price_rub": 565, "nominal": 10, "exchange_rate": 86.0},
        {"title": "STEAM GIFT CARD 20$ Global (US)", "description": "Код для аккаунтов US. Моментальная выдача.", "price_rub": 1550, "nominal": 20, "exchange_rate": 86.0},
        {"title": "STEAM GIFT CARD 20$ Global СКИДКА", "description": "Глобальный код, моменталка.", "price_rub": 1300, "nominal": 20, "exchange_rate": 86.0}
    ]

    for lot in mock_lots:
        price_usd = lot["price_rub"] / lot["exchange_rate"]
        opportunities = calculate_arbitrage(price_usd, lot["nominal"], lot["title"], lot["description"])
        spreads.append({"title": lot["title"], "buy_price": round(price_usd, 2), "nominal": lot["nominal"], "opportunities": opportunities})
        
        print(f"\n📦 ЛОТ: {lot['title']}")
        print(f"   Номинал: ${lot['nominal']} | Цена покупки: ${price_usd:.2f}")
        
        for opp in opportunities:
            if "ПРОФИТ" in opp["status"]:
                print(f"   {opp['status']} {opp['buyer']} ({opp['rate']*100}%): +${opp['profit']} ({opp['margin']}%)")
            elif "УБЫТОК" in opp["status"]:
                print(f"   {opp['status']} {opp['buyer']} ({opp['rate']*100}%): ${opp['profit']} ({opp['margin']}%)")
            else:
                print(f"   {opp['status']} через {opp['buyer']}")
                if opp['ai_reason']: print(f"      Причина: {opp['ai_reason']}")

    CACHE["data"] = spreads
    best_opp = max([opp for lot in spreads for opp in lot["opportunities"] if "ПРОФИТ" in opp["status"]], key=lambda x: x['margin'], default=None)
    
    print("\n" + "="*60)
    if best_opp:
        print(f"🏆 ЛУЧШАЯ СВЯЗКА: {best_opp['buyer']} (+{best_opp['margin']}%)")
        CACHE["summary"] = f"Топ: {best_opp['buyer']} (+{best_opp['margin']}%)"
    else:
        print("⚠️ ВНИМАНИЕ: Прибыльных безопасных связок не найдено.")
        CACHE["summary"] = "⚠️ Все лоты убыточные или опасные!"
    print("="*60 + "\n")
    CACHE["last_update"] = time.strftime("%H:%M:%S")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html lang="ru">
            <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>AI Arbitrage</title><script src="https://cdn.tailwindcss.com"></script></head>
            <body class="bg-gray-900 text-white font-sans p-4 md:p-6">
                <div class="max-w-4xl mx-auto">
                    <header class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-gray-700 pb-4 gap-4">
                        <h1 class="text-2xl md:text-3xl font-bold text-blue-400">🤖 AI Arbitrage Scanner</h1>
                        <div class="text-left md:text-right">
                            <p class="text-sm text-gray-400">Обновлено: <span id="ts" class="font-mono text-white">-</span></p>
                            <p id="summary" class="text-green-400 font-semibold mt-1">Загрузка...</p>
                        </div>
                    </header>
                    <div id="content" class="space-y-6"></div>
                </div>
                <script>
                    async function u() {
                        try {
                            const r = await fetch('/api/spreads'); const data = await r.json();
                            const container = document.getElementById('content'); container.innerHTML = '';
                            data.forEach(lot => {
                                let oppsHtml = '';
                                lot.opportunities.forEach(opp => {
                                    let color = 'text-gray-400';
                                    if (opp.status.includes('ПРОФИТ')) color = 'text-green-400';
                                    if (opp.status.includes('УБЫТОК')) color = 'text-red-400';
                                    if (opp.status.includes('РИСК') || opp.status.includes('СКАМ')) color = 'text-yellow-400';
                                    oppsHtml += `<div class="flex flex-col md:flex-row justify-between items-start md:items-center bg-gray-800 p-3 rounded mb-2 border border-gray-700 gap-2">
                                        <div><span class="font-bold text-blue-300">${opp.buyer}</span><span class="text-xs bg-gray-700 px-2 py-1 rounded ml-2">${opp.region} / ${opp.rate*100}%</span></div>
                                        <div class="md:text-right"><p class="font-bold ${color} text-sm md:text-base">${opp.status}</p>
                                        <p class="text-xs text-gray-400">Профит: $${opp.profit} (+${opp.margin}%)</p>
                                        ${opp.ai_reason ? `<p class="text-xs text-red-400 font-bold">⚠️ ${opp.ai_reason}</p>` : ''}</div></div>`;
                                });
                                container.innerHTML += `<div class="bg-gray-800 rounded-lg p-4 md:p-5 shadow-lg border border-gray-700">
                                    <div class="flex flex-col md:flex-row justify-between items-start mb-4 gap-2"><div>
                                    <h2 class="text-lg md:text-xl font-bold text-white mb-1">${lot.title}</h2>
                                    <p class="text-gray-400 text-sm">Номинал: <span class="text-white font-bold">$${lot.nominal}</span> | Цена покупки: <span class="text-white font-bold">$${lot.buy_price}</span></p></div>
                                    <span class="bg-blue-600 text-white text-xs px-3 py-1 rounded-full whitespace-nowrap">🤖 AI Проверен</span></div>
                                    <div class="space-y-2">${oppsHtml}</div></div>`;
                            });
                        } catch(e) {}
                    }
                    async function s() {
                        try { const r = await fetch('/api/summary'); const d = await r.json(); document.getElementById('summary').textContent = d.summary; document.getElementById('ts').textContent = d.last_update; } catch(e) {}
                    }
                    u(); s(); setInterval(u, 30000); setInterval(s, 30000);
                </script>
            </body></html>
            """
            self.wfile.write(html.encode())
        elif self.path == "/api/spreads":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps(CACHE["data"], ensure_ascii=False).encode())
        elif self.path == "/api/summary":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"summary": CACHE["summary"], "last_update": CACHE["last_update"]}, ensure_ascii=False).encode())
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("🚀 ЗАПУСК СКАНЕРА")
    scan()
    
    def bg_scan():
        while True:
            time.sleep(600)
            try: scan()
            except Exception as e: print(f"Ошибка: {e}")
                
    threading.Thread(target=bg_scan, daemon=True).start()
    
    try:
        server = HTTPServer(("0.0.0.0", 8000), Handler)
        print("\n🌐 Панель (браузер): http://127.0.0.1:8000")
        print("⏳ Ожидание следующего авто-скана (каждые 10 минут)...")
        server.serve_forever()
    except OSError:
        print("\n⚠️ Порт 8000 занят (возможно, висит старая версия скрипта).")
        print("💻 Скрипт продолжит работу в терминале.")
        while True: time.sleep(1)
