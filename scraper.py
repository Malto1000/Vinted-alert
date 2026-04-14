import requests
import json
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

SEARCHES = [
    {"query": "ralph lauren", "min_price": 3, "max_price": 25},
    {"query": "lacoste", "min_price": 3, "max_price": 25},
    {"query": "the north face", "min_price": 3, "max_price": 25},
    {"query": "tommy hilfiger", "min_price": 3, "max_price": 25},
    {"query": "carhartt", "min_price": 3, "max_price": 25},
]

MOTS_SUSPECTS = [
    "boite", "box", "vide", "coque", "housse", "sans", "accessoire",
    "lot", "étiquette", "tag", "logo", "patch", "badge", "flocage"
]

SEEN_FILE = "seen.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def is_suspect(item):
    title = item.get("title", "").lower()
    price_raw = item.get("price", 0)
    price = float(price_raw["amount"]) if isinstance(price_raw, dict) else float(price_raw)

    photos = item.get("photos", [])
    
    # Filtre mots suspects
    for mot in MOTS_SUSPECTS:
        if mot in title:
            return True
    
    # Filtre prix trop bas
    if price < 3:
        return True
    
    # Filtre pas assez de photos
    if len(photos) < 2:
        return True
    
    return False

def get_session():
    session = requests.Session()
    session.get("https://www.vinted.fr", headers={
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    return session

def search_vinted(session, query, min_price, max_price):
    url = "https://www.vinted.fr/api/v2/catalog/items"
    params = {
        "search_text": query,
        "price_from": min_price,
        "price_to": max_price,
        "order": "newest_first",
        "per_page": 20,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
    try:
        r = session.get(url, params=params, headers=headers, timeout=15)
        print(f"Status {query}: {r.status_code}")
        data = r.json()
        return data.get("items", [])
    except Exception as e:
        print(f"Erreur: {e}")
        return []

def send_telegram(item):
    title = item.get("title", "Sans titre")
    price = item.get("price", "?")
    url = f"https://www.vinted.fr/items/{item['id']}"
    nb_photos = len(item.get("photos", []))
    msg = f"🔥 {title}\n💶 {price}€\n📸 {nb_photos} photos\n🔗 {url}"
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )
    print(f"Telegram status: {r.status_code}")

def main():
    seen = load_seen()
    new_seen = set()
    session = get_session()

    for search in SEARCHES:
        items = search_vinted(session, search["query"], search["min_price"], search["max_price"])
        print(f"{search['query']}: {len(items)} articles trouvés")
        for item in items:
            item_id = str(item["id"])
            new_seen.add(item_id)
            if item_id not in seen and not is_suspect(item):
                send_telegram(item)

    save_seen(seen | new_seen)

if __name__ == "__main__":
    main()
