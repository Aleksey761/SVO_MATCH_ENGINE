from pathlib import Path
from decimal import Decimal

import pytest
from openpyxl import Workbook

from svo.engine import Engine
from svo.matcher import Matcher


@pytest.fixture(autouse=True)
def _isolate_output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)


def _create_master(path: Path, rows: list[list[object]]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "MASTER"
    ws.append(["SKU", "Category", "Brand", "Variant", "Volume", "MASTER_NAME"])
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def _create_price(path: Path, rows: list[list[object]]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "PRICE"
    ws.append(["Supplier article", "Product name", "Free stock", "Distributor price"])
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def test_first_confirmed_mapping_reused(tmp_path: Path):
    master_file = _create_master(
        tmp_path / "MASTER.xlsx",
        [["SKU-APPLE", "Шампунь", "SVO", "AQUA", "1 л", "Шампунь SVO AQUA 1 л"]],
    )
    price_file = _create_price(
        tmp_path / "PRICE.xlsx",
        [["A-100", "SVO shampoo aqua 1 l", 10, "35,50"]],
    )

    engine = Engine(learning_map_file=tmp_path / "learning_map.xlsx")
    saved = engine.confirm_review_matches(
        master_file=master_file,
        confirmed_rows=[
            {
                "SupplierArticle": "A-100",
                "SupplierName": "SVO shampoo aqua 1 l",
                "CanonicalSupplier": "SVO SHAMPOO AQUA 1 L",
                "SKU": "SKU-APPLE",
                "MASTER_NAME": "Шампунь SVO AQUA 1 л",
                "Confidence": 97.0,
            }
        ],
        confirmed_by="QA",
    )

    result = engine.run_price_matching(master_file=master_file, price_file=price_file)

    assert saved == 1
    assert result["learning_reused"] == 1
    assert result["rows"][0]["MatchStatus"] == "MATCH"
    assert result["rows"][0]["SKU"] == "SKU-APPLE"


def test_repeated_import_skips_matcher_for_learned_rows(tmp_path: Path, monkeypatch):
    master_file = _create_master(
        tmp_path / "MASTER.xlsx",
        [["SKU-APPLE", "Шампунь", "SVO", "AQUA", "1 л", "Шампунь SVO AQUA 1 л"]],
    )
    price_file = _create_price(
        tmp_path / "PRICE.xlsx",
        [["A-100", "SVO shampoo aqua 1 l", 10, "35,50"]],
    )

    engine = Engine(learning_map_file=tmp_path / "learning_map.xlsx")
    engine.confirm_review_matches(
        master_file=master_file,
        confirmed_rows=[
            {
                "SupplierArticle": "A-100",
                "SupplierName": "SVO shampoo aqua 1 l",
                "CanonicalSupplier": "SVO SHAMPOO AQUA 1 L",
                "SKU": "SKU-APPLE",
                "MASTER_NAME": "Шампунь SVO AQUA 1 л",
                "Confidence": 96.0,
            }
        ],
        confirmed_by="QA",
    )

    spy = {"matched_items": None}
    original_match_all = Matcher.match_all

    def _spy_match_all(self, items):
        spy["matched_items"] = len(items)
        return original_match_all(self, items)

    monkeypatch.setattr(Matcher, "match_all", _spy_match_all)

    result = engine.run_price_matching(master_file=master_file, price_file=price_file)

    assert result["learning_reused"] == 1
    assert spy["matched_items"] == 0


def test_unknown_article_still_uses_matcher(tmp_path: Path, monkeypatch):
    master_file = _create_master(
        tmp_path / "MASTER.xlsx",
        [["SKU-APPLE", "Шампунь", "SVO", "AQUA", "1 л", "Шампунь SVO AQUA 1 л"]],
    )
    price_file = _create_price(
        tmp_path / "PRICE.xlsx",
        [["B-200", "SVO shampoo aqua 1 l", 10, "35,50"]],
    )

    engine = Engine(learning_map_file=tmp_path / "learning_map.xlsx")
    engine.confirm_review_matches(
        master_file=master_file,
        confirmed_rows=[
            {
                "SupplierArticle": "A-100",
                "SupplierName": "SVO shampoo aqua 1 l",
                "CanonicalSupplier": "SVO SHAMPOO AQUA 1 L",
                "SKU": "SKU-APPLE",
                "MASTER_NAME": "Шампунь SVO AQUA 1 л",
                "Confidence": 96.0,
            }
        ],
        confirmed_by="QA",
    )

    spy = {"matched_items": None}
    original_match_all = Matcher.match_all

    def _spy_match_all(self, items):
        spy["matched_items"] = len(items)
        return original_match_all(self, items)

    monkeypatch.setattr(Matcher, "match_all", _spy_match_all)

    result = engine.run_price_matching(master_file=master_file, price_file=price_file)

    assert result["learning_reused"] == 0
    assert spy["matched_items"] == 1
    assert result["rows"][0]["MatchStatus"] == "MATCH"
    assert result["rows"][0]["SKU"] == "SKU-APPLE"


def test_deleted_sku_in_learning_map_is_handled_safely(tmp_path: Path):
    master_file = _create_master(
        tmp_path / "MASTER.xlsx",
        [["SKU-APPLE", "Шампунь", "SVO", "AQUA", "1 л", "Шампунь SVO AQUA 1 л"]],
    )
    price_file = _create_price(
        tmp_path / "PRICE.xlsx",
        [["A-100", "Unknown product without master", 10, "35,50"]],
    )

    engine = Engine(learning_map_file=tmp_path / "learning_map.xlsx")
    engine.learning_map.upsert(
        supplier_article="A-100",
        supplier_name="Unknown product without master",
        canonical_supplier="UNKNOWN PRODUCT WITHOUT MASTER",
        sku="SKU-DELETED",
        master_name="Deleted row",
        confidence=95.0,
        confirmed_by="QA",
    )

    result = engine.run_price_matching(master_file=master_file, price_file=price_file)

    assert result["learning_reused"] == 0
    assert result["learning_stale"] == 1
    assert result["rows"][0]["MatchStatus"] == "REVIEW"
    assert result["rows"][0]["SKU"] == ""


def test_learning_map_survives_restart(tmp_path: Path):
    master_file = _create_master(
        tmp_path / "MASTER.xlsx",
        [["SKU-APPLE", "Шампунь", "SVO", "AQUA", "1 л", "Шампунь SVO AQUA 1 л"]],
    )
    price_file = _create_price(
        tmp_path / "PRICE.xlsx",
        [["A-100", "SVO shampoo aqua 1 l", 10, Decimal("35.50")]],
    )
    learning_file = tmp_path / "learning_map.xlsx"

    first_engine = Engine(learning_map_file=learning_file)
    first_engine.confirm_review_matches(
        master_file=master_file,
        confirmed_rows=[
            {
                "SupplierArticle": "A-100",
                "SupplierName": "SVO shampoo aqua 1 l",
                "CanonicalSupplier": "SVO SHAMPOO AQUA 1 L",
                "SKU": "SKU-APPLE",
                "MASTER_NAME": "Шампунь SVO AQUA 1 л",
                "Confidence": 98.0,
            }
        ],
        confirmed_by="QA",
    )

    second_engine = Engine(learning_map_file=learning_file)
    result = second_engine.run_price_matching(master_file=master_file, price_file=price_file)

    assert result["learning_reused"] == 1
    assert result["rows"][0]["MatchStatus"] == "MATCH"
    assert result["rows"][0]["SKU"] == "SKU-APPLE"
