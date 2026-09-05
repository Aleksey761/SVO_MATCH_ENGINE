from pathlib import Path
from collections import Counter
from decimal import Decimal
import re
from openpyxl import Workbook

from svo.engine import Engine
from svo.matcher import Matcher
from svo.business_rules import BusinessRules
from svo.normalizer import Normalizer

OUT = Path('output/VOLUME_REAL_MISMATCHS.xlsx')
DATA_DIR = Path('data')
AUTO_MATCH_SCORE_DELTA = 20.0

normalizer = Normalizer()


def safe(value):
    return str(value or '').strip()


def norm_volume(value: str) -> str:
    text = safe(value)
    if not text:
        return ''
    detected = normalizer._detect_volume(text)
    if detected:
        return detected
    return text.upper()


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


num_unit_re = re.compile(r'(?<!\d)(\d+(?:[.,]\d+)?)\s*(L|Л|ML|МЛ|KG|КГ|G|Г)\b', re.IGNORECASE)
pack_re = re.compile(r'(?<!\d)(\d+)\s*[XХ×]\s*(\d+(?:[.,]\d+)?)\s*(G|Г)\b', re.IGNORECASE)


def parse_volume(value: str):
    text = safe(value).upper().replace(',', '.')
    if not text:
        return None
    m = pack_re.search(text)
    if m:
        return {
            'kind': 'pack',
            'count': Decimal(m.group(1)),
            'size': Decimal(m.group(2)),
            'unit': 'G',
            'base': Decimal(m.group(1)) * Decimal(m.group(2)),
            'dim': 'G',
        }
    m = num_unit_re.search(text)
    if not m:
        return None
    num = Decimal(m.group(1))
    unit = m.group(2)
    if unit in {'L', 'Л'}:
        return {'kind': 'single', 'value': num, 'unit': 'L', 'base': num * Decimal('1000'), 'dim': 'ML'}
    if unit in {'ML', 'МЛ'}:
        return {'kind': 'single', 'value': num, 'unit': 'ML', 'base': num, 'dim': 'ML'}
    if unit in {'KG', 'КГ'}:
        return {'kind': 'single', 'value': num, 'unit': 'KG', 'base': num * Decimal('1000'), 'dim': 'G'}
    if unit in {'G', 'Г'}:
        return {'kind': 'single', 'value': num, 'unit': 'G', 'base': num, 'dim': 'G'}
    return None


def mismatch_reason(arrival_vol: str, candidate_vol: str):
    if not safe(arrival_vol):
        return 'Missing volume in supplier text'
    if not safe(candidate_vol):
        return 'Missing volume in MASTER'
    a = parse_volume(arrival_vol)
    c = parse_volume(candidate_vol)
    if a is None or c is None:
        return 'Other'
    if a['kind'] != c['kind']:
        return 'Different package size'
    if a['kind'] == 'pack' and (a['count'] != c['count'] or a['size'] != c['size'] or a['unit'] != c['unit']):
        return 'Different package size'
    if a['dim'] != c['dim']:
        return 'Different unit'
    if a['base'] != c['base']:
        return 'Different numeric value'
    return 'Other'


price_candidates = sorted([p for p in DATA_DIR.glob('PRC*.xlsx') if p.is_file()], key=lambda p: p.stat().st_mtime)
if not price_candidates:
    raise FileNotFoundError('No PRICE workbook found')
price_file = price_candidates[-1]

engine = Engine()
master_items = engine.loader.load_master(DATA_DIR / 'MASTER.xlsx')
price_items = engine.price_loader.load(price_file)
for item in price_items:
    engine.normalizer.normalize(item)
matcher = Matcher(master_items, auto_resolve_multiple_candidates=True, auto_match_score_delta=AUTO_MATCH_SCORE_DELTA)
unresolved, _, _ = engine._apply_learning_map_matches(price_items, master_items)
matcher.match_all(unresolved)
BusinessRules(master_items).apply(price_items)
engine._validate_price_name_sku_conflicts(price_items)

rows = []
reasons = Counter()
equal_examples = []
equal_count = 0
real_mismatch_count = 0

for item in price_items:
    if safe(getattr(item, 'status', None)).upper() != 'REVIEW':
        continue
    details = candidate_details(item, matcher)
    if classify_resolution(item, details) != 'Volume normalization':
        continue
    if not getattr(item, 'candidates', None):
        continue
    candidate = item.candidates[0]

    arrival_volume = norm_volume(getattr(item, 'volume', None))
    candidate_volume = norm_volume(getattr(candidate, 'volume', None))
    volume_equal = 'YES' if arrival_volume and candidate_volume and arrival_volume == candidate_volume else 'NO'
    reason = '' if volume_equal == 'YES' else mismatch_reason(arrival_volume, candidate_volume)

    if volume_equal == 'YES':
        equal_count += 1
        if len(equal_examples) < 20:
            equal_examples.append((
                int(getattr(item, 'row_number', 0) or 0),
                safe(getattr(item, 'original_product_name', None) or getattr(item, 'source_name', None)),
                arrival_volume,
                safe(getattr(candidate, 'sku', None)),
                candidate_volume,
            ))
    else:
        real_mismatch_count += 1
        reasons[reason] += 1

    rows.append([
        int(getattr(item, 'row_number', 0) or 0),
        safe(getattr(item, 'original_product_name', None) or getattr(item, 'source_name', None)),
        arrival_volume,
        safe(getattr(candidate, 'sku', None)),
        safe(getattr(candidate, 'master_name', None)),
        candidate_volume,
        volume_equal,
        reason,
    ])

wb = Workbook()
ws = wb.active
ws.title = 'VOLUME_REAL_MISMATCHS'
ws.append(['Row', 'SupplierName', 'ArrivalVolume', 'CandidateSKU', 'CandidateMASTER', 'CandidateVolume', 'VolumeEqual', 'MismatchReason'])
for row in rows:
    ws.append(row)
OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)

print('VOLUME_REAL_MISMATCHS_PATH', OUT.as_posix())
print('Rows analyzed', len(rows))
print('Equal volumes', equal_count)
print('Real volume mismatches', real_mismatch_count)
print('Top mismatch reasons')
for reason, count in reasons.most_common():
    print(f'{reason}: {count}')
if equal_count > 0:
    print('FIRST_20_EQUAL_EXAMPLES')
    for row_num, supplier_name, arr_v, sku, cand_v in equal_examples:
        supplier_name = supplier_name.encode('unicode_escape').decode('ascii')
        arr_v = arr_v.encode('unicode_escape').decode('ascii')
        cand_v = cand_v.encode('unicode_escape').decode('ascii')
        print(f'{row_num} | {supplier_name} | {arr_v} | {sku} | {cand_v}')
