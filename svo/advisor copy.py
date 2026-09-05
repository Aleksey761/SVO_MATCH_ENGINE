from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ArrivalItem


@dataclass(frozen=True)
class AdviceRule:
    severity: str
    action: str
    gain_ratio: float


ADVICE_RULES: dict[str, AdviceRule] = {
    "MULTIPLE_MATCH": AdviceRule(
        severity="HIGH",
        action="Refine disambiguation rules for variant, aroma, and volume in MASTER and aliases.",
        gain_ratio=0.70,
    ),
    "UNKNOWN_BRAND": AdviceRule(
        severity="HIGH",
        action="Add missing brand aliases or dictionary entries for the detected source names.",
        gain_ratio=0.90,
    ),
    "NO_VOLUME": AdviceRule(
        severity="MEDIUM",
        action="Expand volume parsing rules and normalize missing volume expressions.",
        gain_ratio=0.50,
    ),
    "LOW_SCORE": AdviceRule(
        severity="MEDIUM",
        action="Improve token normalization and matching rules for weak-scoring products.",
        gain_ratio=0.40,
    ),
    "NO_REVIEW_REASON": AdviceRule(
        severity="LOW",
        action="Review unmatched items manually and add targeted normalization rules if patterns repeat.",
        gain_ratio=0.20,
    ),
}

DEFAULT_RULE = AdviceRule(
    severity="LOW",
    action="Review the unresolved products manually and add a focused rule only if the pattern repeats.",
    gain_ratio=0.25,
)

SEVERITY_ORDER = ("HIGH", "MEDIUM", "LOW")


def _rule_for_reason(reason: str) -> AdviceRule:
    return ADVICE_RULES.get(reason, DEFAULT_RULE)


def _review_items(items: list["ArrivalItem"]) -> list["ArrivalItem"]:
    return [item for item in items if item.status == "REVIEW"]


def _reason_groups(items: list["ArrivalItem"]) -> dict[str, list["ArrivalItem"]]:
    groups: dict[str, list[ArrivalItem]] = {}
    for item in _review_items(items):
        reasons = item.review_reasons or ["NO_REVIEW_REASON"]
        for reason in reasons:
            groups.setdefault(reason, []).append(item)
    return groups


def _estimate_gain_for_count(reason: str, count: int) -> int:
    if count <= 0:
        return 0
    ratio = _rule_for_reason(reason).gain_ratio
    estimated = round(count * ratio)
    return max(1, min(count, estimated))


def _estimate_total_gain(review_items: list["ArrivalItem"]) -> int:
    estimated_gain = 0.0
    for item in review_items:
        reasons = item.review_reasons or ["NO_REVIEW_REASON"]
        best_ratio = max(_rule_for_reason(reason).gain_ratio for reason in reasons)
        estimated_gain += best_ratio
    return min(len(review_items), ceil(estimated_gain))


def format_improvement_plan(
    *,
    total_rows: int,
    match_count: int,
    review_count: int,
    items: list["ArrivalItem"],
) -> str:
    review_items = _review_items(items)
    reason_groups = _reason_groups(items)
    projected_gain = _estimate_total_gain(review_items)
    projected_match = min(total_rows, match_count + projected_gain)
    projected_coverage = (projected_match / total_rows * 100.0) if total_rows else 0.0

    lines = [
        "========================================",
        "IMPROVEMENT PLAN",
        "----------------------------------------",
        "REVIEW SUMMARY",
        f"TOTAL ROWS        : {total_rows}",
        f"MATCH             : {match_count}",
        f"REVIEW            : {review_count}",
        f"UNIQUE REASONS    : {len(reason_groups)}",
        "----------------------------------------",
        "REVIEW REASONS",
    ]

    if not reason_groups:
        lines.append("- none")
    else:
        for reason in sorted(reason_groups, key=lambda value: (-len(reason_groups[value]), value)):
            reason_items = reason_groups[reason]
            rule = _rule_for_reason(reason)
            expected_gain = _estimate_gain_for_count(reason, len(reason_items))
            lines.append(f"REASON            : {reason}")
            lines.append(f"COUNT             : {len(reason_items)}")
            lines.append(f"SEVERITY          : {rule.severity}")
            lines.append(f"RECOMMENDED ACTION: {rule.action}")
            lines.append(f"EXPECTED MATCH GAIN: {expected_gain}")
            lines.append("ITEMS             :")
            for item in reason_items:
                lines.append(f"- ROW {item.row_number}: {item.source_name}")
            lines.append("----------------------------------------")

    severity_summary = Counter()
    for reason, reason_items in reason_groups.items():
        severity_summary[_rule_for_reason(reason).severity] += _estimate_gain_for_count(reason, len(reason_items))

    lines.append("PRIORITY SUMMARY")
    for severity in SEVERITY_ORDER:
        lines.append(f"{severity:<18}: {severity_summary.get(severity, 0)}")

    lines.extend([
        "----------------------------------------",
        "FINAL FORECAST",
        f"PROJECTED MATCH   : {projected_match}",
        f"PROJECTED COVERAGE: {projected_coverage:.2f}%",
        "If all recommendations are implemented, the projected coverage is based on the best estimated gain per REVIEW item.",
        "========================================",
    ])

    return "\n".join(lines)


def generate_improvement_plan(
    *,
    total_rows: int,
    match_count: int,
    review_count: int,
    items: list["ArrivalItem"],
    output_file: str | Path = "output/IMPROVEMENT_PLAN.txt",
) -> str:
    text = format_improvement_plan(
        total_rows=total_rows,
        match_count=match_count,
        review_count=review_count,
        items=items,
    )

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")
    return text
