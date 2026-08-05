from __future__ import annotations

from decimal import Decimal


class FinanceCalculator:
    """Computes finance valuation metrics from inventory quantities and resolved price."""

    @staticmethod
    def _as_decimal(value: Decimal | int | str) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _validate_pricing_status(pricing_status: str) -> None:
        if pricing_status != "OK":
            raise ValueError("pricing_status must be OK")

    @staticmethod
    def _validate_price(*, price: Decimal | None, field_name: str) -> None:
        if price is None:
            raise ValueError(f"{field_name} is required")
        if price < Decimal("0"):
            raise ValueError(f"{field_name} must be non-negative")

    @staticmethod
    def _validate_inputs(*, unit_cost: Decimal, pricing_status: str) -> None:
        FinanceCalculator._validate_pricing_status(pricing_status)
        FinanceCalculator._validate_price(price=unit_cost, field_name="unit_cost")

    def calculate_inventory_valuation(
        self,
        *,
        calculated_stock_qty: int,
        actual_stock_qty: int,
        variance_qty: int,
        supplier_return_qty: int,
        unit_cost: Decimal | int | str,
        pricing_status: str,
    ) -> dict[str, Decimal]:
        normalized_unit_cost = self._as_decimal(unit_cost)
        self._validate_inputs(unit_cost=normalized_unit_cost, pricing_status=pricing_status)

        stock_value = Decimal(calculated_stock_qty) * normalized_unit_cost
        actual_stock_value = Decimal(actual_stock_qty) * normalized_unit_cost
        inventory_difference_value = Decimal(variance_qty) * normalized_unit_cost
        supplier_return_value = Decimal(supplier_return_qty) * normalized_unit_cost

        return {
            "StockValue": stock_value,
            "ActualStockValue": actual_stock_value,
            "InventoryDifferenceValue": inventory_difference_value,
            "SupplierReturnValue": supplier_return_value,
        }

    def calculate_revenue(
        self,
        *,
        sales_qty: int,
        retail_price: Decimal | int | str,
        pricing_status: str,
    ) -> Decimal:
        self._validate_pricing_status(pricing_status)
        normalized_retail_price = self._as_decimal(retail_price)
        self._validate_price(price=normalized_retail_price, field_name="retail_price")
        return Decimal(sales_qty) * normalized_retail_price

    def calculate_cogs(
        self,
        *,
        sales_qty: int,
        unit_cost: Decimal | int | str,
        pricing_status: str,
    ) -> Decimal:
        self._validate_pricing_status(pricing_status)
        normalized_unit_cost = self._as_decimal(unit_cost)
        self._validate_price(price=normalized_unit_cost, field_name="unit_cost")
        return Decimal(sales_qty) * normalized_unit_cost

    def calculate_gross_profit(
        self,
        *,
        revenue: Decimal | int | str,
        cogs: Decimal | int | str,
    ) -> Decimal:
        normalized_revenue = self._as_decimal(revenue)
        normalized_cogs = self._as_decimal(cogs)
        return normalized_revenue - normalized_cogs

    def calculate_gross_margin_percent(
        self,
        *,
        revenue: Decimal | int | str,
        gross_profit: Decimal | int | str,
    ) -> Decimal:
        normalized_revenue = self._as_decimal(revenue)
        normalized_gross_profit = self._as_decimal(gross_profit)
        if normalized_revenue == Decimal("0"):
            return Decimal("0")
        return (normalized_gross_profit / normalized_revenue) * Decimal("100")
