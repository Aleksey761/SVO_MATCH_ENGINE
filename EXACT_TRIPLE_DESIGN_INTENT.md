# Exact Triple Design Intent

## Scope
Repository-wide search for:
- _preferred_exact_triple_candidate
- exact_triple_candidates

## All References Found

### Production logic
1. Definition of exact-triple matcher predicate:
- [svo/matcher.py](svo/matcher.py#L627)
- Why it matters: establishes exact triple as ProductType + Brand + Volume equality (with non-empty normalized values).

2. Definition of preference selector:
- [svo/matcher.py](svo/matcher.py#L647)
- Why it matters: this is the only place where exact_triple_candidates is created and evaluated.

3. Internal exact_triple_candidates flow:
- Build list: [svo/matcher.py](svo/matcher.py#L655)
- Empty set gate: [svo/matcher.py](svo/matcher.py#L660)
- Sort by score desc: [svo/matcher.py](svo/matcher.py#L663)
- Uniqueness gate len == 1: [svo/matcher.py](svo/matcher.py#L665)
- Winner/runner-up gap check when len > 1: [svo/matcher.py](svo/matcher.py#L668)

4. Call site in match decision:
- [svo/matcher.py](svo/matcher.py#L739)
- Why it matters: preferred exact-triple result is checked before normal threshold/margin auto-match gate.

### Tests
5. Direct method invocation in test:
- [tests/test_master_first.py](tests/test_master_first.py#L186)
- Context: verifies that unique exact-triple candidate can be preferred in tie-range scenario.

### Diagnostics artifacts
6. Runtime trace output mention:
- [output/SINGLE_ROW_DECISION_TRACE.txt](output/SINGLE_ROW_DECISION_TRACE.txt#L92)
- Context: observed value of _preferred_exact_triple_candidate() during one traced decision.

## Why Uniqueness (len == 1) Is Required
In the selector logic at [svo/matcher.py](svo/matcher.py#L665), len == 1 is the unambiguous case:
- If exactly one exact-triple candidate exists, the function can safely return it without tie arbitration among exact-triple peers.
- If more than one exact-triple candidate exists, uniqueness is not satisfied, so the code requires a second disambiguation rule (score gap vs confidence_margin) before selecting one.
- If that disambiguation fails (gap < margin), function returns None, which keeps the row on downstream REVIEW path unless other gates resolve it.

This means uniqueness is used as the first deterministic gate to avoid arbitrary selection among multiple structurally equivalent (exact-triple) candidates.

## Test Coverage: Is There an Explicit Test That Multiple Exact-Triples Must Remain REVIEW?
Short answer: no explicit test by name/intent says exactly that.

What exists:
1. Generic multi-candidate REVIEW behavior is tested:
- [tests/test_master_first.py](tests/test_master_first.py#L76)
- Assertions at [tests/test_master_first.py](tests/test_master_first.py#L89) and [tests/test_master_first.py](tests/test_master_first.py#L91)
- This test verifies REVIEW + MULTIPLE_MATCH when candidates are close.

2. Unique exact-triple preference is explicitly tested:
- [tests/test_master_first.py](tests/test_master_first.py#L131)
- Direct selector assertion at [tests/test_master_first.py](tests/test_master_first.py#L186)
- Confirms unique exact-triple candidate can be auto-selected.

What is not found:
- No test that explicitly states/labels the scenario as: multiple exact-triple candidates must remain REVIEW.
- No direct assertion on selector behavior like: len(exact_triple_candidates) > 1 and insufficient gap => preferred is None and final status REVIEW.

## Conclusion
Design intent in code is two-stage for exact triples:
1. Uniqueness shortcut (len == 1) for deterministic selection.
2. If multiple exact triples exist, require score-gap disambiguation; otherwise do not prefer and allow REVIEW gating.

Current tests explicitly cover unique exact-triple preference and generic multi-candidate REVIEW, but do not explicitly pin the named requirement that multiple exact-triple candidates must remain REVIEW.