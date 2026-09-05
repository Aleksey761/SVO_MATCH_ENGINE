from pathlib import Path

from svo.advisor import format_improvement_plan, generate_improvement_plan
from svo.models import ArrivalItem


def test_format_improvement_plan_groups_reasons_and_forecast():
    items = [
        ArrivalItem(row_number=2, source_name="Known item", status="MATCH"),
        ArrivalItem(
            row_number=3,
            source_name="Unknown brand item",
            status="REVIEW",
            review_reasons=["UNKNOWN_BRAND", "LOW_SCORE"],
        ),
        ArrivalItem(
            row_number=4,
            source_name="No volume item",
            status="REVIEW",
            review_reasons=["NO_VOLUME"],
        ),
    ]

    report = format_improvement_plan(
        total_rows=3,
        match_count=1,
        review_count=2,
        items=items,
    )

    assert "IMPROVEMENT PLAN" in report
    assert "REVIEW            : 2" in report
    assert "REASON            : UNKNOWN_BRAND" in report
    assert "REASON            : NO_VOLUME" in report
    assert "EXPECTED MATCH GAIN: 1" in report
    assert "- ROW 3: Unknown brand item" in report
    assert "- ROW 4: No volume item" in report
    assert "HIGH" in report
    assert "MEDIUM" in report
    assert "PROJECTED MATCH   : 3" in report
    assert "PROJECTED COVERAGE: 100.00%" in report


def test_generate_improvement_plan_writes_file(tmp_path: Path):
    output_file = tmp_path / "IMPROVEMENT_PLAN.txt"
    text = generate_improvement_plan(
        total_rows=1,
        match_count=1,
        review_count=0,
        items=[ArrivalItem(row_number=2, source_name="Known item", status="MATCH")],
        output_file=output_file,
    )

    assert output_file.exists()
    saved = output_file.read_text(encoding="utf-8")
    assert text in saved
    assert "PROJECTED COVERAGE: 100.00%" in saved
