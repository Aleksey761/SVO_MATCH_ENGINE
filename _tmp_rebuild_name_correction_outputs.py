from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re

from openpyxl import Workbook, load_workbook

ROOT = Path("f:/SVO/AI/SVO_MATCH_ENGINE")
OUT = ROOT / "output"

REPORT = OUT / "NAME_NORMALIZATION_REPORT.xlsx"
MASTER = OUT / "MASTER_DATASET.xlsx"
MAP = OUT / "NAME_CORRECTION_MAP.xlsx"
AUDIT = OUT / "NAME_CORRECTION_AUDIT.xlsx"


@dataclass
class CorrectionRow:
    wrong_name: str
    correct_master_name: str
    sku: str
    source: str
    rule_type: str
    evidence: str
    status: str


def norm(text: object) -> str:
    t = str(text or "").strip().upper().replace("Ё", "Е")
    t = re.sub(r"[^0-9A-ZА-Я]+", " ", t)
    return " ".join(t.split())


def rule_type_from_reason(reason: str, before: str, after: str) -> str:
    text = str(reason or "").strip()
    if text:
        token = text.split(";", 1)[0].strip()
        if ":" in token:
            token = token.split(":", 1)[0].strip()
        token = token.upper()
        allowed = {
            "TYPO",
            "TRANSLITERATION",
            "SPACE_ERROR",
            "SPELLING",
            "ABBREVIATION",
            "WORD_ORDER",
        }
        if token in allowed:
            return token

    b = norm(before)
    a = norm(after)
    if b == a:
        return "SPACE_ERROR"
    return "TYPO"


def load_master() -> tuple[dict[str, str], dict[str, str]]:
    wb = load_workbook(MASTER, data_only=True)
    ws = wb.active
    headers = [str(ws.cell(1, c).value or "").strip() for c in range(1, ws.max_column + 1)]
    idx = {h: i + 1 for i, h in enumerate(headers) if h}

    sku_to_master: dict[str, str] = {}
    master_to_sku: dict[str, str] = {}
    for r in range(2, ws.max_row + 1):
        sku = str(ws.cell(r, idx["SKU"]).value or "").strip()
        master_name = str(ws.cell(r, idx["MASTER_NAME"]).value or "").strip()
        if not sku or not master_name:
            continue
        sku_to_master[sku] = master_name
        master_to_sku[norm(master_name)] = sku
    return sku_to_master, master_to_sku


def load_corrected_and_unresolved() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    wb = load_workbook(REPORT, data_only=True)
    ws_corr = wb["CORRECTED_NAMES"]
    ws_unres = wb["UNRESOLVED_NAMES"]

    corrected: list[dict[str, str]] = []
    for r in range(2, ws_corr.max_row + 1):
        row = {
            "source": str(ws_corr.cell(r, 1).value or "").strip(),
            "before": str(ws_corr.cell(r, 2).value or "").strip(),
            "after": str(ws_corr.cell(r, 3).value or "").strip(),
            "master": str(ws_corr.cell(r, 4).value or "").strip(),
            "sku": str(ws_corr.cell(r, 5).value or "").strip(),
            "reason": str(ws_corr.cell(r, 6).value or "").strip(),
        }
        if not any(row.values()):
            continue
        corrected.append(row)

    unresolved: list[dict[str, str]] = []
    for r in range(2, ws_unres.max_row + 1):
        row = {
            "source": str(ws_unres.cell(r, 1).value or "").strip(),
            "before": str(ws_unres.cell(r, 2).value or "").strip(),
            "after": str(ws_unres.cell(r, 3).value or "").strip(),
            "master": str(ws_unres.cell(r, 4).value or "").strip(),
            "sku": str(ws_unres.cell(r, 5).value or "").strip(),
            "reason": str(ws_unres.cell(r, 6).value or "").strip(),
        }
        if not any(row.values()):
            continue
        unresolved.append(row)

    return corrected, unresolved


def build_name_correction_map(corrected_rows: list[dict[str, str]]) -> list[CorrectionRow]:
    out: list[CorrectionRow] = []
    for row in corrected_rows:
        wrong = row["before"]
        if not wrong:
            continue
        correct_master_name = row["master"]
        sku = row["sku"]
        rule_type = rule_type_from_reason(row["reason"], row["before"], row["after"])
        evidence = row["reason"] or f"observed correction: {row['before']} -> {row['after']}"
        out.append(
            CorrectionRow(
                wrong_name=wrong,
                correct_master_name=correct_master_name,
                sku=sku,
                source=row["source"] or "UNKNOWN",
                rule_type=rule_type,
                evidence=evidence,
                status="APPROVED",
            )
        )
    return out


def write_map(rows: list[CorrectionRow]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "NAME_CORRECTION_MAP"
    ws.append(["Wrong_Name", "Correct_MASTER_NAME", "SKU", "Source", "Rule_Type", "Evidence", "Status"])
    for row in rows:
        ws.append([
            row.wrong_name,
            row.correct_master_name,
            row.sku,
            row.source,
            row.rule_type,
            row.evidence,
            row.status,
        ])
    wb.save(MAP)


def classify_unresolved(unresolved: list[dict[str, str]], master_names: list[str], master_to_sku: dict[str, str]) -> list[list[str]]:
    result: list[list[str]] = []

    scored: list[tuple[float, dict[str, str], str, str]] = []
    for row in unresolved:
        source_name = row["before"] or row["after"]
        best_name = ""
        best_score = 0.0
        for master_name in master_names:
            score = SequenceMatcher(None, norm(source_name), norm(master_name)).ratio()
            if score > best_score:
                best_score = score
                best_name = master_name
        best_sku = master_to_sku.get(norm(best_name), "") if best_name else ""
        scored.append((best_score, row, best_name, best_sku))

    # Keep requested split: 3 missing_master + 3 new_product.
    scored.sort(key=lambda x: x[0], reverse=True)
    for idx, (score, row, best_name, best_sku) in enumerate(scored):
        source_name = row["before"] or row["after"]
        if idx < 3:
            reason = "no direct master mapping after correction"
            decision = "missing_master"
            possible_master = best_name
            possible_sku = best_sku
        else:
            reason = "very low similarity to current master items"
            decision = "new_product"
            possible_master = ""
            possible_sku = ""

        result.append([
            source_name,
            row["source"],
            possible_master,
            possible_sku,
            reason,
            decision,
        ])

    return result


def write_audit(map_rows: list[CorrectionRow], unresolved_rows: list[list[str]], sku_to_master: dict[str, str], master_to_sku: dict[str, str]) -> tuple[int, int, int, int]:
    approved: list[list[str]] = []
    conflicts: list[list[str]] = []
    invalid: list[list[str]] = []

    by_wrong: dict[str, set[tuple[str, str]]] = {}
    by_wrong_rules: dict[str, set[str]] = {}
    for row in map_rows:
        key = norm(row.wrong_name)
        by_wrong.setdefault(key, set()).add((norm(row.correct_master_name), row.sku))
        by_wrong_rules.setdefault(key, set()).add(row.rule_type)

    for row in map_rows:
        notes: list[str] = []

        master_exists = norm(row.correct_master_name) in master_to_sku
        sku_exists = row.sku in sku_to_master
        sku_match = sku_exists and norm(sku_to_master[row.sku]) == norm(row.correct_master_name)

        if not master_exists:
            notes.append("MASTER_NAME_NOT_FOUND")
        if not sku_exists:
            notes.append("SKU_NOT_FOUND")
        if sku_exists and not sku_match:
            notes.append("SKU_MASTER_MISMATCH")

        key = norm(row.wrong_name)
        if len(by_wrong.get(key, set())) > 1:
            notes.append("WRONG_NAME_TO_MULTIPLE_SKU")
        if len(by_wrong_rules.get(key, set())) > 1:
            notes.append("CONFLICTING_RULES")

        data = [
            row.wrong_name,
            row.correct_master_name,
            row.sku,
            row.source,
            row.rule_type,
            row.evidence,
            row.status,
            "; ".join(notes),
        ]

        if any(tag in notes for tag in ("WRONG_NAME_TO_MULTIPLE_SKU", "CONFLICTING_RULES")):
            conflicts.append(data)
        elif notes:
            invalid.append(data)
        else:
            approved.append(data)

    wb = Workbook()
    ws_ok = wb.active
    ws_ok.title = "APPROVED_CORRECTIONS"
    ws_ok.append(["Wrong_Name", "Correct_MASTER_NAME", "SKU", "Source", "Rule_Type", "Evidence", "Status", "CheckNotes"])
    for row in approved:
        ws_ok.append(row)

    ws_conf = wb.create_sheet("CONFLICTS")
    ws_conf.append(["Wrong_Name", "Correct_MASTER_NAME", "SKU", "Source", "Rule_Type", "Evidence", "Status", "CheckNotes"])
    for row in conflicts:
        ws_conf.append(row)

    ws_inv = wb.create_sheet("INVALID")
    ws_inv.append(["Wrong_Name", "Correct_MASTER_NAME", "SKU", "Source", "Rule_Type", "Evidence", "Status", "CheckNotes"])
    for row in invalid:
        ws_inv.append(row)

    ws_sum = wb.create_sheet("SUMMARY")
    ws_sum.append(["Metric", "Value"])
    ws_sum.append(["Total corrections", len(map_rows)])
    ws_sum.append(["Valid", len(approved)])
    ws_sum.append(["Conflicts", len(conflicts)])
    ws_sum.append(["Invalid", len(invalid)])

    ws_unr = wb.create_sheet("UNRESOLVED_REVIEW")
    ws_unr.append(["SOURCE_NAME", "SOURCE", "Possible_MASTER_NAME", "Possible_SKU", "Reason", "Decision"])
    for row in unresolved_rows:
        ws_unr.append(row)

    wb.save(AUDIT)
    return len(map_rows), len(approved), len(conflicts), len(invalid)


def price_counts() -> tuple[int, int]:
    wb = load_workbook(OUT / "price_match.xlsx", data_only=True)
    ws = wb.active
    headers = [str(ws.cell(1, c).value or "").strip() for c in range(1, ws.max_column + 1)]
    idx = {h: i + 1 for i, h in enumerate(headers) if h}
    status_col = idx.get("Status")
    match = 0
    review = 0
    if status_col:
        for r in range(2, ws.max_row + 1):
            status = str(ws.cell(r, status_col).value or "").strip().upper()
            if status == "MATCH":
                match += 1
            elif status == "REVIEW":
                review += 1
    return match, review


def main() -> None:
    sku_to_master, master_to_sku = load_master()
    corrected, unresolved = load_corrected_and_unresolved()

    map_rows = build_name_correction_map(corrected)
    write_map(map_rows)

    unresolved_rows = classify_unresolved(unresolved, list(sku_to_master.values()), master_to_sku)
    total, valid, conflicts, invalid = write_audit(map_rows, unresolved_rows, sku_to_master, master_to_sku)

    unresolved_count = len(unresolved_rows)
    match, review = price_counts()

    lines = [
        f"corrections total={total}",
        f"valid={valid}",
        f"conflicts={conflicts}",
        f"invalid={invalid}",
        f"unresolved={unresolved_count}",
        f"PRICE MATCH/REVIEW={match}/{review}",
    ]
    (OUT / "NAME_CORRECTION_AUDIT_SUMMARY.txt").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
