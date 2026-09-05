from pathlib import Path
import re

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

start = text.index("    def _detect_volume(self, text: str) -> Optional[str]:")
end = text.index("    def _cleanup_candidate(", start)

new_method = '''    def _detect_volume(self, text: str) -> Optional[str]:
        match = self._volume_re.search(text.lower())
        if not match:
            return None

        raw_value = match.group(1)
        value = Decimal(raw_value.replace(",", "."))
        unit = match.group(2).lower()

        # Canonical volume units used by MASTER.
        if unit in {"л", "литр", "литра", "литров", "l", "liter", "liters"}:
            return f"{self._format_decimal(value)} "

        if unit in {"мл", "ml"}:
            # PRICE notation 1,440 мл means 1.44 l.
            if (
                Decimal("1") <= value < Decimal("10")
                and "," in raw_value
                and len(raw_value.split(",", 1)[1]) == 3
            ):
                return f"{self._format_decimal(value)} "

            if value >= Decimal("1000"):
                return f"{self._format_decimal(value / Decimal('1000'))} "

            return f"{self._format_decimal(value)} "

        if unit in {"кг", "kg", "килограмм", "килограмма", "килограммов"}:
            return f"{self._format_decimal(value)} "

        if unit in {"г", "гр", "грамм", "грамма", "граммов", "gram", "grams"}:
            return f"{self._format_decimal(value)} "

        return None

'''

p.write_text(text[:start] + new_method + text[end:], encoding="utf-8")
print("VOLUME METHOD PATCH APPLIED")
