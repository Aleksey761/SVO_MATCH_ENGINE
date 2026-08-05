from __future__ import annotations

from .master.checks import (
    check_duplicate_business_key,
    check_duplicate_sku,
    check_empty_sku,
)
from .models import AuditLevel, AuditResult
from .report import write_master_audit_reports


def _to_rows(dataframe) -> list[dict]:
    if dataframe is None:
        return []

    if hasattr(dataframe, "to_dict"):
        records = dataframe.to_dict(orient="records")
        rows: list[dict] = []
        for idx, row in enumerate(records, start=2):
            payload = dict(row)
            payload.setdefault("_row_number", idx)
            rows.append(payload)
        return rows

    rows = []
    for idx, row in enumerate(dataframe, start=2):
        payload = dict(row)
        payload.setdefault("_row_number", idx)
        rows.append(payload)
    return rows


def run_quality_gate(*, gate: str = "master", dataframe=None) -> dict:
    gate_name = str(gate or "").strip().lower()
    if gate_name != "master":
        raise ValueError(f"Unsupported quality gate: {gate}")

    rows = _to_rows(dataframe)
    checks = [
        check_duplicate_sku,
        check_empty_sku,
        check_duplicate_business_key,
    ]
    results: list[AuditResult] = [check(rows) for check in checks]

    failed_errors = sum(1 for item in results if item.level == AuditLevel.ERROR and not item.passed)
    failed_warnings = sum(1 for item in results if item.level == AuditLevel.WARNING and not item.passed)

    write_master_audit_reports(results, output_dir="output")

    return {
        "passed": failed_errors == 0,
        "errors": failed_errors,
        "warnings": failed_warnings,
        "results": results,
    }
