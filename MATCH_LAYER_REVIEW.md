# MATCH LAYER ARCHITECTURE REVIEW

## Scope
Reviewed modules:
- [svo/matcher.py](svo/matcher.py)
- [svo/business_rules.py](svo/business_rules.py)
- [svo/normalizer.py](svo/normalizer.py)
- [svo/dictionary.py](svo/dictionary.py)
- [svo/models.py](svo/models.py) (matching-related models only)
- [svo/revision_name_canonicalizer.py](svo/revision_name_canonicalizer.py)
- [config/canonicalization/brand_alias.yaml](config/canonicalization/brand_alias.yaml)
- [config/canonicalization/category_alias.yaml](config/canonicalization/category_alias.yaml)
- [config/canonicalization/aroma_alias.yaml](config/canonicalization/aroma_alias.yaml)
- [config/canonicalization/color_alias.yaml](config/canonicalization/color_alias.yaml)
- [config/canonicalization/marketing_words.yaml](config/canonicalization/marketing_words.yaml)
- [config/canonicalization/volume_alias.yaml](config/canonicalization/volume_alias.yaml)

Out of scope: loader/reporter/excel internals except where needed to verify dependency direction and pipeline wiring in [svo/engine.py](svo/engine.py).

## Executive Summary
The Match Layer is functionally coherent and mostly respects dependency direction, with data model and dictionary separation already in place. The largest architectural risks are concentration of responsibilities in [svo/matcher.py](svo/matcher.py) and [svo/normalizer.py](svo/normalizer.py), plus hardcoded business/domain exceptions in code that should be externalized into configuration.

Dependency constraints requested in review are satisfied:
- Matcher does not depend on Reporter/Excel.
- BusinessRules does not depend on Loader.
- Normalizer does not depend on Matcher.

Primary issues:
- SRP drift in Matcher and Normalizer (heuristics, NLP/tokenization, scoring, policy thresholds all mixed).
- Repeated normalization/tokenization and repeated MASTER scans in hot paths.
- Rule placement inconsistency (some domain exceptions in BusinessRules, others in Normalizer).
- Rule configuration source [config/rules.json](config/rules.json#L1) is currently empty, while multiple rules are hardcoded.

## Strengths
- Clean core module boundaries by intent: normalization, matching, post-match business corrections.
- Dictionary loading is centralized in [svo/dictionary.py](svo/dictionary.py#L15).
- Canonicalization for revision documents is configuration-driven via YAML files loaded in [svo/revision_name_canonicalizer.py](svo/revision_name_canonicalizer.py#L30-L35).
- Pipeline order in engine is explicit and easy to follow in [svo/engine.py](svo/engine.py#L128-L135).

## 1) Single Responsibility Principle
### Clear Violations
1. Matcher has multiple responsibilities.
Evidence:
- Candidate indexing and retrieval: [svo/matcher.py](svo/matcher.py#L16), [svo/matcher.py](svo/matcher.py#L36)
- Similarity/NLP token canonicalization: [svo/matcher.py](svo/matcher.py#L148), [svo/matcher.py](svo/matcher.py#L186)
- Scoring policy and threshold decisions: [svo/matcher.py](svo/matcher.py#L93), [svo/matcher.py](svo/matcher.py#L423), [svo/matcher.py](svo/matcher.py#L436), [svo/matcher.py](svo/matcher.py#L447)
- Final decision + review reason generation: [svo/matcher.py](svo/matcher.py#L382), [svo/matcher.py](svo/matcher.py#L395)

2. Normalizer has multiple responsibilities.
Evidence:
- Dictionary loading and rule merge bootstrap: [svo/normalizer.py](svo/normalizer.py#L133), [svo/normalizer.py](svo/normalizer.py#L171), [svo/normalizer.py](svo/normalizer.py#L236)
- Category/brand/volume parsing: [svo/normalizer.py](svo/normalizer.py#L304), [svo/normalizer.py](svo/normalizer.py#L280), [svo/normalizer.py](svo/normalizer.py#L356)
- Aroma cleanup + transliteration + stemming: [svo/normalizer.py](svo/normalizer.py#L405), [svo/normalizer.py](svo/normalizer.py#L438), [svo/normalizer.py](svo/normalizer.py#L503)
- Embedded business exceptions: [svo/normalizer.py](svo/normalizer.py#L199), [svo/normalizer.py](svo/normalizer.py#L473), [svo/normalizer.py](svo/normalizer.py#L481), [svo/normalizer.py](svo/normalizer.py#L489-L500)

3. BusinessRules mixes rule orchestration and data-access strategy.
Evidence:
- Rule application orchestration: [svo/business_rules.py](svo/business_rules.py#L13)
- Master lookup scans and selection logic inside same class: [svo/business_rules.py](svo/business_rules.py#L108), [svo/business_rules.py](svo/business_rules.py#L115), [svo/business_rules.py](svo/business_rules.py#L135)

### Borderline (Acceptable but watch)
- ArrivalItem carries both domain state and diagnostic payload (confidence/candidates/reasons): [svo/models.py](svo/models.py#L66-L70). This is practical, but couples pipeline stages.

## 2) Dependency Direction
### Result
Pass for requested constraints.

### Evidence
- Matcher imports only models and stdlib in [svo/matcher.py](svo/matcher.py#L2-L4). No Reporter/Excel dependency found.
- BusinessRules imports models and stdlib only in [svo/business_rules.py](svo/business_rules.py#L6). No Loader dependency found.
- Normalizer imports models + dictionary only in [svo/normalizer.py](svo/normalizer.py#L5-L6). No Matcher dependency found.

### Additional observation
- Top-level orchestrator [svo/engine.py](svo/engine.py#L8-L16) depends on all layers including Reporter; this is expected at composition boundary.

## 3) Matching Pipeline
### Implemented Pipeline
Input
-> Normalization
-> Dictionary lookup / candidate retrieval
-> Business Rules
-> Final Match
-> Result

Concrete flow in engine:
1. Load MASTER and document rows.
2. Normalize each item: [svo/engine.py](svo/engine.py#L128)
3. Optional revision canonicalization: [svo/engine.py](svo/engine.py#L131)
4. Run matcher for all rows: [svo/engine.py](svo/engine.py#L134)
5. Apply business overrides: [svo/engine.py](svo/engine.py#L135)
6. Compute stats and write outputs/review report: [svo/engine.py](svo/engine.py#L138-L160)

### Duplicated work / unnecessary passes
1. Multiple full passes over document_items in one run:
- normalize loop [svo/engine.py](svo/engine.py#L128)
- optional canonicalizer list pass [svo/engine.py](svo/engine.py#L131)
- matcher pass [svo/matcher.py](svo/matcher.py#L471)
- business rules pass [svo/business_rules.py](svo/business_rules.py#L13)
- stat passes via two sums [svo/engine.py](svo/engine.py#L138-L139)

2. In matcher, repeated candidate lookup passes and repeated normalization:
- exact lookup by sku + four metadata fields [svo/matcher.py](svo/matcher.py#L69-L82)
- then candidate collection repeats lookups and intersections [svo/matcher.py](svo/matcher.py#L333-L369)

3. Fallback scoring triggers full MASTER scan per hard row:
- [svo/matcher.py](svo/matcher.py#L371-L376)

## 4) Performance Review
### Findings
1. Repeated iterations over MASTER.
- Matcher fallback scans entire master per item: [svo/matcher.py](svo/matcher.py#L371)
- Business rules scan master for each checked item: [svo/business_rules.py](svo/business_rules.py#L110), [svo/business_rules.py](svo/business_rules.py#L119), [svo/business_rules.py](svo/business_rules.py#L136)

2. Repeated normalization/tokenization.
- String normalization called repeatedly across scoring and metadata checks: [svo/matcher.py](svo/matcher.py#L29), [svo/matcher.py](svo/matcher.py#L93)
- source/master tokenization repeated for same master rows in fallback similarity: [svo/matcher.py](svo/matcher.py#L274-L288)

3. Repeated string allocations.
- master_text assembled per comparison in fallback similarity: [svo/matcher.py](svo/matcher.py#L278)
- Cleanup pipeline in normalizer performs many regex replacements per item: [svo/normalizer.py](svo/normalizer.py#L405-L434)

4. Unnecessary object/list creation.
- Defensive copy of master list and duplicate checks in index build: [svo/matcher.py](svo/matcher.py#L11), [svo/matcher.py](svo/matcher.py#L24)
- Rebuilding removal terms list per item in cleanup: [svo/normalizer.py](svo/normalizer.py#L411-L419)

### Improvements (no behaviour change)
1. Precompute and cache normalized fields and tokenized master representations once during Matcher initialization.
2. Build O(1) master lookup maps for BusinessRules (sku map, keyed subsets) once in constructor.
3. Precompile reusable regex patterns and precomputed removable terms in Normalizer constructor.
4. Collapse post-match counting into one pass.
5. Replace list membership dedupe patterns with set-backed dedupe where order is not semantically required.

## 5) Business Rules Placement Review
### Rules observed
1. Bundle keep-in-review rule: [svo/business_rules.py](svo/business_rules.py#L39-L40)
Verdict: BusinessRules (correct location).

2. LOTOS SKU disambiguation to SKU-064 with NO_VOLUME gate: [svo/business_rules.py](svo/business_rules.py#L42-L58)
Verdict: BusinessRules for now; should become declarative rule data (currently hardcoded).

3. BOTANIC 1,44 disambiguation: [svo/business_rules.py](svo/business_rules.py#L61-L77), [svo/business_rules.py](svo/business_rules.py#L115-L133)
Verdict: BusinessRules for now; partial rule terms should move to canonicalization/dictionary where possible.

4. BOSSFIX diapers default size-1 when size absent: [svo/business_rules.py](svo/business_rules.py#L81-L104), [svo/business_rules.py](svo/business_rules.py#L135-L146)
Verdict: BusinessRules (correct), but matcher-independent declarative expression would improve maintainability.

5. Default brand by category (SVO fallback) in normalizer: [svo/normalizer.py](svo/normalizer.py#L199-L212)
Verdict: Wrong place. This is a domain/business policy and should be data-driven (canonicalization or business rules config).

6. Category/brand-specific aroma overrides ARGAN OIL/VELVET and token surgery for ROMANTIK/ROSE, COLOR/BABY/PASSION FRUIT: [svo/normalizer.py](svo/normalizer.py#L473-L500)
Verdict: Mostly wrong place. These are business/domain exception rules and belong in canonicalization data or rule config, not hardcoded normalizer logic.

## 6) Canonicalization Separation Check
### What is good
- Revision canonicalization dictionaries are externalized to YAML and loaded centrally: [svo/revision_name_canonicalizer.py](svo/revision_name_canonicalizer.py#L30-L35), [svo/revision_name_canonicalizer.py](svo/revision_name_canonicalizer.py#L63-L69).

### Hardcoded mappings still in code (should move to YAML/config)
1. Normalizer default categories/brands/volumes/garbage tokens in class constants:
- [svo/normalizer.py](svo/normalizer.py#L12-L71)

2. Hardcoded category detection keyword tree:
- [svo/normalizer.py](svo/normalizer.py#L304-L353)

3. Hardcoded aroma refinement exceptions:
- [svo/normalizer.py](svo/normalizer.py#L473-L500)

4. Hardcoded aroma stopwords and transliteration map in matcher:
- [svo/matcher.py](svo/matcher.py#L131-L146)

5. Rule repository exists but unused:
- [config/rules.json](config/rules.json#L1)

## 7) Extensibility Estimate
### Add new brand
Difficulty: Medium.
Likely files:
- [config/brands.json](config/brands.json)
- [config/canonicalization/brand_alias.yaml](config/canonicalization/brand_alias.yaml)
- Possibly [svo/normalizer.py](svo/normalizer.py#L23-L31) if defaults are still relied on
- Matching tests in tests folder

### Add new product category
Difficulty: Medium to High (currently split logic).
Likely files:
- [config/categories.json](config/categories.json)
- [config/canonicalization/category_alias.yaml](config/canonicalization/category_alias.yaml)
- [svo/normalizer.py](svo/normalizer.py#L304-L353) when keyword tree lacks it
- Tests

### Add new aroma
Difficulty: Medium.
Likely files:
- [config/aromas.json](config/aromas.json)
- [config/canonicalization/aroma_alias.yaml](config/canonicalization/aroma_alias.yaml)
- Potentially [svo/normalizer.py](svo/normalizer.py#L73-L113) if stop-token behavior conflicts
- Tests

### Add new matching rule
Difficulty: Medium to High.
Likely files:
- [svo/business_rules.py](svo/business_rules.py)
- Potential support in [config/rules.json](config/rules.json)
- Tests

Reason for higher difficulty: no active declarative rule engine yet; logic is code-first.

## 8) Technical Debt
1. Oversized classes:
- [svo/matcher.py](svo/matcher.py)
- [svo/normalizer.py](svo/normalizer.py)

2. Duplicated text normalization/transliteration logic across modules:
- [svo/matcher.py](svo/matcher.py#L29), [svo/matcher.py](svo/matcher.py#L148)
- [svo/normalizer.py](svo/normalizer.py#L276), [svo/normalizer.py](svo/normalizer.py#L503)

3. Hidden dependency on review reasons schema:
- BusinessRules depends on NO_VOLUME reason semantics from matcher: [svo/business_rules.py](svo/business_rules.py#L35-L36)

4. Mixed rule sources (YAML + JSON + code constants + hardcoded branches) increase cognitive load.

5. Empty rules config suggests intended but incomplete externalization:
- [config/rules.json](config/rules.json#L1)

## Weaknesses
- SRP violations in core classes reduce readability and local reasoning.
- Rule placement is inconsistent across Normalizer and BusinessRules.
- Performance hotspots in repeated scans/tokenization may grow nonlinearly with MASTER size.
- Hardcoded exceptions make onboarding new categories/brands/rules riskier.

## Recommended Refactoring
No behavior changes requested. Recommended architecture direction only:
1. Extract matcher text similarity/tokenization into a dedicated scorer component with precomputed master features.
2. Convert BusinessRules master scans to indexed lookups initialized once.
3. Move normalizer exception branches into canonicalization/rules config.
4. Introduce declarative rule format in [config/rules.json](config/rules.json) and keep [svo/business_rules.py](svo/business_rules.py) as execution engine.
5. Consolidate normalization utilities into shared reusable helper to remove divergence.

## Things That Should NOT Be Changed
1. Layer order in orchestrator (normalize -> match -> business rules -> output) in [svo/engine.py](svo/engine.py#L128-L135).
2. Externalized canonicalization YAML mechanism for revision data in [svo/revision_name_canonicalizer.py](svo/revision_name_canonicalizer.py#L30-L35).
3. Lightweight domain models in [svo/models.py](svo/models.py) as shared contracts.
4. Separation of dictionary loading into [svo/dictionary.py](svo/dictionary.py#L15).

## 9) Overall Evaluation (1-10)
- Architecture: 6.5
- Readability: 6
- Maintainability: 5.5
- Performance: 6
- Extensibility: 5.5
- Testability: 6

Overall: workable and improving, but currently constrained by hardcoded rule paths and concentration of responsibilities in two central classes.
