"""AML Python SDK — async client for Adaptive Memory Layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx


@dataclass
class Episode:
    id: UUID
    module_id: str
    action: str
    input_data: dict
    output_data: dict
    metadata: dict
    created_at: str
    avg_score: float | None = None


@dataclass
class Rule:
    id: UUID
    module_id: str
    scope: str
    rule_text: str
    rule_structured: dict | None
    confidence: float
    evidence_count: int
    tags: list[str]
    active: bool
    created_at: str
    updated_at: str


@dataclass
class Context:
    episodes: list[Episode]
    rules: list[Rule]


class MemoryClient:
    """Async client for AML REST API."""

    def __init__(
        self,
        api_url: str,
        project: str,
        module: str,
        timeout: float = 30.0,
    ):
        self.api_url = api_url.rstrip("/")
        self.project = project
        self.module = module
        self._client = httpx.AsyncClient(
            base_url=f"{self.api_url}/api/v1",
            timeout=timeout,
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Episode logging ──

    async def log(
        self,
        action: str,
        input_data: dict,
        output_data: dict,
        metadata: dict | None = None,
    ) -> UUID:
        """Log an episode. Returns episode ID."""
        resp = await self._client.post(
            "/episodes",
            json={
                "module_id": f"{self.project}.{self.module}",
                "action": action,
                "input_data": input_data,
                "output_data": output_data,
                "metadata": metadata or {},
            },
        )
        resp.raise_for_status()
        return UUID(resp.json()["id"])

    # ── Feedback ──

    async def feedback(
        self,
        episode_id: UUID | str,
        score: float,
        feedback_type: str = "auto_metric",
        source: str | None = None,
        details: dict | None = None,
    ) -> UUID:
        """Add feedback to an episode. Returns feedback ID."""
        resp = await self._client.post(
            f"/episodes/{episode_id}/feedback",
            json={
                "score": score,
                "feedback_type": feedback_type,
                "source": source,
                "details": details or {},
            },
        )
        resp.raise_for_status()
        return UUID(resp.json()["id"])

    # ── Context (episodes + rules) ──

    async def get_context(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        min_confidence: float = 0.3,
        tags: list[str] | None = None,
    ) -> Context:
        """Get similar episodes + applicable rules for a query."""
        resp = await self._client.post(
            "/context",
            json={
                "module_id": f"{self.project}.{self.module}",
                "query": query,
                "top_k": top_k,
                "min_score": min_score,
                "min_confidence": min_confidence,
                "tags": tags,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return Context(
            episodes=[Episode(**e) for e in data["episodes"]],
            rules=[Rule(**r) for r in data["rules"]],
        )

    # ── Rules ──

    async def get_rules(
        self,
        tags: list[str] | None = None,
        min_confidence: float = 0.3,
    ) -> list[Rule]:
        """Get applicable rules for this module."""
        params: dict[str, Any] = {
            "module_id": f"{self.project}.{self.module}",
            "min_confidence": min_confidence,
            "active_only": True,
        }
        if tags:
            params["tags"] = ",".join(tags)

        resp = await self._client.get("/rules", params=params)
        resp.raise_for_status()
        return [Rule(**r) for r in resp.json()]

    # ── Setup helpers ──

    async def ensure_project(self, name: str | None = None):
        """Create project if not exists."""
        try:
            await self._client.post(
                "/projects",
                json={"id": self.project, "name": name or self.project},
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 409:
                raise

    async def ensure_module(
        self, module_type: str = "generation", name: str | None = None
    ):
        """Create module if not exists."""
        module_id = f"{self.project}.{self.module}"
        try:
            await self._client.post(
                "/modules",
                json={
                    "id": module_id,
                    "project_id": self.project,
                    "name": name or self.module,
                    "module_type": module_type,
                },
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 409:
                raise
