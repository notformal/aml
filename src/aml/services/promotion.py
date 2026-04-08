"""Cross-module and cross-project rule promotion.

When a rule is confirmed across multiple modules/projects,
it gets promoted to a wider scope.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.module import Module
from aml.models.rule import Rule

logger = logging.getLogger(__name__)


async def check_rule_promotion(db: AsyncSession, rule_id) -> str | None:
    """Check if a rule should be promoted to a wider scope.

    Returns new scope ('project' or 'global') if promotion is warranted, else None.
    """
    rule = await db.get(Rule, rule_id)
    if not rule or not rule.active:
        return None

    if rule.scope == "global":
        return None  # Already at widest scope

    # Get the module and project
    module = await db.get(Module, rule.module_id)
    if not module:
        return None

    # Check sibling modules in the same project
    if rule.scope == "module":
        siblings = await db.execute(
            select(Module)
            .where(Module.project_id == module.project_id)
            .where(Module.id != module.id)
        )
        sibling_modules = siblings.scalars().all()

        # Check if similar rules exist in siblings
        cross_evidence = 0
        for sib in sibling_modules:
            similar = await db.execute(
                select(func.count(Rule.id))
                .where(Rule.module_id == sib.id)
                .where(Rule.active.is_(True))
                .where(Rule.confidence >= 0.6)
                .where(Rule.rule_text.ilike(f"%{_extract_key_phrase(rule.rule_text)}%"))
            )
            if similar.scalar() > 0:
                cross_evidence += 1

        if cross_evidence >= 2:
            rule.scope = "project"
            await db.commit()
            logger.info(
                "Promoted rule %s to project scope (evidence from %d siblings)",
                rule.id, cross_evidence,
            )
            return "project"

    # Check cross-project promotion
    if rule.scope == "project":
        other_projects = await db.execute(
            select(func.count(func.distinct(Module.project_id)))
            .where(Module.project_id != module.project_id)
            .where(
                Module.id.in_(
                    select(Rule.module_id)
                    .where(Rule.active.is_(True))
                    .where(Rule.confidence >= 0.7)
                    .where(Rule.rule_text.ilike(f"%{_extract_key_phrase(rule.rule_text)}%"))
                )
            )
        )
        project_count = other_projects.scalar() or 0

        if project_count >= 2:
            rule.scope = "global"
            await db.commit()
            logger.info("Promoted rule %s to global scope", rule.id)
            return "global"

    return None


def _extract_key_phrase(text: str) -> str:
    """Extract a short key phrase for fuzzy matching."""
    words = text.split()
    # Take up to 4 significant words (skip short ones)
    significant = [w for w in words if len(w) > 3][:4]
    return " ".join(significant) if significant else text[:30]
