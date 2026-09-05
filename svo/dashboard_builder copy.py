from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path

from openpyxl import Workbook, load_workbook


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunContext:
    master_dataset_path: Path
    price_match_path: Path
    price_review_path: Path
    price_change_report_path: Path
    business_metrics_path: Path
    match_analytics_path: Path
    master_audit_path: Path
    output_directory: Path
    run_date: str = "N/A"
    run_time: str = "N/A"
    duration: str = "N/A"
    source_master: str = "N/A"
    source_price: str = "N/A"
    version: str = "N/A"
    status: str = "N/A"


class DashboardBuilder:
    """Builds output/DASHBOARD.xlsx from already generated artifacts."""

    def __init__(self, run_context: RunContext) -> None:
        self.run_context = run_context
        self._missing_sources: set[str] = set()
        self._base_dir = Path.cwd()

    def _absolute_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return (self._base_dir / path).resolve()

    @staticmethod
    def _readable_file(path: Path, *, label: str) -> Path | None:
        if path.exists() and path.is_file():
            return path
        logger.warning("Dashboard source file is missing: %s (%s)", label, path)
        return None

    @staticmethod
    def _as_int(value: object) -> int | None:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            text = value.strip()
            if not text or text.upper() == "N/A":
                return None
            try:
                return int(text)
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_text(value: object) -> str:
        return " ".join(str(value or "").strip().upper().split())

    @staticmethod
    def _parse_analytics(text: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "coverage": "N/A",
            "date": "N/A",
            "new_products": 0,
        }
        lines = text.splitlines()

        in_new_products = False
        new_products = 0
        for line in lines:
            normalized = DashboardBuilder._normalize_text(line)
            if normalized.startswith("DATE") and ":" in line:
                payload["date"] = line.split(":", 1)[1].strip() or "N/A"
            elif normalized.startswith("COVERAGE") and ":" in line:
                payload["coverage"] = line.split(":", 1)[1].strip() or "N/A"

            if normalized == "NEW PRODUCTS FOR MASTER":
                in_new_products = True
                continue
            if in_new_products and normalized.startswith("----------------------------------------"):
                in_new_products = False
                continue
            if in_new_products:
                value = line.strip()
                if not value or value.lower() == "- none":
                    continue
                if value.startswith("-"):
                    new_products += 1

        payload["new_products"] = new_products
        return payload

    def _collect_summary(self) -> dict[str, object]:
        summary: dict[str, object] = {
            "MASTER rows": "N/A",
            "PRICE rows": "N/A",
            "Matched": "N/A",
            "Review": "N/A",
            "New products": "N/A",
            "Updated prices": "N/A",
            "Skipped": "N/A",
            "Coverage %": "N/A",
            "Run date": "N/A",
            "Run time": "N/A",
        }

        master_dataset_file = self._readable_file(self._absolute_path(self.run_context.master_dataset_path), label="MASTER_DATASET")
        if master_dataset_file is None:
            self._missing_sources.add("MASTER_DATASET")
        if master_dataset_file is not None:
            wb = load_workbook(filename=master_dataset_file, data_only=True)
            ws = wb.active
            master_rows = 0
            for row in range(2, ws.max_row + 1):
                sku = str(ws.cell(row=row, column=1).value or "").strip()
                if sku:
                    master_rows += 1
            summary["MASTER rows"] = master_rows

        price_match_file = self._readable_file(self._absolute_path(self.run_context.price_match_path), label="PRICE_MATCH")
        if price_match_file is None:
            self._missing_sources.add("PRICE_MATCH")
        if price_match_file is not None:
            wb = load_workbook(filename=price_match_file, data_only=True)
            ws = wb.active
            headers = [self._normalize_text(ws.cell(row=1, column=col).value) for col in range(1, ws.max_column + 1)]
            status_col = headers.index("STATUS") + 1 if "STATUS" in headers else None
            original_name_col = headers.index("ORIGINALPRODUCTNAME") + 1 if "ORIGINALPRODUCTNAME" in headers else None

            price_rows = 0
            matched = 0
            for row in range(2, ws.max_row + 1):
                row_has_data = False
                if original_name_col is not None:
                    row_has_data = bool(str(ws.cell(row=row, column=original_name_col).value or "").strip())
                if not row_has_data:
                    sku = str(ws.cell(row=row, column=1).value or "").strip()
                    row_has_data = bool(sku)
                if not row_has_data:
                    continue
                price_rows += 1
                if status_col is not None:
                    status = self._normalize_text(ws.cell(row=row, column=status_col).value)
                    if status == "MATCH":
                        matched += 1
            summary["PRICE rows"] = price_rows
            summary["Matched"] = matched

        price_review_file = self._readable_file(self._absolute_path(self.run_context.price_review_path), label="PRICE_REVIEW")
        if price_review_file is None:
            self._missing_sources.add("PRICE_REVIEW")
        if price_review_file is not None:
            wb = load_workbook(filename=price_review_file, data_only=True)
            ws = wb.active
            summary["Review"] = max(0, ws.max_row - 1)

        price_change_file = self._readable_file(self._absolute_path(self.run_context.price_change_report_path), label="PRICE_CHANGE_REPORT")
        if price_change_file is None:
            self._missing_sources.add("PRICE_CHANGE_REPORT")
        if price_change_file is not None:
            wb = load_workbook(filename=price_change_file, data_only=True)
            ws = wb.active
            headers = [self._normalize_text(ws.cell(row=1, column=col).value) for col in range(1, ws.max_column + 1)]
            status_col = headers.index("STATUS") + 1 if "STATUS" in headers else None
            updated = 0
            skipped = 0
            has_skipped = False
            if status_col is not None:
                for row in range(2, ws.max_row + 1):
                    status = self._normalize_text(ws.cell(row=row, column=status_col).value)
                    if status == "UPDATED":
                        updated += 1
                    elif status == "SKIPPED":
                        skipped += 1
                        has_skipped = True
            summary["Updated prices"] = updated
            summary["Skipped"] = skipped if has_skipped else "N/A"

        analytics_file = self._readable_file(self._absolute_path(self.run_context.match_analytics_path), label="MATCH_ANALYTICS")
        if analytics_file is None:
            self._missing_sources.add("MATCH_ANALYTICS")
        if analytics_file is not None:
            analytics = self._parse_analytics(analytics_file.read_text(encoding="utf-8"))
            summary["New products"] = analytics.get("new_products", 0)

        price_rows = self._as_int(summary.get("PRICE rows"))
        matched = self._as_int(summary.get("Matched"))
        if price_rows is not None and matched is not None and price_rows > 0:
            summary["Coverage %"] = f"{matched / price_rows * 100.0:.2f} %"
        else:
            summary["Coverage %"] = "N/A"

        run_date = str(self.run_context.run_date or "").strip()
        run_time = str(self.run_context.run_time or "").strip()
        if run_date:
            summary["Run date"] = run_date
        if run_time:
            summary["Run time"] = run_time

        return summary

    def _append_audit_warning(self, reason: str) -> None:
        audit_path = self._absolute_path(self.run_context.master_audit_path)
        payload: dict[str, object]
        if audit_path.exists() and audit_path.is_file():
            try:
                payload = json.loads(audit_path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        else:
            payload = {}

        warnings = payload.get("dashboard_warnings")
        if not isinstance(warnings, list):
            warnings = []
        if reason not in warnings:
            warnings.append(reason)
        payload["dashboard_warnings"] = warnings
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _build_validation_rows(self, summary: dict[str, object]) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        rows.append(("Validation", ""))
        rows.append(("Status 1", "✓ Dashboard created"))

        if self._missing_sources:
            rows.append(("Status 2", "⚠ Sources missing"))
        else:
            rows.append(("Status 2", "✓ Sources loaded"))

        price_rows = self._as_int(summary.get("PRICE rows"))
        matched = self._as_int(summary.get("Matched"))
        review = self._as_int(summary.get("Review"))
        skipped = self._as_int(summary.get("Skipped"))
        skipped_value = 0 if skipped is None else skipped

        mismatch_reason = ""
        if price_rows is not None and matched is not None and review is not None:
            actual = matched + review + skipped_value
            if actual != price_rows:
                mismatch_reason = (
                    "Dashboard metrics mismatch: "
                    f"Matched({matched}) + Review({review}) + Skipped({skipped_value}) != PRICE rows({price_rows})"
                )

        if mismatch_reason:
            logger.warning(mismatch_reason)
            self._append_audit_warning(mismatch_reason)
            rows.append(("Status 3", "⚠ Metrics mismatch"))
        else:
            rows.append(("Status 3", "✓ Metrics verified"))

        return rows

    def _collect_review(self) -> dict[str, int | str]:
        result: dict[str, int | str] = {
            "NO_MATCH": "N/A",
            "MULTIPLE_CANDIDATES": "N/A",
            "PRODUCT_TYPE_MISMATCH": "N/A",
            "MANUAL_REVIEW": "N/A",
        }

        price_review_file = self._readable_file(self._absolute_path(self.run_context.price_review_path), label="PRICE_REVIEW")
        if price_review_file is None:
            return result

        wb = load_workbook(filename=price_review_file, data_only=True)
        ws = wb.active
        headers = [self._normalize_text(ws.cell(row=1, column=col).value) for col in range(1, ws.max_column + 1)]
        reason_col = headers.index("REASON") + 1 if "REASON" in headers else None
        recommendation_col = headers.index("RECOMMENDATION") + 1 if "RECOMMENDATION" in headers else None

        counts = {
            "NO_MATCH": 0,
            "MULTIPLE_CANDIDATES": 0,
            "PRODUCT_TYPE_MISMATCH": 0,
            "MANUAL_REVIEW": 0,
        }

        if reason_col is None:
            logger.warning("Dashboard source is missing REASON column in %s", price_review_file)
            result.update(counts)
            return result

        for row in range(2, ws.max_row + 1):
            reason = self._normalize_text(ws.cell(row=row, column=reason_col).value)
            recommendation = self._normalize_text(ws.cell(row=row, column=recommendation_col).value) if recommendation_col else ""

            if (
                "PRODUCT_TYPE_MISMATCH" in reason
                or "PRODUCT TYPE" in reason
                or "PRODUCTTYPE" in reason
            ):
                counts["PRODUCT_TYPE_MISMATCH"] += 1
            elif "AMBIGUOUS" in reason or "MULTIPLE" in reason:
                counts["MULTIPLE_CANDIDATES"] += 1
            elif "NO MASTER" in reason or "NO_MATCH" in reason:
                counts["NO_MATCH"] += 1
            elif "MANUAL" in reason or "MANUAL" in recommendation:
                counts["MANUAL_REVIEW"] += 1
            else:
                counts["MANUAL_REVIEW"] += 1

        result.update(counts)
        return result

    def _collect_price(self) -> dict[str, int | str]:
        result: dict[str, int | str] = {
            "New prices": "N/A",
            "Updated prices": "N/A",
            "Unchanged prices": "N/A",
        }

        price_change_file = self._readable_file(self._absolute_path(self.run_context.price_change_report_path), label="PRICE_CHANGE_REPORT")
        if price_change_file is None:
            return result

        wb = load_workbook(filename=price_change_file, data_only=True)
        ws = wb.active
        headers = [self._normalize_text(ws.cell(row=1, column=col).value) for col in range(1, ws.max_column + 1)]
        status_col = headers.index("STATUS") + 1 if "STATUS" in headers else None
        if status_col is None:
            logger.warning("Dashboard source is missing STATUS column in %s", price_change_file)
            result.update({"New prices": 0, "Updated prices": 0, "Unchanged prices": 0})
            return result

        new_prices = 0
        updated_prices = 0
        unchanged_prices = 0
        has_skipped = False
        for row in range(2, ws.max_row + 1):
            status = self._normalize_text(ws.cell(row=row, column=status_col).value)
            if status == "NEW":
                new_prices += 1
            elif status == "UPDATED":
                updated_prices += 1
            elif status == "SKIPPED":
                unchanged_prices += 1
                has_skipped = True

        result["New prices"] = new_prices
        result["Updated prices"] = updated_prices
        result["Unchanged prices"] = unchanged_prices if has_skipped else "N/A"
        return result

    def _collect_run(self) -> dict[str, object]:
        result: dict[str, object] = {
            "Source MASTER": "N/A",
            "Source PRICE": "N/A",
            "Version": "N/A",
            "Duration": "N/A",
            "Status": "N/A",
        }

        source_master = str(self.run_context.source_master or "").strip()
        source_price = str(self.run_context.source_price or "").strip()
        version = str(self.run_context.version or "").strip()
        duration = str(self.run_context.duration or "").strip()
        status = str(self.run_context.status or "").strip()

        if source_master:
            result["Source MASTER"] = source_master
        if source_price:
            result["Source PRICE"] = source_price
        if version:
            result["Version"] = version
        if duration:
            result["Duration"] = duration
        if status:
            result["Status"] = status

        return result

    def _debug_sources(self, summary: dict[str, object]) -> None:
        logger.debug("Dashboard sources")
        logger.debug("MASTER rows ........ %s = %s", self.run_context.master_dataset_path.name, summary.get("MASTER rows", "N/A"))
        logger.debug("PRICE rows ......... %s = %s", self.run_context.price_match_path.name, summary.get("PRICE rows", "N/A"))
        logger.debug("Matched ............ %s = %s", self.run_context.price_match_path.name, summary.get("Matched", "N/A"))
        logger.debug("Review ............. %s = %s", self.run_context.price_review_path.name, summary.get("Review", "N/A"))
        logger.debug("Coverage ........... %s = %s", self.run_context.match_analytics_path.name, summary.get("Coverage %", "N/A"))

    @staticmethod
    def _write_key_value_sheet(ws, title: str, data: dict[str, object]) -> None:
        ws.title = title
        ws.append(["Metric", "Value"])
        for key, value in data.items():
            ws.append([key, value])

    def _write_summary_sheet(self, ws, summary: dict[str, object]) -> None:
        ws.title = "Summary"
        ws.append(["Metric", "Value"])
        for key, value in summary.items():
            ws.append([key, value])
        ws.append([None, None])
        for key, value in self._build_validation_rows(summary):
            ws.append([key, value])

    def build(self) -> Path:
        output_directory = self._absolute_path(self.run_context.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        output_file = output_directory / "DASHBOARD.xlsx"
        self._missing_sources.clear()

        summary = self._collect_summary()
        review = self._collect_review()
        price = self._collect_price()
        run = self._collect_run()
        self._debug_sources(summary)

        wb = Workbook()
        ws_summary = wb.active
        self._write_summary_sheet(ws_summary, summary)

        ws_review = wb.create_sheet("Review")
        self._write_key_value_sheet(ws_review, "Review", review)

        ws_price = wb.create_sheet("Price")
        self._write_key_value_sheet(ws_price, "Price", price)

        ws_run = wb.create_sheet("Run")
        self._write_key_value_sheet(ws_run, "Run", run)

        wb.save(output_file)
        return output_file
