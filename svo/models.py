from dataclasses import dataclass
from typing import Optional


@dataclass
class MasterItem:
    sku: str
    category: str
    brand: str
    variant: str
    volume: str

    @property
    def normalized_key(self) -> str:
        return (
            f"{self.category.strip().upper()}|"
            f"{self.brand.strip().upper()}|"
            f"{self.variant.strip().upper()}|"
            f"{self.volume.strip().upper()}"
        )


@dataclass
class ArrivalItem:
    row_number: int
    source_name: str

    category: Optional[str] = None
    brand: Optional[str] = None
    variant: Optional[str] = None
    volume: Optional[str] = None

    sku: Optional[str] = None
    master_name: Optional[str] = None

    status: str = "NEW"

    @property
    def normalized_key(self) -> str:
        return (
            f"{(self.category or '').strip().upper()}|"
            f"{(self.brand or '').strip().upper()}|"
            f"{(self.variant or '').strip().upper()}|"
            f"{(self.volume or '').strip().upper()}"
        )
