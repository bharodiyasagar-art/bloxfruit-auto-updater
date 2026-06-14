import json, os, requests
from playwright.sync_api import sync_playwright

GIST_ID = "b421f139c6cf695e25d461b3067ff237"
GIST_FILENAME = "fruits.json"
GH_TOKEN = os.environ["GH_TOKEN"]
URL = "https://bloxfruitsvalues.com/values"

ICONS = {
    "West Dragon":"🐉","East Dragon":"🐲","Kitsune":"🦊","Tiger":"🐅",
    "Yeti":"🦍","Control":"🌀","Gas":"☁️","Dough":"🍩","T-Rex":"🦖",
    "Venom":"🐍","Gravity":"🌌","Mammoth":"🐘","Spirit":"👻","Shadow":"👤",
    "Lightning":"⚡️","Pain":"💢","Portal":"🚪","Buddha":"🧘‍♂️","Blizzard":"❄️",
    "Creation":"🛠️","Phoenix":"🐦","Sound":"🎵","Spider":"🕷️","Love":"💖",
    "Quake":"💥","Magma":"🌋","Light":"☀️","Ghost":"👻","Rubber":"🧤",
    "Diamond":"💎","Eagle":"🦅","Ice":"🧊","Dark":"🌑","Sand":"🏜️",
    "Flame":"🔥","Spike":"🌵","Smoke":"💨","Bomb":"💣","Spring":"🪀",
    "Blade":"⚔️","Spin":"🌪️","Rocket":"🚀","Leopard":"🐆",
}

RARITY_MAP = {
    "West Dragon":"mythical","East Dragon":"mythical","Kitsune":"mythical",
    "Tiger":"mythical","Yeti":"mythical","Control":"mythical","Gas":"mythical",
    "Dough":"mythical","T-Rex":"mythical","Venom":"mythical","Gravity":"mythical",
    "Mammoth":"mythical","Spirit":"mythical","Shadow":"mythical","Leopard":"mythical",
    "Lightning":"legendary","Pain":"legendary","Portal":"legendary","Buddha":"legendary",
    "Blizzard":"legendary","Creation":"legendary","Phoenix":"legendary","Sound":"legendary",
    "Spider":"legendary","Love":"legendary","Quake":"legendary",
    "Magma":"rare","Light":"rare","Ghost":"rare","Rubber":"rare",
    "Diamond":"uncommon","Eagle":"uncommon","Ice":"uncommon","Dark":"uncommon",
    "Sand":"uncommon","Flame":"uncommon",
    "Spike":"common","Smoke":"common","Bomb":"common","Spring":"common",
    "Blade":"common","Spin":"common","Rocket":"common",
}

def parse_value(raw):
    raw = str(raw).strip().replace(",","").replace(" ","")
    mult = 1
    u = raw.upper()
    if u.endswith("B"): mult=1_000_000_000; raw=raw[:-1]
    elif u.endswith("M"): mult=1_000_000; raw=raw[:-1]
    elif u.endswith("K"): mult=1_000; raw=raw[:-1]
    try: return int(float(raw)*mult)
    except: return 0

def parse_page_text(text, fruit_names):
    results = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        if lines[i] in fruit_names:
            name = lines[i]
            for j in range(i+1, min(i+15, len(lines))):
                if lines[j] == "Value":
                    if j+1 < len(lines):
                        val = parse_value(lines[j+1])
                        if val > 0:
                            results[name] = val
                            print(f"  ✅ {name}: {lines[j+1]} → {val:,}")
                    break
        i += 1
    return results

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Use a real viewport size so lazy-load triggers properly
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        def block_ads(route):
            blocked = ["playwire","googlesyndication","doubleclick",
                       "google-analytics","facebook.net","id5-sync","prebid"]
            if any(b in route.request.url for b in blocked):
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_ads)
        print("Loading page...")
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for first fruit to appear
        print("Waiting for initial fruit data...")
        try:
            page.wait_for_function(
                "document.body.innerText.includes('West Dragon')",
                timeout=20000
            )
            print("✅ First fruits loaded!")
        except:
            print("⚠️ Timed out waiting — continuing anyway")

        # Scroll down slowly to trigger lazy loading of ALL fruits
        print("Scrolling to load all fruits...")
        last_fruit_count = 0
        for scroll_attempt in range(20):
            # Scroll down by one screen height
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(800)  # wait for lazy load to trigger

            # Count how many fruit names are now visible
            current_text = page.inner_text("body")
            current_count = sum(1 for name in RARITY_MAP if name in current_text)
            print(f"  Scroll {scroll_attempt+1}: {current_count} fruits visible")

            # Stop if we have all fruits OR no new ones loaded after 3 scrolls
            if current_count >= len(RARITY_MAP):
                print("✅ All fruits loaded!")
                break
            if current_count == last_fruit_count and scroll_attempt > 3:
                print(f"No new fruits after scroll — stopping at {current_count}")
                break
            last_fruit_count = current_count

        # Final wait for any last renders
        page.wait_for_timeout(2000)
        body_text = page.inner_text("body")
        browser.close()

        print(f"\nTotal page text: {len(body_text)} chars")
        return body_text

def update_gist(fruits):
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers,
        json={"files": {GIST_FILENAME: {"content": json.dumps(fruits, indent=2, ensure_ascii=False)}}}
    )
    if r.status_code == 200:
        print(f"✅ Gist updated with {len(fruits)} fruits!")
    else:
        print(f"❌ Failed: {r.status_code} {r.text}"); exit(1)

if __name__ == "__main__":
    fruit_names = set(RARITY_MAP.keys())
    page_text = scrape()

    print("\nParsing values from page text...")
    scraped = parse_page_text(page_text, fruit_names)
    print(f"\nFound {len(scraped)}/{len(fruit_names)} fruits")

    fruits = []
    for name, rarity in RARITY_MAP.items():
        fruits.append({
            "name": name,
            "icon": ICONS.get(name, "🍎"),
            "value": scraped.get(name, 0),
            "rarity": rarity
        })

    found = sum(1 for f in fruits if f["value"] > 0)
    print(f"{found}/{len(fruits)} fruits have values > 0")

    if found < 5:
        print("❌ Too few values found — check logs!"); exit(1)

    update_gist(fruits)
