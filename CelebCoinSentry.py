import time
import requests
import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

# -------------------------------------------------
# CelebCoinSentry Metadata
# -------------------------------------------------
SCRIPT_NAME = "CelebCoinSentry"
AUTHOR_NAME = "rnvntr"
VERSION = "1.0.0"

# -------------------------------------------------
# Configuration
# -------------------------------------------------

# 1) How to alert: "email", "discord", or "both"
ALERT_METHOD = "discord"

# 2) Interval between checks (in seconds)
CHECK_INTERVAL = 3600  # e.g. 1 hour

# 3) If True, scrape CoinGecko's Recently Added HTML page. 
#    If False, fallback to the official /markets API for top coins.
SCRAPE_RECENTLY_ADDED = True

# 4) Time in seconds to wait between requests to reduce rate-limit issues
TIME_BETWEEN_REQUESTS = 60

# 5) Whether to use a custom “User-Agent” header 
#    (helps avoid 403 errors when scraping HTML).
USE_CUSTOM_USER_AGENT = True

# User-Agent to use if USE_CUSTOM_USER_AGENT is True
CUSTOM_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# 3a) CoinGecko "Recently Added" page (HTML)
COINGECKO_RECENTLY_ADDED_URL = "https://www.coingecko.com/en/coins/recently_added"

# 3b) If not scraping HTML, fetch from official API (top coins).
COINGECKO_API_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd"
    "&order=market_cap_desc"
    "&per_page=10"
    "&page=1"
    "&sparkline=false"
    "&locale=en"
    # Removed "&category=new" to avoid 404
)

# Email settings (only relevant if ALERT_METHOD includes "email")
EMAIL_SENDER = "youremail@example.com"
EMAIL_PASSWORD = "YOUR_EMAIL_PASSWORD_OR_APP_PASSWORD"
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_RECIPIENTS = ["recipient1@example.com"]

# Discord settings (only relevant if ALERT_METHOD includes "discord")
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
DISCORD_BOT_NAME = "CelebCoinSentry Bot"
DISCORD_BOT_ICON = ""  # or URL to an image

# Local file with celebrity names (one name per line)
CELEBRITY_NAMES_FILE = "CelebCoinSentry_celebrity_names.txt"

# Where we store alerted coins locally (to avoid duplicates)
ALERTED_COINS_FILE = "CelebCoinSentry_alerted_coins.txt"

# -------------------------------------------------
# Global in-memory sets
# -------------------------------------------------
CELEBRITY_NAMES = set()
ALERTED_COIN_IDS = set()

# -------------------------------------------------
# Request Helpers
# -------------------------------------------------

def build_headers():
    """
    If USE_CUSTOM_USER_AGENT is True, return a dict with a custom User-Agent.
    Otherwise, return None (so requests uses default).
    """
    if USE_CUSTOM_USER_AGENT:
        return {"User-Agent": CUSTOM_USER_AGENT}
    return None

# -------------------------------------------------
# Load/Save Functions
# -------------------------------------------------

def load_celebrity_names():
    """Load celebrity names from a local text file into a set."""
    global CELEBRITY_NAMES
    if not os.path.exists(CELEBRITY_NAMES_FILE):
        print(f"[WARN] {CELEBRITY_NAMES_FILE} not found. No celebrities loaded.")
        CELEBRITY_NAMES = set()
        return
    
    with open(CELEBRITY_NAMES_FILE, "r", encoding="utf-8") as f:
        names = [line.strip() for line in f if line.strip()]
    CELEBRITY_NAMES = set(names)
    print(f"[INFO] Loaded {len(CELEBRITY_NAMES)} celebrity names from {CELEBRITY_NAMES_FILE}.")

def load_alerted_coins():
    """Load previously alerted coin IDs from a file into ALERTED_COIN_IDS set."""
    global ALERTED_COIN_IDS
    if not os.path.exists(ALERTED_COINS_FILE):
        ALERTED_COIN_IDS = set()
        return

    with open(ALERTED_COINS_FILE, "r", encoding="utf-8") as f:
        ids = [line.strip() for line in f if line.strip()]
    ALERTED_COIN_IDS = set(ids)
    print(f"[INFO] Loaded {len(ALERTED_COIN_IDS)} alerted coins from {ALERTED_COINS_FILE}.")

def save_alerted_coins():
    """Save the current ALERTED_COIN_IDS set to file."""
    with open(ALERTED_COINS_FILE, "w", encoding="utf-8") as f:
        for coin_id in ALERTED_COIN_IDS:
            f.write(f"{coin_id}\n")

# -------------------------------------------------
# Coin Fetch (API + HTML)
# -------------------------------------------------

def get_coins_via_api():
    """
    Fetch coins from the CoinGecko /markets endpoint 
    (top by market cap if not specifying category).
    Returns a list of dicts with 'id', 'name', 'symbol', etc.
    """
    headers = build_headers()  # custom or None
    try:
        response = requests.get(COINGECKO_API_URL, headers=headers, timeout=20)
        time.sleep(TIME_BETWEEN_REQUESTS)  # sleep to avoid rate-limits
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            print("[WARN] Unexpected API response format.")
            return []
        return data
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch data from CoinGecko API: {e}")
        return []

def get_coins_via_recently_added_html():
    """
    Scrape the 'Recently Added' page on CoinGecko for newly listed coins.
    Returns a list of dicts with keys like:
        {
          'id': 'some-slug',
          'symbol': 'ABC',
          'name': 'ABC Token',
          'current_price': None,
          'description': ''
        }
    """
    headers = build_headers()  # custom or None
    coins = []
    try:
        response = requests.get(
            COINGECKO_RECENTLY_ADDED_URL, 
            headers=headers, 
            timeout=20
        )
        time.sleep(TIME_BETWEEN_REQUESTS)  # sleep to avoid rate-limits
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # The table of recently added coins is typically .table-scrollable > table > tbody
        table_body = soup.select_one(".table-scrollable table tbody")
        if not table_body:
            print("[WARN] Could not find the 'Recently Added' table body.")
            return coins
        
        rows = table_body.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if not cols or len(cols) < 2:
                continue

            anchor = row.select_one("a.tw-flex")
            if not anchor:
                continue
            
            name_span = anchor.select_one("span.tw-hidden")
            if not name_span:
                continue
            name_text = name_span.get_text(strip=True)

            symbol_span = name_span.find_next_sibling("span")
            if not symbol_span:
                continue
            symbol_text = symbol_span.get_text(strip=True)

            href = anchor.get("href", "")
            slug = href.split("/en/coins/")[-1] if "/en/coins/" in href else ""

            coin_dict = {
                "id": slug or f"{name_text.lower().replace(' ', '-')}-unknown",
                "symbol": symbol_text,
                "name": name_text,
                "current_price": None,
                "description": ""
            }
            coins.append(coin_dict)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch data from CoinGecko Recently Added page: {e}")
        return []

    return coins

def get_coin_description(coin_id):
    """
    If we want extended data for a coin by ID (like official description),
    we can do an extra call: /coins/{coin_id}?localization=false&market_data=false&community_data=false&developer_data=false
    """
    headers = build_headers()
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&market_data=false&community_data=false&developer_data=false"
    try:
        response = requests.get(url, headers=headers, timeout=20)
        time.sleep(TIME_BETWEEN_REQUESTS)  # sleep to avoid rate-limits
        response.raise_for_status()
        info = response.json()
        desc = info.get("description", {}).get("en", "")
        return desc
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch description for {coin_id}: {e}")
        return ""

def get_coins():
    """
    Decide whether to scrape the Recently Added HTML page or fetch from the API,
    based on SCRAPE_RECENTLY_ADDED config.
    """
    if SCRAPE_RECENTLY_ADDED:
        print("[INFO] Scraping CoinGecko 'Recently Added' HTML page...")
        return get_coins_via_recently_added_html()
    else:
        print("[INFO] Fetching coins via CoinGecko API (top market cap)...")
        return get_coins_via_api()

# -------------------------------------------------
# Celebrity Detection (two-step approach)
# -------------------------------------------------

def debug_partial_celeb_check(name, symbol):
    """
    Quick partial check on just 'name' and 'symbol'
    to see if it might reference a celebrity.
    If true, we consider it "suspect" (to fetch description).
    Also prints which celebrity triggered the partial match for debugging.
    """
    text = f"{name} {symbol}".lower()
    for celeb in CELEBRITY_NAMES:
        clow = celeb.lower()
        if clow in text:
            print(f"[DEBUG] Partial match: coin '{name}' matched '{celeb}' in name/symbol.")
            return True
    return False

def is_celebrity_coin(name, symbol, description):
    """
    Final check (name + symbol + description).
    Shows which celeb triggered the final match for debugging.
    """
    text = f"{name} {symbol} {description}".lower()
    for celeb in CELEBRITY_NAMES:
        clow = celeb.lower()
        if clow in text:
            print(f"[DEBUG] Final match: coin '{name}' matched '{celeb}' in full text.")
            return True
    return False

# -------------------------------------------------
# Alert Methods (Email / Discord)
# -------------------------------------------------

def send_alert_email(coin):
    subject = f"Celebrity Coin Alert: {coin['name']} ({coin['symbol']})"
    body = (
        f"Coin ID: {coin['id']}\n"
        f"Name: {coin['name']}\n"
        f"Symbol: {coin['symbol']}\n"
        f"Price: ${coin.get('current_price', 'N/A')}\n"
        f"More info: https://www.coingecko.com/en/coins/{coin['id']}\n"
    )

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("[INFO] Email alert sent.")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")

def send_alert_discord(coin):
    content_lines = [
        "**Celebrity Coin Alert**",
        f"**Name**: {coin['name']} ({coin['symbol']})",
        f"**Price**: ${coin.get('current_price', 'N/A')}",
        f"**Link**: https://www.coingecko.com/en/coins/{coin['id']}"
    ]
    content = "\n".join(content_lines)

    data = {"content": content}
    if DISCORD_BOT_NAME:
        data["username"] = DISCORD_BOT_NAME
    if DISCORD_BOT_ICON:
        data["avatar_url"] = DISCORD_BOT_ICON

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()
        print("[INFO] Discord alert posted.")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to post to Discord: {e}")

def send_alert(coin):
    if ALERT_METHOD in ["email", "both"]:
        send_alert_email(coin)
    if ALERT_METHOD in ["discord", "both"]:
        send_alert_discord(coin)

# -------------------------------------------------
# Main Script
# -------------------------------------------------

def main():
    print(f"[INFO] {SCRIPT_NAME} v{VERSION} by {AUTHOR_NAME} started.")
    print(f"[INFO] Alert method = {ALERT_METHOD}")
    print(f"[INFO] SCRAPE_RECENTLY_ADDED = {SCRAPE_RECENTLY_ADDED}")
    print(f"[INFO] TIME_BETWEEN_REQUESTS = {TIME_BETWEEN_REQUESTS} seconds")
    print(f"[INFO] USE_CUSTOM_USER_AGENT = {USE_CUSTOM_USER_AGENT}")
    print("[INFO] Loading data...")

    load_celebrity_names()
    load_alerted_coins()

    while True:
        coins = get_coins()
        if not coins:
            print("[WARN] No coins found. Retrying next cycle...")
        else:
            for coin in coins:
                coin_id = coin.get("id", "")
                name = coin.get("name", "")
                symbol = coin.get("symbol", "")

                # Skip if missing ID or already alerted
                if not coin_id or coin_id in ALERTED_COIN_IDS:
                    continue

                # 1) Quick partial check on name/symbol
                if not debug_partial_celeb_check(name, symbol):
                    print(f"[INFO] {name} ({symbol}) not matching partial celeb criteria.")
                    continue

                # 2) If partial check is True, fetch description
                description = get_coin_description(coin_id)
                coin["description"] = description

                # 3) Final check with name + symbol + description
                if is_celebrity_coin(name, symbol, description):
                    print(f"[INFO] Found potential celebrity coin: {name} ({symbol})")
                    send_alert(coin)
                    ALERTED_COIN_IDS.add(coin_id)
                    save_alerted_coins()
                else:
                    print(f"[INFO] {name} ({symbol}) not matching final celeb check.")

        print(f"[INFO] Sleeping {CHECK_INTERVAL} seconds before next check...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
