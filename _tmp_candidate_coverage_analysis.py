from pathlib import Path
from collections import Counter
from openpyxl import Workbook

from svo.engine import Engine
from svo.matcher import Matcher
from svo.business_rules import BusinessRules
from svo.models import effective_product_type

OUT = Path('output/CANDIDATE_COVERAGE_ANALYSIS.xlsx')
DATA_DIR = Path('data')
AUTO_MATCH_SCORE_DELTA = 20.0


def safe(value):
    return str(value or '').strip()


def normalize(matcher, value):
    return matcher._normalize_value(value)


def candidate_key(candidate):
    return f"{candidate.sku}|{candidate.normalized_key}"


def intersect_by_key(candidate_groups):
    keyed_groups = [
        {candidate_key(candidate): candidate for candidate in group}
        for group in candidate_groups if group
    ]
    if len(keyed_groups) < 2:
        return []
    common_keys = set(keyed_groups[0].keys())
    for keyed_group in keyed_groups[1:]:
        common_keys &= set(keyed_group.keys())
    if not common_keys:
        return []
    ordered = []
    for key, candidate in keyed_groups[0].items():
        if key in common_keys:
            ordered.append(candidate)
    return ordered


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
recoverable = 0

for item in price_items:
    if safe(getattr(item, 'status', None)).upper() != 'REVIEW':
        continue
    details = candidate_details(item, matcher)
    if classify_resolution(item, details) != 'Volume normalization':
        continue

    summary['Rows analyzed'] += 1

    arrival_product_type = safe(effective_product_type(item))
    arrival_brand = safe(normalize(matcher, getattr(item, 'brand', None)))
    arrival_volume = safe(normalize(matcher, getattr(item, 'volume', None)))

    same_pt = []
    same_brand = []
    same_volume = []
    matching_all = []
    for master in master_items:
        master_pt = safe(effective_product_type(master))
        master_brand = safe(normalize(matcher, getattr(master, 'brand', None)))
        master_volume = safe(normalize(matcher, getattr(master, 'volume', None)))
        pt_ok = bool(arrival_product_type and master_pt and arrival_product_type == master_pt)
        brand_ok = bool(arrival_brand and master_brand and arrival_brand == master_brand)
        volume_ok = bool(arrival_volume and master_volume and arrival_volume == master_volume)
        if pt_ok:
            same_pt.append(master)
        if brand_ok:
            same_brand.append(master)
        if volume_ok:
            same_volume.append(master)
        if pt_ok and brand_ok and volume_ok:
            matching_all.append(master)

    matching_exists = bool(matching_all)
    if matching_exists:
        summary['Matching MASTER exists'] += 1
    else:
        summary['Matching MASTER absent'] += 1

    candidate_objs = list(getattr(item, 'candidates', []) or [])
    candidate_keys = {candidate_key(candidate) for candidate in candidate_objs}
    appears_in_candidates = any(candidate_key(master) in candidate_keys for master in matching_all)

    lost_stage = ''
    reason = ''

    if not matching_exists:
        lost_stage = 'other'
        reason = (
            f"same ProductType={len(same_pt)}; same Brand={len(same_brand)}; "
            f"same Volume={len(same_volume)}; no MASTER with all three"
        )
    else:
        if appears_in_candidates:
            lost_stage = 'rejection'
            reason = 'Matching MASTER exists and appears in candidates, but REVIEW remained after scoring/rejection'
            summary['Lost after candidate generation'] += 1
        else:
            # Reproduce candidate collection stages
            category_candidates = matcher._lookup_candidates(getattr(item, 'category', None))
            brand_candidates = matcher._lookup_candidates(getattr(item, 'brand', None))
            volume_candidates = matcher._lookup_candidates(getattr(item, 'volume', None))
            narrowed = intersect_by_key([category_candidates, brand_candidates, volume_candidates])
            available_groups = [group for group in (category_candidates, brand_candidates, volume_candidates) if group]
            pair_narrowed = intersect_by_key(available_groups) if len(available_groups) >= 2 else []

            broad_union = []
            for value in [getattr(item, 'sku', None), effective_product_type(item), getattr(item, 'category', None), getattr(item, 'brand', None), getattr(item, 'volume', None), getattr(item, 'aroma', None) or getattr(item, 'variant', None)]:
                for candidate in matcher._lookup_candidates(value):
                    if candidate not in broad_union:
                        broad_union.append(candidate)

            matching_keys = {candidate_key(master) for master in matching_all}
            narrowed_has_match = any(candidate_key(candidate) in matching_keys for candidate in narrowed)
            pair_has_match = any(candidate_key(candidate) in matching_keys for candidate in pair_narrowed)
            broad_has_match = any(candidate_key(candidate) in matching_keys for candidate in broad_union)

            fallback_full = []
            for candidate in matcher.master_items:
                similarity = matcher._source_master_similarity(item.source_name, candidate)
                if similarity >= 0.18:
                    fallback_full.append((candidate, similarity))
            fallback_full.sort(key=lambda entry: entry[1], reverse=True)
            fallback_top12 = [candidate for candidate, _ in fallback_full[:12]]
            fallback_all = [candidate for candidate, _ in fallback_full]
            fallback_has_match = any(candidate_key(candidate) in matching_keys for candidate in fallback_all)
            fallback_top12_has_match = any(candidate_key(candidate) in matching_keys for candidate in fallback_top12)

            if (narrowed and not narrowed_has_match) or (pair_narrowed and not pair_has_match):
                lost_stage = 'pre-filter'
                reason = 'Early intersection path returned before broader candidate expansion and excluded matching MASTER'
                summary['Lost before candidate generation'] += 1
                recoverable += 1
            elif broad_has_match:
                lost_stage = 'candidate generation'
                reason = 'Matching MASTER was available in broader lookups but did not survive into final candidate set'
                summary['Lost during candidate generation'] += 1
                recoverable += 1
            elif fallback_has_match and not fallback_top12_has_match:
                lost_stage = 'candidate limit'
                reason = 'Matching MASTER appears only in fallback similarity search beyond top-12 cap'
                summary['Lost during candidate generation'] += 1
                recoverable += 1
            elif fallback_top12_has_match:
                lost_stage = 'other'
                reason = 'Fallback top-12 contains matching MASTER, but final candidate set still missed it'
                summary['Lost during candidate generation'] += 1
                recoverable += 1
            else:
                lost_stage = 'candidate generation'
                reason = 'No lookup/fallback path surfaced the matching MASTER candidate'
                summary['Lost during candidate generation'] += 1
                recoverable += 1

    rows.append([
        int(getattr(item, 'row_number', 0) or 0),
        safe(getattr(item, 'original_product_name', None) or getattr(item, 'source_name', None)),
        arrival_product_type,
        safe(getattr(item, 'brand', None)),
        safe(getattr(item, 'volume', None)),
        'YES' if matching_exists else 'NO',
        'YES' if appears_in_candidates else 'NO',
        lost_stage,
        reason,
    ])

wb = Workbook()
ws = wb.active
ws.title = 'CANDIDATE_COVERAGE_ANALYSIS'
ws.append([
    'Row',
    'SupplierName',
    'ArrivalProductType',
    'ArrivalBrand',
    'ArrivalVolume',
    'Matching MASTER SKU Exists (YES/NO)',
    'Appears in Candidates (YES/NO)',
    'Lost Stage',
    'Reason',
])
for row in rows:
    ws.append(row)

summary_ws = wb.create_sheet('SUMMARY')
summary_ws.append(['Metric', 'Value'])
for label in [
    'Rows analyzed',
    'Matching MASTER exists',
    'Matching MASTER absent',
    'Lost before candidate generation',
    'Lost during candidate generation',
    'Lost after candidate generation',
]:
    summary_ws.append([label, summary.get(label, 0)])
summary_ws.append(['Estimated recoverable rows by improving candidate generation', recoverable])

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)

print('CANDIDATE_COVERAGE_ANALYSIS_PATH', OUT.as_posix())
print('Rows analyzed', summary.get('Rows analyzed', 0))
print('Matching MASTER exists', summary.get('Matching MASTER exists', 0))
print('Matching MASTER absent', summary.get('Matching MASTER absent', 0))
print('Lost before candidate generation', summary.get('Lost before candidate generation', 0))
print('Lost during candidate generation', summary.get('Lost during candidate generation', 0))
print('Lost after candidate generation', summary.get('Lost after candidate generation', 0))
print('Estimated recoverable rows by improving candidate generation', recoverable)
