"""Redis-based rule cache with TTL and invalidation."""

import json
import logging

import redis.asyncio as aioredis

from aml.config import settings

logger = logging.getLogger(__name__)

RULES_CACHE_PREFIX = "aml:rules:"

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _cache_key(module_id: str, min_confidence: float, tags: list[str] | None) -> str:
    tag_str = ",".join(sorted(tags)) if tags else ""
    return f"{RULES_CACHE_PREFIX}{module_id}:{min_confidence}:{tag_str}"


async def get_cached_rules(
    module_id: str,
    min_confidence: float = 0.0,
    tags: list[str] | None = None,
) -> list[dict] | None:
    """Get rules from cache. Returns None on miss."""
    try:
        r = await get_redis()
        key = _cache_key(module_id, min_confidence, tags)
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        logger.debug("Cache miss/error for %s", module_id)
    return None


async def set_cached_rules(
    module_id: str,
    rules: list[dict],
    min_confidence: float = 0.0,
    tags: list[str] | None = None,
) -> None:
    """Store rules in cache with TTL."""
    try:
        r = await get_redis()
        key = _cache_key(module_id, min_confidence, tags)
        await r.setex(key, settings.rules_cache_ttl, json.dumps(rules, default=str))
    except Exception:
        logger.debug("Cache write error for %s", module_id)


async def invalidate_module_cache(module_id: str) -> None:
    """Invalidate all cached rules for a module."""
    try:
        r = await get_redis()
        pattern = f"{RULES_CACHE_PREFIX}{module_id}:*"
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
            logger.info("Invalidated %d cache entries for %s", len(keys), module_id)
    except Exception:
        logger.debug("Cache invalidation error for %s", module_id)
