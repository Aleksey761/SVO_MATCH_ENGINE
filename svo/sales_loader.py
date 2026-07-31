from pathlib import Path

from .arrival_loader import ArrivalLoader
from .models import ArrivalItem


class SalesLoader(ArrivalLoader):
    """Loads SALES workbook rows into the shared arrival item model."""

    def load_sales(self, filename: str | Path) -> list[ArrivalItem]:
        return self.load(filename)