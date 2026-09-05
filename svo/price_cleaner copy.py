from __future__ import annotations

import re


class PriceCleaner:
    """Cleans supplier product names by removing technical noise only."""

    _PACK_MARK_BACKSLASH = re.compile(r"(?:^|\s)\\+\s*\d+(?=$|\s)")
    _PACK_MARK_RATIO = re.compile(r"(?:^|\s)\d{1,4}\s*/\s*\d{1,4}(?=$|\s)")
    _SEPARATORS = re.compile(r"[|;_]+")
    _NON_DECIMAL_COMMA = re.compile(r"(?<!\d),(?!\d)|(?<=\d),\s+(?=\D)|(?<=\D)\s*,(?=\d)")
    _SPACES = re.compile(r"\s+")

    def clean(self, value: object) -> str:
        text = str(value or "")
        text = text.replace("\u00a0", " ")
        text = self._NON_DECIMAL_COMMA.sub(" ", text)
        text = self._SEPARATORS.sub(" ", text)
        text = self._PACK_MARK_BACKSLASH.sub(" ", text)
        text = self._PACK_MARK_RATIO.sub(" ", text)
        text = self._SPACES.sub(" ", text).strip()
        return text
