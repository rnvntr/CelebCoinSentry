# CelebCoinSentry

A two-part project for monitoring **newly listed cryptocurrency coins** for references to **celebrities** and alerting via **email** or **Discord**.

## Table of Contents
1. [Overview](#overview)
2. [Scripts](#scripts)
   - [CelebCoinSentry_WikiScraper.py](#celebcoinsentry_wikiscraperpy)
   - [CelebCoinSentry.py](#celebcoinsentrypy)
3. [Setup & Requirements](#setup--requirements)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [How It Works](#how-it-works)
7. [Troubleshooting](#troubleshooting)
8. [License](#license)

---

## Overview

The **CelebCoinSentry** system consists of:

- **`CelebCoinSentry_WikiScraper.py`**:  
  - Scrapes Wikipedia’s “Lists of celebrities” page plus sub-pages to gather a large set of celebrity names.  
  - Only re-scrapes when the page is updated (using Wikipedia’s last revision timestamp).  
  - Outputs a text file `CelebCoinSentry_celebrity_names.txt`.

- **`CelebCoinSentry.py`**:  
  - Loads `CelebCoinSentry_celebrity_names.txt` to detect celebrity references.  
  - Monitors new or top coins from [CoinGecko](https://www.coingecko.com/) (either via the **Recently Added** page HTML or the official **/markets** API).  
  - Substring-matches coin names/symbols/descriptions to see if they reference a celebrity.  
  - Sends alerts via **email** or **Discord** when a match is found, storing alerted coins in `CelebCoinSentry_alerted_coins.txt` to avoid duplicates.

---

## Scripts

### CelebCoinSentry_WikiScraper.py

- **Purpose**:  
  Periodically check Wikipedia’s “Lists_of_celebrities” page for changes; if updated, scrape sub-pages to build a comprehensive local list of celebrity names.
  
- **Key Features**:
  - Uses Wikipedia’s MediaWiki API to compare revision timestamps.  
  - When a revision changes, scrapes all sub-links from the “Lists_of_celebrities” page.  
  - Collects potential celebrity names from `<li>` items, saving them to `CelebCoinSentry_celebrity_names.txt`.  
  - Sleeps between checks (24 hours by default), but you can change `SCRAPE_INTERVAL`.

- **Output**:
  - `CelebCoinSentry_celebrity_names.txt`  
    - One name per line (e.g., “Taylor Swift”, “Elon Musk”).  
  - `CelebCoinSentry_last_revision.json`  
    - Stores the last seen timestamp so we only re-scrape if the page changes.

### CelebCoinSentry.py

- **Purpose**:  
  Reads celebrity names from `CelebCoinSentry_celebrity_names.txt` and watches CoinGecko for new or top coins, alerting if they reference any listed celebrity.

- **Key Features**:
  - **Two data fetching modes**:
    1. **Recently Added HTML** (`SCRAPE_RECENTLY_ADDED = True`): scrapes the [CoinGecko “Recently Added” page](https://www.coingecko.com/en/coins/recently_added) for new coins.  
    2. **Official API** (`SCRAPE_RECENTLY_ADDED = False`): queries `/coins/markets` to get top coins by market cap.  
  - **Two-step celebrity detection**:  
    1. Quick partial check on coin name/symbol.  
    2. If suspect, optionally fetch coin’s description from CoinGecko, then final check.  
  - **Alert** via **email**, **Discord**, or both.  
  - Stores coin IDs in `CelebCoinSentry_alerted_coins.txt` to avoid repeat alerts.  
  - Supports a custom **User-Agent** (`USE_CUSTOM_USER_AGENT = True`) to avoid 403 errors when scraping CoinGecko HTML.  
  - Respects a **time between requests** to reduce rate-limits (`TIME_BETWEEN_REQUESTS`).

---

## Setup & Requirements

1. **Python 3.7+** (tested up to Python 3.11).
2. **Install dependencies**:
   ```bash
   pip install requests beautifulsoup4
   ```
   *(If using email alerts, Python’s standard libraries `smtplib` and `ssl` are already included.)*
3. **(Optional)** If you want to **run continuously**, consider:
   - Hosting on a server or cloud instance (e.g., AWS, DigitalOcean).
   - Using a system scheduler (cron, systemd on Linux, or Windows Task Scheduler).

---

## Usage

### Run `CelebCoinSentry_WikiScraper.py`
```bash
python CelebCoinSentry_WikiScraper.py
```
- Checks if **Wikipedia “Lists_of_celebrities”** changed since last run.  
- If changed (or first run), scrapes sub-pages and **updates** `CelebCoinSentry_celebrity_names.txt`.  
- Sleeps (default 24 hours) and **repeats**.

### Run `CelebCoinSentry.py`
```bash
python CelebCoinSentry.py
```
- **Loads** `CelebCoinSentry_celebrity_names.txt`.  
- **Checks** CoinGecko for coins (either via HTML or API).  
- **Alerts** if any coin references a known celebrity.  
- Sleeps (`CHECK_INTERVAL`) and **repeats**.

### Check Logs & Output
- **`CelebCoinSentry_celebrity_names.txt`**: Updated celebrity names from Wikipedia (generated by `WikiScraper`).  
- **`CelebCoinSentry_alerted_coins.txt`**: Coin IDs that were already announced, preventing duplicate alerts.  
- Console output includes `[INFO]`, `[DEBUG]`, and `[ERROR]` messages.

---

## Configuration

Both scripts have configuration variables near the top:

### `CelebCoinSentry_WikiScraper.py`
- **`SCRAPE_INTERVAL`** (seconds): frequency for checking Wikipedia changes (default `86400` = 24h).  
- **`MAIN_PAGE_TITLE`, `LAST_REVISION_FILE`, etc.** – Adjust if you want custom pages or file names.

### `CelebCoinSentry.py`
- **`ALERT_METHOD`**: `"email"`, `"discord"`, or `"both"`.  
- **`CHECK_INTERVAL`**: frequency (in seconds) to re-check CoinGecko.  
- **`SCRAPE_RECENTLY_ADDED`**: `True` to scrape HTML for newly added coins, `False` for the CoinGecko `/markets` API.  
- **`TIME_BETWEEN_REQUESTS`**: a delay (in seconds) after each API/HTML request to reduce rate limits.  
- **`USE_CUSTOM_USER_AGENT`**: set to `True` if you get 403 errors scraping HTML.  
- **`CUSTOM_USER_AGENT`**: the user-agent string if `USE_CUSTOM_USER_AGENT` is true.  
- **`EMAIL_*` or `DISCORD_*`**: variables for your SMTP credentials or Discord webhook.  
- **`CELEBRITY_NAMES_FILE`**: path to the text file generated by the Wiki Scraper.  
- **`ALERTED_COINS_FILE`**: file to store coin IDs already alerted.

> **Important**: Ensure `CELEBRITY_NAMES_FILE` and `ALERTED_COINS_FILE` match the actual filenames you prefer.

---

## How It Works

### Celebrity Gathering
- The **Wiki Scraper** checks Wikipedia’s [“Lists_of_celebrities” page](https://en.wikipedia.org/wiki/Lists_of_celebrities) via the MediaWiki API for a **last revision timestamp**.  
- If there’s a **new revision**, it **scrapes** sub-pages (e.g., “List_of_American_film_actresses”) to extract potential celebrity names.  
- Writes them into **`CelebCoinSentry_celebrity_names.txt`** for the main coin script.

### Coin Monitoring
- The **coin script** can **scrape** [CoinGecko’s “Recently Added” page](https://www.coingecko.com/en/coins/recently_added) **or** use the **CoinGecko /markets API**.  
- Each coin’s **name** and **symbol** are initially checked for partial matches against the celebrity list.  
- If found “suspect,” it **fetches** a coin description from CoinGecko, then does a **final** substring check.  
- If a match is confirmed, it **sends alerts** and records the coin ID in `CelebCoinSentry_alerted_coins.txt`.

### Alerting
- On a celebrity match, the script calls `send_alert(...)`, which can go to **email** or **Discord**, depending on `ALERT_METHOD`.

---

## Troubleshooting

1. **Empty Celebrity List**  
   - If `CelebCoinSentry_celebrity_names.txt` is missing or empty, the coin script can’t detect anything. Make sure the Wiki Scraper ran successfully.

2. **403 Errors on Recently Added**  
   - Set `USE_CUSTOM_USER_AGENT = True` to send a browser-like header.  
   - Increase `TIME_BETWEEN_REQUESTS` or `CHECK_INTERVAL` if you’re scraping too frequently.

3. **429 Rate Limits**  
   - **Slow down** requests by raising `TIME_BETWEEN_REQUESTS`.  
   - The script uses a **two-step** approach (partial check → final check) to limit calls.

4. **False Positives**  
   - If “Tether” matches “Heather,” check `[DEBUG]` logs to see which celeb substring caused it. **Remove** or refine that entry in `CelebCoinSentry_celebrity_names.txt`.

5. **Discord 400 Errors**  
   - Verify your **Discord Webhook URL** is correct and active.

6. **Email Issues**  
   - Check SMTP credentials.  
   - For Gmail, consider using an **App Password** if two-factor is on.

---

## License

This project is released under the **MIT License**. Feel free to modify, distribute, or contribute back. Please note that **scraping** or using these APIs continuously may be subject to each site’s Terms of Service.

**Happy Monitoring!** The combination of `CelebCoinSentry_WikiScraper.py` and `CelebCoinSentry.py` lets you automatically keep a **celebrity list** updated from Wikipedia and **track new crypto coins** via CoinGecko—alerting you to any that reference known celebrities!
