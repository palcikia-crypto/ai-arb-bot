import requests, re, json, time

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}
PLATI = "https://plati.io/api/search.ashx"
STEAM = "https://steamcommunity.com/market/priceoverview/"
# комиссия Steam: продавец получает ~85% (CS2 ~13%+2%, TF2 ~10%+2%)
NET_SKINS = 0.85
NET_KEYS = 0.88

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

def steam_price(appid, name):
    try:
        r = requests.get(STEAM, params={"appid": appid, "currency": 1, "market_hash_name": name}, headers=HEADERS, timeout=12)
        d = r.json()
        if d.get("success") and d.get("lowest_price"):
            return float(re.sub(r"[^\d.]", "", d["lowest_price"]))
    except Exception:
        pass
    return None

def plati_cheapest(query, match_words, price_min, price_max):
    params = {"query": query, "pagesize": 50, "pagenum": 1, "visibleOnly": "true", "response": "json"}
    try:
        items = requests.get(PLATI, params=params, headers=HEADERS, timeout=20).json().get("items", [])
    except Exception:
        return None
    best = None
    for it in items:
        name = (it.get("name") or "").lower()
        price = it.get("price_usd")
        url = it.get("url")
        if not price or not url: continue
        if not all(w.lower() in name for w in match_words): continue
        if not (price_min <= float(price) <= price_max): continue
        if best is None or float(price) < best["price"]:
            best = {"name": it.get("name","")[:70], "price": float(price), "seller": it.get("seller_name",""), "url": url}
    return best

def scan_keys(out):
    sp = steam_price(440, KEY_STEAM_NAME)
    out["keys"]["steam_price"] = sp
    if sp is None: return
    net = round(sp * NET_KEYS, 2)
    out["keys"]["net_sell"] = net
    lot = plati_cheapest("ключ mann co supply crate tf2", ["mann"], max(1.0, net * 0.55), net * 0.98)
    if lot:
        profit = round(net - lot["price"], 2)
        pct = round(profit / lot["price"] * 100, 1)
        out["keys"]["offers"] = [{**lot, "steam_sell": sp, "net_sell": net, "profit": profit, "pct": pct}]

def scan_skins(out):
    for skin in SKINS:
        sp = steam_price(730, skin)
        if sp is None:
            out["skins"].append({"skin": skin, "status": "нет цены Steam"})
            time.sleep(3)
            continue
        net = sp * NET_SKINS
        words = [w for w in re.split(r"\s*\|\s*|\s*\(\s*|\)\s*", skin) if w][:3]
        words = [w for w in words if not w.lower().startswith(("field", "factory", "minimal", "well", "battle"))][:2]
        if not words: continue
        lot = plati_cheapest(skin, words, max(0.5, net * 0.4), net * 0.98)
        entry = {"skin": skin, "steam_price": sp, "net_sell": round(net, 2), "status": "ok"}
        if lot:
            profit = round(net - lot["price"], 2)
            entry.update({"buy": lot, "profit": profit, "pct": round(profit / lot["price"] * 100, 1)})
        else:
            entry["status"] = "дешёвого лота на plati нет"
        out["skins"].append(entry)
        time.sleep(3)

def main():
    out = {"updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "keys": {"offers": []}, "skins": []}
    scan_keys(out)
    scan_skins(out)
    with open("skins.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    k = len(out["keys"].get("offers", []))
    s = sum(1 for x in out["skins"] if x.get("profit", 0) > 0)
    print("keys offers:", k, "| skins profitable:", s, "/", len(out["skins"]))

if __name__ == "__main__":
    main()