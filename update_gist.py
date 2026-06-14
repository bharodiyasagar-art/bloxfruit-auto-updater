import json
import os
import requests
from playwright.sync_api import sync_playwright

# ── Config ───────────────────────────────────────────────────────────────
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
    raw = raw.strip().replace(",", "").replace(" ", "")
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

def scrape():
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print("Loading page...")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        
        # Wait for items to load - try multiple possible selectors
        print("Waiting for content...")
        page.wait_for_timeout(5000)
        
        # Dump ALL visible text from the page so we can debug what's there
        # This prints the full page text to the Actions log
        all_text = page.inner_text("body")
        print("=== PAGE TEXT SAMPLE (first 3000 chars) ===")
        print(all_text[:3000])
        print("=== END SAMPLE ===")
        
        # Try to find cards using various selectors the site might use
        selectors_to_try = [
            "div[class*='card']",
            "div[class*='item']", 
            "div[class*='fruit']",
            "div[class*='value']",
            "li[class*='item']",
            "article",
            "[data-name]",
            "[data-fruit]",
        ]
        
        cards = []
        for selector in selectors_to_try:
            found = page.query_selector_all(selector)
            if len(found) > 5:  # We expect many fruits
                print(f"Found {len(found)} elements with selector: {selector}")
                cards = found
                break
        
        if cards:
            print(f"Extracting from {len(cards)} cards...")
            for card in cards:
                try:
                    text = card.inner_text()
                    # Print first few cards so we can see the structure
                    if len(results) < 3:
                        print(f"Card text sample: {repr(text[:200])}")
                    
                    # Match against known fruit names
                    for name in RARITY_MAP.keys():
                        if name.lower() in text.lower():
                            # Extract numbers from this card
                            import re
                            numbers = re.findall(r'[\d,]+(?:\.\d+)?[KMBkmb]?', text)
                            for num in numbers:
                                val = parse_value(num)
                                if val > 1000:  # Skip tiny numbers
                                    if name not in results or val > results[name]:
                                        results[name] = val
                                    break
                except Exception as e:
                    pass
        
        browser.close()
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
    print("Scraping bloxfruitsvalues.com...")
    scraped = scrape()
    print(f"Scraped values for: {list(scraped.keys())}")

    fruits = []
    for name, rarity in RARITY_MAP.items():
        value = scraped.get(name, 0)
        fruits.append({
            "name": name,
            "icon": ICONS.get(name, "🍎"),
            "value": value,
            "rarity": rarity
        })
        print(f"  {name}: {value}")

    update_gist(fruits)
