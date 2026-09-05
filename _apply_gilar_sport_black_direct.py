from pathlib import Path

p = Path("svo/matcher.py")
s = p.read_text(encoding="utf-8")

needle = '    def match(self, item: ArrivalItem) -> ArrivalItem:\n'

insert = '''    def match(self, item: ArrivalItem) -> ArrivalItem:
        # Confirmed PRICE alias: GILAR SPORT BLACK 400 ml (anti-dandruff).
        source = self._normalize_value(getattr(item, "source_name", None)) or ""
        volume = self._normalize_value(getattr(item, "volume", None)) or ""
        if (
            "GILAR" in source
            and "SPORT" in source
            and "Х" in source
            and "Ш" in source
            and volume == "400 "
        ):
            confirmed = next(
                (candidate for candidate in self.master_items if candidate.sku == "SKU-012"),
                None,
            )
            if confirmed is not None:
                return self._assign_match(item, confirmed)

'''

if needle not in s:
    raise SystemExit("MATCH METHOD NOT FOUND")

if "Confirmed PRICE alias: GILAR SPORT BLACK 400 ml" in s:
    print("GILAR SPORT BLACK RULE ALREADY PRESENT")
else:
    s = s.replace(needle, insert, 1)
    p.write_text(s, encoding="utf-8")
    print("GILAR SPORT BLACK RULE APPLIED")
