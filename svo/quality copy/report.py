from __future__ import annotations

import json
from pathlib import Path

from .models import AuditLevel, AuditResult


def _result_line(result: AuditResult) -> str:
    status = "OK" if result.passed else "FAIL"
    dots = "." * max(1, 30 - len(result.name))
    return f"{result.name} {dots} {status}"


def _details_lines(results: list[AuditResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        if result.passed:
            continue

        lines.append(f"[{result.level.value}] {result.name}")
        lines.append(f"Message: {result.message}")
        for detail in result.details:
            lines.append(f"- {detail}")
        lines.append("")

    if not lines:
        return ["No issues found."]

    if lines[-1] == "":
        lines.pop()
    return lines


def build_master_audit_text(results: list[AuditResult]) -> str:
    failed_error_count = sum(1 for item in results if item.level == AuditLevel.ERROR and not item.passed)
    failed_warning_count = sum(1 for item in results if item.level == AuditLevel.WARNING and not item.passed)
    failed_info_count = sum(1 for item in results if item.level == AuditLevel.INFO and not item.passed)
    passed = failed_error_count == 0

    lines = [
        "================================",
        "",
        "MASTER AUDIT",
        "",
        "================================",
        "",
        f"STATUS : {'PASSED' if passed else 'FAILED'}",
        "",
        f"Errors : {failed_error_count}",
        f"Warnings : {failed_warning_count}",
        f"Info : {failed_info_count}",
        "",
        "--------------------------------",
        "",
    ]

    for result in results:
        lines.append(_result_line(result))

    lines.extend([
        "",
        "--------------------------------",
        "",
        "DETAILS",
        "",
    ])
    lines.extend(_details_lines(results))
    return "\n".join(lines)


def build_master_audit_json(results: list[AuditResult]) -> dict:
    failed_error_count = sum(1 for item in results if item.level == AuditLevel.ERROR and not item.passed)
    failed_warning_count = sum(1 for item in results if item.level == AuditLevel.WARNING and not item.passed)
    failed_info_count = sum(1 for item in results if item.level == AuditLevel.INFO and not item.passed)

    return {
        "gate": "master",
        "status": "PASSED" if failed_error_count == 0 else "FAILED",
        "errors": failed_error_count,
        "warnings": failed_warning_count,
        "info": failed_info_count,
        "results": [result.to_dict() for result in results],
    }


def write_master_audit_reports(
    results: list[AuditResult],
    *,
    output_dir: str | Path = "output",
) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    txt_path = output_path / "MASTER_AUDIT.txt"
    json_path = output_path / "MASTER_AUDIT.json"

    txt_path.write_text(build_master_audit_text(results) + "\n", encoding="utf-8")
    json_payload = build_master_audit_json(results)
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return txt_path, json_path
