from openpyxl import load_workbook

TARGET = Path(r"output\MASTER_DATASET.xlsx")
OLD = "ШЕЙХ"
NEW = "Magina"

wb = load_workbook(TARGET)
ws = wb.active

changed = 0

for row in ws.iter_rows(min_row=2):
    category = str(row[1].value or "").strip()
    brand = str(row[2].value or "").strip()
    volume = str(row[4].value or "").strip()
    variant = str(row[3].value or "").strip()
    aroma = str(row[5].value or "").strip()
    master_name = str(row[9].value or "").strip()

    if category == "Порошок стиральный" and brand == "SVO" and volume == "5 кг":
        row[3].value = NEW
        row[5].value = NEW
        row[9].value = "Порошок стиральный SVO Magina 5 кг"
        changed += 1
        print(
            "UPDATED:",
            row[0].value, "|",
            category, "|",
            brand, "|",
            OLD, "->", NEW, "|",
            volume, "|",
            row[9].value
        )

if changed == 0:
    raise RuntimeError("5 KG SVO POWDER ROW NOT FOUND")

wb.save(TARGET)
print(f"MASTER 5 KG SHEIKH -> MAGINA APPLIED: {changed} row(s)")
