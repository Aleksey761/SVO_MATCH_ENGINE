from pathlib import Path

p = Path("svo/matcher.py")
t = p.read_text(encoding="utf-8")

needle = '''    def _find_exact_master(self, item: ArrivalItem) -> MasterItem | None:
        exact_matches: list[MasterItem] = []
'''

replacement = '''    def _find_exact_master(self, item: ArrivalItem) -> MasterItem | None:
        # MASTER-aware exact metadata match.
        # Resolve only when category + brand + volume + aroma
        # identify exactly one MASTER position.
        arrival_aroma = item.aroma or item.variant

        if (
            item.category
            and item.brand
            and item.volume
            and arrival_aroma
        ):
            metadata_matches = [
                candidate
                for candidate in self.master_items
                if self._metadata_matches(item, candidate)
            ]
            if len(metadata_matches) == 1:
                return metadata_matches[0]

        exact_matches: list[MasterItem] = []
'''

if needle not in t:
    raise SystemExit("CATEGORY/METADATA PATCH TARGET NOT FOUND")

t = t.replace(needle, replacement, 1)
p.write_text(t, encoding="utf-8")

print("MASTER EXACT METADATA PATCH OK")
