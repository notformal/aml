"""Integration tests for phases 2-7: stats, extraction, feedback connectors."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_module_stats(client: AsyncClient):
    # Setup
    await client.post("/api/v1/projects", json={"id": "stats_proj", "name": "Stats"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "stats_proj.gen",
            "project_id": "stats_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )

    # Create some episodes with feedback
    for i in range(3):
        resp = await client.post(
            "/api/v1/episodes",
            json={
                "module_id": "stats_proj.gen",
                "action": f"action_{i}",
                "input_data": {"i": i},
                "output_data": {"result": i * 10},
            },
        )
        ep_id = resp.json()["id"]
        await client.post(
            f"/api/v1/episodes/{ep_id}/feedback",
            json={"score": 0.5 + i * 0.15, "feedback_type": "human"},
        )

    # Create a rule
    await client.post(
        "/api/v1/rules",
        json={
            "module_id": "stats_proj.gen",
            "rule_text": "Test rule",
            "confidence": 0.7,
        },
    )

    # Get stats
    resp = await client.get("/api/v1/modules/stats_proj.gen/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["module_id"] == "stats_proj.gen"
    assert data["total_episodes"] == 3
    assert data["feedback_coverage"] > 0
    assert data["avg_feedback_score"] is not None
    assert data["rules"]["total_active"] >= 1


@pytest.mark.asyncio
async def test_extraction_insufficient_data(client: AsyncClient):
    """Extraction should skip when not enough episodes."""
    await client.post("/api/v1/projects", json={"id": "ext_proj", "name": "Ext"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "ext_proj.gen",
            "project_id": "ext_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )

    resp = await client.post(
        "/api/v1/extract", params={"module_id": "ext_proj.gen"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skipped"] is True
    assert data["reason"] == "insufficient_data"


@pytest.mark.asyncio
async def test_rule_lifecycle(client: AsyncClient):
    """Test full rule lifecycle: create -> update confidence -> deactivate."""
    await client.post("/api/v1/projects", json={"id": "lc_proj", "name": "LC"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "lc_proj.gen",
            "project_id": "lc_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )

    # Create as hypothesis
    resp = await client.post(
        "/api/v1/rules",
        json={
            "module_id": "lc_proj.gen",
            "rule_text": "Hypothesis rule",
            "confidence": 0.2,
            "tags": ["test"],
        },
    )
    assert resp.status_code == 201
    rule_id = resp.json()["id"]
    assert resp.json()["confidence"] == 0.2

    # Promote to weak
    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        json={"confidence": 0.45},
    )
    assert resp.json()["confidence"] == 0.45

    # Promote to strong
    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        json={"confidence": 0.75},
    )
    assert resp.json()["confidence"] == 0.75

    # Deactivate
    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        json={"active": False},
    )
    assert resp.json()["active"] is False

    # Should not appear in active list
    resp = await client.get(
        "/api/v1/rules",
        params={"module_id": "lc_proj.gen", "active_only": "true"},
    )
    ids = [r["id"] for r in resp.json()]
    assert rule_id not in ids


@pytest.mark.asyncio
async def test_rule_tags_filter(client: AsyncClient):
    """Test filtering rules by tags."""
    await client.post("/api/v1/projects", json={"id": "tag_proj", "name": "Tags"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "tag_proj.gen",
            "project_id": "tag_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )

    # Create rules with different tags
    await client.post(
        "/api/v1/rules",
        json={
            "module_id": "tag_proj.gen",
            "rule_text": "Visual rule",
            "confidence": 0.7,
            "tags": ["visual", "color"],
        },
    )
    await client.post(
        "/api/v1/rules",
        json={
            "module_id": "tag_proj.gen",
            "rule_text": "Copy rule",
            "confidence": 0.6,
            "tags": ["copy", "cta"],
        },
    )

    # Filter by tag
    resp = await client.get(
        "/api/v1/rules",
        params={"module_id": "tag_proj.gen", "tags": "visual"},
    )
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 1
    assert all(any("visual" in r.get("tags", []) for _ in [1]) for r in rules)


@pytest.mark.asyncio
async def test_episode_list_pagination(client: AsyncClient):
    """Test episode listing with pagination."""
    await client.post("/api/v1/projects", json={"id": "pag_proj", "name": "Pag"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "pag_proj.gen",
            "project_id": "pag_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )

    # Create 5 episodes
    for i in range(5):
        await client.post(
            "/api/v1/episodes",
            json={
                "module_id": "pag_proj.gen",
                "action": f"action_{i}",
                "input_data": {"i": i},
                "output_data": {"r": i},
            },
        )

    # Get first 2
    resp = await client.get(
        "/api/v1/episodes",
        params={"module_id": "pag_proj.gen", "limit": 2, "offset": 0},
    )
    assert len(resp.json()) == 2

    # Get next 2
    resp = await client.get(
        "/api/v1/episodes",
        params={"module_id": "pag_proj.gen", "limit": 2, "offset": 2},
    )
    assert len(resp.json()) == 2
