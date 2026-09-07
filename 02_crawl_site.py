import time
import warnings
import urllib.parse
from collections import deque

warnings.filterwarnings("ignore")

import urllib3
import requests
from bs4 import BeautifulSoup

# Suppress SSL certificate verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

START_URL = "https://www.kawambwacouncil.gov.zm/"
DOMAIN_SUFFIX = "kawambwacouncil.gov.zm"
MAX_PAGES = 60
REQUEST_DELAY = 0.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_url(url: str, base_url: str) -> str:
    full_url = urllib.parse.urljoin(base_url, url.strip())
    parsed = urllib.parse.urlparse(full_url)
    # Strip URL fragments (#section) and normalize scheme to https if same domain
    clean = urllib.parse.urlunparse((
        "https" if parsed.scheme in ("http", "https") else parsed.scheme,
        parsed.netloc.lower(),
        parsed.path,
        parsed.params,
        parsed.query,
        ""
    ))
    return clean


def is_same_domain(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    return netloc == DOMAIN_SUFFIX or netloc.endswith("." + DOMAIN_SUFFIX)


def is_pdf(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.path.lower().endswith(".pdf")


def crawl():
    print(f"Starting crawl from: {START_URL}")
    print(f"Cap: {MAX_PAGES} pages | Max depth: 1 level | Delay: {REQUEST_DELAY}s\n")

    # Queue contains tuples of (url, depth)
    queue = deque([(normalize_url(START_URL, START_URL), 0)])
    enqueued = {normalize_url(START_URL, START_URL)}
    
    # Store visited pages: {url: title}
    crawled_pages = {}
    pdf_links = set()

    session = requests.Session()
    session.headers.update(HEADERS)
    session.verify = False

    while queue and len(crawled_pages) < MAX_PAGES:
        current_url, depth = queue.popleft()

        print(f"[{len(crawled_pages) + 1}/{MAX_PAGES}] (depth={depth}) Fetching: {current_url}")
        try:
            resp = session.get(current_url, timeout=25)
            # Check content-type
            content_type = resp.headers.get("Content-Type", "").lower()
            if "application/pdf" in content_type or is_pdf(current_url):
                pdf_links.add(current_url)
                time.sleep(REQUEST_DELAY)
                continue

            if resp.status_code != 200:
                print(f"    Status {resp.status_code}, skipping.")
                time.sleep(REQUEST_DELAY)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
            # Normalize whitespace in title
            title = " ".join(title.split())
            crawled_pages[current_url] = title
            print(f"    Title: {title}")

            # Extract links on this page
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue

                full_url = normalize_url(href, current_url)
                if not is_same_domain(full_url):
                    continue

                if is_pdf(full_url):
                    pdf_links.add(full_url)
                else:
                    # If we crawled the homepage (depth 0), queue level-1 links
                    if depth == 0 and full_url not in enqueued:
                        enqueued.add(full_url)
                        queue.append((full_url, 1))

        except requests.exceptions.RequestException as e:
            print(f"    Request failed: {e}")

        time.sleep(REQUEST_DELAY)

    print(f"\nCrawl complete!")
    print(f"Total HTML pages crawled: {len(crawled_pages)}")
    print(f"Total unique PDF links discovered: {len(pdf_links)}")

    # Save to crawled_pages.txt
    with open("crawled_pages.txt", "w", encoding="utf-8") as f:
        for url, title in crawled_pages.items():
            f.write(f"{url}\t{title}\n")
    print("Saved crawled pages to crawled_pages.txt")

    # Save to pdf_links.txt
    with open("pdf_links.txt", "w", encoding="utf-8") as f:
        for pdf_url in sorted(pdf_links):
            f.write(f"{pdf_url}\n")
    print("Saved PDF links to pdf_links.txt")


if __name__ == "__main__":
    crawl()
