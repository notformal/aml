"""Context service — combines similar episodes + applicable rules."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from aml.repositories.episode import search_similar_episodes
from aml.repositories.rule import list_rules
from aml.services.embedding import embed_text


async def get_context(
    db: AsyncSession,
    module_id: str,
    query: str,
    top_k: int = 10,
    min_score: float = 0.0,
    min_confidence: float = 0.3,
    tags: list[str] | None = None,
) -> dict:
    """Get context = similar episodes + applicable rules for a query."""
    embedding = await embed_text(query)

    episodes = []
    if embedding:
        episodes = await search_similar_episodes(
            db, module_id=module_id, embedding=embedding, top_k=top_k, min_score=min_score
        )

    rules = await list_rules(
        db,
        module_id=module_id,
        min_confidence=min_confidence,
        tags=tags,
        active_only=True,
    )

    return {"episodes": episodes, "rules": rules}


def format_rules_for_prompt(rules: list) -> str:
    """Format rules as text block for LLM prompt injection."""
    if not rules:
        return ""

    lines = []
    for r in rules:
        lines.append(f"- [{r.confidence:.0%}] {r.rule_text}")

    return "LEARNED RULES:\n" + "\n".join(lines)


def format_episodes_for_prompt(episodes: list, max_episodes: int = 3) -> str:
    """Format episodes as text block for LLM prompt injection."""
    if not episodes:
        return ""

    lines = []
    for ep in episodes[:max_episodes]:
        score_str = f" (score: {ep.avg_score:.2f})" if ep.avg_score else ""
        lines.append(
            f"- {ep.action}{score_str}: "
            f"input={json.dumps(ep.input_data, ensure_ascii=False)[:200]}, "
            f"output={json.dumps(ep.output_data, ensure_ascii=False)[:200]}"
        )

    return "SIMILAR PAST CASES:\n" + "\n".join(lines)
