from pathlib import Path
from collections import Counter
from openpyxl import Workbook

from svo.engine import Engine
from svo.matcher import Matcher
from svo.business_rules import BusinessRules
from svo.models import effective_product_type

OUT = Path('output/EXACT_MATCH_RECOVERY_ANALYSIS.xlsx')
DATA_DIR = Path('data')
AUTO_MATCH_SCORE_DELTA = 20.0


def safe(value):
    return str(value or '').strip()


def norm(matcher, value):
    return safe(matcher._normalize_value(value))


def candidate_details(item, matcher):
    explanation = getattr(item, 'review_explanation', {}) or {}
    detailed = [c for c in explanation.get('candidates', []) if isinstance(c, dict)]
    if not detailed and getattr(item, 'candidates', None):
        detailed = [matcher._score_detail(item, c) for c in item.candidates]
    detailed.sort(key=lambda e: float(e.get('score') or 0.0), reverse=True)
    return detailed


def exact_matches_for(item, matcher, master_items):
    arrival_pt = norm(matcher, effective_product_type(item))
    arrival_brand = norm(matcher, getattr(item, 'brand', None))
    arrival_volume = norm(matcher, getattr(item, 'volume', None))
    return [
        master for master in master_items
        if norm(matcher, effective_product_type(master)) == arrival_pt
        and norm(matcher, getattr(master, 'brand', None)) == arrival_brand
        and norm(matcher, getattr(master, 'volume', None)) == arrival_volume
    ]


def name_score(breakdown):
    return round(float(breakdown.get('Aroma', 0.0) or 0.0) + float(breakdown.get('Color', 0.0) or 0.0) + float(breakdown.get('Keywords', 0.0) or 0.0), 2)


def other_score(total, breakdown):
    used = float(breakdown.get('ProductType', 0.0) or 0.0) + float(breakdown.get('Brand', 0.0) or 0.0) + float(breakdown.get('Volume', 0.0) or 0.0) + name_score(breakdown)
    return round(float(total or 0.0) - used, 2)


def winner_loser_reason(best_breakdown, exact_breakdown):
    diffs = {
        'Name': round(name_score(best_breakdown) - name_score(exact_breakdown), 2),
        'Brand': round(float(best_breakdown.get('Brand', 0.0) or 0.0) - float(exact_breakdown.get('Brand', 0.0) or 0.0), 2),
        'Volume': round(float(best_breakdown.get('Volume', 0.0) or 0.0) - float(exact_breakdown.get('Volume', 0.0) or 0.0), 2),
        'ProductType': round(float(best_breakdown.get('ProductType', 0.0) or 0.0) - float(exact_breakdown.get('ProductType', 0.0) or 0.0), 2),
    }
    ordered = sorted(diffs.items(), key=lambda item: item[1], reverse=True)
    positive = [(name, delta) for name, delta in ordered if delta > 0]
    negative = [(name, delta) for name, delta in ordered if delta < 0]
    why_wins = ', '.join(f'{name}+{delta:.2f}' for name, delta in positive[:3]) if positive else 'No component advantage'
    why_loses = ', '.join(f'{name}{delta:.2f}' for name, delta in negative[:3]) if negative else 'No component deficit'
    return why_wins, why_loses, diffs


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
rows_analyzed = 0
minimal_change = None
component_recovery = Counter()

for item in price_items:
    if safe(getattr(item, 'status', None)).upper() != 'REVIEW':
        continue
    exact_matches = exact_matches_for(item, matcher, master_items)
    if not exact_matches:
        continue

    details = candidate_details(item, matcher)
    reasons = {safe(r).upper() for r in (getattr(item, 'review_reasons', []) or [])}
    if 'PRICE_CONFLICT' in reasons:
        continue
    # limit to the 15 exact failures: still review even though exact triple exists
    rows_analyzed += 1

    best = details[0] if details else None
    if best is None:
        continue

    best_breakdown = dict(best.get('breakdown') or {})
    best_total = round(float(best.get('score') or 0.0), 2)

    exact_details = [matcher._score_detail(item, master) for master in exact_matches]
    exact_details.sort(key=lambda entry: float(entry.get('score') or 0.0), reverse=True)
    exact_detail = exact_details[0]
    exact_breakdown = dict(exact_detail.get('breakdown') or {})
    exact_total = round(float(exact_detail.get('score') or 0.0), 2)
    difference = round(best_total - exact_total, 2)
    if minimal_change is None or difference < minimal_change:
        minimal_change = difference

    why_candidate1_wins, why_exact_loses, diffs = winner_loser_reason(best_breakdown, exact_breakdown)

    if diffs['Name'] > 0:
        component_recovery['Name'] += 1
    elif diffs['Brand'] > 0:
        component_recovery['Brand'] += 1
    elif diffs['ProductType'] > 0:
        component_recovery['ProductType'] += 1
    elif diffs['Volume'] > 0:
        component_recovery['Volume'] += 1
    else:
        component_recovery['Other'] += 1

    rows.append([
        int(getattr(item, 'row_number', 0) or 0),
        safe(best.get('sku')),
        safe(exact_detail.get('sku')),
        best_total,
        exact_total,
        difference,
        name_score(exact_breakdown),
        round(float(exact_breakdown.get('Brand', 0.0) or 0.0), 2),
        round(float(exact_breakdown.get('Volume', 0.0) or 0.0), 2),
        round(float(exact_breakdown.get('ProductType', 0.0) or 0.0), 2),
        other_score(exact_total, exact_breakdown),
        why_candidate1_wins,
        why_exact_loses,
    ])

wb = Workbook()
ws = wb.active
ws.title = 'EXACT_MATCH_RECOVERY_ANALYSIS'
ws.append([
    'Row',
    'Candidate1 SKU',
    'Exact MASTER SKU',
    'Candidate1 TotalScore',
    'Exact MASTER TotalScore',
    'Difference',
    'NameScore',
    'BrandScore',
    'VolumeScore',
    'ProductTypeScore',
    'OtherScore',
    'Why Candidate1 wins',
    'Why Exact MASTER loses',
])
for row in rows:
    ws.append(row)
OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)

max_recoverable = rows_analyzed
minimal_change = round(minimal_change or 0.0, 2)
recommend_component = component_recovery.most_common(1)[0][0] if component_recovery else 'Other'
if recommend_component == 'Name':
    recommendation = 'Reduce generic name-weight dominance by slightly down-weighting Keywords/source-name similarity when an exact ProductType+Brand+Volume MASTER exists.'
elif recommend_component == 'Brand':
    recommendation = 'Increase brand weight modestly for exact ProductType+Volume matches.'
elif recommend_component == 'ProductType':
    recommendation = 'Increase ProductType weight only for exact Brand+Volume matches.'
elif recommend_component == 'Volume':
    recommendation = 'Increase Volume weight for exact ProductType+Brand matches.'
else:
    recommendation = 'Add a narrow exact ProductType+Brand+Volume preference before generic name-based tie-breaking.'

print('EXACT_MATCH_RECOVERY_ANALYSIS_PATH', OUT.as_posix())
print('Maximum recoverable MATCH', max_recoverable)
print('Minimal scoring change required', minimal_change)
print('Recommend ONE scoring improvement', recommendation)
print('Dominant recovery component', recommend_component)
