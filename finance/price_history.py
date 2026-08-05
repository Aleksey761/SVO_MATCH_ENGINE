from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re


_PACKAGE_UNIT_RE = re.compile(r"^\s*упак\s*\(\s*(\d+)\s*шт\s*\)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class PriceHistoryRecord:
    SKU: str
    MASTER_NAME: str
    UnitCost: Decimal
    RetailPrice: Decimal
    ValidFrom: datetime
    ValidTo: datetime | None
    Status: str
    SourceFile: str
    ImportedAt: datetime
    SourceUnit: str | None
    PackQty: int | None
    OriginalPrice: Decimal


@dataclass(frozen=True)
class PriceHistoryChange:
    SKU: str
    MASTER_NAME: str
    PreviousPrice: Decimal
    NewPrice: Decimal
    Difference: Decimal
    ValidFrom: datetime
    SourceFile: str


@dataclass(frozen=True)
class PriceHistoryImportSummary:
    created_records: int
    updated_records: int
    skipped_records: int
    changes: list[PriceHistoryChange]
    events: list[dict[str, object]]
    created: list[PriceHistoryRecord]


class PriceHistory:
    """Append-only in-memory price history with active-version rollover semantics."""

    def __init__(self) -> None:
        self.records: list[PriceHistoryRecord] = []

    @staticmethod
    def _as_decimal(value: Decimal | int | float | str) -> Decimal:
        if isinstance(value, Decimal):
            return value
        text = str(value).strip().replace(" ", "").replace(",", ".")
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid Decimal value: {value}")

    @staticmethod
    def _normalize_sku(value: object) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _normalize_master_name(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def _normalize_source_unit(value: object) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _normalize_imported_at(imported_at: datetime | None) -> datetime:
        if imported_at is None:
            return datetime.now(timezone.utc)
        if imported_at.tzinfo is None:
            return imported_at.replace(tzinfo=timezone.utc)
        return imported_at

    @staticmethod
    def _extract_pack_qty(source_unit: str | None) -> int | None:
        if not source_unit:
            return None
        match = _PACKAGE_UNIT_RE.match(source_unit)
        if match is None:
            return None
        qty = int(match.group(1))
        if qty <= 0:
            return None
        return qty

    def _active_record_for(self, sku: str) -> PriceHistoryRecord | None:
        for record in reversed(self.records):
            if record.SKU == sku and record.Status == "ACTIVE":
                return record
        return None

    def _close_active_record(self, active_record: PriceHistoryRecord, imported_at: datetime) -> None:
        close_at = imported_at - timedelta(seconds=1)
        for index, record in enumerate(self.records):
            if record is not active_record:
                continue
            self.records[index] = PriceHistoryRecord(
                SKU=record.SKU,
                MASTER_NAME=record.MASTER_NAME,
                UnitCost=record.UnitCost,
                RetailPrice=record.RetailPrice,
                ValidFrom=record.ValidFrom,
                ValidTo=close_at,
                Status="CLOSED",
                SourceFile=record.SourceFile,
                ImportedAt=record.ImportedAt,
                SourceUnit=record.SourceUnit,
                PackQty=record.PackQty,
                OriginalPrice=record.OriginalPrice,
            )
            return

    def import_prices(
        self,
        rows: list[dict[str, object]],
        *,
        source_file: str,
        imported_at: datetime | None = None,
    ) -> list[PriceHistoryRecord]:
        """Import canonical rows into history and return newly created ACTIVE records."""
        return self.import_prices_with_summary(
            rows,
            source_file=source_file,
            imported_at=imported_at,
        ).created

    def import_prices_with_summary(
        self,
        rows: list[dict[str, object]],
        *,
        source_file: str,
        imported_at: datetime | None = None,
    ) -> PriceHistoryImportSummary:
        """Import canonical rows into history and return full import summary."""
        timestamp = self._normalize_imported_at(imported_at)
        created: list[PriceHistoryRecord] = []
        skipped = 0
        updated = 0
        changes: list[PriceHistoryChange] = []
        events: list[dict[str, object]] = []

        for row in rows:
            sku = self._normalize_sku(row.get("SKU"))
            master_name = self._normalize_master_name(row.get("MASTER_NAME"))
            if not sku:
                raise ValueError("SKU is required for price history import")

            source_unit = self._normalize_source_unit(row.get("SourceUnit"))
            pack_qty = row.get("PackQty")
            if pack_qty is not None:
                pack_qty = int(pack_qty)
            if pack_qty is None:
                pack_qty = self._extract_pack_qty(source_unit)

            incoming_unit_cost = self._as_decimal(row.get("UnitCost"))
            retail_price = self._as_decimal(row.get("RetailPrice"))

            # Preserve incoming value and normalize per-piece unit cost for package rows.
            original_price_value = row.get("OriginalPrice")
            if original_price_value is not None:
                original_price = self._as_decimal(original_price_value)
            else:
                original_price = incoming_unit_cost
            if pack_qty is not None:
                base_for_conversion = original_price
                incoming_unit_cost = base_for_conversion / Decimal(pack_qty)

            active = self._active_record_for(sku)
            if active is not None and active.UnitCost == incoming_unit_cost:
                skipped += 1
                events.append(
                    {
                        "SKU": sku,
                        "MASTER_NAME": master_name,
                        "PreviousPrice": active.UnitCost,
                        "NewPrice": incoming_unit_cost,
                        "Difference": Decimal("0"),
                        "PercentChange": Decimal("0"),
                        "SourceUnit": source_unit,
                        "PackQty": pack_qty,
                        "OriginalPrice": original_price,
                        "ValidFrom": active.ValidFrom,
                        "ImportedAt": timestamp,
                        "SourceFile": source_file,
                        "Status": "SKIPPED",
                    }
                )
                continue

            previous_price: Decimal | None = None
            if active is not None:
                previous_price = active.UnitCost
                self._close_active_record(active, timestamp)
                updated += 1
                changes.append(
                    PriceHistoryChange(
                        SKU=sku,
                        MASTER_NAME=master_name,
                        PreviousPrice=previous_price,
                        NewPrice=incoming_unit_cost,
                        Difference=incoming_unit_cost - previous_price,
                        ValidFrom=timestamp,
                        SourceFile=source_file,
                    )
                )

            new_record = PriceHistoryRecord(
                SKU=sku,
                MASTER_NAME=master_name,
                UnitCost=incoming_unit_cost,
                RetailPrice=retail_price,
                ValidFrom=timestamp,
                ValidTo=None,
                Status="ACTIVE",
                SourceFile=source_file,
                ImportedAt=timestamp,
                SourceUnit=source_unit,
                PackQty=pack_qty,
                OriginalPrice=original_price,
            )
            self.records.append(new_record)
            created.append(new_record)

            difference = incoming_unit_cost - previous_price if previous_price is not None else None
            percent_change = None
            if previous_price is not None and previous_price != 0:
                percent_change = (difference / previous_price) * Decimal("100")

            events.append(
                {
                    "SKU": sku,
                    "MASTER_NAME": master_name,
                    "PreviousPrice": previous_price,
                    "NewPrice": incoming_unit_cost,
                    "Difference": difference,
                    "PercentChange": percent_change,
                    "SourceUnit": source_unit,
                    "PackQty": pack_qty,
                    "OriginalPrice": original_price,
                    "ValidFrom": new_record.ValidFrom,
                    "ImportedAt": timestamp,
                    "SourceFile": source_file,
                    "Status": "UPDATED" if previous_price is not None else "NEW",
                }
            )

        return PriceHistoryImportSummary(
            created_records=len(created),
            updated_records=updated,
            skipped_records=skipped,
            changes=changes,
            events=events,
            created=created,
        )

    def lookup_unit_cost(self, sku: str, at: datetime) -> Decimal | None:
        target_sku = self._normalize_sku(sku)
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)

        matching = [record for record in self.records if record.SKU == target_sku]
        matching.sort(key=lambda record: record.ValidFrom)

        for record in matching:
            starts_before_or_at = record.ValidFrom <= at
            ends_after_or_open = record.ValidTo is None or at <= record.ValidTo
            if starts_before_or_at and ends_after_or_open:
                return record.UnitCost
        return None
