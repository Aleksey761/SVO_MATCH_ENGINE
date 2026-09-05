from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

start = s.index("        powder_pattern = re.compile(")
end = s.index("        def is_block_header", start)

replacement = r'''        powder_pattern = re.compile(
            r"^орошок\s+(\d+(?:[.,]\d+)?)\s+(.+)$",
            re.IGNORECASE,
        )

        powder_aromas = {
            "": "Lavender",
            "Ы": "Black",
            "": "Rose",
            "С": "Snowdrop",
            "С": "Snowdrop",
            "Ы": "Mountain Breeze",
            "": "Mountain Breeze",
            "Ы": "Mountain Breeze",
            "": "Lemon",
            "ТС": "Baby",
        }

        elegant_aromas = {
            "WHITE": "White",
            "MANGO": "Mango",
            "FLORIAL MIST": "Floral Mist",
            "MIDNIGHT": "Midnight",
            "SPRING": "Spring",
            "SWEET TROPIK": "Sweet Tropic",
            "VELVET": "Velvet",
            "DREAM": "Dream",
            "BLACK": "Black",
        }

'''
s = s[:start] + replacement + s[end:]

# Fix the two damaged explicit block headers.
s = s.replace(
    'r"^ель\\s+кондиционер\\s+1400\\s+MAGINA$"',
    'r"^ель\\s+кондиционер\\s+1400\\s+MAGINA$"',
)
s = s.replace(
    'r"^SVO\\s+1500\\s+ELEGANT\\s+WHITE$"',
    'r"^SVO\\s+1500\\s+ELEGANT\\s+WHITE$"',
)

p.write_text(s, encoding="utf-8")
print("SALES UTF-8 BLOCK DEFINITIONS FIXED")
