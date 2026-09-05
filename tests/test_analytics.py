from pathlib import Path

from svo.analytics import (
    DatasetAnalytics,
    format_match_analytics_report,
    format_summary_report,
    generate_dataset_summary_report,
    generate_match_analytics_report,
)
from svo.dataset_builder import DatasetRecord
from svo.models import ArrivalItem
from svo.validator import ResultValidationReport


def _sample_dataset() -> list[DatasetRecord]:
    return [
        DatasetRecord(
            sku="SKU-001",
            master_name="Product A",
            category="C1",
            brand="B1",
            aroma="A1",
            arrival_quantity=10,
            sales_quantity=0,
        ),
        DatasetRecord(
            sku="SKU-002",
            master_name="Product B",
            category="C2",
            brand="B2",
            aroma="A2",
            arrival_quantity=5,
            sales_quantity=2,
        ),
        DatasetRecord(
            sku="SKU-003",
            master_name="Product C",
            category="C3",
            brand="B3",
            aroma="A3",
            arrival_quantity=0,
            sales_quantity=8,
        ),
    ]


def test_analytics_metrics():
    analytics = DatasetAnalytics(_sample_dataset())
    metrics = analytics.dataset_metrics()

    assert metrics["master_sku"] == 3
    assert metrics["arrival_linked"] == 2
    assert metrics["sales_linked"] == 2
    assert metrics["arrival_quantity"] == 15
    assert metrics["sales_quantity"] == 10
    assert round(metrics["coverage_pct"], 2) == 100.00
    assert round(metrics["average_arrival_quantity"], 2) == 7.50
    assert round(metrics["average_sales_quantity"], 2) == 5.00


def test_coverage_partial():
    dataset = [
        DatasetRecord("SKU-1", "M1", "C", "B", "A", arrival_quantity=0, sales_quantity=0),
        DatasetRecord("SKU-2", "M2", "C", "B", "A", arrival_quantity=1, sales_quantity=0),
        DatasetRecord("SKU-3", "M3", "C", "B", "A", arrival_quantity=0, sales_quantity=0),
        DatasetRecord("SKU-4", "M4", "C", "B", "A", arrival_quantity=2, sales_quantity=0),
    ]

    metrics = DatasetAnalytics(dataset).dataset_metrics()
    assert round(metrics["coverage_pct"], 2) == 50.00


def test_duplicates_and_missing_master():
    dataset = [
        DatasetRecord("SKU-1", "M1", "C", "B", "A", arrival_quantity=1, sales_quantity=0),
        DatasetRecord("SKU-1", "M1 DUP", "C", "B", "A", arrival_quantity=0, sales_quantity=0),
        DatasetRecord("", "", "C", "B", "A", arrival_quantity=0, sales_quantity=0),
    ]

    integrity = DatasetAnalytics(dataset).integrity_metrics()

    assert integrity["duplicate_sku"] == 1
    assert integrity["missing_master"] == 1
    assert integrity["rows_without_arrival"] == 2
    assert integrity["rows_without_sales"] == 3
    assert integrity["rows_without_movement"] == 2
    assert integrity["integrity"] == "FAILED"


def test_empty_dataset():
    analytics = DatasetAnalytics([])
    metrics = analytics.dataset_metrics()
    integrity = analytics.integrity_metrics()

    assert metrics["master_sku"] == 0
    assert metrics["coverage_pct"] == 0.0
    assert metrics["average_arrival_quantity"] == 0.0
    assert metrics["average_sales_quantity"] == 0.0

    assert integrity["duplicate_sku"] == 0
    assert integrity["missing_master"] == 0
    assert integrity["rows_without_movement"] == 0
    assert integrity["integrity"] == "OK"


def test_dataset_summary_output(tmp_path: Path):
    summary_file = tmp_path / "DATASET_SUMMARY.txt"
    summary = generate_dataset_summary_report(
        _sample_dataset(),
        output_file=summary_file,
        print_report=False,
    )

    assert summary_file.exists()
    text = summary_file.read_text(encoding="utf-8")
    assert "SVO ERP CORE" in text
    assert "MASTER DATASET SUMMARY" in text
    assert "RESULT : SUCCESS" in text

    report = format_summary_report(summary)
    assert "Coverage" in report
    assert "Duplicate SKU" in report


def test_match_analytics_report_formatting():
    items = [
        ArrivalItem(row_number=2, source_name="Known product", status="MATCH"),
        ArrivalItem(
            row_number=3,
            source_name="New product",
            status="REVIEW",
            review_reasons=["LOW_SCORE", "UNKNOWN_BRAND"],
        ),
    ]
    validation = ResultValidationReport(
        passed=False,
        match_count=1,
        review_count=1,
        empty_sku_count=0,
        empty_name_count=0,
        duplicate_sku_count=0,
        issues=["Issue 1", "Issue 2"],
    )

    report = format_match_analytics_report(
        report_date="15.07.2026",
        source_file="data/SALES_15.07.2026.xlsx",
        total_rows=2,
        match_count=1,
        review_count=1,
        validation_report=validation,
        items=items,
    )

    assert "MATCH ANALYTICS" in report
    assert "DATE              : 15.07.2026" in report
    assert "FILE              : SALES_15.07.2026.xlsx" in report
    assert "MATCH             : 1" in report
    assert "REVIEW            : 1" in report
    assert "COVERAGE          : 50.00%" in report
    assert "- LOW_SCORE: 1" in report
    assert "- UNKNOWN_BRAND: 1" in report
    assert "- ROW 3: New product [LOW_SCORE, UNKNOWN_BRAND]" in report
    assert "RESULT VALIDATION : FAILED" in report
    assert "ISSUES COUNT      : 2" in report


def test_match_analytics_report_output(tmp_path: Path):
    output_file = tmp_path / "MATCH_ANALYTICS.txt"
    validation = ResultValidationReport(
        passed=True,
        match_count=2,
        review_count=0,
        empty_sku_count=0,
        empty_name_count=0,
        duplicate_sku_count=0,
        issues=[],
    )

    text = generate_match_analytics_report(
        report_date="16.07.2026",
        source_file="data/SALES.xlsx",
        total_rows=2,
        match_count=2,
        review_count=0,
        validation_report=validation,
        items=[ArrivalItem(row_number=2, source_name="Known product", status="MATCH")],
        output_file=output_file,
    )

    assert output_file.exists()
    saved = output_file.read_text(encoding="utf-8")
    assert text in saved
    assert "RESULT VALIDATION : PASSED" in saved
