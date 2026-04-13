import requests
import json
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Tes mots-clés et prix max
SEARCHES = [
    {"query": "iphone 13", "max_price": 300},
    {"query": "nike tn", "max_price": 60},
    {"query": "airpods", "max_price": 50},
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

def search_vinted(query, max_price):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={query}&price_to={max_price}&order=newest_first&per_page=20"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        return data.get("items", [])
    except:
        return []

def send_telegram(item):
    title = item.get("title", "Sans titre")
    price = item.get("price", "?")
    url = f"https://www.vinted.fr/items/{item['id']}"
    photo = item.get("photo", {}).get("url", "")
    
    msg = f"🔥 *{title}*\n💶 {price}€\n🔗 {url}"
    
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    )

def main():
    seen = load_seen()
    new_seen = set()
    
    for search in SEARCHES:
        items = search_vinted(search["query"], search["max_price"])
        for item in items:
            item_id = str(item["id"])
            new_seen.add(item_id)
            if item_id not in seen:
                send_telegram(item)
    
    save_seen(seen | new_seen)

if __name__ == "__main__":
    main()
