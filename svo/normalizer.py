import re

from .models import ArrivalItem


class Normalizer:
    """Normalizes arrival item text and extracts basic fields."""

    _CATEGORY_RULES = [
        ("Кондиционер", ["кондиционер"]),
        ("ЖМС", ["жмс", "жидкое средство"]),
        ("Гель для душа", ["гель для душа"]),
        ("Шампунь", ["шампун"]),
    ]

    _BRANDS = ("SVO", "GILAR", "BOSSFIX")

    _VOLUME_RE = re.compile(
        r'(\d+(?:[.,]\d+)?)\s*(л|литр|литра|литров|мл|ml)',
        re.IGNORECASE
    )

    def normalize(self, item: ArrivalItem) -> ArrivalItem:
        text = " ".join(item.source_name.replace(",", " ").split())
        upper = text.upper()

        for brand in self._BRANDS:
            if brand in upper:
                item.brand = brand
                break

        lower = text.lower()
        for category, patterns in self._CATEGORY_RULES:
            if any(p in lower for p in patterns):
                item.category = category
                break

        m = self._VOLUME_RE.search(lower)
        if m:
            value = m.group(1).replace(",", ".")
            unit = m.group(2).lower()
            item.volume = f"{value} л" if unit.startswith("л") else f"{value} мл"

        if item.brand:
            parts = re.split(item.brand, text, flags=re.IGNORECASE, maxsplit=1)
            if len(parts) == 2:
                candidate = parts[1]
                candidate = re.sub(self._VOLUME_RE, "", candidate)
                candidate = re.sub(
                    r'парфюмированн\w*|для стирки|детских вещей|синий|красный|желтый|фиолетовый|розовый|черный',
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                )
                candidate = " ".join(candidate.replace(",", " ").split()).strip()
                if candidate:
                    item.variant = candidate.upper()

        return item
