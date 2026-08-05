from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .dataset_builder import DatasetRecord

if TYPE_CHECKING:
    from .models import ArrivalItem
    from .validator import ResultValidationReport


class DatasetAnalytics:
    """Analytics layer operating strictly on in-memory MASTER_DATASET records."""

    def __init__(self, dataset: list[DatasetRecord]):
        self.dataset = list(dataset)

    def dataset_metrics(self) -> dict:
        master_sku = len(self.dataset)
        arrival_linked = sum(1 for row in self.dataset if row.arrival_quantity > 0)
        sales_linked = sum(1 for row in self.dataset if row.sales_quantity > 0)
        arrival_quantity = sum(row.arrival_quantity for row in self.dataset)
        sales_quantity = sum(row.sales_quantity for row in self.dataset)

        coverage = (sum(1 for row in self.dataset if row.total_movement > 0) / master_sku * 100.0) if master_sku else 0.0
        average_arrival_quantity = (arrival_quantity / arrival_linked) if arrival_linked else 0.0
        average_sales_quantity = (sales_quantity / sales_linked) if sales_linked else 0.0

        return {
            "master_sku": master_sku,
            "arrival_linked": arrival_linked,
            "sales_linked": sales_linked,
            "arrival_quantity": arrival_quantity,
            "sales_quantity": sales_quantity,
            "coverage_pct": coverage,
            "average_arrival_quantity": average_arrival_quantity,
            "average_sales_quantity": average_sales_quantity,
        }

    def integrity_metrics(self) -> dict:
        sku_counter = Counter(row.sku for row in self.dataset)
        duplicate_sku = sum(count - 1 for count in sku_counter.values() if count > 1)

        # A missing master row indicates dataset integrity issue (e.g. blank SKU/master_name).
        missing_master = sum(1 for row in self.dataset if not row.sku.strip() or not row.master_name.strip())

        rows_without_arrival = sum(1 for row in self.dataset if row.arrival_quantity <= 0)
        rows_without_sales = sum(1 for row in self.dataset if row.sales_quantity <= 0)
        rows_without_movement = sum(1 for row in self.dataset if row.total_movement <= 0)

        integrity = "OK" if duplicate_sku == 0 and missing_master == 0 else "FAILED"

        return {
            "duplicate_sku": duplicate_sku,
            "missing_master": missing_master,
            "rows_without_arrival": rows_without_arrival,
            "rows_without_sales": rows_without_sales,
            "rows_without_movement": rows_without_movement,
            "integrity": integrity,
        }

    def summary(self) -> dict:
        metrics = self.dataset_metrics()
        integrity = self.integrity_metrics()
        payload = {}
        payload.update(metrics)
        payload.update(integrity)
        return payload


def format_summary_report(summary: dict) -> str:
    lines = [
        "========================================",
        "SVO ERP CORE",
        "MASTER DATASET SUMMARY",
        "----------------------------------------",
        f"MASTER SKU      : {summary['master_sku']}",
        f"Arrival linked  : {summary['arrival_linked']}",
        f"Sales linked    : {summary['sales_linked']}",
        f"Arrival Qty     : {summary['arrival_quantity']}",
        f"Sales Qty       : {summary['sales_quantity']}",
        f"Coverage        : {summary['coverage_pct']:.2f}%",
        f"Duplicate SKU   : {summary['duplicate_sku']}",
        f"Missing MASTER  : {summary['missing_master']}",
        f"Integrity       : {summary['integrity']}",
        "----------------------------------------",
        "RESULT : SUCCESS" if summary["integrity"] == "OK" else "RESULT : FAILED",
        "========================================",
    ]
    return "\n".join(lines)


def generate_dataset_summary_report(
    dataset: list[DatasetRecord],
    *,
    output_file: str | Path = "output/DATASET_SUMMARY.txt",
    print_report: bool = True,
) -> dict:
    analytics = DatasetAnalytics(dataset)
    summary = analytics.summary()
    text = format_summary_report(summary)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")

    if print_report:
        print(text)

    return summary


def _review_reason_counts(items: list["ArrivalItem"]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in items:
        if item.status != "REVIEW":
            continue
        if item.review_reasons:
            counts.update(item.review_reasons)
        else:
            counts["NO_REVIEW_REASON"] += 1
    return counts


def _new_master_candidates(items: list["ArrivalItem"]) -> list["ArrivalItem"]:
    return [item for item in items if item.status == "REVIEW"]


def format_match_analytics_report(
    *,
    report_date: str | None,
    source_file: str | Path | None,
    total_rows: int,
    match_count: int,
    review_count: int,
    validation_report: "ResultValidationReport",
    items: list["ArrivalItem"],
) -> str:
    resolved_date = report_date or datetime.now().strftime("%d.%m.%Y")
    source_name = Path(source_file).name if source_file is not None else "<unknown>"
    coverage = (match_count / total_rows * 100.0) if total_rows else 0.0
    review_reason_counts = _review_reason_counts(items)
    new_candidates = _new_master_candidates(items)

    lines = [
        "========================================",
        "MATCH ANALYTICS",
        "----------------------------------------",
        f"DATE              : {resolved_date}",
        f"FILE              : {source_name}",
        f"TOTAL ROWS        : {total_rows}",
        f"MATCH             : {match_count}",
        f"REVIEW            : {review_count}",
        f"COVERAGE          : {coverage:.2f}%",
        "----------------------------------------",
        "REVIEW REASONS",
    ]

    if review_reason_counts:
        for reason, count in review_reason_counts.most_common():
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")

    lines.extend([
        "----------------------------------------",
        "NEW PRODUCTS FOR MASTER",
    ])

    if new_candidates:
        for item in new_candidates:
            reasons = ", ".join(item.review_reasons) if item.review_reasons else "NO_REVIEW_REASON"
            lines.append(f"- ROW {item.row_number}: {item.source_name} [{reasons}]")
    else:
        lines.append("- none")

    lines.extend([
        "----------------------------------------",
        "VALIDATION",
        f"RESULT VALIDATION : {'PASSED' if validation_report.passed else 'FAILED'}",
        f"ISSUES COUNT      : {len(validation_report.issues)}",
        "========================================",
    ])

    return "\n".join(lines)


def generate_match_analytics_report(
    *,
    report_date: str | None,
    source_file: str | Path | None,
    total_rows: int,
    match_count: int,
    review_count: int,
    validation_report: "ResultValidationReport",
    items: list["ArrivalItem"],
    output_file: str | Path = "output/MATCH_ANALYTICS.txt",
) -> str:
    text = format_match_analytics_report(
        report_date=report_date,
        source_file=source_file,
        total_rows=total_rows,
        match_count=match_count,
        review_count=review_count,
        validation_report=validation_report,
        items=items,
    )

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")
    return text
