from pathlib import Path
from collections import Counter
from openpyxl import Workbook

from svo.engine import Engine
from svo.matcher import Matcher
from svo.business_rules import BusinessRules
from svo.models import effective_product_type

OUT = Path('output/EXACT_MATCH_FAILURES.xlsx')
DATA_DIR = Path('data')
AUTO_MATCH_SCORE_DELTA = 20.0


def safe(value):
    return str(value or '').strip()


def norm(matcher, value):
    return safe(matcher._normalize_value(value))


def candidate_key(candidate):
    return f"{candidate.sku}|{candidate.normalized_key}"


def candidate_details(item, matcher):
    explanation = getattr(item, 'review_explanation', {}) or {}
    detailed = [c for c in explanation.get('candidates', []) if isinstance(c, dict)]
    if not detailed and getattr(item, 'candidates', None):
        detailed = [matcher._score_detail(item, c) for c in item.candidates]
    detailed.sort(key=lambda e: float(e.get('score') or 0.0), reverse=True)
    return detailed


def classify_exact_reason(item, detail):
    reasons = {safe(r).upper() for r in (getattr(item, 'review_reasons', []) or [])}
    rejection_reason = safe(detail.get('rejection_reason')).upper() if isinstance(detail, dict) else ''
    breakdown = dict(detail.get('breakdown') or {}) if isinstance(detail, dict) else {}

    if 'PRICE_CONFLICT' in reasons:
        return 'PRICE_CONFLICT', 'PRICE_CONFLICT triggered after match evaluation'
    if 'MULTIPLE_MATCH' in reasons:
        best_rej = (getattr(item, 'review_explanation', {}) or {}).get('best_candidate_rejected_reason')
        return 'MULTIPLE_MATCH', safe(best_rej) or 'MULTIPLE_MATCH review path retained'
    if 'LOW_SCORE' in reasons:
        best_rej = (getattr(item, 'review_explanation', {}) or {}).get('best_candidate_rejected_reason')
        return 'LOW_SCORE', safe(best_rej) or 'LOW_SCORE review path retained'
    if 'PRODUCT_TYPE_MISMATCH' in reasons or rejection_reason == 'PRODUCT_TYPE_MISMATCH':
        return 'PRODUCT_TYPE', 'PRODUCT_TYPE mismatch blocked match'
    if float(breakdown.get('Brand', 0.0) or 0.0) <= 0.0 and safe(getattr(item, 'brand', None)):
        return 'BRAND', 'Brand score for exact triple candidate is zero'
    return 'Other', safe((getattr(item, 'review_explanation', {}) or {}).get('best_candidate_rejected_reason')) or 'Candidate missing from candidate set'


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
groups = Counter()
rows_analyzed = 0
recoverable_without_master_changes = 0
recoverable_after_scoring_change = 0
recoverable_after_rule_change = 0

for item in price_items:
    if safe(getattr(item, 'status', None)).upper() != 'REVIEW':
        continue

    arrival_pt = norm(matcher, effective_product_type(item))
    arrival_brand = norm(matcher, getattr(item, 'brand', None))
    arrival_volume = norm(matcher, getattr(item, 'volume', None))

    exact_matches = [
        master for master in master_items
        if norm(matcher, effective_product_type(master)) == arrival_pt
        and norm(matcher, getattr(master, 'brand', None)) == arrival_brand
        and norm(matcher, getattr(master, 'volume', None)) == arrival_volume
    ]
    if not exact_matches:
        continue

    rows_analyzed += 1
    recoverable_without_master_changes += 1

    details = candidate_details(item, matcher)
    detail_by_sku = {safe(detail.get('sku')): detail for detail in details}
    exact_details = []
    for master in exact_matches:
        detail = detail_by_sku.get(safe(master.sku))
        if detail is None:
            detail = matcher._score_detail(item, master)
        exact_details.append((master, detail))

    exact_details.sort(key=lambda entry: float(entry[1].get('score') or 0.0), reverse=True)
    chosen_master, chosen_detail = exact_details[0]
    chosen_sku = safe(chosen_master.sku)

    candidate_exists = 'YES' if chosen_sku in detail_by_sku else 'NO'
    candidate_rank = ''
    if candidate_exists == 'YES':
        for index, detail in enumerate(details, start=1):
            if safe(detail.get('sku')) == chosen_sku:
                candidate_rank = index
                break

    total_score = round(float(chosen_detail.get('score') or 0.0), 2)
    breakdown = dict(chosen_detail.get('breakdown') or {})
    breakdown_text = '; '.join(f'{key}={round(float(value), 2)}' for key, value in breakdown.items())
    review_reason = '; '.join(safe(r) for r in (getattr(item, 'review_reasons', []) or []) if safe(r))
    group, exact_reason = classify_exact_reason(item, chosen_detail)
    groups[group] += 1

    if group in {'LOW_SCORE', 'MULTIPLE_MATCH', 'BRAND', 'PRODUCT_TYPE'}:
        recoverable_after_scoring_change += 1
    if group == 'PRICE_CONFLICT':
        recoverable_after_rule_change += 1

    rows.append([
        int(getattr(item, 'row_number', 0) or 0),
        safe(getattr(item, 'original_product_name', None) or getattr(item, 'source_name', None)),
        chosen_sku,
        safe(getattr(chosen_master, 'master_name', None)),
        candidate_exists,
        candidate_rank,
        total_score,
        breakdown_text,
        review_reason,
        exact_reason,
    ])

wb = Workbook()
ws = wb.active
ws.title = 'EXACT_MATCH_FAILURES'
ws.append([
    'Row',
    'SupplierName',
    'MASTER SKU',
    'MASTER_NAME',
    'Candidate exists (YES/NO)',
    'Candidate rank',
    'Total score',
    'Breakdown',
    'Review reason',
    'Exact reason MATCH was rejected',
])
for row in rows:
    ws.append(row)

summary_ws = wb.create_sheet('SUMMARY')
summary_ws.append(['Metric', 'Value'])
summary_ws.append(['Rows analyzed', rows_analyzed])
for label in ['LOW_SCORE', 'PRICE_CONFLICT', 'MULTIPLE_MATCH', 'PRODUCT_TYPE', 'BRAND', 'Other']:
    summary_ws.append([label, groups.get(label, 0)])
summary_ws.append(['Recoverable without MASTER changes', recoverable_without_master_changes])
summary_ws.append(['Recoverable after scoring change', recoverable_after_scoring_change])
summary_ws.append(['Recoverable after rule change', recoverable_after_rule_change])

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)

print('EXACT_MATCH_FAILURES_PATH', OUT.as_posix())
print('Rows analyzed', rows_analyzed)
print('Recoverable without MASTER changes', recoverable_without_master_changes)
print('Recoverable after scoring change', recoverable_after_scoring_change)
print('Recoverable after rule change', recoverable_after_rule_change)
for label in ['LOW_SCORE', 'PRICE_CONFLICT', 'MULTIPLE_MATCH', 'PRODUCT_TYPE', 'BRAND', 'Other']:
    print(label, groups.get(label, 0))
