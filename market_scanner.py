import requests, re, json, time

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36", "Accept-Encoding": "br, gzip"}
PLATI = "https://plati.io/api/search.ashx"
STEAM = "https://steamcommunity.com/market/priceoverview/"
SKINPORT = "https://api.skinport.com/v1/items"
# комиссия: продавец получает ~85% на Steam (~15%), ~88% на Skinport (12%)
NET_STEAM = 0.85
NET_SKINPORT = 0.88

KEY_STEAM_NAME = "Mann Co. Supply Crate Key"
SKINS = [
    "AK-47 | Redline (Field-Tested)",
    "AWP | Asiimov (Field-Tested)",
    "AK-47 | Slate (Field-Tested)",
    "AWP | Neo-Noir (Field-Tested)",
    "M4A1-S | Hyper Beast (Field-Tested)",
    "Desert Eagle | Blaze (Factory New)",
    "Glock-18 | Fade (Factory New)",
    "USP-S | Kill Confirmed (Field-Tested)",
]

cache = {}

def steam_price(appid, name):
    for attempt in range(3):
        try:
            r = requests.get(STEAM, params={"appid": appid, "currency": 1, "cc": "us", "market_hash_name": name}, headers=HEADERS, timeout=12)
            if r.status_code == 429:
                time.sleep(9); continue
            d = r.json()
            if d.get("success") and d.get("lowest_price"):
                return float(re.sub(r"[^\d.]", "", d["lowest_price"]))
            return None
        except Exception:
            time.sleep(5)
    return None

def skinport_map(app_id):
    if app_id in cache: return cache[app_id]
    m = {}
    try:
        r = requests.get(SKINPORT, params={"app_id": app_id, "currency": "USD"}, headers=HEADERS, timeout=25)
        for it in r.json():
            if it.get("sale_price") is not None:
                m[it["market_hash_name"]] = float(it["sale_price"])
    except Exception:
        pass
    cache[app_id] = m
    return m

def sell_side(app_id, name):
    """(цена продажи, площадка, коэфф. на руки) или None."""
    sp = steam_price(app_id, name)
    if sp: return sp, "Steam", NET_STEAM
    sk = skinport_map(app_id).get(name)
    if sk: return sk, "Skinport", NET_SKINPORT
    return None

def plati_cheapest(query, match_words, price_min, price_max):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        items = requests.get(PLATI, params=params, headers=HEADERS, timeout=25).json().get("items", [])
    except Exception:
        return None
    best = None
    for it in items:
        nm = (it.get("name") or "").lower()
        price = it.get("price_usd"); url = it.get("url")
        if not price or not url: continue
        if not all(w.lower() in nm for w in match_words): continue
        if not (price_min <= float(price) <= price_max): continue
        if best is None or float(price) < best["price"]:
            best = {"name": it.get("name","")[:70], "price": float(price), "seller": it.get("seller_name",""), "url": url}
    return best

def scan_keys(out):
    s = sell_side(440, KEY_STEAM_NAME)
    if not s:
        out["keys"]["status"] = "нет цены продажи (Steam и Skinport молчат)"
        return
    price, venue, netk = s
    net = round(price * netk, 2)
    out["keys"].update({"sell_price": price, "venue": venue, "net_sell": net, "status": "ok"})
    lot = plati_cheapest("ключ mann co supply crate tf2", ["mann"], max(1.0, net * 0.5), net * 0.98)
    if lot:
        profit = round(net - lot["price"], 2)
        out["keys"]["offers"] = [{**lot, "venue": venue, "profit": profit, "pct": round(profit / lot["price"] * 100, 1)}]
    else:
        out["keys"]["status"] = "дешёвого ключа на plati нет (нужно дешевле $" + str(net) + ")"

def scan_skins(out):
    for skin in SKINS:
        s = sell_side(730, skin)
        if not s:
            out["skins"].append({"skin": skin, "status": "нет цены продажи"})
            time.sleep(2)
            continue
        price, venue, netk = s
        net = price * netk
        words = [w for w in re.split(r"\s*\|\s*|\s*\(\s*|\)\s*", skin) if w][:3]
        words = [w for w in words if not w.lower().startswith(("field", "factory", "minimal", "well", "battle"))][:2]
        entry = {"skin": skin, "sell_price": price, "venue": venue, "net_sell": round(net, 2), "status": "ok"}
        lot = plati_cheapest(skin, words, max(0.5, net * 0.35), net * 0.98) if words else None
        if lot:
            profit = round(net - lot["price"], 2)
            entry.update({"buy": lot, "profit": profit, "pct": round(profit / lot["price"] * 100, 1)})
        else:
            entry["status"] = "дешёвого лота на plati нет"
        out["skins"].append(entry)
        time.sleep(2)

def main():
    out = {"updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "keys": {"offers": []}, "skins": []}
    scan_keys(out)
    scan_skins(out)
    with open("skins.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("keys net:", out["keys"].get("net_sell"), "| skins ok:", sum(1 for x in out["skins"] if x.get("venue")))

if __name__ == "__main__":
    main()