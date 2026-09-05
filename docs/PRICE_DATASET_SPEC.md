# PRICE Dataset Specification

## 1. Purpose
Define the canonical PriceDataset contract produced by PriceLoader and consumed by Finance Layer.

Finance consumes only datasets:
- InventoryDataset
- PriceDataset

Finance does not parse PRICE.xlsx directly.

## 2. Source Ownership

Source file:
- PRICE.xlsx

Business owner:
- Commercial / Finance operations

Technical owner:
- PriceLoader boundary component

## 3. Canonical Schema

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| sku | string | Yes | non-empty, trimmed, case-normalized | Join key with InventoryDataset |
| unit_cost | decimal | Yes | >= 0 | Procurement or internal cost per unit |
| retail_price | decimal | Yes | >= 0 | End-customer retail price |
| wholesale_price | decimal | Yes | >= 0 | Wholesale channel price |
| marketplace_price | decimal | Yes | >= 0 | Marketplace listing price |
| effective_from | date | Yes | valid date | Start date of price validity |
| effective_to | date nullable | No | null or >= effective_from | End date of validity |
| status | enum | Yes | Active, Inactive, Draft, Archived | Price lifecycle state |

Optional extension fields:
- price_list_id
- channel_code
- currency_code
- region_code
- source_row_id
- updated_at

## 4. Ingestion Rules (PriceLoader)

Normalization rules:
- SKU trim and uppercase normalization
- Decimal parsing with invariant numeric format
- Date parsing into canonical date type
- Status normalization to enum values

Validation rules:
- Reject rows with missing SKU
- Reject negative price values
- Reject invalid date intervals
- Reject unknown status values

Quality warnings:
- Duplicate active records for same SKU and date window
- Gaps in effective-date coverage

## 5. Effective-date Semantics

Validity interval:
- Starts at effective_from (inclusive)
- Ends at effective_to (inclusive) when present
- Open-ended when effective_to is null

Default valuation date policy:
- Provided by Finance execution context
- If absent, use report/inventory snapshot date

Tie-break precedence for multiple valid rows:
1. Active status over non-active
2. Latest effective_from
3. Latest source update timestamp (future)

## 6. Join Contract with InventoryDataset

Join key:
- SKU exact match

Expected join result:
- 1 inventory row -> 0 or 1 resolved price row under deterministic resolver

Unmatched SKU handling:
- Keep inventory row
- Attach pricing_status = MissingPrice
- Emit diagnostics for coverage metrics

Ambiguous SKU handling:
- Attach pricing_status = AmbiguousPrice
- Emit diagnostics and optional quality gate violation

## 7. PriceDataset Output Model

PriceDataset is a collection of PriceRecord rows with metadata.

Dataset metadata fields:
- dataset_version
- source_file_name
- source_loaded_at
- row_count
- valid_row_count
- rejected_row_count
- warning_count

PriceRecord example:
- sku: SKU-001
- unit_cost: 35.50
- retail_price: 79.90
- wholesale_price: 58.00
- marketplace_price: 82.00
- effective_from: 2026-07-01
- effective_to: null
- status: Active

## 8. Backward Compatibility

Versioning policy:
- Additive fields are backward compatible
- Renames and type changes require major schema version increment

Required compatibility guarantees:
- Existing required fields remain stable across minor versions
- Status enum changes require migration notes

## 9. Test Requirements

Unit tests:
- Field parsing and validation
- Date-window resolver
- Duplicate and overlap detection

Integration tests:
- InventoryDataset + PriceDataset join coverage
- Missing and ambiguous price scenarios

Regression tests:
- Golden PriceDataset snapshots
- Deterministic normalization output for same PRICE.xlsx input

## 10. Future Extensions

Designed to support:
- price history across overlapping seasons
- multiple price lists by customer segment
- multiple currencies and FX valuation
- multiple channels and channel-specific prices
- discounts and promotions with effective windows
- marketplace-specific commercial terms

## 11. Explicit Boundary Constraints

Must remain true:
- MASTER does not store price fields.
- Price data is sourced from PRICE.xlsx via PriceLoader only.
- Finance consumes PriceDataset and InventoryDataset only.
- Reporting does not own pricing business logic.
