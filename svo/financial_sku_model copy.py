from dataclasses import dataclass


@dataclass
class SKUFinancialRecord:
    SKU: str
    MASTER_NAME: str

    ReceivedQty: int
    ShippedQty: int
    RetailQty: int
    BalanceQty: int

    PurchasePrice: float
    AverageCost: float
    SalePrice: float

    Revenue: float
    InventoryValue: float
    GrossProfit: float

    @staticmethod
    def _to_int(value: object) -> int:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(round(value))
        text = str(value).strip().replace(" ", "").replace(",", ".")
        if not text:
            return 0
        try:
            return int(round(float(text)))
        except ValueError:
            return 0

    @staticmethod
    def _to_float(value: object) -> float:
        if value is None:
            return 0.0
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(" ", "").replace(",", ".")
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0

    @classmethod
    def from_quantities(
        cls,
        *,
        sku: str,
        master_name: str,
        received_qty: object,
        shipped_qty: object,
        retail_qty: object,
        balance_qty: object,
        purchase_price: object,
        average_cost: object,
        sale_price: object,
    ) -> "SKUFinancialRecord":
        received = cls._to_int(received_qty)
        shipped = cls._to_int(shipped_qty)
        retail = cls._to_int(retail_qty)
        balance = cls._to_int(balance_qty)

        purchase = cls._to_float(purchase_price)
        average = cls._to_float(average_cost)
        sale = cls._to_float(sale_price)

        sold_qty = shipped + retail
        revenue = sold_qty * sale
        inventory_value = balance * average
        gross_profit = revenue - (sold_qty * average)

        return cls(
            SKU=str(sku or "").strip(),
            MASTER_NAME=str(master_name or "").strip(),
            ReceivedQty=received,
            ShippedQty=shipped,
            RetailQty=retail,
            BalanceQty=balance,
            PurchasePrice=purchase,
            AverageCost=average,
            SalePrice=sale,
            Revenue=revenue,
            InventoryValue=inventory_value,
            GrossProfit=gross_profit,
        )
