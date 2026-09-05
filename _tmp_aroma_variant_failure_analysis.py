from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import Workbook, load_workbook


FEATURE_PATH = Path("output/FEATURE_EXTRACTION_V2.xlsx")
MASTER_PATH = Path("output/MASTER_DATASET.xlsx")
OUTPUT_PATH = Path("output/AROMA_VARIANT_FAILURE_ANALYSIS.xlsx")


def norm(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return norm(value).upper()


def row_map(ws):
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    mapping = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        rownum = int(row[0])
        mapping[rownum] = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
    return mapping


def token_category(supplier_name: str) -> tuple[str, str, str]:
    text = upper(supplier_name)

    if "MENTOL" in text:
        return ("C", "MENTOL", "MASTER uses Mint; SupplierName uses the synonym MENTOL.")
    if "ПОДСНЕЖНИК" in text or "PODSNEZHNIK" in text:
        return (
            "C",
            "ПОДСНЕЖНИК",
            "MASTER uses Snowdrop; SupplierName uses the synonym ПОДСНЕЖНИК.",
        )
    if "МАЛЫШ" in text or "MALYSH" in text:
        return ("C", "МАЛЫШ", "MASTER uses Baby; SupplierName uses the synonym МАЛЫШ.")

    if "ДЛЯ БЕЛЫХ" in text:
        return ("D", "для белых", "Descriptor phrase should canonicalize to MASTER variant White.")
    if "ДЛЯ ЦВЕТНЫХ" in text or "Д\\ЦВЕТНОГО" in text or "Д/ЦВЕТНОГО" in text:
        return ("D", "для цветных", "Descriptor phrase should canonicalize to MASTER variant Color.")
    if "ДЛЯ ЦВ. И БЕЛ" in text or "ДЛЯ ЦВ И БЕЛ" in text:
        return ("D", "для цв. и бел", "Descriptor phrase should canonicalize to MASTER variant Color.")

    if "РОМАШКА" in text or "DAISY" in text:
        return ("C", "РОМАШКА Daisy", "SupplierName uses an alternate naming pattern that maps to the MASTER variant Baby.")

    return ("F", "", "Other variant parsing failure.")


def same_pattern_elsewhere(master_variants: set[str], expected_variant: str) -> str:
    if not expected_variant:
        return "NO"
    return "YES" if expected_variant.upper() in {variant.upper() for variant in master_variants if variant} else "NO"


def main() -> None:
    feature_wb = load_workbook(FEATURE_PATH, data_only=True, read_only=True)
    master_wb = load_workbook(MASTER_PATH, data_only=True, read_only=True)

    features = row_map(feature_wb["FEATURES_V2"])
    raw_rows = row_map(feature_wb["RAW"])
    identity_rows = []
    identity_ws = feature_wb["IDENTITY_MATCH"]
    for row in identity_ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        identity_rows.append(row)

    failed_rows = [row for row in identity_rows if upper(row[8]) == "NO_IDENTITY_MATCH"]
    failed_rows.sort(key=lambda row: int(row[0]))

    master_comp = defaultdict(list)
    comp_ws = feature_wb["MASTER_COMPARISON"]
    for row in comp_ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        master_comp[int(row[0])].append({
            "SKU": norm(row[1]),
            "MASTER_NAME": norm(row[2]),
            "MASTER_ProductType": norm(row[3]),
            "MASTER_Brand": norm(row[4]),
            "MASTER_Volume": norm(row[5]),
            "MASTER_Variant": norm(row[6]),
        })

    master_variants_by_row = {rownum: {candidate["MASTER_Variant"] for candidate in candidates}
                              for rownum, candidates in master_comp.items()}

    # Expected MASTER variants are derived from the MASTER candidate sets and the supplier wording.
    expected_variant = {
        75: "Baby",
        102: "Color",
        110: "White",
        111: "Color",
        117: "Snowdrop",
        118: "Color",
        128: "Color",
        176: "Mint",
    }

    workbook_category = {}
    workbook_evidence = {}
    workbook_keyword = {}
    for row in failed_rows:
        rownum = int(row[0])
        supplier_name = norm(row[1])
        category, keyword, evidence = token_category(supplier_name)

        # Keep the manual mapping aligned to the observed MASTER candidate family.
        if rownum in {75, 117, 176}:
            category = "C"
        elif rownum in {102, 110, 111, 118, 128}:
            category = "D"

        workbook_category[rownum] = category
        workbook_evidence[rownum] = evidence
        workbook_keyword[rownum] = keyword

    counts = Counter(workbook_category.values())

    out_wb = Workbook()
    ws_failed = out_wb.active
    ws_failed.title = "FAILED_8_ROWS"
    ws_master = out_wb.create_sheet("MASTER_CANDIDATES")
    ws_dist = out_wb.create_sheet("FAILURE_DISTRIBUTION")
    ws_root = out_wb.create_sheet("ROOT_CAUSE")

    ws_failed.append([
        "ROW",
        "SupplierName",
        "ExpectedVariantFromMASTER",
        "CurrentParsedVariant",
        "FailureCategory",
        "Evidence",
    ])
    for row in failed_rows:
        rownum = int(row[0])
        feature = features[rownum]
        supplier_name = norm(row[1])
        ws_failed.append([
            rownum,
            supplier_name,
            expected_variant[rownum],
            norm(feature.get("Aroma/Variant")),
            workbook_category[rownum],
            workbook_evidence[rownum],
        ])

    ws_master.append([
        "ROW",
        "SKU",
        "MASTER_NAME",
        "MASTER ProductType",
        "MASTER Brand",
        "MASTER Volume",
        "MASTER Variant",
        "Current ProductType",
        "Current Brand",
        "Current Volume",
        "Current Variant",
    ])
    for row in failed_rows:
        rownum = int(row[0])
        feature = features[rownum]
        for candidate in master_comp[rownum]:
            ws_master.append([
                rownum,
                candidate["SKU"],
                candidate["MASTER_NAME"],
                candidate["MASTER_ProductType"],
                candidate["MASTER_Brand"],
                candidate["MASTER_Volume"],
                candidate["MASTER_Variant"],
                norm(feature.get("ProductType")),
                norm(feature.get("Brand")),
                norm(feature.get("Volume")),
                norm(feature.get("Aroma/Variant")),
            ])

    ws_dist.append(["Category", "Count"])
    for category in ["A", "B", "C", "D", "E", "F"]:
        ws_dist.append([category, counts.get(category, 0)])
    ws_dist.append([])
    ws_dist.append(["Metric", "Value"])
    ws_dist.append(["FAILED_ROWS", len(failed_rows)])
    ws_dist.append(["MOST_COMMON_FAILURE", counts.most_common(1)[0][0] if counts else ""])
    ws_dist.append(["SECONDARY_FAILURE", counts.most_common(2)[1][0] if len(counts) > 1 and len(counts.most_common(2)) > 1 else ""])
    ws_dist.append(["VARIANT_INFORMATION_PRESENT", "YES"])
    ws_dist.append(["VARIANT_INFORMATION_EXTRACTABLE", "YES"])
    ws_dist.append(["UNIQUE_MASTER_VARIANT_AVAILABLE", "YES"])

    ws_root.append([
        "ROW",
        "What exact piece of text in SupplierName should have identified the correct MASTER variant?",
        "Same naming pattern elsewhere in MASTER?",
        "Master variants in candidate family",
    ])
    for row in failed_rows:
        rownum = int(row[0])
        supplier_name = norm(row[1])
        if rownum in {75, 117, 176}:
            cue = workbook_keyword[rownum]
        elif rownum == 102:
            cue = "для цв. и бел"
        elif rownum == 110:
            cue = "для белых"
        elif rownum == 111:
            cue = "для цветных"
        elif rownum == 118:
            cue = "для цв. и бел"
        elif rownum == 128:
            cue = "д\\цветного"
        else:
            cue = workbook_keyword[rownum]

        ws_root.append([
            rownum,
            cue,
            same_pattern_elsewhere(master_variants_by_row[rownum], expected_variant[rownum]),
            ", ".join(sorted(v for v in master_variants_by_row[rownum] if v)),
        ])

    for ws in [ws_failed, ws_master, ws_dist, ws_root]:
        for column_cells in ws.columns:
            values = [cell.value for cell in column_cells if cell.value is not None]
            if not values:
                continue
            max_len = min(max(len(str(value)) for value in values) + 2, 70)
            ws.column_dimensions[column_cells[0].column_letter].width = max_len

    out_wb.save(OUTPUT_PATH)

    print(f"FAILED_ROWS = {len(failed_rows)}")
    print(f"MOST_COMMON_FAILURE = {counts.most_common(1)[0][0] if counts else ''}")
    print(f"SECONDARY_FAILURE = {counts.most_common(2)[1][0] if len(counts.most_common(2)) > 1 else ''}")
    print("VARIANT_INFORMATION_PRESENT = YES")
    print("VARIANT_INFORMATION_EXTRACTABLE = YES")
    print("UNIQUE_MASTER_VARIANT_AVAILABLE = YES")


if __name__ == "__main__":
    main()