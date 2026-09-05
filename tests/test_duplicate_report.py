from pathlib import Path

from svo.duplicate_report import (
    build_duplicate_sku_groups,
    format_duplicate_sku_report,
    generate_duplicate_sku_report,
)
from svo.models import ArrivalItem


def test_build_duplicate_sku_groups_uses_match_items_only():
    items = [
        ArrivalItem(row_number=17, source_name="Кондиционер лотос", status="MATCH", sku="SKU-064", master_name="Кондиционер SVO Lotos 2,7 л"),
        ArrivalItem(row_number=53, source_name="Кондиционер LOTOS", status="MATCH", sku="SKU-064", master_name="Кондиционер SVO Lotos 2,7 л"),
        ArrivalItem(row_number=71, source_name="Одиночная позиция", status="MATCH", sku="SKU-100", master_name="Товар 100"),
        ArrivalItem(row_number=177, source_name="Сборка", status="REVIEW", sku="SKU-064", master_name="Кондиционер SVO Lotos 2,7 л"),
    ]

    groups = build_duplicate_sku_groups(items)

    assert len(groups) == 1
    group = groups[0]
    assert group.sku == "SKU-064"
    assert group.master_name == "Кондиционер SVO Lotos 2,7 л"
    assert group.rows == [
        (17, "Кондиционер лотос"),
        (53, "Кондиционер LOTOS"),
    ]


def test_format_duplicate_sku_report_contains_totals_and_blocks():
    items = [
        ArrivalItem(row_number=17, source_name="Кондиционер для стирки SVO Таинственный лотос", status="MATCH", sku="SKU-064", master_name="Кондиционер SVO Lotos 2,7 л"),
        ArrivalItem(row_number=53, source_name="Кондиционер SVO LOTOS", status="MATCH", sku="SKU-064", master_name="Кондиционер SVO Lotos 2,7 л"),
        ArrivalItem(row_number=61, source_name="Гель для душа", status="MATCH", sku="SKU-200", master_name="Гель для душа SVO"),
    ]

    text = format_duplicate_sku_report(items)

    assert "SKU: SKU-064" in text
    assert "MASTER_NAME: Кондиционер SVO Lotos 2,7 л" in text
    assert "ROW 17" in text
    assert "ROW 53" in text
    assert "Комментарий:" in text
    assert "Повтор одного SKU." in text
    assert "TOTAL DUPLICATE SKU GROUPS : 1" in text
    assert "TOTAL ROWS INVOLVED        : 2" in text


def test_generate_duplicate_sku_report_writes_file(tmp_path: Path):
    output_file = tmp_path / "DUPLICATE_SKU_REPORT.txt"
    items = [
        ArrivalItem(row_number=10, source_name="Товар A", status="MATCH", sku="SKU-1", master_name="Товар A"),
        ArrivalItem(row_number=11, source_name="Товар A дубль", status="MATCH", sku="SKU-1", master_name="Товар A"),
    ]

    text = generate_duplicate_sku_report(items, output_file=output_file)

    assert output_file.exists()
    saved = output_file.read_text(encoding="utf-8")
    assert text in saved
    assert "TOTAL DUPLICATE SKU GROUPS : 1" in saved
