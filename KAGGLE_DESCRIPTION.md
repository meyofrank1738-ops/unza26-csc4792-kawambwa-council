# Kawambwa Town Council: Multi-Source Local Government Finance, CDF Projects, and Governance Dataset (2022–2028)
### *A standardized, pipe-delimited relational dataset capturing Constituency Development Fund (CDF) allocations, MTEF budgets, audited financial outturns, capital investment programmes, and municipal resolutions across Kawambwa and Pambashe, Zambia.*

---

## 1. Overview & Context

This dataset represents a curated, multi-source collection of local government operational, financial, and developmental records from **Kawambwa Town Council**, a statutory local authority in Luapula Province, Zambia. Kawambwa District administers two parliamentary constituencies—**Kawambwa** and **Pambashe**—encompassing 22 administrative wards.

Under Zambia's decentralization reforms (bolstered by the Local Government Act No. 2 of 2019 and the expanded Constituency Development Fund Act No. 11 of 2021), local councils bear substantial responsibility for municipal infrastructure, public finance allocation, and community-driven development. Despite this statutory importance, local government records in Sub-Saharan Africa frequently remain locked inside scanned, disparate, and inconsistent PDF documents published across municipal web portals.

### Why This Data Matters
- **Civic Accountability & Public Finance Management (PFM):** Enables researchers, civil society organizations, and policy analysts to track public expenditure from initial council-level budget proposals down to ward-level physical projects.
- **Constituency Development Fund (CDF) Transparency:** Provides complete longitudinal project data (2022–2025) comparing proposed, approved, and deferred allocations across both parliamentary constituencies.
- **Multi-Year Capital Planning:** Pairs medium-term fiscal frameworks (Output-Based Budget 2024–2028) with statutory 10-year Capital Investment Programmes (CIP) and audited cash-basis financial statements (IPSAS Cash Basis).
- **Environmental & Social Governance:** Documents concrete environmental mitigation standards and statutory council resolutions governing municipal land and commercial infrastructure.

---

## 2. Dataset Architecture & File Descriptions

The dataset consists of **6 relational, pipe-delimited (`|`) CSV files** (UTF-8 encoded) totaling **690 structured records**, extracted from 18 primary statutory documents (culled from an exhaustive crawl of 73 municipal PDF publications).

| File Name | Records | Columns | Primary Source Document(s) | Focus Area |
| :--- | :---: | :---: | :--- | :--- |
| **`db-unza26-csc4792-kawambwa_cdf_projects.csv`** | 442 | 10 | 12 Annual CDF Project Lists (2022–2025) | Ward-level CDF projects & allocations |
| **`db-unza26-csc4792-kawambwa_budget_obb.csv`** | 105 | 11 | `KTC-OBB-BUDGET-2026-to-2027.pdf` | MTEF revenue & economic expenditures |
| **`db-unza26-csc4792-kawambwa_financials_2022.csv`** | 42 | 13 | `Kawambwa-Town-Council-Audited-Financial-Statements-2022.pdf` | Audited budget vs. actuals (IPSAS) |
| **`db-unza26-csc4792-kawambwa_idp_projects.csv`** | 43 | 11 | `Kawambwa-IDP.pdf` | 10-Year Capital Investment Programme |
| **`db-unza26-csc4792-kawambwa_esmp_bus_station.csv`** | 14 | 8 | `KTC-ESMP-MODERN-BUS-STATION.pdf` | Bus station environmental mitigations |
| **`db-unza26-csc4792-kawambwa_council_resolutions.csv`** | 44 | 8 | 4 Ordinary Council Minutes + 2 Stakeholder Minutes | Statutory resolutions & decisions |

---

### File 1: `db-unza26-csc4792-kawambwa_cdf_projects.csv`
- **Record Count:** 442 rows
- **Source Documents:** 12 statutory CDF PDF schedules covering Kawambwa and Pambashe constituencies (2022–2025), including approved, updated, and deferred schedules.
- **Schema & Field Definitions:**
  - `ward` *(string)*: Canonical administrative ward name (standardized across 22 wards; or "Constituency-wide / Not Specified" / "All Wards").
  - `project_name` *(string)*: Full descriptive title of the community infrastructure, equipment, or service project.
  - `year` *(integer)*: Fiscal budget cycle year (2022, 2023, 2024, or 2025).
  - `status` *(string)*: Statutory administrative status (`Approved`, `Deferred / Not Approved`, or specific council note).
  - `amount` *(string / numeric)*: Approved or estimated project cost in Zambian Kwacha (ZMW).
  - `category` *(string)*: Sector classification (e.g., `Education`, `Health`, `Water & Sanitation`, `Roads`, `Community Infrastructure`).
  - `project_type` *(string)*: Specific classification of asset intervention (e.g., `Infrastructure`, `Goods`, `Disaster Relief`).
  - `constituency` *(string)*: Parliamentary constituency name (`Kawambwa` or `Pambashe`).
  - `source_file` *(string)*: Originating PDF document filename.
  - `data_conflict` *(boolean)*: Audit flag (`True`/`False`) indicating whether overlapping official source documents published contradictory status information for this project.

---

### File 2: `db-unza26-csc4792-kawambwa_budget_obb.csv`
- **Record Count:** 105 rows
- **Source Document:** `KTC-OBB-BUDGET-2026-to-2027.pdf` (Pages 3–5)
- **Schema & Field Definitions:**
  - `budget_section` *(string)*: High-level fiscal classification (`Revenue` or `Expenditure`).
  - `classification_level` *(string)*: Aggregation hierarchy (`Summary Category` or `Detailed Line Item`).
  - `code` *(string)*: Government Financial Statistics (GFS) / Chart of Accounts budget code.
  - `description` *(string)*: Standardized economic line item description (e.g., `Local taxes/rates`, `National Equalization Grants`, `Personnel Emoluments`, `Capital Expenditure`).
  - `amount_2024` *(numeric)*: Baseline outturn/allocation for FY2024 (ZMW).
  - `amount_2025` *(numeric)*: Approved budget estimate for FY2025 (ZMW).
  - `amount_2026` *(numeric)*: MTEF projection for FY2026 (ZMW).
  - `amount_2027` *(numeric)*: MTEF forward projection for FY2027 (ZMW).
  - `amount_2028` *(numeric)*: MTEF forward projection for FY2028 (ZMW).
  - `source_file` *(string)*: PDF source filename.
  - `page` *(integer)*: Document page number.

---

### File 3: `db-unza26-csc4792-kawambwa_financials_2022.csv`
- **Record Count:** 42 rows
- **Source Document:** `Kawambwa-Town-Council-Audited-Financial-Statements-2022.pdf` (Page 12)
- **Schema & Field Definitions:**
  - `statement_name` *(string)*: Accounting schedule title (`Statement of Comparison of Budget and Actual Amounts`).
  - `section` *(string)*: Cash accounting division (`Receipts` or `Payments`).
  - `item_name` *(string)*: Specific economic account item (e.g., `Local taxes`, `Fees and charges`, `Local Government Equalisation Fund`, `Compensation of Employees`).
  - `original_budget` *(numeric)*: Approved initial budget for FY2022 (ZMW).
  - `adjustments` *(numeric)*: Supplementary appropriations or council-approved adjustments (ZMW).
  - `final_budget` *(numeric)*: Net statutory budget ceiling for FY2022 (ZMW).
  - `actual_amount` *(numeric)*: Audited cash receipts or disbursements outturn (ZMW).
  - `pct_performance` *(string)*: Budget execution or revenue realization rate percentage.
  - `variance` *(numeric)*: Nominal variance between final budget and actual outturn (ZMW).
  - `pct_variance` *(string)*: Variance percentage against final budget.
  - `year` *(integer)*: Audited fiscal year (2022).
  - `source_file` *(string)*: Audited financial statements source PDF.
  - `page` *(integer)*: Document page number.

---

### File 4: `db-unza26-csc4792-kawambwa_idp_projects.csv`
- **Record Count:** 43 rows
- **Source Document:** `Kawambwa-IDP.pdf` (Pages 154–157)
- **Schema & Field Definitions:**
  - `programme` *(string)*: Strategic IDP development sector (e.g., `Capital Infrastructure`, `Livestock development`, `Early warning and surveillance systems`).
  - `project_name` *(string)*: Long-term planned capital project title.
  - `location_priority` *(string)*: Targeted geographic or ward locality (`District-wide`, `Pambashe and Kawambwa`, `Ngona`, `Fisaka`, etc.).
  - `cost_2024` through `cost_2028` *(numeric)*: Phased multi-year capital investment allocations across the 2024–2028 medium-term horizon (ZMW).
  - `responsible_agency` *(string)*: Coordinating statutory entities (e.g., `LA` [Local Authority], `MOA` [Ministry of Agriculture], `MOFL` [Ministry of Fisheries & Livestock]).
  - `source_file` *(string)*: IDP source filename.
  - `page` *(integer)*: Document page number.

---

### File 5: `db-unza26-csc4792-kawambwa_esmp_bus_station.csv`
- **Record Count:** 14 rows
- **Source Document:** `KTC-ESMP-MODERN-BUS-STATION.pdf` (Pages 8–9)
- **Schema & Field Definitions:**
  - `impact_no` *(integer)*: Sequential environmental/social risk item (1 through 14).
  - `impact_category` *(string)*: Environmental or social risk domain (e.g., `Loss of flora / fauna`, `Dust pollution`, `Safety and Risk of workers`, `Generation of sewage`).
  - `potential_impact` *(string)*: Anticipated risk narrative across site preparation, construction, or operational phases.
  - `mitigation_measure` *(string)*: Prescribed mitigation, prevention, or engineering measure.
  - `responsibility` *(string)*: Assigned supervisory body (`Contractor/Local Authority`).
  - `timeline` *(string)*: Operational window (`Short Term`, `Long term`, `Throughout the construction period`).
  - `source_file` *(string)*: ESMP source document.
  - `page` *(integer)*: Document page number.

---

### File 6: `db-unza26-csc4792-kawambwa_council_resolutions.csv`
- **Record Count:** 44 rows
- **Source Documents:** Four Ordinary Council Meeting Minutes (1st & 2nd Ordinary 2024, 1st & 2nd Ordinary 2025) and two OCR-extracted stakeholder consultation assemblies (Property Rates Revision 2025 and Modern Bus Station Vendor Engagement).
- **Schema & Field Definitions:**
  - `meeting_sequence` *(string)*: Disambiguating assembly identifier (`1st Ordinary 2024`, `2nd Ordinary 2024`, `1st Ordinary 2025`, `2nd Ordinary 2025`, `Stakeholder Consultation 2025 Budget`, `Stakeholder Engagement Modern Bus Station`).
  - `meeting_date` *(string)*: Formal meeting date formatted as `YYYY-MM-DD`.
  - `minute_no` *(string)*: Official statutory minute code (e.g., `KTC/41/02/2024`, `DCM/39/02/2024`).
  - `subject` *(string)*: Agenda item subject matter.
  - `decision_type` *(string)*: Standardized action category (`Statutory Election`, `Committee Adoption`, `Declaration of Interest`, `Matters Arising / Directives`, `Stakeholder Resolution`).
  - `resolution_text` *(string)*: Full verbatim text of the council's adopted resolution.
  - `proposer_seconder` *(string)*: Recording of proposing and seconding councillors (where recorded in the minutes).
  - `source_file` *(string)*: Source minute publication PDF.

---

## 3. Data Quality & Data Engineering Methodology

Rather than relying on naive automated conversion, the pipeline implemented rigorous data engineering heuristics tailored to municipal PDF idiosyncrasies:

### A. The Truncation Slicing Bug
Early extraction prototypes clipped project titles to 40 characters (`name[:40]`) for fuzzy hashing. In municipal datasets, this created fatal false collisions: distinct capital projects with common administrative prefixes (e.g., *"Construction of 1x3 Classroom Block at Mweo Primary"* and *"Construction of 1x3 Classroom Block at Chibote Secondary"*) erroneously collapsed into single rows. The production pipeline eliminated string truncation entirely, enforcing full-text canonical tokenization combined with `SequenceMatcher` with a strict ($\ge 0.90$) similarity threshold.

### B. Amount-Aware Exact Deduplication
Within individual annual PDF schedules, typists frequently repeated line items with blank or zero values across page breaks. However, naive deduplication matching only on `(ward, project_name, year, source_file)` inadvertently collapsed legitimate, distinct budget allocations. In FY2023, for example, four separate desk procurement entries with different amounts (`K532,000`, `K632,000`, `K632,000`, and `K3,074,000`) were collapsed into one row, erasing ~K4M in approved civic expenditure. Adding `amount` as a strict composite matching dimension safeguarded distinct allocations while collapsing authentic zero-amount typo duplicates.

### C. 2025 Cross-File Conflict Resolution (The Mawaya Case Study)
In FY2025, the local authority released three distinct PDF schedules: `APPROVED`, `UPDATED`, and `DEFERRED`. Several projects appeared in multiple documents with conflicting statuses. A prime example occurred with **"Construction of Health Facility at Mawaya"** in **Mulunda Ward** (Mawaya is a local area within Mulunda Ward). The project appeared with `status = Approved` in `APPROVED-PAMBASHE-COMMUNITY-PROJECTS-2025.pdf`, but simultaneously appeared with `status = Deferred` in `DEFERRED-2025-Pambashe-CommProjects-updated.pdf`. The pipeline established an **Authority Hierarchy** (`APPROVED` [Rank 3] > `UPDATED` [Rank 2] > `DEFERRED` [Rank 1]), retaining the authoritative ministerial approval while systematically setting `data_conflict = True` to preserve provenance for auditability.

### D. Ward Canonicalization
Source documents contained widespread phonological and orthographic variants across the 22 administrative wards (e.g., `Chipili` $\rightarrow$ `Chimpili`, `Pampashe` $\rightarrow$ `Pambashe`, `Ntumacushi` $\rightarrow$ `Ntumbachushi`). A gazetteer mapping dictionary standardized all ward entities against official Ministry of Local Government ward boundaries.

### E. Multiline Cell Wrap-Around Recovery
In multi-page landscape tables (such as the Bus Station ESMP), cell content routinely wrapped across page and row boundaries, producing orphaned rows with blank primary keys and fragmented mitigation text. A lookback merge heuristic detected wrapped single-cell rows and merged them back into their parent records (items 4 and 7), restoring tabular integrity without data loss.

---

## 4. Licensing, Source Attribution & Citation

### License: Creative Commons Public Domain Dedication (CC0 1.0 Universal)
This dataset consists of public records published by a statutory authority of the Republic of Zambia in fulfillment of statutory disclosure obligations under the Local Government Act and the Constituency Development Fund Act. The curated dataset, schemas, and extraction pipelines are dedicated to the public domain under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).

### Attribution
Original records sourced from:  
**Kawambwa Town Council**  
P.O. Box 730013, Kawambwa, Luapula Province, Zambia  
Official Web Portal: [https://www.kawambwacouncil.gov.zm](https://www.kawambwacouncil.gov.zm)

### Recommended Citation (BibTeX)
```bibtex
@dataset{unza_kawambwa_council_2026,
  author       = {Team #35 (UNZA CSC4792)},
  title        = {Kawambwa Town Council: Multi-Source Local Government Finance, CDF Projects, and Governance Dataset (2022–2028)},
  year         = {2026},
  publisher    = {Kaggle},
  howpublished = {\\url{https://www.kaggle.com/datasets/}},
  note         = {Curated dataset extracted from official public records of Kawambwa Town Council, Luapula Province, Zambia}
}
```
