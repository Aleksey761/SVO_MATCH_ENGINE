# Inventory Mapping Compliance Review

Reviewed against [docs/INVENTORY_MAPPING_V1.md](docs/INVENTORY_MAPPING_V1.md).

## Summary
Current implementation is compliant with the documented Inventory Mapping V1 rules in the reviewed reconciliation path.

No implementation differences from the documented business rules were found in:
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py)
- [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py)
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py)

## Passed Checks

### 1. OpeningStockQty
Status: Passed

Expected:
- Source column: `Остаток на складе (шт) на 20.02.2024`
- Meaning: initial stock balance

Implementation:
- Opening header detection requires `ОСТАТОК НА СКЛАДЕ` and `20.02.2024` in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L71)
- Opening column is selected from the same hardcoded baseline in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L161)
- Opening value is read directly and rounded to int in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L184) and [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L199)

Result:
- Matches documented source and calculation.

### 2. SupplierReturnQty
Status: Passed

Expected:
- `SupplierReturnQty = Воронеж + Краснодар 1 + Краснодар 2`

Implementation:
- Initialized in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L190)
- Adds `Воронеж` in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L191)
- Adds `Краснодар 1` in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L192)
- Adds `Краснодар 2` in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L193)
- Stored as `supplier_return` in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L201)

Test coverage:
- Explicit extraction mapping asserted in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L112)
- Aggregated reconciliation output asserted in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L177) and [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L178)

Result:
- Matches documented source columns and formula.

### 3. SalesQty
Status: Passed

Expected:
- `SalesQty = розница`

Implementation:
- Retail column lookup via `РОЗНИЦА` in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L174)
- Sales assigned only from retail column in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L194)
- Stored as `sales` in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L202)

Test coverage:
- Explicit extraction mapping asserted in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L112)
- Reconciliation output values asserted in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L177) and [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L178)

Result:
- Matches documented source and calculation.

### 4. ReceiptQty
Status: Passed

Expected:
- Must remain `0`

Implementation:
- Set to `0` in quantity records in [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L200)

Test coverage:
- Output receipt column remains `0` in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L177) and [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L178)

Result:
- Matches documented current state.

### 5. CalculatedStockQty Formula
Status: Passed

Expected:
- `CalculatedStockQty = OpeningStockQty + ReceiptQty - SupplierReturnQty - SalesQty`

Implementation:
- Formula implemented exactly in [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L46) and [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L52)

Test coverage:
- Direct formula test in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L96)
- Output rows match expected calculated stock in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L177) and [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L178)

Result:
- Matches documented formula exactly.

### 6. VarianceQty Formula
Status: Passed

Expected:
- `VarianceQty = ActualStockQty - CalculatedStockQty`

Implementation:
- Formula implemented exactly in [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L55) and [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L56)

Test coverage:
- Direct variance formula test in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L96)
- Output rows match expected variance in [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L177) and [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L178)

Result:
- Matches documented formula exactly.

## Failed Checks
No failed checks were found.

## Code Locations
Primary implementation locations:
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L71)
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L161)
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L190)
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L194)
- [svo/inventory_input_reader.py](svo/inventory_input_reader.py#L200)
- [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L46)
- [svo/inventory_reconciliation.py](svo/inventory_reconciliation.py#L55)

Primary compliance tests:
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L96)
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L112)
- [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L177)

## Recommended Fixes
No code fixes are required for compliance with Inventory Mapping V1.

Low-priority recommendations:
1. Keep [tests/test_inventory_reconciliation.py](tests/test_inventory_reconciliation.py#L112) as the authoritative extraction-level guard for mapping regressions.
2. If the baseline opening date ever changes, update both the documentation and the hardcoded opening column logic together to preserve compliance.
3. Consider adding a dedicated compliance-oriented test for the exact documented formulas if this mapping is expected to evolve beyond v1.
