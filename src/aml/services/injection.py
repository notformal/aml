"""Rule Injection — three modes for applying learned rules.

1. Context Enrichment — add rules to LLM system prompt
2. Parameter Override — directly modify pipeline parameters
3. Post-filter — validate output against quality gate rules
"""

import logging
import operator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aml.repositories.rule import list_rules
from aml.services.context import format_episodes_for_prompt, format_rules_for_prompt

logger = logging.getLogger(__name__)

# ── Condition evaluators ──

_OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "in": lambda a, b: a in b,
    "contains": lambda a, b: b in a,
}


def evaluate_condition(condition: dict | str, context: dict) -> bool:
    """Evaluate a structured condition against context.

    Supports: {"field": "category", "op": "eq", "value": "swimwear"}
    Or simple string equality: "category=swimwear"
    """
    if isinstance(condition, str):
        if "=" in condition:
            field, value = condition.split("=", 1)
            return str(context.get(field.strip())) == value.strip()
        return True

    field = condition.get("field")
    op_name = condition.get("op", "eq")
    value = condition.get("value")

    if not field:
        return True

    ctx_value = context.get(field)
    if ctx_value is None:
        return False

    op_fn = _OPS.get(op_name, operator.eq)
    try:
        return op_fn(ctx_value, value)
    except (TypeError, ValueError):
        return False


# ── Context Enrichment ──

async def enrich_prompt(
    db: AsyncSession,
    module_id: str,
    base_prompt: str,
    task_description: str = "",
    min_confidence: float = 0.6,
) -> str:
    """Add learned rules and similar cases to an LLM prompt."""
    rules = await list_rules(db, module_id=module_id, min_confidence=min_confidence)

    if not rules:
        return base_prompt

    rules_block = format_rules_for_prompt(rules)

    enriched = f"""{base_prompt}

{rules_block}"""

    return enriched


# ── Parameter Override ──

async def apply_rules_to_params(
    db: AsyncSession,
    module_id: str,
    params: dict,
    context: dict,
    min_confidence: float = 0.8,
) -> dict:
    """Apply high-confidence rules to pipeline parameters.

    Only rules with rule_structured and confidence >= min_confidence are applied.
    Returns modified params dict with _applied_rules list.
    """
    rules = await list_rules(db, module_id=module_id, min_confidence=min_confidence)

    modified = params.copy()
    applied = []

    for rule in rules:
        if not rule.rule_structured:
            continue

        rs = rule.rule_structured

        # Check condition
        condition = rs.get("condition")
        if condition and not evaluate_condition(condition, context):
            continue

        param_name = rs.get("param")
        if not param_name:
            continue

        # Direct value set
        if "value" in rs:
            modified[param_name] = rs["value"]
            applied.append(str(rule.id))

        # Value range clamp
        elif "value_range" in rs and len(rs["value_range"]) == 2:
            current = modified.get(param_name)
            if current is not None:
                try:
                    modified[param_name] = max(
                        rs["value_range"][0],
                        min(rs["value_range"][1], float(current)),
                    )
                    applied.append(str(rule.id))
                except (TypeError, ValueError):
                    pass

    modified["_applied_rules"] = applied
    return modified


# ── Post-filter ──

async def post_filter(
    db: AsyncSession,
    module_id: str,
    result: dict,
    context: dict,
    min_confidence: float = 0.7,
) -> dict:
    """Check result against quality gate rules.

    Returns {"result": ..., "passed": bool, "issues": [...]}
    """
    rules = await list_rules(
        db, module_id=module_id, tags=["quality_gate"], min_confidence=min_confidence
    )

    issues = []
    for rule in rules:
        if not rule.rule_structured:
            continue

        rs = rule.rule_structured

        # Check if result violates the rule
        check_field = rs.get("check_field")
        if not check_field:
            continue

        actual = result.get(check_field)
        if actual is None:
            continue

        condition = rs.get("condition")
        if condition and not evaluate_condition(condition, {"result": actual, **context}):
            continue

        # Check value constraints
        if "min_value" in rs and actual < rs["min_value"]:
            issues.append({
                "rule_id": str(rule.id),
                "rule": rule.rule_text,
                "confidence": rule.confidence,
                "field": check_field,
                "expected_min": rs["min_value"],
                "actual": actual,
                "suggestion": rs.get("fix_suggestion"),
            })

        if "max_value" in rs and actual > rs["max_value"]:
            issues.append({
                "rule_id": str(rule.id),
                "rule": rule.rule_text,
                "confidence": rule.confidence,
                "field": check_field,
                "expected_max": rs["max_value"],
                "actual": actual,
                "suggestion": rs.get("fix_suggestion"),
            })

    return {
        "result": result,
        "passed": len(issues) == 0,
        "issues": issues,
    }
