"""Delayed Feedback Connector framework.

Supports polling external APIs (Meta Ads, CRM, analytics) to attach
feedback to episodes after the fact.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Awaitable

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.episode import Episode
from aml.models.feedback import Feedback

logger = logging.getLogger(__name__)


@dataclass
class ConnectorConfig:
    module_id: str
    source: str
    connector_type: str  # 'polling', 'webhook', 'cron'
    poll_interval_hours: int = 24
    lookback_days: int = 7
    episode_match_field: str = "metadata.external_id"  # dot-path into episode metadata
    score_formula: str = "value"  # simple expression
    details_fields: list[str] = field(default_factory=list)


@dataclass
class FeedbackConnectorRegistry:
    """Registry of all feedback connectors."""

    connectors: dict[str, ConnectorConfig] = field(default_factory=dict)

    def register(self, config: ConnectorConfig) -> None:
        key = f"{config.module_id}:{config.source}"
        self.connectors[key] = config
        logger.info("Registered feedback connector: %s", key)

    def get_connectors_for_module(self, module_id: str) -> list[ConnectorConfig]:
        return [c for c in self.connectors.values() if c.module_id == module_id]


# Global registry
registry = FeedbackConnectorRegistry()


async def poll_connector(
    db: AsyncSession,
    config: ConnectorConfig,
    fetch_fn: Callable[[dict], Awaitable[list[dict]]],
) -> int:
    """Poll an external source and attach feedback to matching episodes.

    fetch_fn receives {"module_id", "lookback_days"} and returns list of:
        {"match_value": str, "score": float, "details": dict}

    Returns number of feedback records created.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.lookback_days)

    # Fetch external data
    external_data = await fetch_fn({
        "module_id": config.module_id,
        "lookback_days": config.lookback_days,
    })

    if not external_data:
        return 0

    # Find episodes without feedback from this source
    match_field_parts = config.episode_match_field.split(".")
    created = 0

    for item in external_data:
        match_value = item.get("match_value")
        if not match_value:
            continue

        # Build JSON path query for matching
        # For SQLite/portable: load all recent episodes and filter in Python
        result = await db.execute(
            select(Episode)
            .where(Episode.module_id == config.module_id)
            .where(Episode.created_at >= cutoff)
            .order_by(Episode.created_at.desc())
            .limit(500)
        )
        episodes = result.scalars().all()

        for ep in episodes:
            # Navigate dot-path in episode data
            data = ep.metadata_ if match_field_parts[0] == "metadata" else ep.input_data
            val = data
            for part in match_field_parts[1:]:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break

            if str(val) != str(match_value):
                continue

            # Check if feedback from this source already exists
            existing = await db.execute(
                select(func.count(Feedback.id))
                .where(Feedback.episode_id == ep.id)
                .where(Feedback.source == config.source)
            )
            if existing.scalar() > 0:
                continue

            # Create feedback
            fb = Feedback(
                episode_id=ep.id,
                score=float(item["score"]),
                feedback_type="auto_metric",
                source=config.source,
                details=item.get("details", {}),
            )
            db.add(fb)
            created += 1

    if created:
        await db.commit()

    logger.info("Connector %s:%s created %d feedback records", config.module_id, config.source, created)
    return created


# ── Built-in connector adapters ──

async def meta_ads_adapter(params: dict) -> list[dict]:
    """Example adapter for Meta Ads API. Override with real implementation."""
    logger.warning("Meta Ads adapter is a stub — implement with real API calls")
    return []


async def google_analytics_adapter(params: dict) -> list[dict]:
    """Example adapter for Google Analytics. Override with real implementation."""
    logger.warning("GA adapter is a stub — implement with real API calls")
    return []
