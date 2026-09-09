# UNZA CSC4792 — Kawambwa Town Council Data Pipeline & Datasets

**Team #35 — Kawambwa Town Council Local Government Data Collection & Structuring**  
Course: UNZA CSC4792 (Data Engineering / Data Systems)  
Target Institution: [Kawambwa Town Council](https://www.kawambwacouncil.gov.zm) (Luapula Province, Zambia)

---

## Overview

This repository contains the end-to-end data acquisition, extraction, optical character recognition (OCR), cleaning, and structuring pipeline for public local government records from Kawambwa Town Council.

The pipeline ingests raw HTML pages and 73 PDF documents across financial, planning, developmental, and administrative domains to build machine-readable, pipe-separated (`|`) relational datasets matching the course database specification (`db-unza26-csc4792-[DESCRIPTION].csv`).

---

## Repository Structure & Pipeline Scripts

| Script | Purpose | Key Output Datasets / Manifests |
| :--- | :--- | :--- |
| **`01_explore_site.py`** | Site discovery, SSL-bypass configuration, link collection | Initial link inventory |
| **`02_crawl_site.py`** | Recursive crawl of council portal, discovery of 26 web pages & 73 PDFs | `crawled_pages.txt`, `pdf_links.txt` |
| **`03_extract_pdfs.py`** | Batch PDF downloader and text/table extraction with `pdfplumber` | `pdf_downloads/`, `pdf_text/` |
| **`04_categorize_and_extract.py`** | Domain classification into 5 distinct statutory governance categories | `categorized_text/`, `category_index.json` |
| **`05_structure_cdf_projects.py`** | Constituency Development Fund (CDF) extraction (2022–2025), cross-file conflict resolution, ward canonical mapping, and intra-file deduplication | `db-unza26-csc4792-kawambwa_cdf_projects.csv` (442 rows) |
| **`06_structure_budget_financials.py`** | Output-Based Budget (OBB) and Audited Financial Statements extraction | `db-unza26-csc4792-kawambwa_budget_obb.csv` (105 rows), `db-unza26-csc4792-kawambwa_financials_2022.csv` (42 rows), `financial_documents_manifest.json/.md` |
| **`07_structure_idp_docs.py`** | Integrated Development Plan (CIP) and Bus Station ESMP mitigation matrix | `db-unza26-csc4792-kawambwa_idp_projects.csv` (43 rows), `db-unza26-csc4792-kawambwa_esmp_bus_station.csv` (14 rows), `idp_documents_manifest.json/.md` |
| **`08_structure_admin_minutes.py`** | Council meeting resolutions & OCR-extracted stakeholder consultations | `db-unza26-csc4792-kawambwa_council_resolutions.csv` (44 rows), `admin_minutes_manifest.json/.md` |
| **`ocr_property_rates.py`** | Apple Vision framework OCR script for scanned ratepayer consultation minutes | `property_rates_ocr.txt` |
| **`kawambwa_council_pipeline.ipynb`** | End-to-end reproducible Jupyter Notebook unifying all pipelines, methodology notes, and audit checks | Full workflow with data previews and audits |

---

## Structured Datasets Summary

All datasets are pipe-delimited (`|`) with UTF-8 encoding:

1. **`db-unza26-csc4792-kawambwa_cdf_projects.csv` (442 rows)**
   - *Columns:* `ward|project_name|year|status|amount|category|project_type|constituency|source_file|data_conflict`
   - *Coverage:* Approved and deferred projects across Kawambwa and Pambashe constituencies (2022–2025).
2. **`db-unza26-csc4792-kawambwa_budget_obb.csv` (105 rows)**
   - *Columns:* `budget_section|classification_level|code|description|amount_2024|amount_2025|amount_2026|amount_2027|amount_2028|source_file|page`
   - *Coverage:* MTEF Output-Based Budget estimates and expenditure by economic classification (2024–2028).
3. **`db-unza26-csc4792-kawambwa_financials_2022.csv` (42 rows)**
   - *Columns:* `statement_name|section|item_name|original_budget|adjustments|final_budget|actual_amount|pct_performance|variance|pct_variance|year|source_file|page`
   - *Coverage:* Audited financial statements under Cash Basis IPSAS (comparison of budget vs. actual).
4. **`db-unza26-csc4792-kawambwa_idp_projects.csv` (43 rows)**
   - *Columns:* `programme|project_name|location_priority|cost_2024|cost_2025|cost_2026|cost_2027|cost_2028|responsible_agency|source_file|page`
   - *Coverage:* 10-year IDP Capital Investment Programme multi-year development allocations.
5. **`db-unza26-csc4792-kawambwa_esmp_bus_station.csv` (14 rows)**
   - *Columns:* `impact_no|impact_category|potential_impact|mitigation_measure|responsibility|timeline|source_file|page`
   - *Coverage:* Environmental & Social Management Plan mitigation matrix for modern bus station capital project.
6. **`db-unza26-csc4792-kawambwa_council_resolutions.csv` (44 rows)**
   - *Columns:* `meeting_sequence|meeting_date|minute_no|subject|decision_type|resolution_text|proposer_seconder|source_file`
   - *Coverage:* Statutory resolutions from 2024–2025 Ordinary Council meetings and stakeholder consultative assemblies.

---

## Setup & Execution

```bash
# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # requests, beautifulsoup4, pdfplumber, pypdfium2, pillow

# Run data structuring pipelines
python3 05_structure_cdf_projects.py
python3 06_structure_budget_financials.py
python3 07_structure_idp_docs.py
python3 08_structure_admin_minutes.py
```
