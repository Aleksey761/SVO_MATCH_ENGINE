from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ArrivalItem


@dataclass(frozen=True)
class DuplicateSkuGroup:
    sku: str
    master_name: str
    rows: list[tuple[int, str]]


def build_duplicate_sku_groups(items: list["ArrivalItem"]) -> list[DuplicateSkuGroup]:
    grouped_rows: dict[str, list[tuple[int, str]]] = defaultdict(list)
    grouped_names: dict[str, str] = {}

    for item in items:
        if item.status != "MATCH":
            continue
        sku = str(item.sku or "").strip()
        if not sku:
            continue
        grouped_rows[sku].append((item.row_number, item.source_name))
        if sku not in grouped_names:
            grouped_names[sku] = str(item.master_name or "").strip()

    groups: list[DuplicateSkuGroup] = []
    for sku, rows in grouped_rows.items():
        if len(rows) <= 1:
            continue
        groups.append(
            DuplicateSkuGroup(
                sku=sku,
                master_name=grouped_names.get(sku, ""),
                rows=sorted(rows, key=lambda value: value[0]),
            )
        )

    return sorted(groups, key=lambda group: group.sku)


def format_duplicate_sku_report(items: list["ArrivalItem"]) -> str:
    groups = build_duplicate_sku_groups(items)
    total_rows_involved = sum(len(group.rows) for group in groups)

    lines: list[str] = []
    for group in groups:
        lines.extend(
            [
                "==================================================",
                f"SKU: {group.sku}",
                f"MASTER_NAME: {group.master_name}",
                "",
                f"Количество строк: {len(group.rows)}",
                "",
            ]
        )

        for row_number, source_name in group.rows:
            lines.extend(
                [
                    f"ROW {row_number}",
                    "Исходное наименование:",
                    source_name,
                    "",
                ]
            )

        lines.extend(
            [
                "--------------------------------------------------",
                "Комментарий:",
                "Повтор одного SKU.",
                "==================================================",
                "",
            ]
        )

    lines.extend(
        [
            f"TOTAL DUPLICATE SKU GROUPS : {len(groups)}",
            f"TOTAL ROWS INVOLVED        : {total_rows_involved}",
        ]
    )

    return "\n".join(lines)


def generate_duplicate_sku_report(
    items: list["ArrivalItem"],
    *,
    output_file: str | Path = "output/DUPLICATE_SKU_REPORT.txt",
) -> str:
    text = format_duplicate_sku_report(items)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")
    return text
