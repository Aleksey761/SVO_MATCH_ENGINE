# INVENTORY MAPPING V1

Confirmed inventory business mapping for reconciliation.

## OpeningStockQty
- Source column: `Остаток на складе (шт) на 20.02.2024`
- Meaning: initial stock balance.

## ReceiptQty
- Current value: `0`
- Meaning: receipts are not connected yet because no source document is available.

## SupplierReturnQty
- Source columns:
  - `Воронеж`
  - `Краснодар 1`
  - `Краснодар 2`
- Calculation:
  - `SupplierReturnQty = Воронеж + Краснодар 1 + Краснодар 2`
- Meaning: supplier returns split by warehouse location.

## SalesQty
- Source column: `розница`
- Calculation:
  - `SalesQty = розница`
- Meaning: retail sales to final customers.

## ActualStockQty
- Source: revision-period stock snapshot column selected by revision file date.
- Meaning: factual stock on revision date.

## CalculatedStockQty
- Formula:
  - `CalculatedStockQty = OpeningStockQty + ReceiptQty - SupplierReturnQty - SalesQty`

## VarianceQty
- Formula:
  - `VarianceQty = ActualStockQty - CalculatedStockQty`

## Notes
- Regional columns must not be treated as sales.
- `розница` must not be merged with regional return columns.
- Excel output structure remains unchanged.
