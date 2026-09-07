import csv
import json
import os
import re
import pdfplumber

DOWNLOADS_DIR = "pdf_downloads"
OBB_BUDGET_PDF = os.path.join(DOWNLOADS_DIR, "KTC-OBB-BUDGET-2026-to-2027.pdf")
FINANCIALS_2022_PDF = os.path.join(DOWNLOADS_DIR, "Kawambwa-Town-Council-Audited-Financial-Statements-2022.pdf")

OUTPUT_OBB_CSV = "db-unza26-csc4792-kawambwa_budget_obb.csv"
OUTPUT_FIN_CSV = "db-unza26-csc4792-kawambwa_financials_2022.csv"
OUTPUT_MANIFEST_JSON = "financial_documents_manifest.json"
OUTPUT_MANIFEST_MD = "financial_documents_manifest.md"


def clean_num(val: str) -> str:
    if not val:
        return ""
    v = str(val).replace("\n", " ").replace(",", "").strip()
    v = v.replace("(", "-").replace(")", "")
    m = re.search(r"[-+]?\d*\.?\d+", v)
    if m:
        try:
            num = float(m.group(0))
            return f"{num:,.2f}"
        except ValueError:
            pass
    return ""


def clean_text(val: str) -> str:
    if not val:
        return ""
    t = str(val).replace("\n", " ").replace("\r", " ").replace("|", "/")
    return re.sub(r"\s+", " ", t).strip()


# ==============================================================================
# DATASET A: OUTPUT-BASED BUDGET (OBB) 2024 - 2028
# ==============================================================================
def extract_obb_budget():
    print(f"Extracting OBB Budget from {OBB_BUDGET_PDF} ...")
    records = []

    if not os.path.exists(OBB_BUDGET_PDF):
        print(f"Error: {OBB_BUDGET_PDF} not found.")
        return records

    with pdfplumber.open(OBB_BUDGET_PDF) as pdf:
        # 1. Revenue Schedule (Pages 3, 4, 5)
        for page_num in [3, 4, 5]:
            page = pdf.pages[page_num - 1]
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                for row in tbl[1:]:
                    if not any(row) or len(row) < 3:
                        continue
                    code = clean_text(row[0])
                    desc = clean_text(row[1])
                    if not desc or desc.upper() in ("REVENUE DESCRIPTION", "TOTAL"):
                        continue

                    # Determine columns for numbers
                    app_2026 = ""
                    rev_2027 = ""
                    est_2028 = ""
                    if len(row) >= 8:
                        app_2026 = clean_num(row[2])
                        rev_2027 = clean_num(row[5])
                        est_2028 = clean_num(row[7])
                    elif len(row) >= 6:
                        app_2026 = clean_num(row[2])
                        rev_2027 = clean_num(row[4])
                        est_2028 = clean_num(row[5])

                    records.append({
                        "budget_section": "Revenue",
                        "classification_level": "Detailed Line Item",
                        "code": code,
                        "description": desc,
                        "amount_2024": "",
                        "amount_2025": "",
                        "amount_2026": app_2026,
                        "amount_2027": rev_2027,
                        "amount_2028": est_2028,
                        "source_file": "KTC-OBB-BUDGET-2026-to-2027.pdf",
                        "page": page_num
                    })

        # 2. Economic Classification Summary (Page 6)
        p6 = pdf.pages[5]
        for tbl in p6.extract_tables():
            for row in tbl[1:]:
                if not any(row) or len(row) < 4:
                    continue
                code = clean_text(row[0])
                desc = clean_text(row[1])
                if not desc or "ECONOMIC CLASSIFICATION" in desc.upper():
                    continue
                records.append({
                    "budget_section": "Expenditure - Economic",
                    "classification_level": "Summary",
                    "code": code,
                    "description": desc,
                    "amount_2024": clean_num(row[2]),
                    "amount_2025": clean_num(row[3]),
                    "amount_2026": clean_num(row[4]),
                    "amount_2027": "",
                    "amount_2028": "",
                    "source_file": "KTC-OBB-BUDGET-2026-to-2027.pdf",
                    "page": 6
                })

        # 3. Programme Expenditure Summary (Page 7)
        p7 = pdf.pages[6]
        for tbl in p7.extract_tables():
            for row in tbl[1:]:
                if not any(row) or len(row) < 4:
                    continue
                code = clean_text(row[0])
                desc = clean_text(row[1])
                if not desc or "PROGRAMME" in desc.upper():
                    continue
                records.append({
                    "budget_section": "Expenditure - Programme",
                    "classification_level": "Summary",
                    "code": code,
                    "description": desc,
                    "amount_2024": clean_num(row[2]),
                    "amount_2025": clean_num(row[3]),
                    "amount_2026": clean_num(row[4]),
                    "amount_2027": "",
                    "amount_2028": "",
                    "source_file": "KTC-OBB-BUDGET-2026-to-2027.pdf",
                    "page": 7
                })

    print(f"Extracted {len(records)} budget rows from OBB Budget.")
    return records


def fix_split_numbers(s: str) -> str:
    s = re.sub(r"(\d+)\s+,\s*(\d+)", r"\1,\2", s)
    s = re.sub(r"\b(\d)\s+(\d{1,2}(?:,\d{3})+)", r"\1\2", s)
    s = re.sub(r"\b(\d)\s+(\d{1,3}(?:,\d{3})+)", r"\1\2", s)
    return s


# ==============================================================================
# DATASET B: AUDITED FINANCIAL STATEMENTS 2022
# ==============================================================================
def extract_financials_2022():
    print(f"Extracting Audited Financials from {FINANCIALS_2022_PDF} ...")
    records = []

    if not os.path.exists(FINANCIALS_2022_PDF):
        print(f"Error: {FINANCIALS_2022_PDF} not found.")
        return records

    with pdfplumber.open(FINANCIALS_2022_PDF) as pdf:
        # Page 12: Statement of Comparison of Budget and Actual Amounts
        raw_lines = pdf.pages[11].extract_text().split("\n")
        merged_lines = []
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i].strip()
            nums = re.findall(r"[-+]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?", line)
            # If label is on one line and numbers on next line
            if not nums and i + 1 < len(raw_lines):
                next_nums = re.findall(r"[-+]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?", raw_lines[i + 1])
                if len(next_nums) >= 3 and not re.search(r"[a-zA-Z]{4,}", raw_lines[i + 1]):
                    line = f"{line} {raw_lines[i + 1].strip()}"
                    i += 1
            merged_lines.append(line)
            i += 1

        current_section = "Receipts"

        for line in merged_lines:
            line = clean_text(line)
            if not line or "STATEMENT OF COMPARISON" in line.upper() or "ENDED 31ST" in line.upper():
                continue
            if line.upper().startswith("RECEIPTS"):
                current_section = "Receipts"
                continue
            elif line.upper().startswith("PAYMENTS"):
                current_section = "Payments"
                continue

            fixed_line = fix_split_numbers(line)
            numbers = re.findall(r"[-+]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|-", fixed_line)
            pcts = re.findall(r"[-+]?[0-9]+%", fixed_line)

            # Match lines that represent financial line items
            if len(numbers) >= 4:
                # Find start of numbers
                first_num_match = re.search(r"[-+]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?", fixed_line)
                if not first_num_match:
                    continue
                item_name = fixed_line[:first_num_match.start()].strip()
                if not item_name or item_name.upper() in ("ORIGINAL BUDGET", "TOTAL"):
                    if "TOTAL" in fixed_line.upper():
                        item_name = "TOTAL RECEIPTS" if current_section == "Receipts" else "TOTAL PAYMENTS"
                    else:
                        continue

                # Parse numbers (Orig Budget, Adjustments, Final Budget, Actual, Variance)
                non_dash = [n for n in numbers if n != "-"]
                orig_budget = clean_num(numbers[0]) if len(numbers) > 0 else "0.00"
                adjustments = clean_num(numbers[1]) if len(numbers) > 1 and numbers[1] != "-" else "0.00"
                final_budget = clean_num(numbers[2]) if len(numbers) > 2 else orig_budget
                actual = clean_num(numbers[3]) if len(numbers) > 3 else "0.00"
                variance = clean_num(numbers[5]) if len(numbers) > 5 else "0.00"
                pct_perf = pcts[0] if len(pcts) > 0 else ""
                pct_var = pcts[1] if len(pcts) > 1 else ""

                records.append({
                    "statement_name": "Statement of Comparison of Budget and Actual Amounts",
                    "section": current_section,
                    "item_name": item_name,
                    "original_budget": orig_budget,
                    "adjustments": adjustments,
                    "final_budget": final_budget,
                    "actual_amount": actual,
                    "pct_performance": pct_perf,
                    "variance": variance,
                    "pct_variance": pct_var,
                    "year": 2022,
                    "source_file": "Kawambwa-Town-Council-Audited-Financial-Statements-2022.pdf",
                    "page": 12
                })

        # Page 11: Statement of Cash Receipts and Payments (2022 vs 2021)
        # Note: Local taxes, Fees, Levies, LGEF, CDF, Personal Emoluments, etc.
        p11_lines = [
            ("Local taxes", "468,731.00", "361,756.00", "Receipts"),
            ("Fees and Charges", "2,471,780.00", "2,273,865.00", "Receipts"),
            ("Licences", "243,628.00", "183,126.00", "Receipts"),
            ("Levies", "25,441.00", "6,072.00", "Receipts"),
            ("Permits", "332,168.00", "159,128.00", "Receipts"),
            ("Local Government Equalisation Fund (LGEF)", "10,152,215.00", "8,885,740.00", "Receipts"),
            ("Constituency Development Fund (CDF)", "47,479,821.00", "3,200,000.00", "Receipts"),
            ("Commercial Venture", "-14,120.00", "8,527.00", "Receipts"),
            ("Other Receipts", "803,063.00", "326,099.00", "Receipts"),
            ("TOTAL RECEIPTS", "61,962,727.00", "15,404,312.00", "Receipts"),
            ("Personnel Emoluments", "8,985,725.00", "8,305,161.00", "Payments"),
            ("Use of goods and services", "5,870,910.00", "6,444,034.00", "Payments"),
            ("Financial Charges", "0.00", "116,855.00", "Payments"),
            ("Social benefits", "765,055.00", "0.00", "Payments"),
            ("Non-financial assets acquisition", "3,751,289.00", "157,337.00", "Payments"),
            ("Financial Assets", "0.00", "46,755.00", "Payments"),
            ("Other payments", "39,600.00", "62,991.00", "Payments"),
            ("TOTAL PAYMENTS", "19,412,579.00", "15,133,132.00", "Payments"),
            ("Increase/(Decrease) in Cash", "42,550,148.00", "271,180.00", "Net Cash"),
            ("Cash at end of the year", "49,494,861.00", "6,944,713.00", "Cash Balance"),
        ]

        for item, act_2022, act_2021, s_type in p11_lines:
            records.append({
                "statement_name": "Statement of Cash Receipts and Payments (IPSAS Cash Basis)",
                "section": s_type,
                "item_name": item,
                "original_budget": "",
                "adjustments": "",
                "final_budget": "",
                "actual_amount": act_2022,
                "pct_performance": "",
                "variance": f"2021 Actual: {act_2021}",
                "pct_variance": "",
                "year": 2022,
                "source_file": "Kawambwa-Town-Council-Audited-Financial-Statements-2022.pdf",
                "page": 11
            })

    print(f"Extracted {len(records)} financial rows from 2022 Audited Statements.")
    return records


# ==============================================================================
# MANIFEST: ALL 8 DOCUMENTS
# ==============================================================================
def create_manifest():
    manifest = [
        {
            "filename": "KTC-OBB-BUDGET-2026-to-2027.pdf",
            "title": "Kawambwa Town Council Output-Based Budget (OBB) 2026 - 2028",
            "type": "Digital Structured Document",
            "pages": 65,
            "has_extractable_tables": True,
            "dataset_output": OUTPUT_OBB_CSV,
            "key_data_points": [
                "Detailed 111-line revenue schedule (2026 Approved, 2027 Revised, 2028 Estimates)",
                "Economic classification summary (Personal Emoluments, Goods & Services, Assets)",
                "Programme summaries (Local Governance, Integrated Dev Planning, Resource Mobilisation)",
                "Sub-programme allocations across 2024, 2025, and 2026"
            ],
            "ocr_priority": "Not needed (fully digital vector data)"
        },
        {
            "filename": "Kawambwa-Town-Council-Audited-Financial-Statements-2022.pdf",
            "title": "Audited Financial Statements for Year Ended 31st December 2022",
            "type": "Digital Accounting Document",
            "pages": 29,
            "has_extractable_tables": True,
            "dataset_output": OUTPUT_FIN_CSV,
            "key_data_points": [
                "Statement of Comparison of Budget and Actual Amounts (Page 12)",
                "Statement of Cash Receipts & Payments (2022 Actual vs 2021 Restated)",
                "Local Taxes: K652,945 Budget vs K468,731 Actual (72% performance)",
                "Constituency Development Fund (CDF): K51,400,000 Budget vs K47,479,821 Actual",
                "Total Council Receipts: K61,962,727; Total Payments: K19,412,579; Cash Balance: K49,494,861"
            ],
            "ocr_priority": "Not needed (fully digital text)"
        },
        {
            "filename": "UNMODIFIED-AUDIT-OPINION-FOR-2022-FINANCIAL-STATEMENTS.pdf",
            "title": "Auditor General Independent Auditor's Report (Clean Opinion)",
            "type": "Narrative Legal Letter",
            "pages": 3,
            "has_extractable_tables": False,
            "dataset_output": "Manifest Only",
            "key_data_points": [
                "Official Unmodified (Clean) Audit Opinion issued by Office of the Auditor General",
                "Confirms council cash receipts and payments present fairly under Cash Basis IPSAS",
                "Addressed to the Minister of Local Government and Rural Development"
            ],
            "ocr_priority": "Not needed (digital narrative text)"
        },
        {
            "filename": "SIGNED-PROPERTY-RATES-2025.pdf",
            "title": "Minutes of Meeting between Property Rate Payers and Management (17 July 2025)",
            "type": "Scanned Document (OCR Verified)",
            "pages": 5,
            "has_extractable_tables": False,
            "dataset_output": "Manifest & OCR Summary",
            "key_data_points": [
                "Official ratepayer consultation meeting chaired by Council Secretary Andrew Bwali",
                "2024 Property rate collection performance: 63%",
                "2025 Current property rate collection performance: 33%",
                "Council incentive policy: 20% write-off on outstanding rates if 80% is paid within 3 months (August 2025)",
                "Register of 62 property owners across Low Density, Medium Density, Messengers, Suburbs",
                "Signed and stamped with official seal on 25 July 2025"
            ],
            "ocr_priority": "High Value OCR Completed (Governance & Compliance Metrics)"
        },
        {
            "filename": "FINANCIAL-STATEMENTS-REPORT-2024.pdf",
            "title": "Draft Financial Statements Report 2024",
            "type": "Scanned Financial Booklet",
            "pages": 41,
            "has_extractable_tables": False,
            "dataset_output": "Manifest Only",
            "key_data_points": [
                "Complete 41-page signed draft financial statements for 2024",
                "Contains 2024 cash receipts and payments schedules and CDF expenditure notes"
            ],
            "ocr_priority": "High Priority for Second Pass (if full 2024 cash actuals needed)"
        },
        {
            "filename": "SEMI-ANNUAL-BUDGET-EXECUTION-REPORTS.pdf",
            "title": "Semi-Annual Budget Execution Report",
            "type": "Scanned Administrative Report",
            "pages": 19,
            "has_extractable_tables": False,
            "dataset_output": "Manifest Only",
            "key_data_points": [
                "Mid-year budget performance schedules and department execution rates"
            ],
            "ocr_priority": "Medium Priority for Second Pass"
        },
        {
            "filename": "SEMI-ANNUAL-BUDGET-2024.pdf",
            "title": "Semi-Annual Budget 2024 Resolution",
            "type": "Scanned Council Resolution",
            "pages": 3,
            "has_extractable_tables": False,
            "dataset_output": "Manifest Only",
            "key_data_points": [
                "Council resolution approving 2024 supplementary adjustments"
            ],
            "ocr_priority": "Low Priority"
        },
        {
            "filename": "2024-Annual-Perfomance-Report.pdf",
            "title": "Annual Performance Report 2024 Submission",
            "type": "Scanned Administrative Memo",
            "pages": 3,
            "has_extractable_tables": False,
            "dataset_output": "Manifest Only",
            "key_data_points": [
                "Official submission letter on institutional KPI performance to MLGRD"
            ],
            "ocr_priority": "Low Priority"
        }
    ]

    with open(OUTPUT_MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Write Markdown Manifest
    with open(OUTPUT_MANIFEST_MD, "w", encoding="utf-8") as f:
        f.write("# Kawambwa Town Council — Financial & Budget Documents Manifest\n\n")
        f.write("This manifest tracks all 8 budget and financial documents, their data formats, and processing status.\n\n")
        f.write("| Document File | Type | Pages | Processed Dataset | Key Data / Governance Insight |\n")
        f.write("| :--- | :--- | :---: | :--- | :--- |\n")
        for m in manifest:
            f.write(f"| **`{m['filename']}`** | {m['type']} | {m['pages']} | `{m['dataset_output']}` | {m['key_data_points'][0]} |\n")
        f.write("\n## Second-Pass OCR Recommendations\n")
        f.write("- **`FINANCIAL-STATEMENTS-REPORT-2024.pdf` (High Priority):** 41-page scanned booklet containing full 2024 actual expenditures and CDF reconciliation. Worth OCR-ing if comprehensive 2024 cash actuals are needed.\n")
        f.write("- **`SEMI-ANNUAL-BUDGET-EXECUTION-REPORTS.pdf` (Medium Priority):** 19-page report with mid-year execution rates.\n")
        f.write("- **`SIGNED-PROPERTY-RATES-2025.pdf`:** OCR verified; provides official local revenue compliance benchmarks (2024: 63%, 2025: 33%, 20% settlement discount).\n")

    print(f"Saved manifest to {OUTPUT_MANIFEST_JSON} and {OUTPUT_MANIFEST_MD}")


# ==============================================================================
# MAIN PIPELINE EXECUTION
# ==============================================================================
def main():
    print("======================================================================")
    print("BUILDING BUDGET AND FINANCIAL DATASETS")
    print("======================================================================")

    # 1. Dataset A: OBB Budget
    obb_records = extract_obb_budget()
    obb_fieldnames = [
        "budget_section",
        "classification_level",
        "code",
        "description",
        "amount_2024",
        "amount_2025",
        "amount_2026",
        "amount_2027",
        "amount_2028",
        "source_file",
        "page"
    ]
    with open(OUTPUT_OBB_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=obb_fieldnames, delimiter="|")
        writer.writeheader()
        for r in obb_records:
            writer.writerow(r)
    print(f"Saved Dataset A to: {OUTPUT_OBB_CSV} ({len(obb_records)} rows)")

    # 2. Dataset B: Audited Financials 2022
    fin_records = extract_financials_2022()
    fin_fieldnames = [
        "statement_name",
        "section",
        "item_name",
        "original_budget",
        "adjustments",
        "final_budget",
        "actual_amount",
        "pct_performance",
        "variance",
        "pct_variance",
        "year",
        "source_file",
        "page"
    ]
    with open(OUTPUT_FIN_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fin_fieldnames, delimiter="|")
        writer.writeheader()
        for r in fin_records:
            writer.writerow(r)
    print(f"Saved Dataset B to: {OUTPUT_FIN_CSV} ({len(fin_records)} rows)")

    # 3. Metadata Manifest
    create_manifest()
    print("======================================================================\n")


if __name__ == "__main__":
    main()
