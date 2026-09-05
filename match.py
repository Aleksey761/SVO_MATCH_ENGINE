from pathlib import Path

from svo.advisor import generate_improvement_plan
from svo.analytics import generate_match_analytics_report
from svo.duplicate_report import generate_duplicate_sku_report
from svo.engine import Engine
from svo.validator import validate_result


def main():
    base = Path(__file__).parent
    engine = Engine()
    result = engine.run(input_dir=base / "data")
    sales_result = result.get("sales_result")
    summary = sales_result if sales_result is not None else result
    arrival_rows = result.get("arrival_rows", result["rows"])
    sales_rows = result.get("sales_rows", 0)

    print("=" * 40)
    print("SVO Match Engine v0.2")
    print("=" * 40)
    print(f"MASTER FILE : {result['master_file']}")
    print(f"ARRIVAL FILE: {result['arrival_file']}")
    print(f"SALES FILE  : {result['sales_file']}")
    print(f"ARRIVAL DATE: {result['arrival_date']}")
    print(f"SALES DATE  : {result['sales_date']}")
    print(f"MASTER : {summary['master']}")
    print(f"MATCH       : {summary['match']}")
    print(f"REVIEW      : {summary['review']}")
    print(f"OUTPUT      : {result['output']}")
    print(f"ARRIVAL_ROWS: {arrival_rows}")
    print(f"SALES_ROWS  : {sales_rows}")

    validation = validate_result(
        result["output"],
        pipeline_match_count=summary["match"],
        pipeline_review_count=summary["review"],
    )

    print("=" * 40)
    print("RESULT VALIDATION")
    print("=" * 40)
    print(f"MATCH       : {validation.match_count}")
    print(f"REVIEW      : {validation.review_count}")
    print(f"EMPTY SKU   : {validation.empty_sku_count}")
    print(f"EMPTY NAME  : {validation.empty_name_count}")
    print(f"DUP SKU     : {validation.duplicate_sku_count}")

    if validation.passed:
        print("RESULT VALIDATION: PASSED")
    else:
        print("RESULT VALIDATION: FAILED")
        for issue in validation.issues:
            print(f" - {issue}")

    generate_match_analytics_report(
        report_date=result.get("sales_date") or result.get("arrival_date"),
        source_file=result.get("sales_file") or result.get("arrival_file"),
        total_rows=summary["rows"],
        match_count=summary["match"],
        review_count=summary["review"],
        validation_report=validation,
        items=summary.get("items", []),
        output_file=base / "output" / "MATCH_ANALYTICS.txt",
    )

    generate_duplicate_sku_report(
        engine.items,
        output_file=base / "output" / "DUPLICATE_SKU_REPORT.txt",
    )

    generate_improvement_plan(
        total_rows=summary["rows"],
        match_count=summary["match"],
        review_count=summary["review"],
        items=engine.items,
        output_file=base / "output" / "IMPROVEMENT_PLAN.txt",
    )


if __name__ == '__main__':
    main()
