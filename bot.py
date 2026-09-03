#!/usr/bin/env python3
"""
Bot de veille cartes Pokémon -> alertes Telegram.

Deux modes :
  - WATCH-LIST (watchlist.json) : cartes precises que tu choisis.
  - DETECTEUR D'AFFAIRES (discovery.json) : scanne large, IDENTIFIE chaque carte via son
    numero de collection (ex. 199/165), recupere sa cote Cardmarket, et n'alerte QUE si
    l'annonce est nettement sous la cote.

Source de prix (discovery.json -> "price_source") :
  - "pokemontcg" (defaut) : pokemontcg.io. Gratuit aujourd'hui (1000/j sans cle, 20000/j avec cle),
    mais voue a fermer un jour (remplace par Scrydex, qui est PAYANT -> on ne l'utilise pas).
  - "tcgdex" : tcgdex.dev. Gratuit, SANS cle, prix Cardmarket en EUR. Le filet de secours
    pour quand pokemontcg.io fermera. Bascule aussi automatiquement si la source primaire tombe.

Dedup via seen.json. Cache de prix via price_cache.json.
"""
import base64
import json
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

import requests

# --- Secrets / config ---
EBAY_CLIENT_ID = os.environ["EBAY_CLIENT_ID"]
EBAY_CLIENT_SECRET = os.environ["EBAY_CLIENT_SECRET"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
POKEMONTCG_API_KEY = os.environ.get("POKEMONTCG_API_KEY", "")  # utile tant qu'on est sur pokemontcg.io

MARKETPLACE = os.environ.get("EBAY_MARKETPLACE", "EBAY_FR")
CURRENCY = os.environ.get("CURRENCY", "EUR")

WATCHLIST_FILE = Path("watchlist.json")
DISCOVERY_FILE = Path("discovery.json")
SEEN_FILE = Path("seen.json")
CACHE_FILE = Path("price_cache.json")

EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
POKEMONTCG_URL = "https://api.pokemontcg.io/v2/cards"
TCGDEX_BASE = "https://api.tcgdex.net/v2"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

NUM_RE = re.compile(r"(\d{1,3})\s*/\s*(\d{1,3})")
GRADED_RE = re.compile(r"\b(psa|cgc|bgs|gradée?|graded|slab)\b", re.I)

DEFAULT_EXCLUDE = ["lot", "lots", "bulk", "vrac", "fake", "proxy", "replique",
                   "réplique", "replica", "orica", "custom", "classeur",
                   "booster", "display", "coffret", "sealed", "scellé", "étui"]
CACHE_TTL_DAYS = 3
SETS_TTL_DAYS = 30


# ----------------------------- eBay -----------------------------
def get_ebay_token():
    client_id = EBAY_CLIENT_ID.strip()
    client_secret = EBAY_CLIENT_SECRET.strip()
    creds = f"{client_id}:{client_secret}".encode()
    headers = {"Authorization": "Basic " + base64.b64encode(creds).decode(),
               "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"}
    r = requests.post(EBAY_OAUTH_URL, headers=headers, data=data, timeout=30)
    if r.status_code != 200:
        # eBay renvoie la vraie raison dans le corps -> on l'affiche pour diagnostiquer
        print("=== Echec token eBay ===")
        print("Statut :", r.status_code)
        print("Corps  :", r.text)
        print(f"Diag : App ID = {len(client_id)} caractères, "
              f"Cert ID = {len(client_secret)} caractères "
              f"(App ID commence par {client_id[:5]!r})")
        print("========================")
        r.raise_for_status()
    return r.json()["access_token"]


def ebay_search(token, query, min_price, max_price, category_ids=None, limit=200):
    headers = {"Authorization": f"Bearer {token}",
               "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE,
               "Content-Type": "application/json"}
    hi = max_price if max_price else 1000000
    filters = ["buyingOptions:{FIXED_PRICE}",
               f"price:[{min_price:.2f}..{hi:.2f}]",
               f"priceCurrency:{CURRENCY}"]
    params = {"q": query, "filter": ",".join(filters),
              "sort": "newlyListed", "limit": str(limit)}
    if category_ids:
        params["category_ids"] = str(category_ids)
    r = requests.get(EBAY_SEARCH_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("itemSummaries") or []


# ------------------ Prix : source pokemontcg.io -----------------
def _cm_pokemontcg(card):
    p = (card.get("cardmarket") or {}).get("prices") or {}
    return p.get("trendPrice") or p.get("averageSellPrice") or p.get("avg30")


def lookup_pokemontcg(num, total, title):
    """(ref, name) via pokemontcg.io. Peut lever une exception si la source est KO."""
    headers = {"X-Api-Key": POKEMONTCG_API_KEY} if POKEMONTCG_API_KEY else {}
    params = {"q": f"number:{num} set.printedTotal:{total}", "pageSize": 10}
    try:
        r = requests.get(POKEMONTCG_URL, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        cards = r.json().get("data") or []
    finally:
        time.sleep(2.1)  # respecte 30 req/min
    return _pick_card(cards, title, _cm_pokemontcg, name_key="name")


# --------------------- Prix : source tcgdex ---------------------
def _cm_tcgdex(card):
    cm = (card.get("pricing") or {}).get("cardmarket") or {}
    return cm.get("trend") or cm.get("avg") or cm.get("avg30")


def _tcgdex_sets_map(cache):
    """Map {nombre_de_cartes: [setIds]} depuis tcgdex, mise en cache 30j."""
    key = "__tcgdex_sets__"
    e = cache.get(key)
    if e and (time.time() - e.get("ts", 0)) < SETS_TTL_DAYS * 86400:
        return e["map"]
    r = requests.get(f"{TCGDEX_BASE}/en/sets", timeout=30)
    r.raise_for_status()
    m = {}
    for s in r.json():
        cc = s.get("cardCount") or {}
        for cnt in {cc.get("official"), cc.get("total")}:
            if cnt:
                m.setdefault(str(cnt), []).append(s.get("id"))
    cache[key] = {"map": m, "ts": time.time()}
    return m


def lookup_tcgdex(num, total, title, cache):
    """(ref, name) via tcgdex.dev. N'accepte QUE si le nom du Pokemon est dans le titre."""
    setmap = _tcgdex_sets_map(cache)
    candidates = setmap.get(str(total), [])
    tnorm = _norm(title)
    hits = []  # (ref, name) des cartes dont le nom est confirme dans le titre
    for sid in candidates:
        card = None
        for lang in ("fr", "en"):
            try:
                r = requests.get(f"{TCGDEX_BASE}/{lang}/cards/{sid}-{num}", timeout=20)
                if r.status_code == 200:
                    card = r.json()
                    break
            except Exception:
                pass
            finally:
                time.sleep(0.3)
        if not card:
            continue
        name = card.get("name") or ""
        ref = _cm_tcgdex(card)
        if ref and _name_in_title(name, tnorm):
            hits.append((round(float(ref), 2), name))
    if not hits:
        return None, None
    # Plusieurs sets collent au nom mais avec des prix differents -> on ne tranche pas
    if len({r for r, _ in hits}) > 1:
        return None, None
    return hits[0]


# --------------------- Selection / dispatch ---------------------
def _norm(s):
    """minuscule + sans accents, pour comparer noms FR et titres."""
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _name_in_title(name, title_norm):
    """Vrai si un mot significatif (>=4 lettres) du nom apparait dans le titre."""
    for tok in _norm(name).split():
        if len(tok) >= 4 and tok in title_norm:
            return True
    return False


def _pick_card(cards, title, price_fn, name_key="name"):
    if not cards:
        return None, None
    tnorm = _norm(title)
    matched = [c for c in cards if _name_in_title(c.get(name_key, ""), tnorm)]
    if not matched:
        return None, None  # nom non confirme dans le titre -> on ne devine pas
    prices = {round(float(price_fn(c)), 2) for c in matched if price_fn(c)}
    if len(prices) > 1:
        return None, None  # plusieurs cartes plausibles, prix differents -> ambigu
    c = matched[0]
    return price_fn(c), c.get(name_key)


def resolve_price(num, total, title, cache, source):
    """Prix de reference avec cache + bascule automatique entre sources."""
    key = f"{num}/{total}"
    e = cache.get(key)
    if e and (time.time() - e.get("ts", 0)) < CACHE_TTL_DAYS * 86400:
        return e.get("ref"), e.get("name")

    order = ["tcgdex", "pokemontcg"] if source == "tcgdex" else ["pokemontcg", "tcgdex"]
    ref = name = None
    for src in order:
        try:
            if src == "pokemontcg":
                ref, name = lookup_pokemontcg(num, total, title)
            else:
                ref, name = lookup_tcgdex(num, total, title, cache)
            if ref:
                break
        except Exception as ex:
            print(f"    [warn] source {src} KO ({ex}) -> bascule")
            continue

    cache[key] = {"ref": ref, "name": name, "ts": time.time()}
    return ref, name


# ------------------------- Telegram -----------------------------
def _item_image(item):
    if item.get("image"):
        return item["image"].get("imageUrl")
    if item.get("thumbnailImages"):
        return item["thumbnailImages"][0].get("imageUrl")
    return None


def send_telegram(caption, image=None):
    try:
        if image:
            requests.post(f"{TELEGRAM_API}/sendPhoto",
                          data={"chat_id": TELEGRAM_CHAT_ID, "photo": image,
                                "caption": caption, "parse_mode": "HTML"}, timeout=30)
        else:
            requests.post(f"{TELEGRAM_API}/sendMessage",
                          data={"chat_id": TELEGRAM_CHAT_ID, "text": caption,
                                "parse_mode": "HTML"}, timeout=30)
    except Exception as e:
        print(f"  [warn] envoi Telegram echoue: {e}")


def alert_deal(item, name, price, reference, pct):
    title = item.get("title", "")
    url = item.get("itemWebUrl", "")
    caption = (f"💰 <b>AFFAIRE — {pct}% sous la cote</b>\n"
               f"<b>{name}</b>\n{title}\n\n"
               f"💶 Prix : <b>{price:.2f} €</b>\n"
               f"📊 Cote Cardmarket : {reference:.2f} €\n\n"
               f'<a href="{url}">Voir l\'annonce</a>\n'
               f"<i>Vérifie l'état sur les photos (la cote = état correct).</i>")
    send_telegram(caption, _item_image(item))


def alert_watchlist(item, card_name, reference, max_price):
    price = float(item["price"]["value"])
    title = item.get("title", "")
    url = item.get("itemWebUrl", "")
    if reference:
        pct = round((1 - price / reference) * 100)
        ref_block = f"Cote Cardmarket : {reference:.2f} €\n➡️ {pct}% sous la cote\n"
    else:
        ref_block = ""
    caption = (f"🔥 <b>{card_name}</b>\n{title}\n\n"
               f"💶 <b>{price:.2f} €</b>  (seuil {max_price:.2f} €)\n{ref_block}\n"
               f'<a href="{url}">Voir l\'annonce</a>')
    send_telegram(caption, _item_image(item))


# --------------------------- Utils ------------------------------
def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def resolve_max_price(card, cache, source):
    reference = None
    pid = card.get("pokemontcg_id")
    if pid and source != "tcgdex":  # id pokemontcg -> uniquement via pokemontcg.io
        headers = {"X-Api-Key": POKEMONTCG_API_KEY} if POKEMONTCG_API_KEY else {}
        try:
            r = requests.get(f"{POKEMONTCG_URL}/{quote(pid)}", headers=headers, timeout=30)
            r.raise_for_status()
            reference = _cm_pokemontcg(r.json().get("data", {}))
        except Exception as e:
            print(f"    [warn] ref {pid}: {e}")
        time.sleep(2.1)
    if card.get("reference_eur"):
        reference = float(card["reference_eur"])
    if reference:
        return round(reference * card.get("threshold_pct", 100) / 100, 2), reference
    if card.get("max_price"):
        return float(card["max_price"]), None
    return None, None


def title_excluded(title, words):
    t = title.lower()
    return any(w in t for w in words)


# ---------------------------- Modes -----------------------------
def run_watchlist(token, seen, new_seen, cache, source):
    alerts = 0
    for card in load_json(WATCHLIST_FILE, []):
        name = card.get("name", "?")
        query = card.get("ebay_query") or name
        max_price, reference = resolve_max_price(card, cache, source)
        if max_price is None:
            continue
        print(f"• [watch] {name} — seuil {max_price:.2f} €")
        try:
            items = ebay_search(token, query, 0, max_price, limit=50)
        except Exception as e:
            print(f"  [warn] {e}")
            continue
        for it in items:
            iid = it.get("itemId")
            if not iid or iid in seen:
                continue
            new_seen.add(iid)
            try:
                price = float(it["price"]["value"])
            except (KeyError, ValueError, TypeError):
                continue
            if price <= max_price:
                alert_watchlist(it, name, reference, max_price)
                alerts += 1
                time.sleep(1)
        time.sleep(0.4)
    return alerts


def run_deal_detector(token, seen, new_seen, cache, source):
    cfg = load_json(DISCOVERY_FILE, {})
    if not cfg.get("enabled"):
        return 0
    query = cfg.get("query", "pokemon")
    min_price = float(cfg.get("min_price", 7))
    min_ref = float(cfg.get("min_reference_eur", 10))
    min_disc = float(cfg.get("min_discount_pct", 30))
    cap = int(cfg.get("max_alerts_per_run", 25))
    max_lookups = int(cfg.get("max_lookups_per_run", 60))
    category_ids = cfg.get("category_ids") or None
    skip_graded = cfg.get("skip_graded", True)
    exclude = [w.lower() for w in cfg.get("exclude_keywords", DEFAULT_EXCLUDE)]

    print(f"• [affaires] source={source} q={query!r} plancher {min_price:.0f}€ "
          f"| cote≥{min_ref:.0f}€ | décote≥{min_disc:.0f}%")
    try:
        items = ebay_search(token, query, min_price, None, category_ids, limit=200)
    except Exception as e:
        print(f"  [warn] recherche echouee: {e}")
        return 0

    sent = lookups = 0
    for it in items:
        iid = it.get("itemId")
        if not iid or iid in seen:
            continue
        new_seen.add(iid)
        title = it.get("title", "")
        if title_excluded(title, exclude):
            continue
        if skip_graded and GRADED_RE.search(title):
            continue
        try:
            price = float(it["price"]["value"])
        except (KeyError, ValueError, TypeError):
            continue

        m = NUM_RE.search(title)
        if not m:
            continue
        num, total = str(int(m.group(1))), str(int(m.group(2)))

        key = f"{num}/{total}"
        cached = key in cache and (time.time() - cache[key].get("ts", 0)) < CACHE_TTL_DAYS * 86400
        if not cached:
            if lookups >= max_lookups:
                continue
            lookups += 1
        reference, name = resolve_price(num, total, title, cache, source)

        if not reference or reference < min_ref:
            continue
        pct = round((1 - price / reference) * 100)
        if pct < min_disc:
            continue
        if sent >= cap:
            continue
        print(f"  💰 {pct}% — {name} — {price:.2f}€ (cote {reference:.2f}€)")
        alert_deal(it, name or f"Carte {num}/{total}", price, reference, pct)
        sent += 1
        time.sleep(1)

    print(f"  -> {sent} affaire(s), {lookups} lookups.")
    return sent


def main():
    seen = set(load_json(SEEN_FILE, []))
    new_seen = set(seen)
    cache = load_json(CACHE_FILE, {})
    source = (load_json(DISCOVERY_FILE, {}) or {}).get("price_source", "pokemontcg")
    token = get_ebay_token()

    a1 = run_watchlist(token, seen, new_seen, cache, source)
    a2 = run_deal_detector(token, seen, new_seen, cache, source)

    SEEN_FILE.write_text(json.dumps(sorted(new_seen)[-12000:], ensure_ascii=False),
                         encoding="utf-8")
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"\nTerminé. Watch-list: {a1}, Affaires: {a2}. {len(new_seen)} IDs mémorisés.")


if __name__ == "__main__":
    main()
