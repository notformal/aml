"""Pattern Extraction Engine.

Analyzes episodes with feedback, uses Claude API to extract rules/patterns,
and manages the rule lifecycle (create, update, deactivate).
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.config import settings
from aml.models.episode import Episode
from aml.models.extraction import ExtractionRun
from aml.models.feedback import Feedback
from aml.models.rule import Rule

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a pattern analyst. You are given results from an AI system:
successful cases (high score) and unsuccessful cases (low score).

MODULE: {module_id}

SUCCESSFUL CASES (score >= 0.7):
{top_episodes}

UNSUCCESSFUL CASES (score <= 0.3):
{bottom_episodes}

EXISTING RULES:
{existing_rules}

TASK:
1. Find patterns: what do successful cases have in common? What about unsuccessful ones?
2. Formulate NEW rules (not already in existing rules)
3. Suggest UPDATES to existing rules (if data confirms/disproves)
4. Suggest DEACTIVATION of rules not supported by data

Rules must be:
- Specific and actionable (not "do better", but "parameter X in range Y-Z")
- Data-based (state how many cases confirm)
- Include machine-readable version where possible

Response strictly JSON:
{{
  "new_rules": [
    {{
      "text": "Human-readable rule",
      "structured": {{"param": "...", "condition": "...", "value_range": [...]}},
      "confidence": 0.75,
      "evidence": "12 of 15 successful cases confirm",
      "tags": ["visual", "params"]
    }}
  ],
  "updates": [
    {{
      "rule_id": "uuid",
      "new_text": "Updated text",
      "new_structured": {{}},
      "new_confidence": 0.85,
      "reason": "Confirmed by 8 more cases"
    }}
  ],
  "deactivate": [
    {{
      "rule_id": "uuid",
      "reason": "5 of 6 recent cases disprove"
    }}
  ]
}}"""


async def _fetch_episodes_with_feedback(
    db: AsyncSession, module_id: str, days: int = 7, limit: int = 200
) -> list[dict]:
    """Fetch recent episodes with aggregated feedback."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    avg_score = (
        select(func.avg(Feedback.score))
        .where(Feedback.episode_id == Episode.id)
        .correlate(Episode)
        .scalar_subquery()
    )
    feedback_count = (
        select(func.count(Feedback.id))
        .where(Feedback.episode_id == Episode.id)
        .correlate(Episode)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Episode,
            avg_score.label("avg_score"),
            feedback_count.label("feedback_count"),
        )
        .where(Episode.module_id == module_id)
        .where(Episode.created_at >= cutoff)
        .where(feedback_count >= 1)
        .order_by(Episode.created_at.desc())
        .limit(limit)
    )

    episodes = []
    for ep, score, count in result.all():
        episodes.append({
            "id": str(ep.id),
            "action": ep.action,
            "input_data": ep.input_data,
            "output_data": ep.output_data,
            "metadata": ep.metadata_,
            "avg_score": round(float(score), 3) if score else 0,
            "feedback_count": int(count),
        })
    return episodes


def _format_episodes(episodes: list[dict], max_items: int = 30) -> str:
    """Format episodes as compact JSON for the prompt."""
    items = episodes[:max_items]
    return json.dumps(items, ensure_ascii=False, indent=2)[:8000]


def _format_rules(rules: list[Rule]) -> str:
    """Format existing rules for the prompt."""
    items = []
    for r in rules:
        items.append({
            "id": str(r.id),
            "text": r.rule_text,
            "structured": r.rule_structured,
            "confidence": r.confidence,
            "evidence_count": r.evidence_count,
        })
    return json.dumps(items, ensure_ascii=False, indent=2)[:4000]


async def _call_claude(prompt: str) -> tuple[dict, int]:
    """Call Claude API for extraction. Returns (parsed_response, tokens_used)."""
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed — pip install anthropic")
        return {"new_rules": [], "updates": [], "deactivate": []}, 0

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping extraction")
        return {"new_rules": [], "updates": [], "deactivate": []}, 0

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens

    # Parse JSON from response (handle markdown code blocks)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        parsed = json.loads(text.strip())
    except json.JSONDecodeError:
        logger.error("Failed to parse extraction response: %s", text[:500])
        parsed = {"new_rules": [], "updates": [], "deactivate": []}

    return parsed, tokens


async def _apply_changes(
    db: AsyncSession, module_id: str, changes: dict
) -> tuple[int, int, int]:
    """Apply extraction results: create new rules, update existing, deactivate."""
    created = updated = deactivated = 0

    # New rules
    for new_rule in changes.get("new_rules", []):
        rule = Rule(
            module_id=module_id,
            rule_text=new_rule["text"],
            rule_structured=new_rule.get("structured"),
            confidence=min(new_rule.get("confidence", 0.3), 0.3),  # Start as hypothesis
            tags=new_rule.get("tags", []),
            evidence_count=1,
        )
        db.add(rule)
        created += 1

    # Updates
    for upd in changes.get("updates", []):
        try:
            rule_id = uuid.UUID(upd["rule_id"])
        except (ValueError, KeyError):
            continue
        rule = await db.get(Rule, rule_id)
        if not rule or rule.module_id != module_id:
            continue
        if "new_text" in upd:
            rule.rule_text = upd["new_text"]
        if "new_structured" in upd:
            rule.rule_structured = upd["new_structured"]
        if "new_confidence" in upd:
            rule.confidence = upd["new_confidence"]
        rule.evidence_count += 1
        rule.last_confirmed_at = datetime.now(timezone.utc)
        updated += 1

    # Deactivations
    for deact in changes.get("deactivate", []):
        try:
            rule_id = uuid.UUID(deact["rule_id"])
        except (ValueError, KeyError):
            continue
        rule = await db.get(Rule, rule_id)
        if not rule or rule.module_id != module_id:
            continue
        rule.active = False
        deactivated += 1

    if created or updated or deactivated:
        await db.commit()

    return created, updated, deactivated


async def extract_patterns(db: AsyncSession, module_id: str) -> dict:
    """Main extraction job for a module. Returns extraction stats."""
    start = time.time()

    # 1. Fetch episodes with feedback
    episodes = await _fetch_episodes_with_feedback(db, module_id)

    if len(episodes) < settings.extraction_min_episodes:
        logger.info(
            "Module %s: only %d episodes with feedback (min %d) — skipping",
            module_id, len(episodes), settings.extraction_min_episodes,
        )
        return {"skipped": True, "reason": "insufficient_data", "count": len(episodes)}

    # 2. Cluster: top vs bottom
    top = [e for e in episodes if e["avg_score"] >= 0.7]
    bottom = [e for e in episodes if e["avg_score"] <= 0.3]

    if not top and not bottom:
        return {"skipped": True, "reason": "no_clear_clusters"}

    # 3. Get existing rules
    result = await db.execute(
        select(Rule).where(Rule.module_id == module_id).where(Rule.active.is_(True))
    )
    existing_rules = list(result.scalars().all())

    # 4. Build prompt and call Claude
    prompt = EXTRACTION_PROMPT.format(
        module_id=module_id,
        top_episodes=_format_episodes(top),
        bottom_episodes=_format_episodes(bottom),
        existing_rules=_format_rules(existing_rules),
    )
    changes, tokens = await _call_claude(prompt)

    # 5. Apply changes
    created, updated, deactivated = await _apply_changes(db, module_id, changes)

    duration_ms = int((time.time() - start) * 1000)

    # 6. Audit log
    run = ExtractionRun(
        module_id=module_id,
        episodes_analyzed=len(episodes),
        rules_created=created,
        rules_updated=updated,
        rules_deactivated=deactivated,
        llm_model="claude-sonnet-4-20250514",
        llm_tokens_used=tokens,
        duration_ms=duration_ms,
    )
    db.add(run)
    await db.commit()

    logger.info(
        "Extraction %s: analyzed=%d, created=%d, updated=%d, deactivated=%d, tokens=%d, %dms",
        module_id, len(episodes), created, updated, deactivated, tokens, duration_ms,
    )

    return {
        "skipped": False,
        "episodes_analyzed": len(episodes),
        "top_count": len(top),
        "bottom_count": len(bottom),
        "rules_created": created,
        "rules_updated": updated,
        "rules_deactivated": deactivated,
        "tokens_used": tokens,
        "duration_ms": duration_ms,
    }
