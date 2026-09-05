# SVO_MATCH_ENGINE Project Rules

## Source of truth

MASTER.xlsx is the only source of truth.

All SKU mapping and canonical names must come from MASTER.

---

## Excel finalization rules

Do not:
- create new columns;
- delete existing columns;
- move columns;
- change column widths;
- change cell formatting;
- change styles.

Only update cell values.

---

## Final file structure

Column 1:
№

Column 2:
SKU

Column "Наименование":
must contain only MASTER_NAME.

Never build names by concatenating:
- type;
- brand;
- aroma;
- volume.

Never parse names.

---

## Mapping

Use direct mapping:

MASTER.SKU → SKU

MASTER.MASTER_NAME → Наименование

Other attributes must come from MASTER fields.

---

## Sorting

Final output must be sorted according to MASTER order.

---

## Files

Keep date from source filename.

Do not remove dates.

---

## Development

Before changing code:
- inspect existing logic;
- make minimal changes;
- do not rewrite architecture.

After changes:
run tests and report only results.
