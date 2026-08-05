import json
from pathlib import Path

from svo.quality.runner import run_quality_gate


def _result_by_name(payload: dict, name: str):
    for result in payload["results"]:
        if result.name == name:
            return result
    raise AssertionError(f"Result not found: {name}")


def test_quality_runner_duplicate_sku(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = [
        {"SKU": "SKU-1", "CATEGORY": "C1", "BRAND": "B1", "VARIANT": "V1", "VOLUME": "1L"},
        {"SKU": "SKU-1", "CATEGORY": "C2", "BRAND": "B2", "VARIANT": "V2", "VOLUME": "2L"},
    ]

    audit = run_quality_gate(gate="master", dataframe=rows)

    assert audit["passed"] is False
    assert audit["errors"] == 1
    duplicate = _result_by_name(audit, "Duplicate SKU")
    assert duplicate.passed is False
    assert duplicate.count == 1


def test_quality_runner_empty_sku(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = [
        {"SKU": "", "CATEGORY": "C1", "BRAND": "B1", "VARIANT": "V1", "VOLUME": "1L"},
        {"SKU": "SKU-2", "CATEGORY": "C2", "BRAND": "B2", "VARIANT": "V2", "VOLUME": "2L"},
    ]

    audit = run_quality_gate(gate="master", dataframe=rows)

    assert audit["passed"] is False
    assert audit["errors"] == 1
    empty = _result_by_name(audit, "Empty SKU")
    assert empty.passed is False
    assert empty.count == 1


def test_quality_runner_duplicate_business_key(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = [
        {"SKU": "SKU-1", "CATEGORY": "C1", "BRAND": "B1", "VARIANT": "V1", "VOLUME": "1L"},
        {"SKU": "SKU-2", "CATEGORY": "C1", "BRAND": "B1", "VARIANT": "V1", "VOLUME": "1L"},
    ]

    audit = run_quality_gate(gate="master", dataframe=rows)

    assert audit["passed"] is False
    assert audit["errors"] == 1
    duplicate_bk = _result_by_name(audit, "Duplicate Business Key")
    assert duplicate_bk.passed is False
    assert duplicate_bk.count == 1


def test_quality_runner_success_and_reports(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = [
        {"SKU": "SKU-1", "CATEGORY": "C1", "BRAND": "B1", "VARIANT": "V1", "VOLUME": "1L"},
        {"SKU": "SKU-2", "CATEGORY": "C2", "BRAND": "B2", "VARIANT": "V2", "VOLUME": "2L"},
    ]

    audit = run_quality_gate(gate="master", dataframe=rows)

    assert audit["passed"] is True
    assert audit["errors"] == 0
    assert audit["warnings"] == 0

    txt_path = tmp_path / "output" / "MASTER_AUDIT.txt"
    json_path = tmp_path / "output" / "MASTER_AUDIT.json"
    assert txt_path.exists()
    assert json_path.exists()

    txt = txt_path.read_text(encoding="utf-8")
    assert "MASTER AUDIT" in txt
    assert "STATUS : PASSED" in txt

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASSED"
    assert len(payload["results"]) == 3
