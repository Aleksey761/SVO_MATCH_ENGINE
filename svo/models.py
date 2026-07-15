import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class MasterItem:
    sku: str
    category: str
    brand: str
    variant: str
    volume: str
    aroma: Optional[str] = None

    @property
    def normalized_key(self) -> str:
        return (
            f"{self.category.strip().upper()}|"
            f"{self.brand.strip().upper()}|"
            f"{self.variant.strip().upper()}|"
            f"{self.volume.strip().upper()}"
        )

    def index_values(self) -> list[tuple[str, str]]:
        values = []
        for field_name, value in (
            ("sku", self.sku),
            ("category", self.category),
            ("brand", self.brand),
            ("volume", self.volume),
            ("aroma", self.aroma or self.variant),
        ):
            normalized = self._normalize_value(value)
            if normalized:
                values.append((field_name, normalized))
        return values

    @staticmethod
    def _normalize_value(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        text = re.sub(r"\s+", " ", text).upper()
        return text


@dataclass
class ArrivalItem:
    row_number: int
    source_name: str

    category: Optional[str] = None
    brand: Optional[str] = None
    variant: Optional[str] = None
    volume: Optional[str] = None
    aroma: Optional[str] = None

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
