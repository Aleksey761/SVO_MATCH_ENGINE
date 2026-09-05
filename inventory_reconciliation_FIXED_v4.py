from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .inventory_input_reader import InventoryInputReader
from .loader import Loader
from .report_builder import ReportBuilder


@dataclass
class StockBusinessRow:
    sku: str
    master_name: str
    opening_stock_qty: int
    receipt_qty: int
    supplier_return_qty: int
    sales_qty: int
    calculated_stock_qty: int
    actual_stock_qty: int
    variance_qty: int


class InventoryReconciliation:
    """Builds stock reconciliation using existing RESULT and inventory source workbooks."""

    STOCK_HEADERS_RU = [
        "SKU",
        "Наименование",
        "Начальный остаток",
        "Приход",
        "Возврат поставщику",
        "Продажи",
        "Расчетный остаток",
        "Фактический остаток",
        "Расхождение",
    ]

    def __init__(self) -> None:
        self.loader = Loader()
        self.input_reader = InventoryInputReader()
        self.report_builder = ReportBuilder()

    @staticmethod
    def _calculate_stock_qty(
        opening_stock_qty: int,
        receipt_qty: int,
        supplier_return_qty: int,
        sales_qty: int,
    ) -> int:
        return opening_stock_qty + receipt_qty - supplier_return_qty - sales_qty

    @staticmethod
    def _calculate_variance_qty(actual_stock_qty: int, calculated_stock_qty: int) -> int:
        return actual_stock_qty - calculated_stock_qty

    @staticmethod
    def _parse_date_from_filename(filename: str | Path) -> str | None:
        stem = Path(filename).stem
        match = re.search(r"(?<!\d)(\d{2})\.(\d{2})\.(\d{2}|\d{4})(?!\d)", stem)
        if not match:
            return None
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"

    def _build_rows(
        self,
        result_rows: list[dict[str, str]],
        quantities: list[dict[str, object]],
        master_name_by_sku: dict[str, str],
        master_sku_by_name: dict[str, str],
    ) -> tuple[list[StockBusinessRow], list[StockBusinessRow], int, dict[str, int]]:
        stock_by_sku: dict[str, StockBusinessRow] = {}
        unmatched_rows = 0
        diagnostics = {
            "missing_inventory_sku": 0,
            "inventory_without_result_sku": 0,
            "duplicate_result_sku": 0,
            "duplicate_inventory_sku": 0,
            "ambiguous_inventory_source": 0,
        }

        def normalized_source(value: object) -> str:
            return " ".join(str(value or "").strip().upper().split())

        source_to_skus: dict[str, set[str]] = {}
        match_rows_by_sku: dict[str, dict[str, str]] = {}

        for result_row in result_rows:
            sku = str(result_row.get("sku", "")).strip()
            status = str(result_row.get("status", "")).strip().upper()
            if status != "MATCH" or not sku:
                unmatched_rows += 1
                continue

            if sku in match_rows_by_sku:
                diagnostics["duplicate_result_sku"] += 1
            else:
                match_rows_by_sku[sku] = result_row

            source_key = normalized_source(result_row.get("source_name", ""))
            if source_key:
                sku_set = source_to_skus.setdefault(source_key, set())
                sku_set.add(sku)

        inventory_by_sku: dict[str, dict[str, int]] = {}
        for quantity in quantities:
            explicit_sku = str(quantity.get("sku", "")).strip()
            if explicit_sku:
                if explicit_sku not in match_rows_by_sku:
                    diagnostics["inventory_without_result_sku"] += 1
                    continue
                sku = explicit_sku
            else:
                source_key = normalized_source(quantity.get("source_name", ""))
                candidate_skus = source_to_skus.get(source_key)

                # FIXED_v4: fallback through MASTER name index
                if not candidate_skus and source_key in master_sku_by_name:
                    candidate_skus = {master_sku_by_name[source_key]}

                if not source_key or not candidate_skus:
                    diagnostics["inventory_without_result_sku"] += 1
                    continue
                if len(candidate_skus) > 1:
                    diagnostics["ambiguous_inventory_source"] += 1
                    continue

                sku = next(iter(candidate_skus))
            row_qty = {
                "opening": int(quantity.get("opening", 0)),
                "receipt": int(quantity.get("receipt", 0)),
                "supplier_return": int(quantity.get("supplier_return", 0)),
                "sales": int(quantity.get("sales", 0)),
                "actual": int(quantity.get("actual", 0)),
            }

            existing = inventory_by_sku.get(sku)
            if existing is None:
                inventory_by_sku[sku] = row_qty
            else:
                diagnostics["duplicate_inventory_sku"] += 1
                existing["opening"] += row_qty["opening"]
                existing["receipt"] += row_qty["receipt"]
                existing["supplier_return"] += row_qty["supplier_return"]
                existing["sales"] += row_qty["sales"]
                existing["actual"] += row_qty["actual"]

        for sku, result_row in match_rows_by_sku.items():
            row_qty = inventory_by_sku.get(sku)
            if row_qty is None:
                diagnostics["missing_inventory_sku"] += 1
                print(f"WARNING: Inventory quantities not found for MATCH SKU '{sku}'. Using zero quantities.")
                row_qty = {
                    "opening": 0,
                    "receipt": 0,
                    "supplier_return": 0,
                    "sales": 0,
                    "actual": 0,
                }

            opening = int(row_qty.get("opening", 0))
            receipt = int(row_qty.get("receipt", 0))
            supplier_return = int(row_qty.get("supplier_return", 0))
            sales = int(row_qty.get("sales", 0))
            actual = int(row_qty.get("actual", 0))
            calculated = self._calculate_stock_qty(opening, receipt, supplier_return, sales)
            variance = self._calculate_variance_qty(actual, calculated)

            resolved_master_name = (
                master_name_by_sku.get(sku)
                or str(result_row.get("master_name", "")).strip()
            )

            stock_by_sku[sku] = StockBusinessRow(
                sku=sku,
                master_name=resolved_master_name,
                opening_stock_qty=opening,
                receipt_qty=receipt,
                supplier_return_qty=supplier_return,
                sales_qty=sales,
                calculated_stock_qty=calculated,
                actual_stock_qty=actual,
                variance_qty=variance,
            )

        stock_rows = [stock_by_sku[key] for key in sorted(stock_by_sku)]
        variance_rows = [row for row in stock_rows if row.variance_qty != 0]
        variance_rows.sort(key=lambda row: abs(row.variance_qty), reverse=True)
        return stock_rows, variance_rows, unmatched_rows, diagnostics

    @staticmethod
    def _rows_from_business(records: list[StockBusinessRow]) -> list[list[object]]:
        rows: list[list[object]] = []
        for record in records:
            rows.append(
                [
                    record.sku,
                    record.master_name,
                    record.opening_stock_qty,
                    record.receipt_qty,
                    record.supplier_return_qty,
                    record.sales_qty,
                    record.calculated_stock_qty,
                    record.actual_stock_qty,
                    record.variance_qty,
                ]
            )
        return rows

    def build(
        self,
        *,
        master_file: str | Path,
        result_file: str | Path,
        inventory_file: str | Path,
        output_file: str | Path | None = None,
    ) -> dict:
        master_file = Path(master_file)
        result_file = Path(result_file)
        inventory_file = Path(inventory_file)
        revision_date = self._parse_date_from_filename(result_file.name)

        if output_file is None:
            output_name = f"STOCK_RECONCILIATION_{revision_date}.xlsx" if revision_date else "STOCK_RECONCILIATION.xlsx"
            output_file = Path("output") / output_name

        master_name_by_sku: dict[str, str] = {}
        master_sku_by_name: dict[str, str] = {}
        for master_item in self.loader.load_master(master_file):
            sku = str(master_item.sku or "").strip()
            if not sku:
                continue
            name = str(master_item.master_name or "").strip() or (
                f"{master_item.category} {master_item.brand} {master_item.variant} {master_item.volume}".strip()
            )
            master_name_by_sku[sku] = name
            master_sku_by_name[" ".join(name.upper().split())] = sku

        result_rows = self.input_reader.read_result_rows(result_file)
        quantities = self.input_reader.read_inventory_quantities(inventory_file)
        stock_business_rows, variance_business_rows, unmatched_rows, diagnostics = self._build_rows(
            result_rows,
            quantities,
            master_name_by_sku,
            master_sku_by_name,
        )

        stock_rows = self._rows_from_business(stock_business_rows)
        variance_rows = self._rows_from_business(variance_business_rows)

        self.report_builder.build_inventory_reconciliation_workbook(
            output_file=output_file,
            headers=self.STOCK_HEADERS_RU,
            stock_rows=stock_rows,
            variance_rows=variance_rows,
            variance_col=9,
            numeric_start_col=3,
            numeric_end_col=9,
        )

        return {
            "output": str(Path(output_file)),
            "master_file": str(master_file),
            "result_file": str(result_file),
            "inventory_file": str(inventory_file),
            "matched_rows": len(stock_rows),
            "variance_rows": len(variance_rows),
            "unmatched_rows": unmatched_rows,
            "missing_inventory_sku": diagnostics["missing_inventory_sku"],
            "inventory_without_result_sku": diagnostics["inventory_without_result_sku"],
            "duplicate_result_sku": diagnostics["duplicate_result_sku"],
            "duplicate_inventory_sku": diagnostics["duplicate_inventory_sku"],
            "ambiguous_inventory_source": diagnostics["ambiguous_inventory_source"],
        }


def build_inventory_reconciliation(
    *,
    master_file: str | Path,
    result_file: str | Path,
    inventory_file: str | Path,
    output_file: str | Path | None = None,
) -> dict:
    return InventoryReconciliation().build(
        master_file=master_file,
        result_file=result_file,
        inventory_file=inventory_file,
        output_file=output_file,
    )
