from pathlib import Path
import re

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

start = t.find('                aliases = {')
end = t.find('                normalized_candidate = candidate.strip()', start)

if start < 0 or end < 0:
    raise SystemExit("BROKEN ALIASES BLOCK NOT FOUND")

new_block = '''                aliases = {
                    "MEDINA": "MAGINA",
                    "MENTOL": "MINT",
                    "Я ССТЬ": "MOUNTAIN BREEZE",
                    "Ы ": "MOUNTAIN BREEZE",
                    "": "ROSE",
                    "С": "SNOWDROP",
                    "ШХ": "SHEIKH",
                    "Я": "PASSION FRUIT",
                    "": "PASSION FRUIT",
                    "ЬС": "ORANGE",
                    "Т": "GRAPEFRUIT",
                    "Я": "APPLE",
                    "ТЫ": "YELLOW",
                    "ТЫ": "YELLOW",
                    "СЫ": "RED",
                    "Ы": "PINK",
                    "С": "BLUE",
                    "ТЫ": "PURPLE",
                    "Ы": "BLACK",
                    "Ы": "BLACK",
                }

'''

t = t[:start] + new_block + t[end:]

p.write_text(t, encoding="utf-8")
print("ALIASES BLOCK FIXED")
