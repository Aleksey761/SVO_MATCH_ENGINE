from openpyxl import Workbook

from svo.business_metrics import BusinessMetrics, BusinessMetricsLayer, build_business_metrics, run_business_metrics
from svo.dataset_builder import DatasetRecord


def _dataset() -> list[DatasetRecord]:
    return [
        DatasetRecord(
            sku="SKU-001",
            master_name="Product 1",
            category="Cat-1",
            brand="Brand-1",
            aroma="A1",
            arrival_quantity=10,
            sales_quantity=4,
            last_arrival_date="10.07.2026",
            last_sales_date="11.07.2026",
        ),
        DatasetRecord(
            sku="SKU-002",
            master_name="Product 2",
            category="Cat-2",
            brand="Brand-2",
            aroma="A2",
            arrival_quantity=0,
            sales_quantity=7,
            last_arrival_date="",
            last_sales_date="12.07.2026",
        ),
        DatasetRecord(
            sku="SKU-003",
            master_name="Product 3",
            category="Cat-3",
            brand="Brand-3",
            aroma="A3",
            arrival_quantity=3,
            sales_quantity=0,
            last_arrival_date="09.07.2026",
            last_sales_date="",
        ),
        DatasetRecord(
            sku="SKU-004",
            master_name="Product 4",
            category="Cat-4",
            brand="Brand-4",
            aroma="A4",
            arrival_quantity=0,
            sales_quantity=0,
            last_arrival_date="",
            last_sales_date="",
        ),
    ]


def test_business_metrics_contains_only_required_fields():
    metrics = BusinessMetricsLayer(_dataset()).build()

    assert isinstance(metrics, BusinessMetrics)
    assert set(metrics.__dataclass_fields__.keys()) == {
        "arrival_quantity",
        "sales_quantity",
        "net_movement",
    }


def test_business_metrics_totals():
    metrics = BusinessMetricsLayer(_dataset()).build()

    assert metrics.arrival_quantity == 13
    assert metrics.sales_quantity == 11
    assert metrics.net_movement == 2


def test_build_business_metrics_wrapper():
    metrics = build_business_metrics(_dataset())
    assert metrics.arrival_quantity == 13
    assert metrics.sales_quantity == 11
    assert metrics.net_movement == 2


def test_business_metrics_empty_dataset():
    metrics = BusinessMetricsLayer([]).build()

    assert metrics.arrival_quantity == 0
    assert metrics.sales_quantity == 0
    assert metrics.net_movement == 0


def test_duplicate_rows_are_summed():
    dataset = [
        DatasetRecord(
            sku="SKU-100",
            master_name="Product 100",
            category="Cat",
            brand="Brand",
            aroma="A",
            arrival_quantity=3,
            sales_quantity=1,
            last_arrival_date="01.07.2026",
            last_sales_date="02.07.2026",
        ),
        DatasetRecord(
            sku="SKU-100",
            master_name="Product 100 duplicate",
            category="Cat",
            brand="Brand",
            aroma="A",
            arrival_quantity=2,
            sales_quantity=5,
            last_arrival_date="03.07.2026",
            last_sales_date="04.07.2026",
        ),
    ]

    metrics = BusinessMetricsLayer(dataset).build()

    assert metrics.arrival_quantity == 5
    assert metrics.sales_quantity == 6
    assert metrics.net_movement == -1


def test_negative_quantities_are_clamped_to_zero():
    dataset = [
        DatasetRecord("SKU-1", "M1", "C", "B", "A", arrival_quantity=-5, sales_quantity=7),
        DatasetRecord("SKU-2", "M2", "C", "B", "A", arrival_quantity=3, sales_quantity=-2),
    ]

    metrics = BusinessMetricsLayer(dataset).build()

    assert metrics.arrival_quantity == 3
    assert metrics.sales_quantity == 7
    assert metrics.net_movement == -4


def test_run_business_metrics_uses_dataset_api(tmp_path):
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    data_dir.mkdir()
    output_dir.mkdir()

    wb = Workbook()
    ws = wb.active
    ws.title = "MASTER"
    ws.append(["SKU", "Category", "Brand", "Variant", "Volume"])
    ws.append(["SKU-001", "Cat", "Brand", "Aroma", "1L"])
    ws.append(["SKU-002", "Cat", "Brand", "Aroma", "1L"])
    wb.save(data_dir / "MASTER.xlsx")

    metrics = run_business_metrics(
        dataset_file=output_dir / "MASTER_DATASET.xlsx",
        input_dir=data_dir,
        rebuild_if_missing=True,
    )

    assert metrics.arrival_quantity == 0
    assert metrics.sales_quantity == 0
    assert metrics.net_movement == 0
    assert (output_dir / "MASTER_DATASET.xlsx").exists()
