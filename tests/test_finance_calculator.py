from decimal import Decimal
from dataclasses import FrozenInstanceError

import pytest

from finance.calculator import FinanceCalculator
from finance.models import FinancialSummary


def test_finance_calculator_inventory_valuation_happy_path():
    metrics = FinanceCalculator().calculate_inventory_valuation(
        calculated_stock_qty=115,
        actual_stock_qty=112,
        variance_qty=-3,
        supplier_return_qty=30,
        unit_cost=Decimal("35.50"),
        pricing_status="OK",
    )

    assert metrics["StockValue"] == Decimal("4082.50")
    assert metrics["ActualStockValue"] == Decimal("3976.00")
    assert metrics["InventoryDifferenceValue"] == Decimal("-106.50")
    assert metrics["SupplierReturnValue"] == Decimal("1065.00")


def test_finance_calculator_inventory_valuation_zero_quantity():
    metrics = FinanceCalculator().calculate_inventory_valuation(
        calculated_stock_qty=0,
        actual_stock_qty=0,
        variance_qty=0,
        supplier_return_qty=0,
        unit_cost=Decimal("35.50"),
        pricing_status="OK",
    )

    assert metrics["StockValue"] == Decimal("0.00")
    assert metrics["ActualStockValue"] == Decimal("0.00")
    assert metrics["InventoryDifferenceValue"] == Decimal("0.00")
    assert metrics["SupplierReturnValue"] == Decimal("0.00")


def test_finance_calculator_inventory_valuation_zero_price():
    metrics = FinanceCalculator().calculate_inventory_valuation(
        calculated_stock_qty=115,
        actual_stock_qty=112,
        variance_qty=-3,
        supplier_return_qty=30,
        unit_cost=Decimal("0"),
        pricing_status="OK",
    )

    assert metrics["StockValue"] == Decimal("0")
    assert metrics["ActualStockValue"] == Decimal("0")
    assert metrics["InventoryDifferenceValue"] == Decimal("-0")
    assert metrics["SupplierReturnValue"] == Decimal("0")


def test_finance_calculator_inventory_valuation_negative_quantity_allowed():
    metrics = FinanceCalculator().calculate_inventory_valuation(
        calculated_stock_qty=-10,
        actual_stock_qty=-12,
        variance_qty=-2,
        supplier_return_qty=-5,
        unit_cost=Decimal("35.50"),
        pricing_status="OK",
    )

    assert metrics["StockValue"] == Decimal("-355.00")
    assert metrics["ActualStockValue"] == Decimal("-426.00")
    assert metrics["InventoryDifferenceValue"] == Decimal("-71.00")
    assert metrics["SupplierReturnValue"] == Decimal("-177.50")


def test_finance_calculator_inventory_valuation_decimal_precision_no_rounding():
    metrics = FinanceCalculator().calculate_inventory_valuation(
        calculated_stock_qty=3,
        actual_stock_qty=2,
        variance_qty=-1,
        supplier_return_qty=1,
        unit_cost=Decimal("0.333333333333333333"),
        pricing_status="OK",
    )

    assert metrics["StockValue"] == Decimal("0.999999999999999999")
    assert metrics["ActualStockValue"] == Decimal("0.666666666666666666")
    assert metrics["InventoryDifferenceValue"] == Decimal("-0.333333333333333333")
    assert metrics["SupplierReturnValue"] == Decimal("0.333333333333333333")


def test_finance_calculator_rejects_non_ok_pricing_status():
    with pytest.raises(ValueError, match="pricing_status must be OK"):
        FinanceCalculator().calculate_inventory_valuation(
            calculated_stock_qty=10,
            actual_stock_qty=10,
            variance_qty=0,
            supplier_return_qty=1,
            unit_cost=Decimal("5.00"),
            pricing_status="MissingPrice",
        )


def test_finance_calculator_revenue_happy_path():
    revenue = FinanceCalculator().calculate_revenue(
        sales_qty=5,
        retail_price=Decimal("79.90"),
        pricing_status="OK",
    )

    assert revenue == Decimal("399.50")


def test_finance_calculator_revenue_zero_sales():
    revenue = FinanceCalculator().calculate_revenue(
        sales_qty=0,
        retail_price=Decimal("79.90"),
        pricing_status="OK",
    )

    assert revenue == Decimal("0.00")


def test_finance_calculator_revenue_zero_retail_price():
    revenue = FinanceCalculator().calculate_revenue(
        sales_qty=5,
        retail_price=Decimal("0"),
        pricing_status="OK",
    )

    assert revenue == Decimal("0")


def test_finance_calculator_revenue_decimal_precision_no_rounding():
    revenue = FinanceCalculator().calculate_revenue(
        sales_qty=3,
        retail_price=Decimal("0.333333333333333333"),
        pricing_status="OK",
    )

    assert revenue == Decimal("0.999999999999999999")


def test_finance_calculator_revenue_very_large_quantity():
    revenue = FinanceCalculator().calculate_revenue(
        sales_qty=1_000_000_000,
        retail_price=Decimal("12345.6789"),
        pricing_status="OK",
    )

    assert revenue == Decimal("12345678900000.0000")


@pytest.mark.parametrize(
    "pricing_status",
    ["MissingPrice", "InactivePrice", "AmbiguousPrice", "FuturePrice", "ExpiredPrice"],
)
def test_finance_calculator_revenue_rejects_non_ok_pricing_statuses(pricing_status: str):
    with pytest.raises(ValueError, match="pricing_status must be OK"):
        FinanceCalculator().calculate_revenue(
            sales_qty=5,
            retail_price=Decimal("79.90"),
            pricing_status=pricing_status,
        )


def test_finance_calculator_cogs_happy_path():
    cogs = FinanceCalculator().calculate_cogs(
        sales_qty=5,
        unit_cost=Decimal("35.50"),
        pricing_status="OK",
    )

    assert cogs == Decimal("177.50")


def test_finance_calculator_cogs_zero_sales():
    cogs = FinanceCalculator().calculate_cogs(
        sales_qty=0,
        unit_cost=Decimal("35.50"),
        pricing_status="OK",
    )

    assert cogs == Decimal("0.00")


def test_finance_calculator_cogs_zero_unit_cost():
    cogs = FinanceCalculator().calculate_cogs(
        sales_qty=5,
        unit_cost=Decimal("0"),
        pricing_status="OK",
    )

    assert cogs == Decimal("0")


def test_finance_calculator_cogs_decimal_precision_no_rounding():
    cogs = FinanceCalculator().calculate_cogs(
        sales_qty=3,
        unit_cost=Decimal("0.333333333333333333"),
        pricing_status="OK",
    )

    assert cogs == Decimal("0.999999999999999999")


def test_finance_calculator_cogs_very_large_quantity():
    cogs = FinanceCalculator().calculate_cogs(
        sales_qty=1_000_000_000,
        unit_cost=Decimal("12345.6789"),
        pricing_status="OK",
    )

    assert cogs == Decimal("12345678900000.0000")


@pytest.mark.parametrize(
    "pricing_status",
    ["MissingPrice", "InactivePrice", "AmbiguousPrice", "FuturePrice", "ExpiredPrice"],
)
def test_finance_calculator_cogs_rejects_non_ok_pricing_statuses(pricing_status: str):
    with pytest.raises(ValueError, match="pricing_status must be OK"):
        FinanceCalculator().calculate_cogs(
            sales_qty=5,
            unit_cost=Decimal("35.50"),
            pricing_status=pricing_status,
        )


def test_finance_calculator_gross_profit_happy_path():
    gross_profit = FinanceCalculator().calculate_gross_profit(
        revenue=Decimal("399.50"),
        cogs=Decimal("177.50"),
    )

    assert gross_profit == Decimal("222.00")


def test_finance_calculator_gross_profit_zero_revenue():
    gross_profit = FinanceCalculator().calculate_gross_profit(
        revenue=Decimal("0"),
        cogs=Decimal("177.50"),
    )

    assert gross_profit == Decimal("-177.50")


def test_finance_calculator_gross_profit_zero_cogs():
    gross_profit = FinanceCalculator().calculate_gross_profit(
        revenue=Decimal("399.50"),
        cogs=Decimal("0"),
    )

    assert gross_profit == Decimal("399.50")


def test_finance_calculator_gross_profit_negative_profit():
    gross_profit = FinanceCalculator().calculate_gross_profit(
        revenue=Decimal("100.00"),
        cogs=Decimal("150.00"),
    )

    assert gross_profit == Decimal("-50.00")


def test_finance_calculator_gross_margin_percent_happy_path():
    margin = FinanceCalculator().calculate_gross_margin_percent(
        revenue=Decimal("399.50"),
        gross_profit=Decimal("222.00"),
    )

    assert margin == Decimal("55.56946182728410513141426783")


def test_finance_calculator_gross_margin_percent_zero_revenue():
    margin = FinanceCalculator().calculate_gross_margin_percent(
        revenue=Decimal("0"),
        gross_profit=Decimal("222.00"),
    )

    assert margin == Decimal("0")


def test_finance_calculator_gross_margin_percent_decimal_precision_no_rounding():
    margin = FinanceCalculator().calculate_gross_margin_percent(
        revenue=Decimal("3"),
        gross_profit=Decimal("1"),
    )

    assert margin == Decimal("33.33333333333333333333333333")


def test_financial_summary_object_creation():
    summary = FinancialSummary(
        StockValue=Decimal("4082.50"),
        ActualStockValue=Decimal("3976.00"),
        InventoryDifferenceValue=Decimal("-106.50"),
        SupplierReturnValue=Decimal("1065.00"),
        Revenue=Decimal("399.50"),
        COGS=Decimal("177.50"),
        GrossProfit=Decimal("222.00"),
        GrossMarginPercent=Decimal("55.56946182728410513141426783"),
    )

    assert summary.StockValue == Decimal("4082.50")
    assert summary.GrossProfit == Decimal("222.00")


def test_financial_summary_value_consistency():
    calculator = FinanceCalculator()
    revenue = calculator.calculate_revenue(
        sales_qty=5,
        retail_price=Decimal("79.90"),
        pricing_status="OK",
    )
    cogs = calculator.calculate_cogs(
        sales_qty=5,
        unit_cost=Decimal("35.50"),
        pricing_status="OK",
    )
    gross_profit = calculator.calculate_gross_profit(revenue=revenue, cogs=cogs)
    gross_margin_percent = calculator.calculate_gross_margin_percent(
        revenue=revenue,
        gross_profit=gross_profit,
    )

    summary = FinancialSummary(
        StockValue=Decimal("4082.50"),
        ActualStockValue=Decimal("3976.00"),
        InventoryDifferenceValue=Decimal("-106.50"),
        SupplierReturnValue=Decimal("1065.00"),
        Revenue=revenue,
        COGS=cogs,
        GrossProfit=gross_profit,
        GrossMarginPercent=gross_margin_percent,
    )

    assert summary.GrossProfit == summary.Revenue - summary.COGS
    assert summary.GrossMarginPercent == (summary.GrossProfit / summary.Revenue) * Decimal("100")


def test_financial_summary_is_immutable():
    summary = FinancialSummary(
        StockValue=Decimal("4082.50"),
        ActualStockValue=Decimal("3976.00"),
        InventoryDifferenceValue=Decimal("-106.50"),
        SupplierReturnValue=Decimal("1065.00"),
        Revenue=Decimal("399.50"),
        COGS=Decimal("177.50"),
        GrossProfit=Decimal("222.00"),
        GrossMarginPercent=Decimal("55.56946182728410513141426783"),
    )

    with pytest.raises(FrozenInstanceError):
        summary.Revenue = Decimal("0")
