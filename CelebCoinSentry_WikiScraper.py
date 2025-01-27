import time
import json
import os
import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------
# CelebCoinSentry Wiki Scraper Metadata
# -----------------------------------------------------
SCRIPT_NAME = "CelebCoinSentry_WikiScraper"
AUTHOR_NAME = "rnvntr"
VERSION = "1.0.0"

# -----------------------------------------------------
# Wikipedia Config
# -----------------------------------------------------
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
BASE_WIKIPEDIA_URL = "https://en.wikipedia.org"
MAIN_PAGE_TITLE = "Lists_of_celebrities"

# How often to check for updates (in seconds).
# 24 hours = 86400 seconds
SCRAPE_INTERVAL = 86400

# -----------------------------------------------------
# Local Filenames
# -----------------------------------------------------
LAST_REVISION_FILE = "CelebCoinSentry_last_revision.json"
CELEBRITY_NAMES_FILE = "CelebCoinSentry_celebrity_names.txt"

# -----------------------------------------------------
# Wikipedia Functions
# -----------------------------------------------------

def get_page_last_revision_timestamp(page_title):
    """
    Fetches the last revision timestamp for the given Wikipedia page.
    Returns a string like '2025-01-27T19:03:08Z' or None if not found.
    """
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "timestamp",
        "titles": page_title,
        "format": "json"
    }
    try:
        response = requests.get(WIKIPEDIA_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        # There's typically only one page in the result
        for _, page_data in pages.items():
            revisions = page_data.get("revisions")
            if revisions and len(revisions) > 0:
                return revisions[0].get("timestamp")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to retrieve revision timestamp: {e}")
    return None

def load_last_revision():
    """
    Load the last known revision timestamp from a local JSON file.
    If the file doesn't exist, return None.
    """
    if os.path.exists(LAST_REVISION_FILE):
        with open(LAST_REVISION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("last_timestamp")
    return None

def save_last_revision(timestamp):
    """
    Save the last known revision timestamp to a local JSON file.
    """
    with open(LAST_REVISION_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_timestamp": timestamp}, f)

def get_subpage_links():
    """
    Scrape the main 'Lists_of_celebrities' page to find links to sub-lists.
    Returns a list of relative URLs like '/wiki/List_of_American_film_actresses', etc.
    """
    url = f"{BASE_WIKIPEDIA_URL}/wiki/{MAIN_PAGE_TITLE}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Could not retrieve {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    content_div = soup.find("div", {"class": "mw-parser-output"})
    if not content_div:
        return []
    
    sub_links = []
    for li in content_div.find_all("li"):
        a_tag = li.find("a", href=True)
        if a_tag and a_tag['href'].startswith("/wiki/"):
            sub_links.append(a_tag['href'])
    
    return list(set(sub_links))  # deduplicate

def parse_list_page(path):
    """
    Scrape a sub-list page for potential celebrity names.
    path is something like '/wiki/List_of_American_film_actresses'.
    Returns a list of name strings.
    """
    url = BASE_WIKIPEDIA_URL + path
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Could not retrieve {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    content_div = soup.find("div", {"class": "mw-parser-output"})
    if not content_div:
        return []
    
    names = []
    # Naive approach: collect text from <li> elements with <a> inside
    for li in content_div.find_all("li"):
        a_tag = li.find("a", href=True)
        if a_tag:
            possible_name = a_tag.get_text().strip()
            # Basic filters to avoid nonsense or references
            if len(possible_name.split()) >= 2 and len(possible_name) < 60:
                names.append(possible_name)
    
    return names

def scrape_celebrity_names():
    """
    Scrape the main 'Lists_of_celebrities' page + sub-links to gather celebrity names.
    Returns a cleaned set of potential names.
    """
    sub_links = get_subpage_links()
    all_celeb_names = set()

    for link in sub_links:
        # Optionally, filter out links that aren't "List_of_..." or skip irrelevant pages
        # For example, you could do:
        # if not link.startswith("/wiki/List_of_"):
        #     continue

        extracted = parse_list_page(link)
        all_celeb_names.update(extracted)
    
    # Additional cleaning/deduping
    cleaned_names = set()
    for name in all_celeb_names:
        # E.g., we only keep entries that have at least two words
        # and are not excessively long
        if len(name.split()) >= 2 and len(name) < 60:
            cleaned_names.add(name)
    
    return cleaned_names

def save_celebrity_names_to_file(names):
    """
    Save the final set of celebrity names to 'CelebCoinSentry_celebrity_names.txt', one per line.
    """
    with open(CELEBRITY_NAMES_FILE, "w", encoding="utf-8") as f:
        for name in sorted(names):
            f.write(name + "\n")

# -----------------------------------------------------
# Main Loop
# -----------------------------------------------------

def main():
    print(f"[INFO] {SCRIPT_NAME} v{VERSION} by {AUTHOR_NAME} started.")

    while True:
        print("[INFO] Checking Wikipedia for updates...")

        last_known_timestamp = load_last_revision()
        current_timestamp = get_page_last_revision_timestamp(MAIN_PAGE_TITLE)

        if current_timestamp is None:
            print("[WARN] Could not retrieve current revision timestamp. Retrying later...")
        else:
            if last_known_timestamp is None:
                print("[INFO] No previous timestamp found. Scraping now for the first time...")
                celeb_names = scrape_celebrity_names()
                save_celebrity_names_to_file(celeb_names)
                save_last_revision(current_timestamp)
                print(f"[INFO] Scraped and saved {len(celeb_names)} names.")
            else:
                # Compare current vs. last-known
                if current_timestamp != last_known_timestamp:
                    print("[INFO] Wikipedia page was updated! Scraping new data...")
                    celeb_names = scrape_celebrity_names()
                    save_celebrity_names_to_file(celeb_names)
                    save_last_revision(current_timestamp)
                    print(f"[INFO] Scraped and saved {len(celeb_names)} names.")
                else:
                    print("[INFO] No changes detected. Using existing data.")
        
        print(f"[INFO] Sleeping for {SCRAPE_INTERVAL} seconds (~{SCRAPE_INTERVAL//3600} hours).")
        time.sleep(SCRAPE_INTERVAL)

if __name__ == "__main__":
    main()
