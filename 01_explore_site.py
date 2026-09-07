import warnings
warnings.filterwarnings("ignore")

import urllib.parse
import urllib3
import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URL = "https://www.kawambwacouncil.gov.zm"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def explore_kawambwa_site():
    print(f"Fetching {TARGET_URL} ...")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, verify=False, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching site: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract page title
    title = soup.title.string.strip() if soup.title and soup.title.string else "No title found"
    print(f"\n==========================================")
    print(f"PAGE TITLE: {title}")
    print(f"STATUS CODE: {response.status_code}")
    print(f"==========================================\n")

    base_netloc = urllib.parse.urlparse(TARGET_URL).netloc.lower()
    # Accept kawambwacouncil.gov.zm and any subdomain (like www.)
    domain_suffix = "kawambwacouncil.gov.zm"

    all_links = set()
    pdf_links = set()
    page_links = set()

    for a_tag in soup.find_all("a", href=True):
        raw_href = a_tag["href"].strip()
        if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Resolve relative URLs against the target URL
        full_url = urllib.parse.urljoin(TARGET_URL, raw_href)
        parsed = urllib.parse.urlparse(full_url)

        # Check if internal (matching netloc)
        netloc = parsed.netloc.lower()
        if netloc == domain_suffix or netloc.endswith("." + domain_suffix):
            # Normalize by stripping fragments
            clean_url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                ""  # drop fragment
            ))

            all_links.add(clean_url)
            if parsed.path.lower().endswith(".pdf"):
                pdf_links.add(clean_url)
            else:
                page_links.add(clean_url)

    print(f"Total internal links discovered: {len(all_links)}")
    print(f"  - Regular pages / resources: {len(page_links)}")
    print(f"  - PDF documents: {len(pdf_links)}")

    print(f"\n--- PDF Documents ({len(pdf_links)}) ---")
    if pdf_links:
        for idx, pdf in enumerate(sorted(pdf_links), start=1):
            print(f"  [{idx:2d}] {pdf}")
    else:
        print("  None found.")

    print(f"\n--- Internal Page Links ({len(page_links)}) ---")
    if page_links:
        for idx, link in enumerate(sorted(page_links), start=1):
            print(f"  [{idx:2d}] {link}")
    else:
        print("  None found.")


if __name__ == "__main__":
    explore_kawambwa_site()
