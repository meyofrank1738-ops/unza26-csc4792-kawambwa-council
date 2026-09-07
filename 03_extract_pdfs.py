import os
import re
import urllib.parse
import warnings

warnings.filterwarnings("ignore")

import urllib3
import requests
import pdfplumber

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PDF_LINKS_FILE = "pdf_links.txt"
DOWNLOADS_DIR = "pdf_downloads"
OUTPUT_DIR = "pdf_text"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
}


def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)


def format_table(table) -> str:
    """Formats a 2D list into a clean plain text table."""
    if not table:
        return ""
    
    # Clean cells
    cleaned_rows = []
    for row in table:
        cleaned_row = [
            re.sub(r'\s+', ' ', str(cell or '')).strip()
            for cell in row
        ]
        cleaned_rows.append(cleaned_row)
    
    # Calculate column widths
    col_widths = {}
    for row in cleaned_rows:
        for col_idx, cell in enumerate(row):
            col_widths[col_idx] = max(col_widths.get(col_idx, 0), len(cell))
    
    lines = []
    for row_idx, row in enumerate(cleaned_rows):
        row_str = " | ".join(cell.ljust(col_widths[col_idx]) for col_idx, cell in enumerate(row))
        lines.append(f"| {row_str} |")
        if row_idx == 0:
            separator = "-+-".join("-" * col_widths[col_idx] for col_idx in range(len(row)))
            lines.append(f"+-{separator}-+")
    
    return "\n".join(lines)


def process_pdfs():
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(PDF_LINKS_FILE):
        print(f"Error: {PDF_LINKS_FILE} not found!")
        return

    with open(PDF_LINKS_FILE, "r", encoding="utf-8") as f:
        pdf_urls = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(pdf_urls)} PDF links from {PDF_LINKS_FILE}.\n")

    session = requests.Session()
    session.headers.update(HEADERS)
    session.verify = False

    stats = {
        "with_tables": 0,
        "text_only": 0,
        "nothing": 0,
        "download_failed": 0
    }

    seen_basenames = set()

    for idx, url in enumerate(pdf_urls, start=1):
        parsed = urllib.parse.urlparse(url)
        raw_basename = os.path.basename(parsed.path) or f"document_{idx}.pdf"
        base_root, _ = os.path.splitext(raw_basename)
        clean_name = sanitize_filename(base_root)
        
        # Avoid collisions
        unique_name = clean_name
        counter = 1
        while unique_name in seen_basenames:
            unique_name = f"{clean_name}_{counter}"
            counter += 1
        seen_basenames.add(unique_name)

        pdf_path = os.path.join(DOWNLOADS_DIR, f"{unique_name}.pdf")
        txt_path = os.path.join(OUTPUT_DIR, f"{unique_name}.txt")

        print(f"[{idx}/{len(pdf_urls)}] {unique_name}")

        # Download if not already downloaded
        if not os.path.exists(pdf_path):
            try:
                resp = session.get(url, timeout=45)
                if resp.status_code == 200:
                    with open(pdf_path, "wb") as f:
                        f.write(resp.content)
                else:
                    print(f"    Download failed with status {resp.status_code}")
                    stats["download_failed"] += 1
                    continue
            except Exception as e:
                print(f"    Download error: {e}")
                stats["download_failed"] += 1
                continue

        # Extract text and tables using pdfplumber
        total_extracted_text = []
        total_tables = 0
        has_any_text = False

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for p_num, page in enumerate(pdf.pages, start=1):
                    page_header = f"\n--- PAGE {p_num} ---\n"
                    page_content = []

                    # Extract raw text
                    raw_text = page.extract_text()
                    if raw_text and raw_text.strip():
                        has_any_text = True
                        page_content.append(raw_text.strip())

                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for t_idx, tbl in enumerate(tables, start=1):
                            # Filter empty table
                            if any(any(cell and str(cell).strip() for cell in row) for row in tbl if row):
                                total_tables += 1
                                formatted = format_table(tbl)
                                page_content.append(f"\n[Table {t_idx} on Page {p_num}]:\n{formatted}")

                    if page_content:
                        total_extracted_text.append(page_header + "\n\n".join(page_content))

            full_text_str = "\n".join(total_extracted_text).strip()

            # Categorize
            if total_tables > 0:
                stats["with_tables"] += 1
                cat = f"HAS TABLES ({total_tables} tables)"
            elif has_any_text:
                stats["text_only"] += 1
                cat = "TEXT-ONLY"
            else:
                stats["nothing"] += 1
                cat = "NOTHING (Scanned/Image)"

            print(f"    Result: {cat}")

            # Save to output file
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"Source URL: {url}\n")
                f.write(f"Filename: {unique_name}.pdf\n")
                f.write(f"Category: {cat}\n")
                f.write("=" * 60 + "\n\n")
                if full_text_str:
                    f.write(full_text_str)
                else:
                    f.write("[NO EXTRACTABLE TEXT OR TABLES - LIKELY SCANNED IMAGE]")

        except Exception as e:
            print(f"    Extraction error: {e}")
            stats["nothing"] += 1

    print("\n==========================================")
    print("EXTRACTION SUMMARY")
    print("==========================================")
    print(f"Total PDFs targeted:        {len(pdf_urls)}")
    print(f"PDFs with extractable tables: {stats['with_tables']}")
    print(f"Text-only PDFs:             {stats['text_only']}")
    print(f"Nothing (scanned images):   {stats['nothing']}")
    if stats["download_failed"] > 0:
        print(f"Download failures:          {stats['download_failed']}")
    print(f"Extracted text saved to:    {OUTPUT_DIR}/")
    print("==========================================")


if __name__ == "__main__":
    process_pdfs()
