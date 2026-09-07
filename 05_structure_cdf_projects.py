import csv
import os
import re
import shutil
from collections import defaultdict
from difflib import SequenceMatcher
import pdfplumber

CDF_FILES = [
    ("KAWAMBWA-COMMUNITY-PROJECTS-year2022.pdf", 2022, "Kawambwa"),
    ("PAMBASHE-COMMUNITY-PROJECTS-2022.pdf", 2022, "Pambashe"),
    ("KAWAMBWA-COMMUNITY-PROJECTS-2023.pdf", 2023, "Kawambwa"),
    ("PAMBASHE-COMMUNITY-PROJECTS-2023.pdf", 2023, "Pambashe"),
    ("KAWAMBWA-COMMUNITY-PROJECTS-2024.pdf", 2024, "Kawambwa"),
    ("PAMBASHE-COMMUNITY-PROJECTS-2024-.pdf", 2024, "Pambashe"),
    ("2025-KAWAMBWA-COMM-PROJECTS-UPDATED.pdf", 2025, "Kawambwa"),
    ("2025-Pambashe-CommProjects-updated.pdf", 2025, "Pambashe"),
    ("APPROVED-KAWAMBWA-COMMUNITY-PROJECTS-2025.pdf", 2025, "Kawambwa"),
    ("APPROVED-PAMBASHE-COMMUNITY-PROJECTS-2025.pdf", 2025, "Pambashe"),
    ("DEFERRED-2025-KAWAMBWA-COMM-PROJECTS-UPDATED.pdf", 2025, "Kawambwa"),
    ("DEFERRED-2025-Pambashe-CommProjects-updated.pdf", 2025, "Pambashe"),
]

DOWNLOADS_DIR = "pdf_downloads"
OUTPUT_CSV = "db-unza26-csc4792-kawambwa_cdf_projects.csv"
ALIAS_CSV = "cdf_projects.csv"

HEADER_KEYWORDS = {
    "sn", "no", "item", "project", "description", "name",
    "ward", "location", "sector", "category", "type",
    "amount", "cost", "comment", "comments", "status", "remark"
}

WARD_CANONICAL_MAP = {
    "kala": "Kala",
    "fisaka": "Fisaka",
    "senga": "Senga",
    "iyanga": "Iyanga",
    "ngona": "Ng'ona",
    "ng'ona": "Ng'ona",
    "lushiba": "Lushiba",
    "ntumbachushi": "Ntumbachushi",
    "ntumacushi": "Ntumbachushi",
    "ntumbacushi": "Ntumbachushi",
    "kawambwa": "Kawambwa",
    "kawmbwa": "Kawambwa",
    "chibote": "Chibote",
    "chibote ward": "Chibote",
    "chikanda": "Chikanda",
    "filenge": "Filenge",
    "kabanse": "Kabanse",
    "chimpili": "Chimpili",
    "chipili": "Chimpili",
    "ilombe": "Ilombe",
    "mulunda": "Mulunda",
    "pambashe": "Pambashe",
    "pampashe": "Pambashe",
    "luongo": "Luongo",
    "luena": "Luena",
    "all": "All Wards",
    "all ward": "All Wards",
    "all wards": "All Wards",
}


def clean_str(val) -> str:
    if val is None:
        return ""
    text = str(val).replace("\n", " ").replace("\r", " ")
    text = text.replace("|", "/")
    return re.sub(r"\s+", " ", text).strip()


def strip_leaked_headers(name: str) -> str:
    """Strips leaked table headers like 'SECTOR STATUS' appended by pdfplumber wraps."""
    cleaned = re.sub(r"\s+(SECTOR\s+STATUS|SECTOR|STATUS|COMMENT|S/N)\s*$", "", name, flags=re.IGNORECASE)
    return cleaned.strip()


def is_true_header(row) -> bool:
    if not row or len(row) < 3:
        return False
    matches = 0
    for cell in row:
        clean = re.sub(r"[^a-z]", "", str(cell or "").lower())
        if clean in HEADER_KEYWORDS or any(
            clean == k for k in [
                "typeofproject", "projectname", "projectdescription",
                "approvedamount", "typeofinfrastructure", "sn"
            ]
        ):
            matches += 1
    return matches >= 2


def normalize_status(raw_status: str, filename: str) -> str:
    s = raw_status.lower() if raw_status else ""
    fn = filename.upper()
    if "DEFERRED" in fn:
        return "Deferred / Not Approved"
    elif "APPROVED" in fn and "NOT" not in s and "DEFERRED" not in s:
        return "Approved"

    if "approved" in s and "not approved" not in s and "deferred" not in s:
        return "Approved"
    elif "not approved" in s or "deferred" in s:
        return "Deferred / Not Approved"
    elif raw_status and len(raw_status) > 2:
        return raw_status.title()
    return "Approved" if "APPROVED" in fn else "Deferred / Not Approved" if "DEFERRED" in fn else "Unspecified"


def clean_amount(val: str) -> str:
    if not val:
        return ""
    m = re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)", val)
    if m:
        num_str = m.group(1).replace(",", "")
        try:
            val_float = float(num_str)
            if val_float > 100:
                return f"{val_float:,.2f}"
        except ValueError:
            pass
    return ""


def identify_columns(header_row):
    mapping = {
        "sn": -1,
        "project_name": -1,
        "ward": -1,
        "sector": -1,
        "project_type": -1,
        "amount": -1,
        "status": -1,
    }

    for idx, col in enumerate(header_row):
        col_clean = re.sub(r"[^a-zA-Z]", "", str(col).lower())
        if col_clean in ("sn", "no", "item", "number"):
            mapping["sn"] = idx
        elif any(k in col_clean for k in ("projectdescription", "projectname", "description")):
            mapping["project_name"] = idx
        elif col_clean == "typeofproject":
            if any(k in re.sub(r"[^a-zA-Z]", "", str(c).lower()) for c in header_row for k in ("projectdescription", "projectname", "description")):
                mapping["project_type"] = idx
            else:
                mapping["project_name"] = idx
        elif "project" in col_clean or "name" in col_clean:
            if mapping["project_name"] == -1:
                mapping["project_name"] = idx
        elif any(k in col_clean for k in ("ward", "location")):
            mapping["ward"] = idx
        elif any(k in col_clean for k in ("sector", "category")):
            mapping["sector"] = idx
        elif any(k in col_clean for k in ("amount", "cost", "budget", "funding")):
            mapping["amount"] = idx
        elif any(k in col_clean for k in ("comment", "status", "remark")):
            mapping["status"] = idx

    return mapping


def normalize_ward(raw_ward: str, proj_name: str) -> str:
    cleaned = re.sub(r"[^a-z]", "", raw_ward.lower())
    if cleaned in WARD_CANONICAL_MAP:
        return WARD_CANONICAL_MAP[cleaned]
    for k, v in WARD_CANONICAL_MAP.items():
        k_clean = re.sub(r"[^a-z]", "", k.lower())
        if cleaned == k_clean:
            return v
    for k, v in WARD_CANONICAL_MAP.items():
        if re.search(r"\b" + re.escape(k) + r"\b", proj_name, re.IGNORECASE):
            return v
    if not raw_ward or raw_ward.lower() in ("not specified", "unknown", "constituency-wide / not specified", ""):
        return "Constituency-wide / Not Specified"
    return raw_ward.strip().title()


def norm_for_match(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\b(construction|procurement|of|a|an|the|at|in|and|for|proposed|1x3|1x2|to)\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def are_near_duplicates_2025(r1, r2) -> bool:
    if r1["constituency"] != r2["constituency"] or r1["year"] != r2["year"]:
        return False

    w1 = r1["ward"].lower()
    w2 = r2["ward"].lower()

    # If different specific wards, they are distinct community projects
    if w1 != w2 and not any(g in [w1, w2] for g in ["constituency-wide / not specified", "all wards"]):
        return False

    n1 = r1["project_name"]
    n2 = r2["project_name"]
    if n1.lower().strip() == n2.lower().strip():
        return True

    s1, s2 = norm_for_match(n1), norm_for_match(n2)
    if s1 == s2 and len(s1) > 2:
        return True

    ratio = SequenceMatcher(None, s1, s2).ratio()
    if ratio >= 0.90:
        return True

    return False


def get_source_authority_rank(source_file: str) -> int:
    """APPROVED- prefixed files are most authoritative (rank 3), UPDATED (2), DEFERRED (1)."""
    if "APPROVED" in source_file.upper():
        return 3
    if "UPDATED" in source_file.upper() and "DEFERRED" not in source_file.upper():
        return 2
    if "DEFERRED" in source_file.upper():
        return 1
    return 0


def extract_raw_projects():
    all_projects = []

    for fname, default_year, default_constituency in CDF_FILES:
        filepath = os.path.join(DOWNLOADS_DIR, fname)
        if not os.path.exists(filepath):
            continue

        current_mapping = None

        with pdfplumber.open(filepath) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if not tables:
                    continue

                for table in tables:
                    if not table or len(table) < 1:
                        continue

                    if is_true_header(table[0]):
                        current_mapping = identify_columns(table[0])
                        rows_to_process = table[1:]
                    elif current_mapping is not None:
                        rows_to_process = table
                    else:
                        continue

                    for row in rows_to_process:
                        if not any(row):
                            continue

                        # Handle wrapped single cells
                        non_empty = [(idx, clean_str(cell)) for idx, cell in enumerate(row) if clean_str(cell)]
                        if len(non_empty) == 1 and all_projects:
                            cell_idx, cell_text = non_empty[0]
                            # Leaked header keyword skip
                            if cell_text.upper() in ("SECTOR", "STATUS", "COMMENT", "SECTOR STATUS", "S/N"):
                                continue
                            if any(p in cell_text.lower() for p in ["limited fund", "due to limited", "not approved", "to limited"]):
                                if "Not Approved" not in all_projects[-1]["status"]:
                                    all_projects[-1]["status"] = "Deferred / Not Approved"
                                continue
                            if current_mapping and cell_idx == current_mapping.get("project_name", -1):
                                all_projects[-1]["project_name"] = clean_str(f"{all_projects[-1]['project_name']} {cell_text}")
                                continue

                        def get_val(col_key):
                            idx = current_mapping.get(col_key, -1)
                            if 0 <= idx < len(row):
                                return clean_str(row[idx])
                            return ""

                        raw_pname = get_val("project_name")
                        proj_name = strip_leaked_headers(raw_pname)
                        if not proj_name or len(proj_name) < 4:
                            continue
                        if proj_name.upper() in (
                            "PROJECT NAME", "PROJECT DESCRIPTION", "TYPE OF PROJECT",
                            "SECTOR", "WARD", "COMMENT", "STATUS", "S/N", "NO.", "AMOUNT"
                        ):
                            continue

                        raw_ward = get_val("ward")
                        ward = normalize_ward(raw_ward, proj_name)

                        sector = get_val("sector")
                        raw_status = get_val("status")
                        status = normalize_status(raw_status, fname)
                        raw_amount = get_val("amount")
                        amount = clean_amount(raw_amount)

                        raw_type = get_val("project_type")
                        cleaned_type = clean_str(raw_type)
                        if re.search(r"infrastructur\s*e", cleaned_type, re.IGNORECASE):
                            project_type = "Infrastructure"
                        elif cleaned_type:
                            project_type = cleaned_type.title()
                        else:
                            project_type = ""

                        record = {
                            "constituency": default_constituency,
                            "ward": ward,
                            "project_name": proj_name,
                            "year": default_year,
                            "status": status,
                            "amount": amount,
                            "category": sector.title() if sector else "Community Infrastructure",
                            "project_type": project_type,
                            "source_file": fname
                        }
                        all_projects.append(record)

    return all_projects


def get_completeness_score(r):
    score = 0
    # Prefer populated project_type over blank
    if r.get("project_type", "").strip():
        score += 10
    # Prefer populated amount over blank
    if r.get("amount", "").strip():
        score += 5
    # Prefer specific category over default "Community Infrastructure"
    cat = r.get("category", "").strip().lower()
    if cat and cat not in ("", "community infrastructure", "unspecified"):
        score += 3
    # Prefer specific status
    st = r.get("status", "").strip().lower()
    if st and st not in ("", "unspecified"):
        score += 2
    # Non-empty fields count
    score += sum(1 for v in r.values() if str(v).strip())
    return score


def deduplicate_exact_source_records(records):
    grouped = defaultdict(list)
    for r in records:
        clean_amt = str(r.get("amount", "")).replace(",", "").strip()
        key = (
            r["ward"].strip().lower(),
            r["project_name"].strip().lower(),
            str(r["year"]),
            r["source_file"],
            clean_amt
        )
        grouped[key].append(r)

    deduped = []
    dropped_count = 0
    for key, group in grouped.items():
        if len(group) == 1:
            deduped.append(group[0])
        else:
            sorted_group = sorted(group, key=get_completeness_score, reverse=True)
            best = sorted_group[0]
            deduped.append(best)
            dropped_count += len(group) - 1
            amt_desc = f"amount={key[4]}" if key[4] else "blank amount"
            print(f"Deduplicated {len(group)} exact records for '{key[1]}' ({key[0]}, {key[2]} in {key[3]}, {amt_desc}), kept most complete.")

    print(f"Exact intra-file deduplication (matching ward, project, year, source_file, and amount) removed {dropped_count} redundant rows across all years.")
    return deduped


def deduplicate_and_flag_conflicts(raw_records):
    # First: deduplicate exact duplicates (same ward, project_name, year, source_file) across ALL years
    cleaned_records = deduplicate_exact_source_records(raw_records)

    # 2022-2024 rows
    rows_other = [r for r in cleaned_records if r["year"] != 2025]
    for r in rows_other:
        r["data_conflict"] = "False"

    # 2025 rows require cross-file deduplication between Updated, Deferred, and Approved files
    rows_2025 = [r for r in cleaned_records if r["year"] == 2025]

    clusters = []
    for r in rows_2025:
        placed = False
        for c in clusters:
            if any(are_near_duplicates_2025(r, member) for member in c):
                c.append(r)
                placed = True
                break
        if not placed:
            clusters.append([r])

    resolved_2025 = []
    conflict_count = 0

    for c in clusters:
        # Sort so highest authority file comes first
        c.sort(key=lambda x: -get_source_authority_rank(x["source_file"]))
        primary = dict(c[0])

        # Check for status conflict across sources
        statuses = set(x["status"] for x in c)
        if len(statuses) > 1:
            primary["data_conflict"] = "True"
            conflict_count += 1
            print(f"Conflict flagged for '{primary['project_name']}':")
            for x in c:
                print(f"   [{x['source_file']}] -> Ward: {x['ward']} | Status: {x['status']}")
        else:
            primary["data_conflict"] = "False"

        # Enrich ward if primary is generic but a duplicate source has a specific ward
        if "not specified" in primary["ward"].lower() or "all wards" in primary["ward"].lower():
            for x in c:
                if "not specified" not in x["ward"].lower() and "all wards" not in x["ward"].lower():
                    primary["ward"] = x["ward"]
                    break

        # Enrich amount if missing
        if not primary["amount"]:
            for x in c:
                if x["amount"]:
                    primary["amount"] = x["amount"]
                    break

        # Enrich project_type if missing
        if not primary.get("project_type"):
            for x in c:
                if x.get("project_type"):
                    primary["project_type"] = x["project_type"]
                    break

        resolved_2025.append(primary)

    final_dataset = rows_other + resolved_2025
    print(f"\nDeduplication complete: {len(raw_records)} raw records -> {len(final_dataset)} final records.")
    print(f"Total conflicts flagged: {conflict_count}")
    return final_dataset


def run_pipeline():
    print("Extracting CDF project tables...")
    raw_records = extract_raw_projects()
    print(f"Extracted {len(raw_records)} raw rows from all files.")

    final_records = deduplicate_and_flag_conflicts(raw_records)

    fieldnames = [
        "ward",
        "project_name",
        "year",
        "status",
        "amount",
        "category",
        "project_type",
        "constituency",
        "source_file",
        "data_conflict"
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="|")
        writer.writeheader()
        for r in final_records:
            writer.writerow(r)

    shutil.copyfile(OUTPUT_CSV, ALIAS_CSV)
    print(f"\nSaved pipe-separated CSV to: {OUTPUT_CSV}")
    print(f"Updated alias file: {ALIAS_CSV}")

    # Summary statistics
    app_count = sum(1 for r in final_records if r["status"] == "Approved")
    def_count = sum(1 for r in final_records if "Deferred" in r["status"])
    conflict_records = sum(1 for r in final_records if r["data_conflict"] == "True")

    by_year_app = {}
    by_year_def = {}
    for r in final_records:
        y = r["year"]
        if r["status"] == "Approved":
            by_year_app[y] = by_year_app.get(y, 0) + 1
        else:
            by_year_def[y] = by_year_def.get(y, 0) + 1

    print("\n==========================================")
    print("FINAL DATASET SUMMARY")
    print("==========================================")
    print(f"Total Rows:            {len(final_records)}")
    print(f"Approved Projects:     {app_count}")
    print(f"Deferred/Not Approved: {def_count}")
    print(f"Data Conflicts Flagged:{conflict_records}")
    print("==========================================")
    print("Yearly Breakdown (Approved / Deferred):")
    for y in sorted(set(list(by_year_app.keys()) + list(by_year_def.keys()))):
        print(f"  {y}: {by_year_app.get(y, 0)} Approved | {by_year_def.get(y, 0)} Deferred / Not Approved")


if __name__ == "__main__":
    run_pipeline()
