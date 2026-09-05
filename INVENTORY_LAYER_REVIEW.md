# Inventory Layer Architecture Review

## 1. Executive Summary
The inventory layer is functional and readable, with a clear stock/variance formula implemented in one place and output formatting separated into a report builder. However, business meaning is spread across loader-like components and reconciliation logic, with hidden row-order dependencies and strong Excel-schema coupling.

Most important risks:
- Source meaning mismatch for SalesQty between revision extraction and inventory extraction.
- ReceiptQty, SupplierReturnQty, and Adjustments are not sourced from input (currently forced to zero).
- Business logic is coupled to Excel headers, fixed dates, and match-file column positions.
- Inventory aggregation relies on positional alignment between two independently parsed datasets.

## 2. Current Architecture
Primary modules in scope:
- Inventory orchestration and formulas: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py)
- Inventory/result Excel readers: [svo/inventory_input_reader.py](svo/inventory_input_reader.py)
- Revision source loader: [svo/revision_loader.py](svo/revision_loader.py)
- Sales source loader: [svo/sales_loader.py](svo/sales_loader.py)
- Arrival loader interface: [svo/arrival_loader.py](svo/arrival_loader.py)
- Dataset consolidation: [svo/dataset_builder.py](svo/dataset_builder.py)
- Dataset access API: [svo/dataset_api.py](svo/dataset_api.py)
- Inventory-adjacent totals: [svo/business_metrics.py](svo/business_metrics.py)
- Inventory output writer/formatter: [svo/report_builder.py](svo/report_builder.py)
- Shared row models: [svo/models.py](svo/models.py)

Pipeline (as implemented):
Source Excel files
-> loader/reader parsing
-> result rows + inventory quantities
-> stock aggregation by SKU
-> variance filtering/sorting
-> STOCK_RESULT + VARIANCE_REPORT workbook

Key entrypoints:
- Reconciliation build: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L162)
- Workbook output: [svo/report_builder.py](svo/report_builder.py#L11)
- Dataset build/load: [svo/dataset_builder.py](svo/dataset_builder.py#L170), [svo/dataset_builder.py](svo/dataset_builder.py#L328)

## 3. Business Model Review
Target model:
OpeningStockQty + ReceiptQty - SupplierReturnQty - SalesQty +/- Adjustments = CalculatedStockQty
ActualStockQty - CalculatedStockQty = VarianceQty

Implemented formula locations:
- Calculated stock: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L47)
- Variance: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L56)

Where each value comes from today:
- OpeningStockQty: inventory workbook opening stock column detected in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L161)
- SalesQty: sum of regional columns in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L187-L191)
- ActualStockQty: detected actual stock column in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L96) and applied in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L186)
- ReceiptQty: hardcoded zero in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L196)
- SupplierReturnQty: hardcoded zero in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L197)
- Adjustments: not represented in schema/calculation.

Consistency issues:
1. Sales meaning inconsistency:
- Inventory reader adds retail to sales: [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L191)
- Revision loader subtracts retail from shipped quantity: [svo/revision_loader.py](svo/revision_loader.py#L197)

2. Receipt/SupplierReturn absent from source extraction:
- Both are fixed to 0, so model is only partially implemented.

3. Ambiguous naming:
- RevisionLoader uses ShippedQty: [svo/revision_loader.py](svo/revision_loader.py#L207)
- Reconciliation uses SalesQty: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L20)
These appear semantically related but are not explicitly mapped.

4. Header assumptions embed meaning:
- Opening baseline hardcoded to header containing 20.02.2024: [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L71), [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L161)

## 4. Data Flow Review
Detailed flow:
1. Read matched result rows from RESULT workbook: [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L220)
2. Read inventory quantities from revision/inventory workbook: [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L139)
3. Pair rows using zip_longest, compute per-row calculated/variance, aggregate by SKU for MATCH rows: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L76), [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L98)
4. Build stock and variance row arrays: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L139-L141), [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L144)
5. Write STOCK_RESULT and VARIANCE_REPORT: [svo/report_builder.py](svo/report_builder.py#L27), [svo/report_builder.py](svo/report_builder.py#L32)

Duplicated/hidden transformations:
1. Hidden positional dependency:
- Reconciliation pairs result_rows and quantities by list position, not a stable key: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L76)
- Any parser filtering drift can misalign business quantities to SKU.

2. Similar parsing logic duplicated:
- Product/header/date parsing appears in both [svo/revision_loader.py](svo/revision_loader.py) and [svo/inventory_input_reader.py](svo/inventory_input_reader.py).

3. Repeated dataset transformations:
- Match files converted row-by-row into quantity totals in [svo/dataset_builder.py](svo/dataset_builder.py#L273-L299), then re-read from workbook in [svo/dataset_builder.py](svo/dataset_builder.py#L328-L347).

## 5. Responsibility Check
Expected boundaries:
- Loader: read/find source data only.
- Inventory calculator: compute quantities only.
- Report builder: output only.

Findings:
1. Loader responsibility violations (partial):
- [svo/revision_loader.py](svo/revision_loader.py#L188-L199) computes shipped quantity semantics from multiple business columns.
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L187-L198) computes SalesQty and assigns business fields receipt/supplier_return.

2. Inventory calculator boundary is mostly good but mixed orchestration:
- [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L47-L57) has formulas (good).
- Same class also performs I/O orchestration and calls report writer: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L199)

3. ReportBuilder separation is good:
- [svo/report_builder.py](svo/report_builder.py#L11-L41) writes and formats only.
- No inventory formulas found in report builder.

## 6. Excel Dependency Review
Business logic is directly tied to Excel details in multiple places:
1. openpyxl in reader/business-adjacent modules:
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L4)
- [svo/revision_loader.py](svo/revision_loader.py#L4)
- [svo/dataset_builder.py](svo/dataset_builder.py#L6)

2. Worksheet-name and column-shape assumptions:
- Match status and SKU extracted by fixed index offsets: [svo/dataset_builder.py](svo/dataset_builder.py#L67-L82)
- Warehouse totals from fixed columns 2..11: [svo/dataset_builder.py](svo/dataset_builder.py#L49-L64)

3. Header text and hardcoded date dependency:
- 20.02.2024 anchor in inventory opening detection: [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L71), [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L161)

4. Formatting concerns are isolated appropriately:
- Conditional formatting and column widths are contained in [svo/report_builder.py](svo/report_builder.py#L46-L85)

## 7. Inventory Ledger Readiness
Target ledger fields:
Date, SKU, Operation Type, Quantity, Source Document.

Current readiness: Medium-Low.

Why:
- Current model is snapshot/aggregate-oriented (opening, sales, actual) rather than event-oriented ledger.
- Receipt, SupplierReturn, Adjustment operations are not extracted today (fixed to zero).
- Quantities are tied to positional pairing instead of explicit transactional keys.

Estimated required changes:
1. Add explicit inventory domain model(s) for ledger events and stock snapshots.
Likely files: [svo/models.py](svo/models.py), new inventory domain module.

2. Extend readers to emit normalized operations with operation_type/date/source_doc.
Likely files: [svo/inventory_input_reader.py](svo/inventory_input_reader.py), [svo/revision_loader.py](svo/revision_loader.py), [svo/sales_loader.py](svo/sales_loader.py).

3. Rework reconciliation to aggregate from ledger events rather than row-paired lists.
Likely file: [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py).

4. Update reporting to render both ledger and summary outputs.
Likely file: [svo/report_builder.py](svo/report_builder.py).

5. Add coverage for operation-wise correctness and empty/malformed sources.
Likely files: tests inventory suite.

## 8. Performance Findings
1. Repeated workbook scans for header detection and column inference:
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L61-L95)
- [svo/revision_loader.py](svo/revision_loader.py#L42-L77)

2. Repeated row materialization allocations in dataset merge:
- [svo/dataset_builder.py](svo/dataset_builder.py#L277) builds full row lists from worksheet rows.

3. Multiple passes over same in-memory records for summary/validation:
- [svo/dataset_builder.py](svo/dataset_builder.py#L122-L127), [svo/dataset_builder.py](svo/dataset_builder.py#L240-L241)

4. Potential misalignment cost/risk from zip_longest pairing (not just correctness; retries/debug overhead):
- [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L76)

Improvement suggestions (no behavior change requested):
- Normalize to key-based joins (row_number/source_name/SKU) before aggregation.
- Cache parsed column indices per workbook format and reuse.
- Replace row list creation with iter_rows(values_only=True) where possible.
- Consolidate summary metrics in one pass over records.

## 9. Test Review
Inventory-related tests present:
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py)
- [tests/test_revision_loader.py](tests/test_revision_loader.py)
- [tests/test_sales_loader.py](tests/test_sales_loader.py)
- [tests/test_dataset_builder.py](tests/test_dataset_builder.py)
- [tests/test_dataset_api.py](tests/test_dataset_api.py)
- [tests/test_business_metrics.py](tests/test_business_metrics.py)

Coverage against requested checklist:
1. Stock calculation: covered.
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L66)

2. Sales deduction: covered (via stock rows and shipped checks).
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L123-L126)
- [tests/test_revision_loader.py](tests/test_revision_loader.py#L51)

3. Supplier return deduction: not covered (and currently always zero in extraction).

4. Actual vs calculated stock: covered.
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L73-L79)

5. Variance report: covered.
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L100-L136)

6. Empty datasets:
- Business metrics empty dataset covered: [tests/test_business_metrics.py](tests/test_business_metrics.py#L82)
- Inventory reconciliation empty result/inventory dataset not explicitly covered.
- Dataset builder empty/no-match behavior partially implicit, but no dedicated empty-input test.

Additional notable gaps:
- No test for non-zero ReceiptQty/SupplierReturnQty/Adjustments paths.
- No test for row-order mismatch between RESULT and inventory quantities.
- No test for hardcoded opening-date header absence variants.

## 10. Strengths
- Stock and variance formulas are explicit and centralized in one module.
- Report formatting/output concerns are extracted to report builder.
- Dataset API gives a single access point for MASTER_DATASET consumers.
- SKU-based aggregation in reconciliation is straightforward and deterministic.

## 11. Weaknesses
- Business semantics embedded in reader-level modules.
- Hidden positional data dependency via zip_longest pairing.
- Hardcoded date/header assumptions reduce robustness.
- Inconsistent sales/shipped semantics across modules.

## 12. Technical Debt
- Duplicate parsing logic across revision and inventory readers.
- Mixed responsibility in reconciliation orchestrator (compute + integration/writing call path).
- Excel schema coupling (column positions and localized headers) in business-adjacent code.
- Inventory model fields incomplete versus target business equation (no adjustments, no real receipt/returns ingestion).

## 13. Recommended Refactoring (for later, not applied now)
1. Introduce explicit inventory domain schema:
- Snapshot record and ledger event record.

2. Convert row-position pairing to key-based reconciliation join.

3. Move business meaning derivation (sales/shipped/returns/adjustments) into a dedicated inventory-calculation layer; keep readers extraction-focused.

4. Centralize header/date parsing utilities shared by revision and inventory readers.

5. Parameterize opening-balance column selection instead of hardcoding 20.02.2024.

## 14. Things NOT to Change
1. Keep ReportBuilder focused on output and formatting only.
2. Keep formula methods explicit and unit-testable.
3. Keep dataset access through a single API entrypoint.
4. Keep compatibility of existing stock report sheet names unless migration plan is explicit.

## 15. Scores (1-10)
- Architecture: 6
- Business Logic: 5
- Maintainability: 5
- Performance: 6
- Testability: 6
- Extensibility: 5
