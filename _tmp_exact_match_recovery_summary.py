from pathlib import Path
from collections import Counter

from svo.engine import Engine
from svo.matcher import Matcher
from svo.business_rules import BusinessRules
from svo.models import effective_product_type

out = Path('_tmp_exact_match_recovery_summary.txt')
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


engine = Engine()
master_items = engine.loader.load_master(DATA_DIR / 'MASTER.xlsx')
price_candidates = sorted([p for p in DATA_DIR.glob('PRC*.xlsx') if p.is_file()], key=lambda p: p.stat().st_mtime)
price_file = price_candidates[-1]
price_items = engine.price_loader.load(price_file)
for item in price_items:
    engine.normalizer.normalize(item)
matcher = Matcher(master_items, auto_resolve_multiple_candidates=True, auto_match_score_delta=AUTO_MATCH_SCORE_DELTA)
unresolved, _, _ = engine._apply_learning_map_matches(price_items, master_items)
matcher.match_all(unresolved)
BusinessRules(master_items).apply(price_items)
engine._validate_price_name_sku_conflicts(price_items)

rows_analyzed = 0
minimal_change = None
component_recovery = Counter()

for item in price_items:
    if safe(getattr(item, 'status', None)).upper() != 'REVIEW':
        continue
    exact_matches = exact_matches_for(item, matcher, master_items)
    if not exact_matches:
        continue
    reasons = {safe(r).upper() for r in (getattr(item, 'review_reasons', []) or [])}
    if 'PRICE_CONFLICT' in reasons:
        continue
    details = candidate_details(item, matcher)
    if not details:
        continue
    rows_analyzed += 1
    best = details[0]
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
    diffs = {
        'Name': round(name_score(best_breakdown) - name_score(exact_breakdown), 2),
        'Brand': round(float(best_breakdown.get('Brand', 0.0) or 0.0) - float(exact_breakdown.get('Brand', 0.0) or 0.0), 2),
        'Volume': round(float(best_breakdown.get('Volume', 0.0) or 0.0) - float(exact_breakdown.get('Volume', 0.0) or 0.0), 2),
        'ProductType': round(float(best_breakdown.get('ProductType', 0.0) or 0.0) - float(exact_breakdown.get('ProductType', 0.0) or 0.0), 2),
    }
    ordered = sorted(diffs.items(), key=lambda item: item[1], reverse=True)
    top = ordered[0][0] if ordered and ordered[0][1] > 0 else 'Other'
    component_recovery[top] += 1

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

lines = [
    f'Maximum recoverable MATCH: {rows_analyzed}',
    f'Minimal scoring change required: {round(minimal_change or 0.0, 2)}',
    f'Dominant recovery component: {recommend_component}',
    f'Recommendation: {recommendation}',
]
out.write_text('\n'.join(lines), encoding='utf-8')
