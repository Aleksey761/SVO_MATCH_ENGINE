import re
from dataclasses import dataclass, field
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
                if field_name == "category" and "\u0428\u0410\u041c\u041f\u0423\u041d" in normalized:
                    values.append((field_name, "SHAMPUN"))
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
    confidence: float = 0.0
    review_reasons: list[str] = field(default_factory=list)
    candidates: list["MasterItem"] = field(default_factory=list)
    review_explanation: dict = field(default_factory=dict)

    @property
    def normalized_key(self) -> str:
        return (
            f"{(self.category or '').strip().upper()}|"
            f"{(self.brand or '').strip().upper()}|"
            f"{(self.variant or '').strip().upper()}|"
            f"{(self.volume or '').strip().upper()}"
        )
