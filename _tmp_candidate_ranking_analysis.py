from pathlib import Path
from collections import Counter
from decimal import Decimal
import re
from openpyxl import Workbook

from svo.engine import Engine
from svo.matcher import Matcher
from svo.business_rules import BusinessRules
from svo.normalizer import Normalizer

OUT = Path('output/CANDIDATE_RANKING_ANALYSIS.xlsx')
DATA_DIR = Path('data')
AUTO_MATCH_SCORE_DELTA = 20.0

normalizer = Normalizer()


def safe(value):
    return str(value or '').strip()


def as_float(value):
    try:
        return round(float(value), 2)
    except Exception:
        return None


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


def volume_equal(left: str, right: str) -> bool:
    left_norm = norm_volume(left)
    right_norm = norm_volume(right)
    return bool(left_norm and right_norm and left_norm == right_norm)


def component_bucket(delta_brand, delta_pt, delta_volume, delta_name, delta_total):
    components = [
        ('Name', delta_name),
        ('Brand', delta_brand),
        ('ProductType', delta_pt),
        ('Volume', delta_volume),
    ]
    components.sort(key=lambda item: item[1], reverse=True)
    if not components or components[0][1] <= 0:
        return 'Other'
    if delta_total > 0 and components[0][1] < delta_total * 0.35:
        return 'Other'
    return components[0][0]


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
summary_counts = Counter()
losing_components = Counter()
score_gaps = []
rows_analyzed = 0
rows_with_correct_volume = 0
rows_without_correct_volume = 0
recoverable_matches = 0

for item in price_items:
    if safe(getattr(item, 'status', None)).upper() != 'REVIEW':
        continue
    details = candidate_details(item, matcher)
    if classify_resolution(item, details) != 'Volume normalization':
        continue
    if not details:
        continue

    arrival_volume = norm_volume(getattr(item, 'volume', None))
    best = details[0]
    best_candidate_volume = norm_volume(best.get('volume'))
    if volume_equal(arrival_volume, best_candidate_volume):
        continue

    rows_analyzed += 1
    best_score = float(best.get('score') or 0.0)
    best_break = dict(best.get('breakdown') or {}) if isinstance(best, dict) else {}

    correct_volume_rank = None
    correct_volume_gap = None
    correct_volume_detail = None

    for rank, detail in enumerate(details, start=1):
        breakdown = dict(detail.get('breakdown') or {}) if isinstance(detail, dict) else {}
        name_score = round(float(breakdown.get('Aroma', 0.0) or 0.0) + float(breakdown.get('Color', 0.0) or 0.0) + float(breakdown.get('Keywords', 0.0) or 0.0), 2)
        total_score = as_float(detail.get('score'))
        volume_score = as_float(breakdown.get('Volume'))
        brand_score = as_float(breakdown.get('Brand'))
        product_type_score = as_float(breakdown.get('ProductType'))
        confidence = round(total_score or 0.0, 2)
        rejected_reason = safe(detail.get('rejection_reason'))
        candidate_volume = norm_volume(detail.get('volume'))
        is_correct_volume = 'YES' if volume_equal(arrival_volume, candidate_volume) else 'NO'
        distance_from_best = round(best_score - float(detail.get('score') or 0.0), 2)

        rows.append([
            int(getattr(item, 'row_number', 0) or 0),
            safe(getattr(item, 'original_product_name', None) or getattr(item, 'source_name', None)),
            arrival_volume,
            rank,
            safe(detail.get('sku')),
            safe(detail.get('master_name')),
            candidate_volume,
            total_score,
            volume_score,
            brand_score,
            product_type_score,
            name_score,
            confidence,
            rejected_reason,
            is_correct_volume,
            distance_from_best,
        ])

        if is_correct_volume == 'YES' and correct_volume_rank is None:
            correct_volume_rank = rank
            correct_volume_gap = distance_from_best
            correct_volume_detail = detail

    if correct_volume_rank is None:
        rows_without_correct_volume += 1
        summary_counts['Not found'] += 1
        continue

    rows_with_correct_volume += 1
    recoverable_matches += 1
    summary_counts['Correct-volume candidate exists'] += 1
    if correct_volume_rank == 2:
        summary_counts['Rank 2'] += 1
    elif correct_volume_rank == 3:
        summary_counts['Rank 3'] += 1
    else:
        summary_counts['Rank >3'] += 1

    if correct_volume_gap is not None:
        score_gaps.append(correct_volume_gap)

    cb = dict(correct_volume_detail.get('breakdown') or {}) if isinstance(correct_volume_detail, dict) else {}
    delta_brand = float(best_break.get('Brand', 0.0) or 0.0) - float(cb.get('Brand', 0.0) or 0.0)
    delta_pt = float(best_break.get('ProductType', 0.0) or 0.0) - float(cb.get('ProductType', 0.0) or 0.0)
    delta_volume = float(best_break.get('Volume', 0.0) or 0.0) - float(cb.get('Volume', 0.0) or 0.0)
    delta_name = (
        float(best_break.get('Aroma', 0.0) or 0.0) + float(best_break.get('Color', 0.0) or 0.0) + float(best_break.get('Keywords', 0.0) or 0.0)
        - float(cb.get('Aroma', 0.0) or 0.0) - float(cb.get('Color', 0.0) or 0.0) - float(cb.get('Keywords', 0.0) or 0.0)
    )
    delta_total = float(best.get('score') or 0.0) - float(correct_volume_detail.get('score') or 0.0)
    losing_components[component_bucket(delta_brand, delta_pt, delta_volume, delta_name, delta_total)] += 1

average_gap = round(sum(score_gaps) / len(score_gaps), 2) if score_gaps else 0.0

wb = Workbook()
ws = wb.active
ws.title = 'CANDIDATE_RANKING_ANALYSIS'
ws.append([
    'Row',
    'SupplierName',
    'ArrivalVolume',
    'Rank',
    'CandidateSKU',
    'MASTER_NAME',
    'CandidateVolume',
    'TotalScore',
    'VolumeScore',
    'BrandScore',
    'ProductTypeScore',
    'NameScore',
    'Confidence',
    'RejectedReason',
    'IsCorrectVolume',
    'DistanceFromBestScore',
])
for row in rows:
    ws.append(row)

summary_ws = wb.create_sheet('SUMMARY')
summary_ws.append(['Rows', 'Count', 'Percent'])
base = rows_analyzed if rows_analyzed else 1
summary_rows = [
    ('Correct-volume candidate exists', summary_counts.get('Correct-volume candidate exists', 0)),
    ('Rank 2', summary_counts.get('Rank 2', 0)),
    ('Rank 3', summary_counts.get('Rank 3', 0)),
    ('Rank >3', summary_counts.get('Rank >3', 0)),
    ('Not found', summary_counts.get('Not found', 0)),
    ('Average score gap', average_gap),
    ('Top score components: Name', losing_components.get('Name', 0)),
    ('Top score components: Brand', losing_components.get('Brand', 0)),
    ('Top score components: ProductType', losing_components.get('ProductType', 0)),
    ('Top score components: Volume', losing_components.get('Volume', 0)),
    ('Top score components: Other', losing_components.get('Other', 0)),
]
for label, value in summary_rows:
    if label == 'Average score gap':
        summary_ws.append([label, value, ''])
    else:
        percent = f"{(float(value) / base * 100.0):.2f}%" if isinstance(value, (int, float)) else ''
        summary_ws.append([label, value, percent])

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)

print('CANDIDATE_RANKING_ANALYSIS_PATH', OUT.as_posix())
print('Rows analyzed', rows_analyzed)
print('Rows with correct-volume candidate', rows_with_correct_volume)
print('Rows without correct-volume candidate', rows_without_correct_volume)
print('Estimated recoverable matches if ranking is improved', recoverable_matches)
