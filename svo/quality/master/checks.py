from __future__ import annotations

from collections import defaultdict

from ..models import AuditLevel, AuditResult


def _value(row: dict, key: str) -> str:
    return str(row.get(key) or "").strip()


def _normalize_token(value: str) -> str:
    return " ".join(value.upper().split())


def check_duplicate_sku(rows: list[dict]) -> AuditResult:
    sku_rows: dict[str, list[int]] = defaultdict(list)

    for row in rows:
        row_number = int(row.get("_row_number", 0))
        sku = _normalize_token(_value(row, "SKU"))
        if not sku:
            continue
        sku_rows[sku].append(row_number)

    duplicates = [
        {"sku": sku, "rows": row_numbers, "count": len(row_numbers)}
        for sku, row_numbers in sku_rows.items()
        if len(row_numbers) > 1
    ]

    if duplicates:
        return AuditResult(
            name="Duplicate SKU",
            level=AuditLevel.ERROR,
            passed=False,
            count=len(duplicates),
            message=f"Found {len(duplicates)} duplicate SKU group(s)",
            details=duplicates,
        )

    return AuditResult(
        name="Duplicate SKU",
        level=AuditLevel.ERROR,
        passed=True,
        count=0,
        message="No duplicate SKU found",
        details=[],
    )


def check_empty_sku(rows: list[dict]) -> AuditResult:
    empty_rows: list[dict] = []

    for row in rows:
        row_number = int(row.get("_row_number", 0))
        sku = _value(row, "SKU")
        if sku:
            continue

        empty_rows.append(
            {
                "row": row_number,
                "category": _value(row, "CATEGORY"),
                "brand": _value(row, "BRAND"),
                "variant": _value(row, "VARIANT"),
                "volume": _value(row, "VOLUME"),
            }
        )

    if empty_rows:
        return AuditResult(
            name="Empty SKU",
            level=AuditLevel.ERROR,
            passed=False,
            count=len(empty_rows),
            message=f"Found {len(empty_rows)} row(s) with empty SKU",
            details=empty_rows,
        )

    return AuditResult(
        name="Empty SKU",
        level=AuditLevel.ERROR,
        passed=True,
        count=0,
        message="No empty SKU found",
        details=[],
    )


def check_duplicate_business_key(rows: list[dict]) -> AuditResult:
    business_key_rows: dict[str, list[int]] = defaultdict(list)
    business_key_values: dict[str, dict] = {}

    for row in rows:
        row_number = int(row.get("_row_number", 0))
        category = _normalize_token(_value(row, "CATEGORY"))
        brand = _normalize_token(_value(row, "BRAND"))
        variant = _normalize_token(_value(row, "VARIANT"))
        volume = _normalize_token(_value(row, "VOLUME"))

        if not any((category, brand, variant, volume)):
            continue

        key = "|".join([category, brand, variant, volume])
        business_key_rows[key].append(row_number)
        business_key_values[key] = {
            "category": category,
            "brand": brand,
            "variant": variant,
            "volume": volume,
        }

    duplicates: list[dict] = []
    for key, row_numbers in business_key_rows.items():
        if len(row_numbers) <= 1:
            continue

        key_parts = business_key_values[key]
        duplicates.append(
            {
                "business_key": key,
                "rows": row_numbers,
                "count": len(row_numbers),
                **key_parts,
            }
        )

    if duplicates:
        return AuditResult(
            name="Duplicate Business Key",
            level=AuditLevel.ERROR,
            passed=False,
            count=len(duplicates),
            message=f"Found {len(duplicates)} duplicate business key group(s)",
            details=duplicates,
        )

    return AuditResult(
        name="Duplicate Business Key",
        level=AuditLevel.ERROR,
        passed=True,
        count=0,
        message="No duplicate business key found",
        details=[],
    )
