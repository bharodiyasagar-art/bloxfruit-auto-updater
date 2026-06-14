import json
import re
import os
import requests
from playwright.sync_api import sync_playwright

# ── Config ──────────────────────────────────────────────────────────────
GIST_ID = "b421f139c6cf695e25d461b3067ff237"
GIST_FILENAME = "fruits.json"
GH_TOKEN = os.environ["GH_TOKEN"]
URL = "https://bloxfruitsvalues.com/values"

# Emoji icons matching your existing gist
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
    "Blade": "⚔️", "Spin": "🌪️", "Rocket": "🚀",
    "Leopard": "🐆", "Dragon": "🐉", "Kitsune": "🦊",
}

DEFAULT_ICON = "🍎"

def parse_value(raw):
    if not raw:
        return 0
    raw = raw.strip().upper().replace(",", "").replace(" ", "")
    mult = 1
    if raw.endswith("B"):
        mult = 1_000_000_000; raw = raw[:-1]
    elif raw.endswith("M"):
        mult = 1_000_000; raw = raw[:-1]
    elif raw.endswith("K"):
        mult = 1_000; raw = raw[:-1]
    try:
        return int(float(raw) * mult)
    except:
        return 0

def scrape():
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)

        # Wait until fruit cards appear
        page.wait_for_selector("[class*='card'], [class*='item'], [class*='fruit']", timeout=30000)
        page.wait_for_timeout(3000)  # extra wait for JS to finish

        # Try to get all text content and look for fruit names + values
        content = page.content()
        browser.close()
    return content

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
        print(f"❌ Failed to update gist: {r.status_code} {r.text}")
        exit(1)

if __name__ == "__main__":
    print("Scraping bloxfruitsvalues.com ...")
    html = scrape()

    # Parse fruit names and values from the rendered HTML
    # We look for known fruit names near number values
    existing = [
        {"name": "West Dragon", "rarity": "mythical"},
        {"name": "East Dragon", "rarity": "mythical"},
        {"name": "Kitsune", "rarity": "mythical"},
        {"name": "Tiger", "rarity": "mythical"},
        {"name": "Yeti", "rarity": "mythical"},
        {"name": "Control", "rarity": "mythical"},
        {"name": "Gas", "rarity": "mythical"},
        {"name": "Dough", "rarity": "mythical"},
        {"name": "T-Rex", "rarity": "mythical"},
        {"name": "Venom", "rarity": "mythical"},
        {"name": "Gravity", "rarity": "mythical"},
        {"name": "Mammoth", "rarity": "mythical"},
        {"name": "Spirit", "rarity": "mythical"},
        {"name": "Shadow", "rarity": "mythical"},
        {"name": "Lightning", "rarity": "legendary"},
        {"name": "Pain", "rarity": "legendary"},
        {"name": "Portal", "rarity": "legendary"},
        {"name": "Buddha", "rarity": "legendary"},
        {"name": "Blizzard", "rarity": "legendary"},
        {"name": "Creation", "rarity": "legendary"},
        {"name": "Phoenix", "rarity": "legendary"},
        {"name": "Sound", "rarity": "legendary"},
        {"name": "Spider", "rarity": "legendary"},
        {"name": "Love", "rarity": "legendary"},
        {"name": "Quake", "rarity": "legendary"},
        {"name": "Magma", "rarity": "rare"},
        {"name": "Light", "rarity": "rare"},
        {"name": "Ghost", "rarity": "rare"},
        {"name": "Rubber", "rarity": "rare"},
        {"name": "Diamond", "rarity": "uncommon"},
        {"name": "Eagle", "rarity": "uncommon"},
        {"name": "Ice", "rarity": "uncommon"},
        {"name": "Dark", "rarity": "uncommon"},
        {"name": "Sand", "rarity": "uncommon"},
        {"name": "Flame", "rarity": "uncommon"},
        {"name": "Spike", "rarity": "common"},
        {"name": "Smoke", "rarity": "common"},
        {"name": "Bomb", "rarity": "common"},
        {"name": "Spring", "rarity": "common"},
        {"name": "Blade", "rarity": "common"},
        {"name": "Spin", "rarity": "common"},
        {"name": "Rocket", "rarity": "common"},
    ]

    fruits = []
    for item in existing:
        name = item["name"]
        # Search for the value near this fruit name in the HTML
        pattern = re.compile(
            re.escape(name) + r'.{0,200}?([\d,]+(?:\.\d+)?[KMBkmb]?)',
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(html)
        value = parse_value(match.group(1)) if match else 0

        fruits.append({
            "name": name,
            "icon": ICONS.get(name, DEFAULT_ICON),
            "value": value,
            "rarity": item["rarity"]
        })

    if not any(f["value"] > 0 for f in fruits):
        print("❌ Could not extract any values from page. Selectors may need updating.")
        exit(1)

    update_gist(fruits)
