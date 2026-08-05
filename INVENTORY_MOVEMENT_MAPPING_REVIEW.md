# Inventory Movement Source Mapping Review

## 1. Current Mapping

### Scope reviewed
- svo/inventory_input_reader.py
- svo/revision_loader.py
- svo/sales_loader.py
- svo/arrival_loader.py
- svo/dataset_builder.py
- svo/inventory_reconciliation.py
- tests/test_revision_loader.py
- docs/BUSINESS_RULES.md

### Mapping table

| Internal field | Source file | Column name | Current calculation | Business meaning in current implementation | Confidence |
| --- | --- | --- | --- | --- | --- |
| OpeningStockQty | svo/inventory_input_reader.py | `Остаток на складе (шт) на 20.02.2024` | Read directly from the first header containing both `ОСТАТОК НА СКЛАДЕ` and `20.02.2024`, then rounded to int | Opening stock snapshot anchored to a hardcoded baseline date | High |
| ReceiptQty | svo/inventory_input_reader.py | None | Always set to `0` | Receipt is not extracted from any source file yet | High |
| SupplierReturnQty | svo/inventory_input_reader.py | None | Always set to `0` | Supplier return is not extracted from any source file yet | High |
| SalesQty | svo/inventory_input_reader.py | `Воронеж`, `Краснодар 1`, `Краснодар 2`, `розница` | Sum of all four columns, then rounded to int | Total period sales is currently assumed to be the sum of these four columns | Medium |
| ActualStockQty | svo/inventory_input_reader.py | `Остаток на складе (шт)` column chosen by file date | Detect stock columns, choose the one matching the revision file date, then round to int | Actual stock snapshot on or nearest to the revision date | High |
| VarianceQty | svo/inventory_reconciliation.py | None | `ActualStockQty - CalculatedStockQty` | Variance between actual stock snapshot and calculated stock | High |

### Adjacent quantity fields used elsewhere

| Internal field | Source file | Column name | Current calculation | Business meaning in current implementation | Confidence |
| --- | --- | --- | --- | --- | --- |
| OpeningQty | svo/revision_loader.py | First header starting with `ОСТАТОК НА СКЛАДЕ` | Read directly and rounded to int | Opening stock-like field attached to revision rows | Medium |
| ShippedQty | svo/revision_loader.py | `Воронеж`, `Краснодар 1`, `Краснодар 2`, `розница` | `Воронеж + Краснодар 1 + Краснодар 2 - розница` | A derived shipment field, not named sales in code | Low |
| ClosingQty | svo/revision_loader.py | Last matching stock column for revision date | Read directly and rounded to int | Closing stock-like field attached to revision rows | Medium |
| arrival_quantity | svo/dataset_builder.py | Columns 2..11 of `ARRIVAL_MATCH_*.xlsx` rows | Sum numeric values in columns 2 through 10 by positional index | Total quantity inferred from match workbook row structure, not from named movement columns | Low |
| sales_quantity | svo/dataset_builder.py | Columns 2..11 of `SALES_MATCH_*.xlsx` rows | Sum numeric values in columns 2 through 10 by positional index | Total quantity inferred from match workbook row structure, not from named movement columns | Low |

## 2. What each module currently does

### inventory_input_reader.py
- Reads a revision-like inventory workbook with product name, opening stock, regional columns, retail column, and one or more stock snapshot columns.
- Produces per-row quantity dictionaries with:
  - `opening`
  - `receipt = 0`
  - `supplier_return = 0`
  - `sales = Воронеж + Краснодар 1 + Краснодар 2 + розница`
  - `actual`
- This is the only reviewed module that maps directly into the reconciliation business formula.

### revision_loader.py
- Loads the same revision-style workbook into shared ArrivalItem objects.
- Produces:
  - `OpeningQty`
  - `ShippedQty = Воронеж + Краснодар 1 + Краснодар 2 - розница`
  - `ClosingQty`
- This module does not call the reconciliation formulas directly, but it defines a different operational meaning for the same columns.

### sales_loader.py
- Reads only product names from SALES source workbooks.
- Does not extract any quantities or movement columns.

### arrival_loader.py
- Delegates to shared document-row loading.
- Does not extract any quantities or movement columns.

### dataset_builder.py
- Does not read source movement columns by name.
- Instead, it reads already-generated match workbooks and sums positional warehouse columns 2..11.
- That means `arrival_quantity` and `sales_quantity` are derived totals from output workbook shape, not explicit source business columns.

### inventory_reconciliation.py
- Applies formulas only after quantity extraction is already finished.
- Does not determine business meaning of movement columns itself.
- Uses:
  - `CalculatedStockQty = OpeningStockQty + ReceiptQty - SupplierReturnQty - SalesQty`
  - `VarianceQty = ActualStockQty - CalculatedStockQty`

## 3. Special Attention Findings

### 3.1 `Отгружено`
Current implementation status:
- No column named `Отгружено` is read in any reviewed module.
- No grep hit for `Отгружено` or `ОТГРУЖЕНО` was found in the reviewed code path.

Conclusion:
- The current implementation does not map `Отгружено` at all.
- There is no code evidence in scope that classifies it as supplier return, warehouse shipment, sales shipment, or another operation.

Confidence: High on absence, none on business meaning.

### 3.2 `розница`
Current implementation:
- In svo/inventory_input_reader.py it is added into `sales_qty` together with `Воронеж`, `Краснодар 1`, and `Краснодар 2`.
- In svo/revision_loader.py it is subtracted from `ShippedQty`.

Conclusion:
- In one module it behaves like one sales channel included in total sales.
- In another module it behaves like a quantity that reduces shipments.
- The code does not explain whether `розница` is retail sales only, total sales, or a balancing adjustment.

Confidence: High on implementation, low on business meaning.

### 3.3 `Воронеж / Краснодар 1 / Краснодар 2`
Current implementation:
- In svo/inventory_input_reader.py all three are added into `SalesQty`.
- In svo/revision_loader.py all three are added into `ShippedQty`.
- docs/BUSINESS_RULES.md explicitly states that current SalesQty is calculated as the sum of `Воронеж`, `Краснодар 1`, `Краснодар 2`, and `розница`.

Conclusion:
- The current code treats them as outbound movement contributing to depletion.
- The code does not prove whether they are supplier returns, warehouse transfers, customer shipments, or sales channels.
- Their meaning is operation-like in one module and geography/channel-like in naming.

Confidence: Medium on business interpretation, high on current calculation.

## 4. Ambiguities and Inconsistencies

1. The same source columns have different meanings in different modules.
- inventory_input_reader.py:
  - `Воронеж + Краснодар 1 + Краснодар 2 + розница` -> `SalesQty`
- revision_loader.py:
  - `Воронеж + Краснодар 1 + Краснодар 2 - розница` -> `ShippedQty`

2. `SalesQty` is not sourced from a sales document in the reviewed reconciliation path.
- It is derived from revision/inventory workbook regional columns, not from sales_loader.py.

3. `ReceiptQty` and `SupplierReturnQty` exist in the formula but have no source mapping.
- They are always zero.
- This means the formula is structurally broader than the actual extracted data.

4. Opening stock baseline is date-hardcoded.
- `20.02.2024` is embedded in inventory_input_reader.py as the opening stock anchor.
- That is a business assumption encoded as a header match.

5. dataset_builder.py uses positional columns instead of named business columns.
- `arrival_quantity` and `sales_quantity` are totals from columns 2..11 of match workbooks.
- Their business meaning depends on workbook layout rather than explicit source semantics.

6. `ShippedQty` is not part of the reconciliation target model but may be informally interpreted as sales.
- That is unsafe because the implementation subtracts `розница` from it.

## 5. Business Risks

1. Financial calculations may classify the same movement differently depending on which module is used.
- The strongest example is `розница` being additive in one place and subtractive in another.

2. Regional columns may be channel totals, warehouse transfers, or dispatches, but they are currently treated as sales depletion without proof in code.

3. Receipt and supplier return are absent from extraction.
- Any financial stock calculation built on current data will understate movement types and overfit to the simplified formula.

4. Dataset quantities are currently shape-driven.
- Because dataset_builder.py sums positional output columns, downstream analytics may inherit workbook-layout assumptions instead of source-truth movement semantics.

## 6. Recommended Target Model

Target model for later clarification, not implementation:

### Source movement types should be explicit
- Opening Balance
- Receipt from Supplier
- Supplier Return
- Inter-warehouse Transfer Out
- Inter-warehouse Transfer In
- Retail Sale
- Wholesale Sale / Shipment
- Inventory Count Snapshot
- Adjustment

### Recommended canonical fields
- movement_date
- sku
- source_document
- source_row
- operation_type
- quantity
- location_or_channel
- snapshot_flag

### Mapping goal
Each source column should map to exactly one explicit operation type or snapshot role.
Examples:
- `Остаток на складе ...` -> snapshot fields
- `розница` -> either retail sales or another documented operation
- `Воронеж / Краснодар 1 / Краснодар 2` -> either sales channels, warehouse transfers, or shipment destinations

## 7. Fields Requiring Clarification

1. `розница`
- Is it retail sales only?
- Is it already included in other regional columns?
- Why is it subtracted in revision_loader.py but added in inventory_input_reader.py?

2. `Воронеж`, `Краснодар 1`, `Краснодар 2`
- Are these stores, warehouses, dispatch destinations, or sales channels?
- Do they represent stock leaving the main warehouse, customer sales, or internal transfers?

3. `Отгружено`
- If this exists in real source files outside the reviewed tests, where should it map?
- Is it a shipment to customer, shipment to branch, or return to supplier?

4. `Остаток на складе (шт) на 20.02.2024`
- Is this always the correct opening balance date for all periods?
- If not, opening stock extraction is period-sensitive but hardcoded.

5. `arrival_quantity` and `sales_quantity` in MASTER_DATASET
- Are they intended to reflect quantities from source operational documents or totals from matched report rows?

## 8. Things NOT to Change Yet

1. Do not rename movement fields yet.
2. Do not change the stock reconciliation formula yet.
3. Do not reinterpret `розница` or regional columns without business confirmation.
4. Do not convert `ShippedQty` into `SalesQty` by assumption.
5. Do not treat missing ReceiptQty or SupplierReturnQty as implementation bugs until source documents and intended business mapping are confirmed.

## 9. Bottom Line

Current code supports a simplified stock model, but it does not yet establish a stable business meaning for every movement type.

What is clear:
- Opening stock and actual stock are snapshot fields.
- Receipt and supplier return are not sourced yet.
- Reconciliation currently treats `Воронеж + Краснодар 1 + Краснодар 2 + розница` as sales.

What is not clear:
- Whether those regional columns and `розница` are truly sales, shipments, transfers, or mixed operations.
- Whether `ShippedQty` in revision_loader.py represents the same business event family as `SalesQty` in reconciliation.
