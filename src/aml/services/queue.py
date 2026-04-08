"""Redis Streams based async logging queue.

Episodes are pushed to a stream and consumed by a background worker
so that memory.log() never blocks the caller.
"""

import json
import logging

import redis.asyncio as aioredis

from aml.config import settings

logger = logging.getLogger(__name__)

STREAM_KEY = "aml:episodes:pending"
GROUP_NAME = "aml-workers"
CONSUMER_NAME = "worker-1"

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def enqueue_episode(episode_data: dict) -> str:
    """Push episode to Redis Stream for async processing. Returns stream message ID."""
    r = await get_redis()
    msg_id = await r.xadd(STREAM_KEY, {"data": json.dumps(episode_data)})
    return msg_id


async def ensure_consumer_group():
    """Create consumer group if not exists."""
    r = await get_redis()
    try:
        await r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def consume_episodes(handler, batch_size: int = 10, block_ms: int = 5000):
    """Consume episodes from stream. Call handler(data_list) for each batch."""
    r = await get_redis()
    await ensure_consumer_group()

    while True:
        entries = await r.xreadgroup(
            GROUP_NAME, CONSUMER_NAME, {STREAM_KEY: ">"}, count=batch_size, block=block_ms
        )
        if not entries:
            continue

        for stream_name, messages in entries:
            batch = []
            ids = []
            for msg_id, fields in messages:
                batch.append(json.loads(fields["data"]))
                ids.append(msg_id)

            try:
                await handler(batch)
                for mid in ids:
                    await r.xack(STREAM_KEY, GROUP_NAME, mid)
            except Exception:
                logger.exception("Failed to process episode batch")
