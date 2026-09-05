# Finance Business Rules

## 1. Scope and Purpose
This document defines immutable business rules for the Finance Layer.

Authoritative dependencies:
- Inventory Mapping V1
- Finance Architecture
- Price Dataset Specification

This document is normative for finance metric definitions and validation behavior.

## 2. Boundary Rules
1. Finance must not read Excel directly.
2. Finance consumes only prepared datasets:
- InventoryDataset
- PriceDataset
3. SKU is the only matching key between inventory and price data.
4. MASTER remains product attributes only and must not contain prices.

## 3. Canonical Input Fields

### InventoryDataset inputs
- sku
- opening_stock_qty
- receipt_qty
- supplier_return_qty
- sales_qty
- calculated_stock_qty
- actual_stock_qty
- variance_qty

### PriceDataset inputs
- sku
- unit_cost
- retail_price
- wholesale_price
- marketplace_price
- effective_from
- effective_to (nullable)
- status
- currency_code (stored only in current version)

## 4. Price Selection Policy
Price selection follows the approved Price Dataset Specification.

Resolver policy for one SKU at valuation time:
1. Candidate rows are filtered by SKU exact match.
2. Status handling:
- Active candidates are preferred.
- Inactive candidates are not used for valuation.
3. Effective-date handling:
- effective_from is inclusive.
- effective_to is inclusive when present.
- effective_to null means open-ended.
4. If multiple Active rows are valid for the same SKU and valuation date:
- mark as AmbiguousPrice.
5. If no valid Active row exists:
- classify into one of MissingPrice, InactivePrice, FuturePrice, ExpiredPrice.

## 5. Diagnostics Statuses
Finance must classify each SKU into one pricing status.

### OK
Definition:
- Exactly one valid Active price record resolved for SKU at valuation date.

### MissingPrice
Definition:
- No price record exists for SKU in PriceDataset.

### AmbiguousPrice
Definition:
- More than one valid Active price record matches SKU and valuation date.

### InactivePrice
Definition:
- Price records exist for SKU, but none are Active.

### FuturePrice
Definition:
- Active price records exist for SKU, but all effective_from dates are after valuation date.

### ExpiredPrice
Definition:
- Active price records exist for SKU, but all validity intervals end before valuation date.

## 6. Rounding and Precision Policy
Official policy:
1. Use Decimal for all monetary calculations.
2. Internal calculations preserve full Decimal precision.
3. Round only at presentation layer.
4. Intermediate metric values must not be rounded.

## 7. Currency Policy
Current version:
1. Single currency only.
2. currency_code may be stored in records for traceability.
3. currency_code is not interpreted for conversion in current version.
4. FX conversion is out of scope.

## 8. Metric Definitions

---

### 8.1 StockValue

Purpose:
- Measure expected inventory value based on calculated stock quantity.

Formula:
- StockValue = CalculatedStockQty x UnitCost

Input fields:
- calculated_stock_qty
- unit_cost

Output:
- Decimal monetary value

Business meaning:
- Value of expected stock after applying inventory movement formula.

Validation rules:
1. pricing_status must be OK.
2. unit_cost must be non-negative.
3. calculated_stock_qty is taken as-is from InventoryDataset.

Zero cases:
- calculated_stock_qty = 0 -> StockValue = 0
- unit_cost = 0 -> StockValue = 0

Negative cases:
- calculated_stock_qty < 0 -> negative StockValue allowed as a diagnostic signal.

Example:
- calculated_stock_qty = 115
- unit_cost = 35.50
- StockValue = 4082.50

---

### 8.2 ActualStockValue

Purpose:
- Measure actual counted inventory value.

Formula:
- ActualStockValue = ActualStockQty x UnitCost

Input fields:
- actual_stock_qty
- unit_cost

Output:
- Decimal monetary value

Business meaning:
- Value of physical stock measured at revision date.

Validation rules:
1. pricing_status must be OK.
2. unit_cost must be non-negative.

Zero cases:
- actual_stock_qty = 0 -> ActualStockValue = 0

Negative cases:
- actual_stock_qty < 0 -> negative value allowed as anomaly signal.

Example:
- actual_stock_qty = 112
- unit_cost = 35.50
- ActualStockValue = 3976.00

---

### 8.3 InventoryDifferenceValue

Purpose:
- Quantify financial impact of inventory variance.

Formula:
- InventoryDifferenceValue = VarianceQty x UnitCost

Input fields:
- variance_qty
- unit_cost

Output:
- Decimal monetary value

Business meaning:
- Monetary representation of shortage/excess versus expected stock.

Validation rules:
1. pricing_status must be OK.
2. unit_cost must be non-negative.

Zero cases:
- variance_qty = 0 -> InventoryDifferenceValue = 0

Negative cases:
- variance_qty < 0 -> negative value indicates shortage value.

Example:
- variance_qty = -3
- unit_cost = 35.50
- InventoryDifferenceValue = -106.50

---

### 8.4 SupplierReturnValue

Purpose:
- Measure value of supplier returns.

Formula:
- SupplierReturnValue = SupplierReturnQty x UnitCost

Input fields:
- supplier_return_qty
- unit_cost

Output:
- Decimal monetary value

Business meaning:
- Value of returned quantity to suppliers according to Inventory Mapping V1.

Validation rules:
1. pricing_status must be OK.
2. supplier_return_qty is sourced from Inventory Mapping V1.
3. unit_cost must be non-negative.

Zero cases:
- supplier_return_qty = 0 -> SupplierReturnValue = 0

Negative cases:
- supplier_return_qty < 0 -> allowed only as data anomaly; flag for diagnostics.

Example:
- supplier_return_qty = 30
- unit_cost = 35.50
- SupplierReturnValue = 1065.00

---

### 8.5 Revenue

Purpose:
- Measure gross sales value at retail pricing in current version.

Formula:
- Revenue = SalesQty x RetailPrice

Input fields:
- sales_qty
- retail_price

Output:
- Decimal monetary value

Business meaning:
- Top-line value from retail sales quantity.

Validation rules:
1. pricing_status must be OK.
2. retail_price must be non-negative.
3. sales_qty is sourced from Inventory Mapping V1 (`розница`).

Zero cases:
- sales_qty = 0 -> Revenue = 0
- retail_price = 0 -> Revenue = 0

Negative cases:
- sales_qty < 0 -> negative Revenue allowed as anomaly signal.

Example:
- sales_qty = 5
- retail_price = 79.90
- Revenue = 399.50

---

### 8.6 Cost Of Goods Sold (COGS)

Purpose:
- Measure cost basis of sold quantity.

Formula:
- COGS = SalesQty x UnitCost

Input fields:
- sales_qty
- unit_cost

Output:
- Decimal monetary value

Business meaning:
- Cost consumed by sold units.

Validation rules:
1. pricing_status must be OK.
2. unit_cost must be non-negative.

Zero cases:
- sales_qty = 0 -> COGS = 0

Negative cases:
- sales_qty < 0 -> negative COGS allowed as anomaly signal.

Example:
- sales_qty = 5
- unit_cost = 35.50
- COGS = 177.50

---

### 8.7 GrossProfit

Purpose:
- Measure gross earnings before taxes, discounts, and commissions.

Formula:
- GrossProfit = Revenue - COGS

Input fields:
- revenue
- cogs

Output:
- Decimal monetary value

Business meaning:
- Margin value from retail revenue after direct cost.

Validation rules:
1. Revenue and COGS must be computed from the same SKU and valuation context.

Zero cases:
- Revenue = 0 and COGS = 0 -> GrossProfit = 0

Negative cases:
- GrossProfit < 0 is allowed and indicates loss.

Example:
- Revenue = 399.50
- COGS = 177.50
- GrossProfit = 222.00

---

### 8.8 GrossMarginPercent

Purpose:
- Measure relative profitability of sales.

Formula:
- GrossMarginPercent = (GrossProfit / Revenue) x 100

Special rule:
- If Revenue == 0 then GrossMarginPercent = 0

Input fields:
- gross_profit
- revenue

Output:
- Decimal percentage value

Business meaning:
- Percent profitability relative to revenue.

Validation rules:
1. Must apply special zero-revenue rule before division.
2. No division by zero allowed.

Zero cases:
- Revenue = 0 -> GrossMarginPercent = 0

Negative cases:
- Revenue > 0 and GrossProfit < 0 -> negative margin allowed.

Example:
- Revenue = 399.50
- COGS = 177.50
- GrossProfit = 222.00
- GrossMarginPercent = 55.569462... (rounded only for presentation)

## 9. Required Validation Set
For each metric, validation must include:
1. happy path
2. zero values
3. negative edge cases
4. missing price scenario
5. precision scenario (Decimal, no premature rounding)

## 10. Testing Requirements Matrix

| Metric | Happy path | Zero case | Negative case | Missing price | Precision test |
| --- | --- | --- | --- | --- | --- |
| StockValue | Required | Required | Required | Required | Required |
| ActualStockValue | Required | Required | Required | Required | Required |
| InventoryDifferenceValue | Required | Required | Required | Required | Required |
| SupplierReturnValue | Required | Required | Required | Required | Required |
| Revenue | Required | Required | Required | Required | Required |
| COGS | Required | Required | Required | Required | Required |
| GrossProfit | Required | Required | Required | Required | Required |
| GrossMarginPercent | Required | Required | Required | Required | Required |

## 11. Out of Scope
The following are explicitly out of scope for this version:
- Taxes
- VAT
- FX conversion
- Discounts
- Promotions
- Marketplace commissions
- Supplier bonuses

## 12. Governance and Change Control
1. This document is immutable baseline for v1 finance calculations.
2. Any formula or status change requires a versioned update.
3. Implementation must conform to this document and to the approved architecture/spec contracts.
