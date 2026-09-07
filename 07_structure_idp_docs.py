import csv
import json
import os
import re
import pdfplumber

DOWNLOADS_DIR = "pdf_downloads"
IDP_FULL_PDF = os.path.join(DOWNLOADS_DIR, "Kawambwa-IDP.pdf")
ESMP_BUS_PDF = os.path.join(DOWNLOADS_DIR, "KTC-ESMP-MODERN-BUS-STATION.pdf")
NEW_IDP_PDF = os.path.join(DOWNLOADS_DIR, "New-IDP-KTC.pdf")
ESCP_PDF = os.path.join(DOWNLOADS_DIR, "Environment-and-Social-Commitment-Plan1.pdf")
STAKEHOLDERS_PDF = os.path.join(DOWNLOADS_DIR, "STAKEHOLDERS-ENGAGEMENT-PLAN.pdf")

OUTPUT_IDP_PROJECTS_CSV = "db-unza26-csc4792-kawambwa_idp_projects.csv"
OUTPUT_ESMP_CSV = "db-unza26-csc4792-kawambwa_esmp_bus_station.csv"
OUTPUT_IDP_MANIFEST_JSON = "idp_documents_manifest.json"
OUTPUT_IDP_MANIFEST_MD = "idp_documents_manifest.md"


def clean_text(val: str) -> str:
    if not val:
        return ""
    t = str(val).replace("\n", " ").replace("\r", " ").replace("|", "/")
    # Remove bullet artifacts
    t = re.sub(r"[\uf06c\uf0d8\uf0b7\u2022]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def clean_num(val: str) -> str:
    if not val:
        return ""
    v = str(val).replace("\n", " ").replace(",", "").strip()
    m = re.search(r"[-+]?\d*\.?\d+", v)
    if m:
        try:
            num = float(m.group(0))
            return f"{num:,.2f}"
        except ValueError:
            pass
    return ""


# ==============================================================================
# 1. CAPITAL INVESTMENT PROGRAMME (CIP) PROJECTS (from Kawambwa-IDP.pdf)
# ==============================================================================
def extract_idp_projects():
    print(f"Extracting Capital Investment Programme from {IDP_FULL_PDF} ...")
    records = []

    if not os.path.exists(IDP_FULL_PDF):
        print(f"Error: {IDP_FULL_PDF} not found.")
        return records

    with pdfplumber.open(IDP_FULL_PDF) as pdf:
        # Implementation Programme is on pages 154 to 158
        for p_num in range(154, 159):
            page = pdf.pages[p_num - 1]
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                for row in tbl:
                    if not any(row) or len(row) < 7:
                        continue
                    
                    row_clean = [clean_text(c) for c in row]
                    header_check = " ".join(row_clean).lower()
                    if any(w in header_check for w in ["strategy", "activity", "responsible agency", "location by priority", "goal:"]):
                        continue

                    # In these 10-column tables:
                    # Col 1: Programme (if present)
                    # Col 2: Activity / Project description
                    # Col 3: Location / Ward priority
                    # Col 4..8: 2024, 2025, 2026, 2027, 2028 allocations
                    # Col 9: Responsible agency
                    activity = ""
                    location = ""
                    agency = ""
                    c24, c25, c26, c27, c28 = "", "", "", "", ""
                    prog = ""

                    if len(row_clean) >= 10:
                        prog = row_clean[1] if row_clean[1] else "Capital Infrastructure"
                        activity = row_clean[2]
                        location = row_clean[3]
                        c24 = clean_num(row_clean[4])
                        c25 = clean_num(row_clean[5])
                        c26 = clean_num(row_clean[6])
                        c27 = clean_num(row_clean[7])
                        c28 = clean_num(row_clean[8])
                        agency = row_clean[9]
                    elif len(row_clean) >= 7:
                        activity = row_clean[0]
                        location = row_clean[1]
                        c24 = clean_num(row_clean[2])
                        c25 = clean_num(row_clean[3])
                        c26 = clean_num(row_clean[4])
                        agency = row_clean[-1]

                    if not activity or len(activity) < 4:
                        continue

                    records.append({
                        "programme": prog if prog else "Local Development Infrastructure",
                        "project_name": activity,
                        "location_priority": location if location else "District-wide",
                        "cost_2024": c24,
                        "cost_2025": c25,
                        "cost_2026": c26,
                        "cost_2027": c27,
                        "cost_2028": c28,
                        "responsible_agency": agency if agency else "Kawambwa Town Council",
                        "source_file": "Kawambwa-IDP.pdf",
                        "page": p_num
                    })

    print(f"Extracted {len(records)} strategic IDP project rows.")
    return records


# ==============================================================================
# 2. ESMP MODERN BUS STATION MITIGATION MATRIX (from KTC-ESMP-MODERN-BUS-STATION.pdf)
# ==============================================================================
def extract_bus_station_esmp():
    print(f"Extracting ESMP Mitigation Matrix from {ESMP_BUS_PDF} ...")
    records = []

    if not os.path.exists(ESMP_BUS_PDF):
        print(f"Error: {ESMP_BUS_PDF} not found.")
        return records

    with pdfplumber.open(ESMP_BUS_PDF) as pdf:
        # Mitigation matrix is on pages 8 to 11
        for p_num in range(8, 12):
            page = pdf.pages[p_num - 1]
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                for row in tbl:
                    if not any(row) or len(row) < 4:
                        continue
                    row_clean = [clean_text(c) for c in row]
                    h_check = " ".join(row_clean).lower()
                    if any(w in h_check for w in ["environmental/ social impact", "mitigation measure", "potential impact", "responsibility"]):
                        continue

                    raw_no = row_clean[0].strip()
                    # Check if this row is a continuation row (no impact number or no digits)
                    has_digits = any(char.isdigit() for char in raw_no)
                    
                    if not has_digits and records:
                        # Merge wrapped continuation lines into previous record
                        if len(row_clean) > 2 and row_clean[2]:
                            records[-1]["potential_impact"] = clean_text(f"{records[-1]['potential_impact']} {row_clean[2]}")
                        if len(row_clean) > 3 and row_clean[3]:
                            records[-1]["mitigation_measure"] = clean_text(f"{records[-1]['mitigation_measure']} {row_clean[3]}")
                        continue

                    # Clean impact number (e.g. "11." -> "11")
                    impact_no = re.sub(r"[^0-9]", "", raw_no) if has_digits else ""
                    if not impact_no:
                        continue

                    impact_cat = row_clean[1] if len(row_clean) > 1 else ""
                    pot_impact = row_clean[2] if len(row_clean) > 2 else ""
                    mitigation = row_clean[3] if len(row_clean) > 3 else ""
                    resp = row_clean[4] if len(row_clean) > 4 and row_clean[4] else "Contractor/Local Authority"
                    timeline = row_clean[5] if len(row_clean) > 5 and row_clean[5] else "Construction Phase"

                    records.append({
                        "impact_no": impact_no,
                        "impact_category": impact_cat,
                        "potential_impact": pot_impact,
                        "mitigation_measure": mitigation,
                        "responsibility": resp,
                        "timeline": timeline,
                        "source_file": "KTC-ESMP-MODERN-BUS-STATION.pdf",
                        "page": p_num
                    })

    print(f"Extracted {len(records)} ESMP mitigation rows.")
    return records


# ==============================================================================
# 3. METADATA MANIFEST FOR ALL 5 DOCUMENTS
# ==============================================================================
def create_idp_manifest():
    manifest = [
        {
            "filename": "Kawambwa-IDP.pdf",
            "title": "Kawambwa Integrated Development Plan (Comprehensive 10-Year Plan)",
            "pages": 227,
            "type": "Statutory Comprehensive Planning Framework",
            "status": "Structured into CSV (Capital Investment Programme)",
            "key_contents": [
                "Demographic Baseline (16 Wards population, density, sex ratio)",
                "Development Framework & Spatial Development Vision",
                "Part Four: Capital Investment Programme 2024-2028 (Mini-hospitals, health posts, roads, water schemes)",
                "5-Year Revenue Projections (Local Taxes K2.6M/yr, LGEF, CDF)",
                "Monitoring and Evaluation Framework"
            ]
        },
        {
            "filename": "KTC-ESMP-MODERN-BUS-STATION.pdf",
            "title": "Environmental and Social Management Plan (ESMP) for Proposed Modern Bus Station",
            "pages": 25,
            "type": "Capital Project Environmental & Social Impact Assessment",
            "status": "Structured into CSV (Mitigation & Monitoring Matrix)",
            "key_contents": [
                "Flora/fauna protection and site clearance controls",
                "Dust emission and noise suppression protocols",
                "Traffic management and road safety during construction",
                "Solid and hazardous waste handling",
                "Institutional oversight and compliance monitoring"
            ]
        },
        {
            "filename": "New-IDP-KTC.pdf",
            "title": "Kawambwa Town Council Updated Executive IDP Draft",
            "pages": 48,
            "type": "Executive Strategic Summary",
            "status": "Manifest Record (Summary Matrix)",
            "key_contents": [
                "Key Priority Issues & Council Solutions (Upgrade 130km roads to Lumangwe Falls & Kala Marine Barracks by 2028)",
                "Fisheries and Aquaculture development (Stocked fish ponds baseline)",
                "Institutional capacity analysis (Equipment and staffing shortfalls in Engineering & Planning)"
            ]
        },
        {
            "filename": "Environment-and-Social-Commitment-Plan1.pdf",
            "title": "Zambia Devolution Support Program (ZDSP) Environmental & Social Commitment Plan",
            "pages": 7,
            "type": "World Bank / National Statutory Commitment Framework",
            "status": "Manifest Record",
            "key_contents": [
                "Institutional environmental and social staffing mandates for council infrastructure",
                "Grievance Redress Mechanism (GRM) establishment for municipal sub-projects",
                "Occupational Health and Safety (OHS) compliance guidelines"
            ]
        },
        {
            "filename": "STAKEHOLDERS-ENGAGEMENT-PLAN.pdf",
            "title": "Stakeholders Engagement Plan for Infrastructure Development",
            "pages": 9,
            "type": "Scanned Document (Public Consultation Register)",
            "status": "Manifest Record",
            "key_contents": [
                "Public consultation framework for council infrastructure investments",
                "Civil society, traditional leadership, and market association engagement protocols"
            ]
        }
    ]

    with open(OUTPUT_IDP_MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    with open(OUTPUT_IDP_MANIFEST_MD, "w", encoding="utf-8") as f:
        f.write("# Kawambwa Town Council — IDP & Environmental Planning Documents Manifest\n\n")
        f.write("This manifest tracks the 5 planning and environmental frameworks for Kawambwa District.\n\n")
        f.write("| Document File | Type | Pages | Structured Dataset / Status | Key Highlight |\n")
        f.write("| :--- | :--- | :---: | :--- | :--- |\n")
        for m in manifest:
            f.write(f"| **`{m['filename']}`** | {m['type']} | {m['pages']} | `{m['status']}` | {m['key_contents'][0]} |\n")

    print(f"Saved manifest to {OUTPUT_IDP_MANIFEST_JSON} and {OUTPUT_IDP_MANIFEST_MD}")


def main():
    print("======================================================================")
    print("BUILDING IDP AND STRATEGIC PLANNING DATASETS")
    print("======================================================================")

    # 1. IDP Projects CSV
    idp_records = extract_idp_projects()
    idp_fieldnames = [
        "programme",
        "project_name",
        "location_priority",
        "cost_2024",
        "cost_2025",
        "cost_2026",
        "cost_2027",
        "cost_2028",
        "responsible_agency",
        "source_file",
        "page"
    ]
    with open(OUTPUT_IDP_PROJECTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=idp_fieldnames, delimiter="|")
        writer.writeheader()
        for r in idp_records:
            writer.writerow(r)
    print(f"Saved IDP Projects CSV to: {OUTPUT_IDP_PROJECTS_CSV} ({len(idp_records)} rows)")

    # 2. ESMP Bus Station CSV
    esmp_records = extract_bus_station_esmp()
    esmp_fieldnames = [
        "impact_no",
        "impact_category",
        "potential_impact",
        "mitigation_measure",
        "responsibility",
        "timeline",
        "source_file",
        "page"
    ]
    with open(OUTPUT_ESMP_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=esmp_fieldnames, delimiter="|")
        writer.writeheader()
        for r in esmp_records:
            writer.writerow(r)
    print(f"Saved ESMP Mitigation CSV to: {OUTPUT_ESMP_CSV} ({len(esmp_records)} rows)")

    # 3. Manifest
    create_idp_manifest()
    print("======================================================================\n")


if __name__ == "__main__":
    main()
