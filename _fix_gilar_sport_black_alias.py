from pathlib import Path

path = Path('svo/matcher.py')
text = path.read_text(encoding='utf-8')

needle = '    def _find_exact_master(self, item: ArrivalItem) -> MasterItem | None:\n'
if needle not in text:
    raise SystemExit('CURRENT _find_exact_master not found')

if 'def _confirmed_price_alias' not in text:
    helper = '''    def _confirmed_price_alias(self, item: ArrivalItem) -> MasterItem | None:\n        source = self._normalize_value(getattr(item, "source_name", None)) or ""\n        if "GILAR" in source and "SPORT" in source and "ОТ ПЕРХ" in source and "400" in source:\n            for master in self.master_items:\n                if self._normalize_value(master.sku) == "SKU-012":\n                    return master\n        return None\n\n'''
    text = text.replace(needle, helper + needle, 1)

call = '        confirmed = self._confirmed_price_alias(item)\n        if confirmed is not None:\n            return confirmed\n\n'
if call not in text:
    text = text.replace(needle, needle + call, 1)

path.write_text(text, encoding='utf-8')
print('GILAR SPORT BLACK ALIAS FIXED')
