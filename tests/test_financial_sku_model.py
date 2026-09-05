from svo.financial_sku_model import SKUFinancialRecord


def test_sku_financial_record_from_quantities():
    record = SKUFinancialRecord.from_quantities(
        sku="SKU-001",
        master_name="Test Product",
        received_qty=100,
        shipped_qty=30,
        retail_qty=5,
        balance_qty=75,
        purchase_price=2.5,
        average_cost=3.0,
        sale_price=5.0,
    )

    assert record.SKU == "SKU-001"
    assert record.MASTER_NAME == "Test Product"

    assert record.ReceivedQty == 100
    assert record.ShippedQty == 30
    assert record.RetailQty == 5
    assert record.BalanceQty == 75

    assert record.PurchasePrice == 2.5
    assert record.AverageCost == 3.0
    assert record.SalePrice == 5.0

    assert record.Revenue == 175.0
    assert record.InventoryValue == 225.0
    assert record.GrossProfit == 70.0


def test_sku_financial_record_parses_strings():
    record = SKUFinancialRecord.from_quantities(
        sku="SKU-002",
        master_name="Another Product",
        received_qty="1 000",
        shipped_qty="200",
        retail_qty="50",
        balance_qty="850",
        purchase_price="10,5",
        average_cost="11,0",
        sale_price="15,0",
    )

    assert record.ReceivedQty == 1000
    assert record.ShippedQty == 200
    assert record.RetailQty == 50
    assert record.BalanceQty == 850

    assert record.PurchasePrice == 10.5
    assert record.AverageCost == 11.0
    assert record.SalePrice == 15.0

    assert record.Revenue == 3750.0
    assert record.InventoryValue == 9350.0
    assert record.GrossProfit == 1000.0
