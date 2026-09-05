from dataclasses import dataclass
from pathlib import Path

from .dataset_api import load_master_dataset
from .dataset_builder import DatasetRecord


@dataclass
class BusinessMetrics:
    arrival_quantity: int
    sales_quantity: int
    net_movement: int


class BusinessMetricsLayer:
    """Build RC3.1 business totals from MASTER_DATASET records only."""

    def __init__(self, dataset: list[DatasetRecord]):
        self.dataset = list(dataset)

    def build(self) -> BusinessMetrics:
        arrival_quantity = sum(max(0, int(row.arrival_quantity)) for row in self.dataset)
        sales_quantity = sum(max(0, int(row.sales_quantity)) for row in self.dataset)

        return BusinessMetrics(
            arrival_quantity=arrival_quantity,
            sales_quantity=sales_quantity,
            net_movement=arrival_quantity - sales_quantity,
        )


def build_business_metrics(dataset: list[DatasetRecord]) -> BusinessMetrics:
    return BusinessMetricsLayer(dataset).build()


def run_business_metrics(
    *,
    dataset_file: str | Path = "output/MASTER_DATASET.xlsx",
    input_dir: str | Path = "data",
    rebuild_if_missing: bool = False,
) -> BusinessMetrics:
    dataset = load_master_dataset(
        dataset_file=dataset_file,
        input_dir=input_dir,
        rebuild_if_missing=rebuild_if_missing,
    )
    return build_business_metrics(dataset)
