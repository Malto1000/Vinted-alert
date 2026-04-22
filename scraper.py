import requests
import json
import os
import csv
import io

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

SHEET_ID = "1NIwcVEZrc79fbj5LXIJ76C4wKPc7_mbegYy5bkAWHbE"

MOTS_SUSPECTS = [
    "boite", "box", "vide", "coque", "housse", "sans", "accessoire",
    "lot", "etiquette", "tag", "logo", "patch", "badge", "flocage"
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

def load_users():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    r = requests.get(url, timeout=10)
    users = []
    reader = csv.DictReader(io.StringIO(r.text))
    for row in reader:
        chat_id = row.get("chat_id", "").strip()
        marques_raw = row.get("Marques", "")
        prix_max = row.get("Prix Maximum (reponse en nombres uniquement)", "25").strip()
        if not chat_id:
            continue
        marques = [m.strip() for m in marques_raw.split(",")]
        users.append({
            "prenom": row.get("Prenom (pas d'espaces ni de caracteres speciaux)", "").strip(),
            "chat_id": chat_id,
            "marques": marques,
            "prix_max": float(prix_max) if prix_max else 25,
        })
    print(f"{len(users)} utilisateurs chargés")
    return users

def is_suspect(item):
    title = item.get("title", "").lower()
    photos = item.get("photos", [])
    price_raw = item.get("price", 0)
    if isinstance(price_raw, dict):
        price = float(price_raw.get("amount", 0))
    else:
        price = float(price_raw)
    for mot in MOTS_SUSPECTS:
        if mot in title:
            return True
    if price < 3:
        return True
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

def search_vinted(session, query, prix_max):
    url = "https://www.vinted.fr/api/v2/catalog/items"
    params = {
        "search_text": query,
        "price_from": 3,
        "price_to": prix_max,
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
        data = r.json()
        return data.get("items", [])
    except Exception as e:
        print(f"Erreur: {e}")
        return []

def send_telegram(chat_id, item):
    title = item.get("title", "Sans titre")
    price_raw = item.get("price", "?")
    if isinstance(price_raw, dict):
        price = price_raw.get("amount", "?")
    else:
        price = price_raw
    url = f"https://www.vinted.fr/items/{item['id']}"
    nb_photos = len(item.get("photos", []))
    msg = f"🔥 {title}\n💶 {price}€\n📸 {nb_photos} photos\n🔗 {url}"
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": msg}
    )
    print(f"Telegram {chat_id}: {r.status_code}")

def main():
    seen = load_seen()
    new_seen = set()
    session = get_session()
    users = load_users()

    for user in users:
        print(f"Recherche pour {user['prenom']}...")
        for marque in user["marques"]:
            items = search_vinted(session, marque, user["prix_max"])
            print(f"  {marque}: {len(items)} articles")
            for item in items:
                item_id = str(item["id"])
                new_seen.add(item_id)
                user_key = f"{item_id}_{user['chat_id']}"
                if user_key not in seen and not is_suspect(item):
                    send_telegram(user["chat_id"], item)

    save_seen(seen | new_seen)

if __name__ == "__main__":
    main()
