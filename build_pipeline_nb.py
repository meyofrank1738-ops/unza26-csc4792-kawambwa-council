import json
import os

def make_cell(cell_type, source, outputs=None, execution_count=None):
    if isinstance(source, list):
        src_lines = [s if s.endswith("\n") else s + "\n" for s in source]
    else:
        # Split on line breaks while preserving newlines
        src_lines = source.splitlines(keepends=True)
    if src_lines:
        src_lines[-1] = src_lines[-1].rstrip("\r\n")
            
    cell = {
        "cell_type": cell_type,
        "metadata": {},
        "source": src_lines
    }
    if cell_type == "code":
        cell["execution_count"] = execution_count
        cell["outputs"] = outputs if outputs is not None else []
    return cell

def build_notebook():
    cells = []

    # 1. Header & Intro
    cells.append(make_cell("markdown", r"""# UNZA CSC4792 — Kawambwa Town Council Data Pipeline
### End-to-End Local Government Data Acquisition, Extraction, Deduplication & Structuring

**Course:** UNZA CSC4792 — Data Mining & Warehousing / Data Engineering  
**Group:** Team #35  
**Target Authority:** [Kawambwa Town Council](https://www.kawambwacouncil.gov.zm) (Luapula Province, Zambia)  
**Constituencies:** Kawambwa & Pambashe (22 Administrative Wards)  
**Output Specification:** Pipe-delimited (`|`) UTF-8 relational datasets (`db-unza26-csc4792-[DESCRIPTION].csv`)

---

## 1. Project Background & Executive Overview

Kawambwa Town Council is a statutory local government authority in Luapula Province, Zambia, responsible for municipal service delivery, local infrastructure, land administration, and fiscal management across two parliamentary constituencies: **Kawambwa** and **Pambashe**. 

A core objective of this project is transforming unstructured and semi-structured public records—including HTML web portal pages, native PDF tables, multi-year developmental budgets, and scanned public consultation minutes—into standardized, machine-readable datasets for data mining, expenditure tracking, and civic accountability.

### 5 Statutory Governance Domains Covered:
1. **Constituency Development Fund (CDF) Projects (2022–2025):** Complete project tracking across approved, deferred, and updated records with canonical ward normalization and conflict tracking.
2. **Output-Based Budget (OBB) & Financial Statements (2022–2028):** Multi-year expenditure ceilings by economic classification and audited budget vs. actuals under Cash Basis IPSAS.
3. **Integrated Development Plan (IDP 2024–2028):** 10-year Capital Investment Programme (CIP) infrastructure commitments.
4. **Environmental & Social Management Plan (ESMP):** Statutory mitigation matrix for the modern bus station capital project.
5. **Council Resolutions & Consultations (2024–2025):** Ordinary Council meeting decisions and ratepayer public consultation assemblies."""))

    # 2. Setup & Environment
    cells.append(make_cell("markdown", r"""## 2. Environment Setup & Core Dependencies

The pipeline relies on:
- `requests` & `urllib3` for SSL-bypassing web scraping and PDF acquisition.
- `beautifulsoup4` for HTML portal traversal.
- `pdfplumber` for geometric table and cell boundary extraction.
- `pypdfium2` & Apple Vision framework for optical character recognition (OCR) of scanned minutes.
- `pandas` for dataframe representation, type casting, and validation."""))

    cells.append(make_cell("code", r"""import os
import re
import csv
import json
import warnings
import urllib3
import requests
import pandas as pd
import pdfplumber
from collections import defaultdict
from difflib import SequenceMatcher

# Suppress SSL and parser warnings
warnings.filterwarnings('ignore')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Pandas display settings
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 20)
pd.set_option('display.width', 1000)

print("Environment configured successfully. Pandas version:", pd.__version__)"""))

    # 3. Web Crawling & Document Discovery
    cells.append(make_cell("markdown", r"""## 3. Web Crawling, PDF Discovery & SSL Workaround

### ⚠️ Methodology Note: The SSL / `verify=False` Workaround
The official Kawambwa Town Council web portal (`kawambwacouncil.gov.zm`) operates with a self-signed or misconfigured SSL/TLS certificate chain. Standard HTTPS requests in Python fail immediately with `SSLCertVerificationError`. 

To ensure continuous data acquisition without manual browser intervention:
1. All HTTP request sessions configure `verify=False`.
2. `urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)` suppresses stdout flood.
3. A polite crawl rate (0.5s delay) was maintained to prevent overloading local municipal servers.

The crawl identified **26 HTML pages** and cataloged **73 statutory PDF publications**."""))

    cells.append(make_cell("code", r"""def summarize_discovered_documents():
    pdf_dir = "pdf_downloads"
    if os.path.exists(pdf_dir):
        files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
        print(f"Total statutory PDFs downloaded and stored in '{pdf_dir}': {len(files)}")
        print("Sample PDF filenames:")
        for f in sorted(files)[:8]:
            print(f"  - {f}")
    else:
        print(f"Directory {pdf_dir} not found. Ensure scraping phase is complete.")

summarize_discovered_documents()"""))

    # 4. Domain Classification
    cells.append(make_cell("markdown", r"""## 4. Statutory Document Categorization

Using regex heuristics on document nomenclature and metadata in `04_categorize_and_extract.py`, all 73 publications were mapped into distinct statutory domains to establish extraction pipelines."""))

    cells.append(make_cell("code", r"""CATEGORIES = {
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

# Display category distribution for downloaded files
if os.path.exists("pdf_downloads"):
    files = [f for f in os.listdir("pdf_downloads") if f.lower().endswith(".pdf")]
    cat_counts = defaultdict(int)
    for f in files:
        cat_counts[categorize_filename(f)] += 1
    
    df_cats = pd.DataFrame(list(cat_counts.items()), columns=["Category", "PDF Count"]).sort_values("PDF Count", ascending=False)
    display(df_cats)"""))

    # 5. CDF Projects Pipeline
    cells.append(make_cell("markdown", r"""## 5. Dataset 1: Constituency Development Fund (CDF) Projects (2022–2025)

The Constituency Development Fund is Zambia's flagship decentralized financing mechanism. In Kawambwa, CDF records are published as annual PDF tables across Kawambwa and Pambashe constituencies.

### ⚠️ Methodology Decisions & Data Engineering Insights:

1. **The `[:40]` Truncation Bug:**  
   Early deduplication prototypes truncated project titles to 40 characters for fast fuzzy hashing (`title[:40]`). This introduced severe false collisions: distinct projects like `"Construction of 1x3 Classroom Block at Mweo Primary"` and `"Construction of 1x3 Classroom Block at Chibote Secondary"` collapsed together. We eliminated slicing, implemented complete canonical normalization (`norm_for_match`), and applied `SequenceMatcher` with a strict similarity threshold ($\ge 0.90$).

2. **Exact-Duplicate vs. Amount-Aware Matching:**  
   Naive deduplication matching on `(ward, project_name, year, source_file)` collapsed legitimately distinct budget entries. For example, in 2023, four separate desk procurement entries with different amounts (`K532,000`, `K632,000`, `K632,000`, and `K3,074,000`) collapsed into one row, discarding ~K4M in distinct public allocations. Adding `amount` to the matching key ensured distinct budget lines remained intact, while collapsing genuine blank-amount extraction duplicates (e.g. Mweo CRB and Ilombe Ablution Block) and keeping the version with the highest completeness score.

3. **2025 Cross-File Conflict Resolution (The Mawaya Case Study):**  
   In 2025, projects were published across multiple overlapping PDF files (`APPROVED`, `UPDATED`, and `DEFERRED`). A direct cross-file status conflict arose with the project **"Construction of Health Facility at Mawaya"** located in **Mulunda Ward** (Mawaya is a locality within Mulunda, not a standalone ward). This single project appeared with `status = Approved` in `APPROVED-PAMBASHE-COMMUNITY-PROJECTS-2025.pdf`, but was simultaneously listed with `status = Deferred` in `DEFERRED-2025-Pambashe-CommProjects-updated.pdf`. We resolved this contradiction by implementing an **Authority Hierarchy** (`APPROVED` [Rank 3] > `UPDATED` [Rank 2] > `DEFERRED` [Rank 1]), which retained the authoritative ministerial approval status while explicitly setting `data_conflict = True` to preserve full auditability for downstream researchers.

4. **Ward Canonical Normalization:**  
   Source PDFs had typos and spelling variants across 22 wards (e.g., `Chipili` $\rightarrow$ `Chimpili`, `Pampashe` $\rightarrow$ `Pambashe`, `Ntumacushi` $\rightarrow$ `Ntumbachushi`). All wards were mapped to their canonical Gazette spellings."""))

    cells.append(make_cell("code", r"""# Execute CDF structuring pipeline
import subprocess

cdf_csv = "db-unza26-csc4792-kawambwa_cdf_projects.csv"
if not os.path.exists(cdf_csv):
    subprocess.run(["python3", "05_structure_cdf_projects.py"], check=True)

df_cdf = pd.read_csv(cdf_csv, sep="|")
print(f"Loaded CDF Projects Dataset: {len(df_cdf)} rows, {df_cdf.shape[1]} columns")
conflicts = (df_cdf['data_conflict'].astype(str).str.lower() == 'true').sum()
print(f"Conflicts Flagged: {conflicts} rows")
display(df_cdf.head(10))"""))

    cells.append(make_cell("code", r"""# Summary statistics on CDF projects by year and approval status
cdf_summary = df_cdf.groupby(['year', 'status']).size().unstack(fill_value=0)
print("CDF Project Counts by Year & Status:")
display(cdf_summary)

print("Top 5 Wards by Number of CDF Projects:")
display(df_cdf['ward'].value_counts().head(5))"""))

    # 6. Budget & Financial Statements Pipeline
    cells.append(make_cell("markdown", r"""## 6. Dataset 2 & 3: Output-Based Budget (OBB) & Audited Financial Statements

### Dataset 2: `db-unza26-csc4792-kawambwa_budget_obb.csv` (105 rows)
Extracted from `KTC-OBB-BUDGET-2026-to-2027.pdf`, this dataset captures Kawambwa's Medium-Term Expenditure Framework (MTEF). It includes:
- **Revenues (Pages 3–4):** Local taxes/rates, fees & charges, national equalization grants, and capital grants across 2024–2028.
- **Expenditures by Economic Classification (Pages 4–5):** Personnel emoluments, goods & services, capital expenditure, and transfers (2024–2026).

### Dataset 3: `db-unza26-csc4792-kawambwa_financials_2022.csv` (42 rows)
Extracted from `Kawambwa-Town-Council-Audited-Financial-Statements-2022.pdf`, capturing the statutory **Statement of Comparison of Budget and Actual Amounts** prepared under Cash Basis IPSAS. It contains:
- Receipts (Local taxes, fees, licenses, national equalization grants)
- Payments (Compensation of employees, use of goods and services, social benefits)
- Original Budget, Adjustments, Final Budget, Actual Outturn, Variance, and Performance %."""))

    cells.append(make_cell("code", r"""obb_csv = "db-unza26-csc4792-kawambwa_budget_obb.csv"
fin_csv = "db-unza26-csc4792-kawambwa_financials_2022.csv"

if not os.path.exists(obb_csv) or not os.path.exists(fin_csv):
    subprocess.run(["python3", "06_structure_budget_financials.py"], check=True)

df_obb = pd.read_csv(obb_csv, sep="|")
df_fin = pd.read_csv(fin_csv, sep="|")

print(f"OBB Budget Dataset: {len(df_obb)} rows")
display(df_obb.head(6))

print(f"2022 Audited Financial Statements Dataset: {len(df_fin)} rows")
display(df_fin.head(6))"""))

    # 7. IDP & ESMP Pipeline
    cells.append(make_cell("markdown", r"""## 7. Dataset 4 & 5: Integrated Development Plan (IDP) & Bus Station ESMP

### Dataset 4: `db-unza26-csc4792-kawambwa_idp_projects.csv` (43 rows)
Extracted from `Kawambwa-IDP.pdf` (pages 154–157), this captures the 10-year **Capital Investment Programme (CIP)** across agriculture, civic infrastructure, water/sanitation, and transportation with 2024–2028 multi-year cost allocations.

### Dataset 5: `db-unza26-csc4792-kawambwa_esmp_bus_station.csv` (14 rows)
Extracted from `KTC-ESMP-MODERN-BUS-STATION.pdf`, capturing the Environmental & Social Management Plan mitigation matrix for Kawambwa's modern bus station.

### ⚠️ Methodology Decision: The Continuation Line Wrap-Around Fix
In `KTC-ESMP-MODERN-BUS-STATION.pdf`, table cells describing potential impacts and mitigation measures wrapped across multiple lines in the PDF stream. Naive table extractors created orphan rows before items 5 and 8 with empty `impact_no` and disconnected text fragments. We applied single-non-empty-cell lookback merging to absorb wrapped lines back into parent items 4 and 7 before emitting clean rows."""))

    cells.append(make_cell("code", r"""idp_csv = "db-unza26-csc4792-kawambwa_idp_projects.csv"
esmp_csv = "db-unza26-csc4792-kawambwa_esmp_bus_station.csv"

if not os.path.exists(idp_csv) or not os.path.exists(esmp_csv):
    subprocess.run(["python3", "07_structure_idp_docs.py"], check=True)

df_idp = pd.read_csv(idp_csv, sep="|")
df_esmp = pd.read_csv(esmp_csv, sep="|")

print(f"IDP CIP Projects Dataset: {len(df_idp)} rows")
display(df_idp.head(5))

print(f"Modern Bus Station ESMP Mitigation Dataset: {len(df_esmp)} rows")
display(df_esmp.head(5))"""))

    # 8. Council Resolutions Pipeline
    cells.append(make_cell("markdown", r"""## 8. Dataset 6: Council Resolutions & Administrative Records (2024–2025)

### Dataset 6: `db-unza26-csc4792-kawambwa_council_resolutions.csv` (44 rows)
Stitching together statutory resolutions from:
1. **Ordinary Council Minutes (2024–2025):** 1st Ordinary 2024, 2nd Ordinary 2024, 1st Ordinary 2025, and 2nd Ordinary 2025.
2. **Consultative Minutes:** Ratepayer property rates review assembly (via Apple Vision OCR) and modern bus station trader engagements.

### ⚠️ Methodology Decision: Meeting Sequence Tracking
Both `MINUTES-OF-FIRST-ORDINARY-COUNCIL-2025.pdf` (held 5 June 2025) and `MINUTES-OF-SECOND-ORDINARY-COUNCIL-2025.pdf` (held 5 August 2025) reuse the minute numbering template `KTC/01/06/2025` through `KTC/09/06/2025`. To prevent primary key collisions, the pipeline introduces a `meeting_sequence` attribute (e.g. `1st Ordinary 2025`, `2nd Ordinary 2025`) ensuring every statutory resolution is uniquely addressable."""))

    cells.append(make_cell("code", r"""res_csv = "db-unza26-csc4792-kawambwa_council_resolutions.csv"

if not os.path.exists(res_csv):
    subprocess.run(["python3", "08_structure_admin_minutes.py"], check=True)

df_res = pd.read_csv(res_csv, sep="|")
print(f"Council Resolutions Dataset: {len(df_res)} rows")
display(df_res.head(8))

print("Resolutions Count by Meeting Sequence:")
display(df_res['meeting_sequence'].value_counts())"""))

    # 9. Final Sanity-Check Summary
    cells.append(make_cell("markdown", r"""## 9. Final Data Integrity & Richness Sanity-Check Summary

Here we verify all 6 structured CSVs, checking file size, line counts, non-empty attributes, and coverage against the UNZA CSC4792 specification."""))

    cells.append(make_cell("code", r"""datasets = [
    ("CDF Community Projects (2022-2025)", "db-unza26-csc4792-kawambwa_cdf_projects.csv"),
    ("Output-Based Budget MTEF (2024-2028)", "db-unza26-csc4792-kawambwa_budget_obb.csv"),
    ("Audited Financial Statements (2022)", "db-unza26-csc4792-kawambwa_financials_2022.csv"),
    ("IDP Capital Investment Programme", "db-unza26-csc4792-kawambwa_idp_projects.csv"),
    ("Bus Station ESMP Mitigation Matrix", "db-unza26-csc4792-kawambwa_esmp_bus_station.csv"),
    ("Council Resolutions & Consultations", "db-unza26-csc4792-kawambwa_council_resolutions.csv"),
]

summary_rows = []
for desc, fname in datasets:
    if os.path.exists(fname):
        df = pd.read_csv(fname, sep="|")
        size_kb = os.path.getsize(fname) / 1024
        summary_rows.append({
            "Description": desc,
            "File Name": fname,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Size (KB)": round(size_kb, 1),
            "Column List": ", ".join(df.columns[:4]) + ("..." if len(df.columns) > 4 else "")
        })
    else:
        summary_rows.append({
            "Description": desc,
            "File Name": fname,
            "Rows": 0,
            "Columns": 0,
            "Size (KB)": 0,
            "Column List": "MISSING"
        })

df_summary = pd.DataFrame(summary_rows)
print("=" * 80)
print("UNZA CSC4792 - KAWAMBWA TOWN COUNCIL STRUCTURED DATASETS AUDIT")
print("=" * 80)
display(df_summary)
print(f"\nTotal Structured Records Across All Domains: {df_summary['Rows'].sum()} rows")"""))

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbformat": "1.0",
                "version": "3.9.6"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    output_nb = "kawambwa_council_pipeline.ipynb"
    with open(output_nb, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=2)
    print(f"Successfully generated {output_nb} with {len(cells)} cells!")

if __name__ == "__main__":
    build_notebook()
