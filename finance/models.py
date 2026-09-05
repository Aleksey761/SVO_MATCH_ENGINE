from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class PriceRecord:
    sku: str
    unit_cost: Decimal
    retail_price: Decimal
    wholesale_price: Decimal
    marketplace_price: Decimal
    effective_from: date
    effective_to: date | None
    status: str
    source_row: int
    currency_code: str | None = None

    def is_active(self) -> bool:
        return self.status == "Active"

    def is_effective_on(self, valuation_date: date) -> bool:
        if self.effective_from > valuation_date:
            return False
        if self.effective_to is not None and self.effective_to < valuation_date:
            return False
        return True


@dataclass
class PriceDataset:
    records: list[PriceRecord]
    source_file_name: str
    source_loaded_at: datetime
    row_count: int
    valid_row_count: int
    rejected_row_count: int
    warning_count: int
    warnings: list[str] = field(default_factory=list)
    duplicate_active_skus: list[str] = field(default_factory=list)
    pricing_status_by_sku: dict[str, str] = field(default_factory=dict)

    def by_sku(self) -> dict[str, list[PriceRecord]]:
        grouped: dict[str, list[PriceRecord]] = {}
        for record in self.records:
            grouped.setdefault(record.sku, []).append(record)
        return grouped

    def resolve_pricing_status(self, sku: str, valuation_date: date) -> str:
        grouped = self.by_sku()
        records = grouped.get(sku, [])
        if not records:
            return "MissingPrice"

        active_records = [record for record in records if record.is_active()]
        if not active_records:
            return "InactivePrice"

        active_effective = [record for record in active_records if record.is_effective_on(valuation_date)]
        if len(active_effective) > 1:
            return "AmbiguousPrice"
        if len(active_effective) == 1:
            return "OK"

        if all(record.effective_from > valuation_date for record in active_records):
            return "FuturePrice"

        if all(record.effective_to is not None and record.effective_to < valuation_date for record in active_records):
            return "ExpiredPrice"

        return "AmbiguousPrice"


@dataclass(frozen=True)
class FinancialSummary:
    StockValue: Decimal
    ActualStockValue: Decimal
    InventoryDifferenceValue: Decimal
    SupplierReturnValue: Decimal
    Revenue: Decimal
    COGS: Decimal
    GrossProfit: Decimal
    GrossMarginPercent: Decimal
