from pathlib import Path
from collections import Counter
from decimal import Decimal, InvalidOperation
import re
from openpyxl import Workbook

from svo.engine import Engine
from svo.matcher import Matcher
from svo.business_rules import BusinessRules
from svo.models import effective_product_type

OUT = Path('output/MASTER_GAPS.xlsx')
DATA_DIR = Path('data')
AUTO_MATCH_SCORE_DELTA = 20.0


def safe(value):
    return str(value or '').strip()


def norm(matcher, value):
    return safe(matcher._normalize_value(value))


def parse_volume_base(value: str):
    text = safe(value).upper().replace(',', '.')
    if not text:
        return None, None
    pack = re.search(r'(?<!\d)(\d+)\s*[XХ×]\s*(\d+(?:\.\d+)?)\s*(G|Г)\b', text)
    if pack:
        try:
            count = Decimal(pack.group(1))
            grams = Decimal(pack.group(2))
            return count * grams, 'G'
        except InvalidOperation:
            return None, None
    match = re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*(L|Л|ML|МЛ|KG|КГ|G|Г)\b', text)
    if not match:
        return None, None
    try:
        value_num = Decimal(match.group(1))
    except InvalidOperation:
        return None, None
    unit = match.group(2)
    if unit in {'L', 'Л'}:
        return value_num * Decimal('1000'), 'ML'
    if unit in {'ML', 'МЛ'}:
        return value_num, 'ML'
    if unit in {'KG', 'КГ'}:
        return value_num * Decimal('1000'), 'G'
    if unit in {'G', 'Г'}:
        return value_num, 'G'
    return None, None


def volume_distance(left: str, right: str):
    left_base, left_dim = parse_volume_base(left)
    right_base, right_dim = parse_volume_base(right)
    if left_base is None or right_base is None or left_dim != right_dim:
        return None
    return abs(left_base - right_base)


def candidate_details(item, matcher):
    explanation = getattr(item, 'review_explanation', {}) or {}
    detailed = [c for c in explanation.get('candidates', []) if isinstance(c, dict)]
    if not detailed and getattr(item, 'candidates', None):
        detailed = [matcher._score_detail(item, c) for c in item.candidates]
    detailed.sort(key=lambda e: float(e.get('score') or 0.0), reverse=True)
    return detailed


def classify_resolution(item, details):
    reasons = {safe(r).upper() for r in (getattr(item, 'review_reasons', []) or [])}
    best = details[0] if details else {}
    breakdown = dict(best.get('breakdown') or {}) if isinstance(best, dict) else {}
    best_rej_raw = (getattr(item, 'review_explanation', {}) or {}).get('best_candidate_rejected_reason')
    if isinstance(best_rej_raw, list):
        best_rej = '; '.join(safe(v) for v in best_rej_raw if safe(v))
    else:
        best_rej = safe(best_rej_raw)
    if 'PRICE_CONFLICT' in reasons:
        return 'Price conflict'
    if 'PRODUCT_TYPE_MISMATCH' in reasons or safe(best.get('rejection_reason')).upper() == 'PRODUCT_TYPE_MISMATCH':
        return 'ProductType normalization'
    if 'NO_VOLUME' in reasons or (float(breakdown.get('Volume', 0.0)) <= 0.0 and bool(safe(getattr(item, 'volume', None)))):
        return 'Volume normalization'
    if float(breakdown.get('Brand', 0.0)) <= 0.0 and bool(safe(getattr(item, 'brand', None))):
        return 'Brand normalization'
    if 'MULTIPLE_MATCH' in reasons:
        return 'Multiple candidates'
    if 'LOW_SCORE' in reasons or 'below threshold' in best_rej.lower():
        return 'Low confidence'
    if not details:
        return 'Missing MASTER SKU'
    if safe(getattr(item, 'status', None)).upper() == 'REVIEW':
        return 'Manual review'
    return 'Other'


def closest_master(item, matcher, master_items):
    arrival_pt = norm(matcher, effective_product_type(item))
    arrival_brand = norm(matcher, getattr(item, 'brand', None))
    arrival_volume = norm(matcher, getattr(item, 'volume', None))

    same_pt_brand = [
        master for master in master_items
        if norm(matcher, effective_product_type(master)) == arrival_pt
        and norm(matcher, getattr(master, 'brand', None)) == arrival_brand
    ]
    same_pt = [master for master in master_items if norm(matcher, effective_product_type(master)) == arrival_pt]

    pool = same_pt_brand or same_pt or list(master_items)
    family_label = 'same ProductType+Brand' if same_pt_brand else ('same ProductType' if same_pt else 'global')

    scored = []
    for master in pool:
        similarity = matcher._source_master_similarity(item.source_name, master)
        dist = volume_distance(arrival_volume, norm(matcher, getattr(master, 'volume', None)))
        scored.append((master, similarity, dist))

    def sort_key(entry):
        master, similarity, dist = entry
        dist_key = float(dist) if dist is not None else 10**12
        return (dist_key, -similarity, safe(master.sku))

    scored.sort(key=sort_key)
    master, similarity, dist = scored[0]
    master_volume = norm(matcher, getattr(master, 'volume', None))
    diff_parts = [family_label]
    if norm(matcher, getattr(master, 'brand', None)) != arrival_brand:
        diff_parts.append(f"brand {safe(getattr(item, 'brand', None))} -> {safe(getattr(master, 'brand', None))}")
    if master_volume != arrival_volume:
        diff_parts.append(f"volume {safe(getattr(item, 'volume', None))} -> {safe(getattr(master, 'volume', None))}")
    if dist is not None:
        diff_parts.append(f"volume_distance={dist}")
    diff_parts.append(f"similarity={similarity:.2f}")
    return master, '; '.join(diff_parts)


engine = Engine()
master_items = engine.loader.load_master(DATA_DIR / 'MASTER.xlsx')
price_candidates = sorted([p for p in DATA_DIR.glob('PRC*.xlsx') if p.is_file()], key=lambda p: p.stat().st_mtime)
if not price_candidates:
    raise FileNotFoundError('No PRICE workbook found')
price_file = price_candidates[-1]
price_items = engine.price_loader.load(price_file)
for item in price_items:
    engine.normalizer.normalize(item)
matcher = Matcher(master_items, auto_resolve_multiple_candidates=True, auto_match_score_delta=AUTO_MATCH_SCORE_DELTA)
unresolved, _, _ = engine._apply_learning_map_matches(price_items, master_items)
matcher.match_all(unresolved)
BusinessRules(master_items).apply(price_items)
engine._validate_price_name_sku_conflicts(price_items)

rows = []
summary = Counter()
missing_combinations = Counter()

for item in price_items:
    if safe(getattr(item, 'status', None)).upper() != 'REVIEW':
        continue
    details = candidate_details(item, matcher)
    summary['Rows analyzed'] += 1

    arrival_pt = norm(matcher, effective_product_type(item))
    arrival_brand = norm(matcher, getattr(item, 'brand', None))
    arrival_volume = norm(matcher, getattr(item, 'volume', None))

    exact_matches = [
        master for master in master_items
        if norm(matcher, effective_product_type(master)) == arrival_pt
        and norm(matcher, getattr(master, 'brand', None)) == arrival_brand
        and norm(matcher, getattr(master, 'volume', None)) == arrival_volume
    ]

    if exact_matches:
        summary['Exact matches'] += 1
        closest = exact_matches[0]
        difference = 'exact ProductType+Brand+Volume match exists in MASTER'
        exact = 'YES'
    else:
        summary['Missing combinations'] += 1
        exact = 'NO'
        combo_key = f"{arrival_pt or '<EMPTY>'} | {safe(getattr(item, 'brand', None)) or '<EMPTY>'} | {safe(getattr(item, 'volume', None)) or '<EMPTY>'}"
        missing_combinations[combo_key] += 1
        closest, difference = closest_master(item, matcher, master_items)

    rows.append([
        int(getattr(item, 'row_number', 0) or 0),
        safe(getattr(item, 'original_product_name', None) or getattr(item, 'source_name', None)),
        safe(effective_product_type(item)),
        safe(getattr(item, 'brand', None)),
        safe(getattr(item, 'volume', None)),
        exact,
        safe(getattr(closest, 'sku', None)),
        safe(getattr(closest, 'master_name', None)),
        difference,
    ])

wb = Workbook()
ws = wb.active
ws.title = 'MASTER_GAPS'
ws.append([
    'Row',
    'SupplierName',
    'ProductType',
    'Brand',
    'Volume',
    'Exact MASTER match (YES/NO)',
    'Closest MASTER SKU',
    'Closest MASTER_NAME',
    'Difference',
])
for row in rows:
    ws.append(row)

summary_ws = wb.create_sheet('SUMMARY')
summary_ws.append(['Metric', 'Value'])
summary_ws.append(['Rows analyzed', summary.get('Rows analyzed', 0)])
summary_ws.append(['Exact matches', summary.get('Exact matches', 0)])
summary_ws.append(['Missing combinations', summary.get('Missing combinations', 0)])
summary_ws.append([])
summary_ws.append(['Top missing ProductType + Brand + Volume combinations', 'Count'])
for combo, count in missing_combinations.most_common(20):
    summary_ws.append([combo, count])

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)

print('MASTER_GAPS_PATH', OUT.as_posix())
print('Rows analyzed', summary.get('Rows analyzed', 0))
print('Exact matches', summary.get('Exact matches', 0))
print('Missing combinations', summary.get('Missing combinations', 0))
print('Top missing ProductType + Brand + Volume combinations')
for combo, count in missing_combinations.most_common(10):
    print(f'{combo}: {count}')
