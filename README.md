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
2. Install dependencies:
   ```bash
   pip install requests beautifulsoup4
If using email alerts, standard libraries (smtplib, ssl) are already included in Python. 3. (Optional) If you want to schedule these scripts to run continuously, consider running on a server or a cloud instance, or using a system scheduler (cron, systemd, Windows Task Scheduler).

Usage
Run CelebCoinSentry_WikiScraper.py:

bash
Copy
Edit
python CelebCoinSentry_WikiScraper.py
Checks if Wikipedia “Lists_of_celebrities” changed since last run.
If changed or first run, scrapes sub-pages and updates CelebCoinSentry_celebrity_names.txt.
Sleeps (default 24 hours) and repeats.
Run CelebCoinSentry.py:

bash
Copy
Edit
python CelebCoinSentry.py
Loads CelebCoinSentry_celebrity_names.txt.
Checks CoinGecko for coins (HTML or API).
Alerts if any coin references a known celebrity.
Sleeps (CHECK_INTERVAL) and repeats.
Check logs and output:

CelebCoinSentry_celebrity_names.txt: updated celebrity names from Wikipedia.
CelebCoinSentry_alerted_coins.txt: coin IDs that were already announced, preventing duplicates.
Console output includes [INFO], [DEBUG], [ERROR] messages.
Configuration
Both scripts have config variables near the top:

CelebCoinSentry_WikiScraper.py:

SCRAPE_INTERVAL: frequency (in seconds) for checking Wikipedia changes. Default is 86400 (24h).
MAIN_PAGE_TITLE, LAST_REVISION_FILE, etc. — adjust if you want custom page or filenames.
CelebCoinSentry.py:

ALERT_METHOD: "email", "discord", or "both".
CHECK_INTERVAL: frequency (in seconds) to re-check CoinGecko.
SCRAPE_RECENTLY_ADDED: True to scrape HTML for newly added coins, False for the CoinGecko /markets API.
TIME_BETWEEN_REQUESTS: a delay (seconds) after each API/HTML request to avoid rate limits.
USE_CUSTOM_USER_AGENT: set True if you get 403 errors scraping HTML.
CUSTOM_USER_AGENT: the user-agent string if USE_CUSTOM_USER_AGENT is true.
EMAIL_* or DISCORD_* variables for your credentials/webhook.
CELEBRITY_NAMES_FILE: points to the text file generated by CelebCoinSentry_WikiScraper.py.
Important: Make sure CELEBRITY_NAMES_FILE and ALERTED_COINS_FILE match the filenames you use or prefer.

How It Works
Celebrity Gathering:

The Wiki Scraper uses Wikipedia’s MediaWiki API to check the last revision timestamp of [Lists_of_celebrities](https://en.wikipedia.org/wiki/Lists_of_celebrities).
If updated, it scrapes sub-pages, grabbing potential celebrity names from HTML lists.
Saves them in a text file for the coin script.
Coin Monitoring:

The coin script either scrapes [CoinGecko’s Recently Added page](https://www.coingecko.com/en/coins/recently_added)** or uses the CoinGecko /markets API**.
Each coin’s name/symbol is partially checked against the celebrity list.
If suspicious, it fetches a description from the CoinGecko coin detail endpoint, then does a final substring check.
If matched, sends an alert and logs the coin ID in CelebCoinSentry_alerted_coins.txt.
Alerting:

If a coin references a known celebrity name, we do a send_alert(...) which can go to email, Discord or both, according to ALERT_METHOD.
Troubleshooting
Empty Celebrity List

If CelebCoinSentry_celebrity_names.txt is missing or empty, the coin script won’t detect anything. Make sure the WikiScraper is running and generating names.
403 Errors on Recently Added

Set USE_CUSTOM_USER_AGENT = True so you have a browser-like header.
Increase TIME_BETWEEN_REQUESTS or CHECK_INTERVAL.
429 Rate Limits

Slow down your requests by increasing TIME_BETWEEN_REQUESTS.
The script includes a “partial check” approach to reduce calls to the coin detail API.
False Positives

“Tether” matching “Heather,” or similar. Check [DEBUG] logs to see which celebrity substring triggered the match. Remove or refine that entry in CelebCoinSentry_celebrity_names.txt.
Discord 400 Errors

Verify your Discord Webhook URL is correct and active.
Email Issues

Make sure you have correct SMTP credentials.
For Gmail, consider using App Passwords if two-factor is on.
License
This project is made available under the MIT License. Feel free to modify, distribute, or contribute back. Use responsibly—note that scraping or constantly hitting APIs may be subject to each site’s Terms of Service.

Happy Monitoring! With these two scripts, you can automatically maintain an up-to-date celebrity list from Wikipedia and track new crypto coins from CoinGecko, alerting you whenever a token name references a known celebrity.
