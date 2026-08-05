from pathlib import Path

from svo.engine import Engine
from svo.loader import Loader

base = Path("data")
master = Loader.discover_master_workbook(base)
price = base / "PRICE_202412...Цена.xlsx"

result = Engine().run_price_matching(master_file=master, price_file=price)
print("MASTER", result["master"])
print("PRICE_ROWS", result["price_rows"])
print("MATCH", result["match"])
print("REVIEW", result["review"])
