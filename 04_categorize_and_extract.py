import os
import re
import json
import urllib.parse
import warnings

warnings.filterwarnings("ignore")

import urllib3
import requests
import pdfplumber

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PDF_LINKS_FILE = "pdf_links.txt"
DOWNLOADS_DIR = "pdf_downloads"
CATEGORIZED_DIR = "categorized_text"

CATEGORIES = {
    "cdf_and_community_projects": [
        r"COMMUNITY-PROJECTS", r"CommProjects", r"APPLICATION-FORM-FOR-COMMUNITY",
        r"SECONDARY-BORADING", r"SKILLS-DEVELOPMENT", r"FORM-FOR-YOUTH-WOMEN",
        r"Grant-Application-Form", r"Constituency-Development-Fund"
    ],
    "budgets_and_financial_statements": [
        r"BUDGET", r"Financial-Statements", r"FINANCIAL-STATEMENTS", r"AUDIT",
        r"PROPERTY-RATES", r"LA-Financial-Regulations", r"Public-Finance-Management",
        r"Public-Procurement", r"Perfomance-Report"
    ],
    "idp_and_strategic_plans": [
        r"IDP", r"NATIONAL-DEVELOPMENT-PLAN"
    ],
    "council_meeting_minutes": [
        r"MINUTES", r"STAKEHOLDER", r"tenants-meeting"
    ],
    "loans_and_empowerment": [
        r"LOAN", r"loans"
    ],
    "acts_policies_and_charters": [
        r"Charter", r"Act-No", r"Act-12", r"Act-20", r"Act\b", r"Acts",
        r"Procedures_ZDSP", r"Commitment-Plan", r"ESMP", r"SI-", r"si_"
    ],
    "newsletters_and_press": [
        r"Newsletter", r"Newletter", r"Press-statement", r"Advert"
    ]
}


def categorize_filename(filename: str) -> str:
    for cat_name, patterns in CATEGORIES.items():
        for pat in patterns:
            if re.search(pat, filename, re.IGNORECASE):
                return cat_name
    return "other_documents"


def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)


def format_table(table) -> str:
    if not table:
        return ""
    cleaned_rows = []
    for row in table:
        cleaned_rows.append([re.sub(r'\s+', ' ', str(cell or '')).strip() for cell in row])
    
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


def run_categorization():
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(CATEGORIZED_DIR, exist_ok=True)

    with open(PDF_LINKS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Deduplicate unique URLs
    unique_urls = list(dict.fromkeys(urls))
    print(f"Total unique PDF URLs: {len(unique_urls)}")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    session.verify = False

    cat_counts = {}
    catalog = []

    for idx, url in enumerate(unique_urls, start=1):
        parsed = urllib.parse.urlparse(url)
        raw_basename = os.path.basename(parsed.path)
        base_name, _ = os.path.splitext(raw_basename)
        clean_name = sanitize_filename(base_name)

        category = categorize_filename(raw_basename)
        cat_counts[category] = cat_counts.get(category, 0) + 1

        cat_dir = os.path.join(CATEGORIZED_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)

        pdf_path = os.path.join(DOWNLOADS_DIR, f"{clean_name}.pdf")
        txt_path = os.path.join(cat_dir, f"{clean_name}.txt")

        # Download if needed
        if not os.path.exists(pdf_path):
            try:
                resp = session.get(url, timeout=45)
                if resp.status_code == 200:
                    with open(pdf_path, "wb") as f:
                        f.write(resp.content)
            except Exception as e:
                print(f"Error downloading {url}: {e}")

        # Extract text + tables if not already extracted
        tables_count = 0
        text_length = 0
        if os.path.exists(pdf_path) and not os.path.exists(txt_path):
            try:
                extracted_chunks = []
                with pdfplumber.open(pdf_path) as pdf:
                    for p_idx, page in enumerate(pdf.pages, start=1):
                        p_text = page.extract_text() or ""
                        p_tables = page.extract_tables() or []

                        chunk = [f"--- PAGE {p_idx} ---"]
                        if p_text.strip():
                            chunk.append(p_text.strip())
                            text_length += len(p_text.strip())

                        for t_idx, tbl in enumerate(p_tables, start=1):
                            if any(any(c and str(c).strip() for c in r) for r in tbl if r):
                                tables_count += 1
                                chunk.append(f"\n[Table {t_idx} on Page {p_idx}]:\n{format_table(tbl)}")

                        if len(chunk) > 1:
                            extracted_chunks.append("\n\n".join(chunk))

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"Source URL: {url}\n")
                    f.write(f"Category: {category}\n")
                    f.write(f"Filename: {clean_name}.pdf\n")
                    f.write("=" * 60 + "\n\n")
                    if extracted_chunks:
                        f.write("\n\n".join(extracted_chunks))
                    else:
                        f.write("[NO EXTRACTABLE TEXT OR TABLES - SCANNED DOCUMENT]")
            except Exception as e:
                print(f"Error extracting {pdf_path}: {e}")

        catalog.append({
            "filename": f"{clean_name}.pdf",
            "url": url,
            "category": category,
            "text_file": txt_path,
        })

    # Save catalog
    with open("category_index.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    print("\n==========================================")
    print("CATEGORIZATION & EXTRACTION SUMMARY")
    print("==========================================")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  • {cat:<35}: {count} files")
    print(f"\nSaved metadata index to category_index.json")
    print(f"Categorized texts organized under: {CATEGORIZED_DIR}/")
    print("==========================================")


if __name__ == "__main__":
    run_categorization()
