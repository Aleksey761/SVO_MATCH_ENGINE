from pathlib import Path

from ._document_loader import load_document_rows
from .models import ArrivalItem


class ArrivalLoader:
    """Loads ARRIVAL workbook rows into the shared arrival item model."""

    def load(self, filename: str | Path) -> list[ArrivalItem]:
        return load_document_rows(filename)

    def load_arrival(self, filename: str | Path) -> list[ArrivalItem]:
        return self.load(filename)