import json
import os
import re
import requests
from playwright.sync_api import sync_playwright

GIST_ID = "b421f139c6cf695e25d461b3067ff237"
GIST_FILENAME = "fruits.json"
GH_TOKEN = os.environ["GH_TOKEN"]
URL = "https://bloxfruitsvalues.com/values"

ICONS = {
    "West Dragon": "🐉", "East Dragon": "🐲", "Kitsune": "🦊",
    "Tiger": "🐅", "Yeti": "🦍", "Control": "🌀", "Gas": "☁️",
    "Dough": "🍩", "T-Rex": "🦖", "Venom": "🐍", "Gravity": "🌌",
    "Mammoth": "🐘", "Spirit": "👻", "Shadow": "👤", "Lightning": "⚡️",
    "Pain": "💢", "Portal": "🚪", "Buddha": "🧘‍♂️", "Blizzard": "❄️",
    "Creation": "🛠️", "Phoenix": "🐦", "Sound": "🎵", "Spider": "🕷️",
    "Love": "💖", "Quake": "💥", "Magma": "🌋", "Light": "☀️",
    "Ghost": "👻", "Rubber": "🧤", "Diamond": "💎", "Eagle": "🦅",
    "Ice": "🧊", "Dark": "🌑", "Sand": "🏜️", "Flame": "🔥",
    "Spike": "🌵", "Smoke": "💨", "Bomb": "💣", "Spring": "🪀",
    "Blade": "⚔️", "Spin": "🌪️", "Rocket": "🚀", "Leopard": "🐆",
}

RARITY_MAP = {
    "West Dragon": "mythical", "East Dragon": "mythical", "Kitsune": "mythical",
    "Tiger": "mythical", "Yeti": "mythical", "Control": "mythical",
    "Gas": "mythical", "Dough": "mythical", "T-Rex": "mythical",
    "Venom": "mythical", "Gravity": "mythical", "Mammoth": "mythical",
    "Spirit": "mythical", "Shadow": "mythical", "Leopard": "mythical",
    "Lightning": "legendary", "Pain": "legendary", "Portal": "legendary",
    "Buddha": "legendary", "Blizzard": "legendary", "Creation": "legendary",
    "Phoenix": "legendary", "Sound": "legendary", "Spider": "legendary",
    "Love": "legendary", "Quake": "legendary",
    "Magma": "rare", "Light": "rare", "Ghost": "rare", "Rubber": "rare",
    "Diamond": "uncommon", "Eagle": "uncommon", "Ice": "uncommon",
    "Dark": "uncommon", "Sand": "uncommon", "Flame": "uncommon",
    "Spike": "common", "Smoke": "common", "Bomb": "common",
    "Spring": "common", "Blade": "common", "Spin": "common", "Rocket": "common",
}

def parse_value(raw):
    if not raw:
        return 0
    raw = str(raw).strip().replace(",", "").replace(" ", "")
    mult = 1
    upper = raw.upper()
    if upper.endswith("B"):
        mult = 1_000_000_000; raw = raw[:-1]
    elif upper.endswith("M"):
        mult = 1_000_000; raw = raw[:-1]
    elif upper.endswith("K"):
        mult = 1_000; raw = raw[:-1]
    try:
        return int(float(raw) * mult)
    except:
        return 0

def search_json_for_fruits(data, fruit_names):
    results = {}
    if isinstance(data, list):
        for item in data:
            results.update(search_json_for_fruits(item, fruit_names))
    elif isinstance(data, dict):
        name = None
        value = None
        for key in ("name", "title", "fruit", "item", "label"):
            if key in data and isinstance(data[key], str):
                candidate = data[key].strip()
                if candidate in fruit_names:
                    name = candidate
                    break
        for key in ("value", "price", "val", "worth", "amount", "regular", "physical"):
            if key in data:
                v = parse_value(str(data[key]))
                if v > 0:
                    value = v
                    break
        if name and value:
            results[name] = value
        for v in data.values():
            if isinstance(v, (dict, list)):
                results.update(search_json_for_fruits(v, fruit_names))
    return results

def scrape():
    captured_responses = []
    fruit_names = list(RARITY_MAP.keys())

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        def handle_response(response):
            url = response.url
            ctype = response.headers.get("content-type", "")
            if "json" in ctype or url.endswith(".json"):
                try:
                    body = response.body()
                    if len(body) > 500:
                        captured_responses.append({
                            "url": url,
                            "body": body.decode("utf-8", errors="replace")
                        })
                        print(f"[CAPTURED] {url} ({len(body)} bytes)")
                except:
                    pass

        page.on("response", handle_response)

        print("Loading page...")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(6000)

        # Print visible text so we can debug
        body_text = page.inner_text("body")
        print("\n=== VISIBLE PAGE TEXT (first 2000 chars) ===")
        print(body_text[:2000])
        print("=== END ===\n")

        browser.close()

    results = {}

    for resp in captured_responses:
        body = resp["body"]
        try:
            data = json.loads(body)
            found = search_json_for_fruits(data, fruit_names)
            if found:
                print(f"Found {len(found)} fruits in {resp['url']}")
                results.update(found)
        except json.JSONDecodeError:
            pass

        for name in fruit_names:
            if name in body and name not in results:
                pattern = re.compile(
                    re.escape(name) + r'.{0,300}?([\d]{3,}[\d,]*)',
                    re.IGNORECASE | re.DOTALL
                )
                m = pattern.search(body)
                if m:
                    val = parse_value(m.group(1))
                    if val > 1000:
                        results[name] = val
                        print(f"  Text match -> {name}: {val}")

    return results

def update_gist(fruits):
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "files": {
            GIST_FILENAME: {
                "content": json.dumps(fruits, indent=2, ensure_ascii=False)
            }
        }
    }
    r = requests.patch(f"https://api.github.com/gists/{GIST_ID}", headers=headers, json=data)
    if r.status_code == 200:
        print(f"✅ Gist updated with {len(fruits)} fruits!")
    else:
        print(f"❌ Failed: {r.status_code} {r.text}")
        exit(1)

if __name__ == "__main__":
    scraped = scrape()
    print(f"\nScraped {len(scraped)} fruits: {list(scraped.keys())}")

    fruits = []
    for name, rarity in RARITY_MAP.items():
        value = scraped.get(name, 0)
        fruits.append({
            "name": name,
            "icon": ICONS.get(name, "🍎"),
            "value": value,
            "rarity": rarity
        })

    found_count = sum(1 for f in fruits if f["value"] > 0)
    print(f"\n{found_count}/{len(fruits)} fruits have values > 0")

    if found_count == 0:
        print("❌ No values found — share this log so I can fix the selectors!")
        exit(1)

    update_gist(fruits)
