"""Integration tests for AML REST API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["api"] == "ok"


@pytest.mark.asyncio
async def test_project_crud(client: AsyncClient):
    # Create
    resp = await client.post(
        "/api/v1/projects",
        json={"id": "test_proj", "name": "Test Project"},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == "test_proj"

    # Duplicate
    resp = await client.post(
        "/api/v1/projects",
        json={"id": "test_proj", "name": "Test Project"},
    )
    assert resp.status_code == 409

    # Get
    resp = await client.get("/api/v1/projects/test_proj")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Project"

    # List
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_module_crud(client: AsyncClient):
    # Setup project
    await client.post("/api/v1/projects", json={"id": "mod_proj", "name": "P"})

    # Create module
    resp = await client.post(
        "/api/v1/modules",
        json={
            "id": "mod_proj.content_gen",
            "project_id": "mod_proj",
            "name": "Content Gen",
            "module_type": "generation",
        },
    )
    assert resp.status_code == 201

    # Module for nonexistent project
    resp = await client.post(
        "/api/v1/modules",
        json={
            "id": "bad.module",
            "project_id": "nonexistent",
            "name": "Bad",
            "module_type": "generation",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_episode_and_feedback(client: AsyncClient):
    # Setup
    await client.post("/api/v1/projects", json={"id": "ep_proj", "name": "P"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "ep_proj.gen",
            "project_id": "ep_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )

    # Create episode
    resp = await client.post(
        "/api/v1/episodes",
        json={
            "module_id": "ep_proj.gen",
            "action": "generate_banner",
            "input_data": {"audience": "25-34 female"},
            "output_data": {"file_url": "https://example.com/banner.png"},
        },
    )
    assert resp.status_code == 201
    episode_id = resp.json()["id"]

    # Get episode
    resp = await client.get(f"/api/v1/episodes/{episode_id}")
    assert resp.status_code == 200

    # Add feedback
    resp = await client.post(
        f"/api/v1/episodes/{episode_id}/feedback",
        json={
            "score": 0.82,
            "feedback_type": "auto_metric",
            "source": "meta_ads_api",
            "details": {"ctr": 0.023},
        },
    )
    assert resp.status_code == 201

    # List feedback
    resp = await client.get(f"/api/v1/episodes/{episode_id}/feedback")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["score"] == 0.82


@pytest.mark.asyncio
async def test_rule_crud(client: AsyncClient):
    # Setup
    await client.post("/api/v1/projects", json={"id": "rule_proj", "name": "P"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "rule_proj.gen",
            "project_id": "rule_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )

    # Create rule
    resp = await client.post(
        "/api/v1/rules",
        json={
            "module_id": "rule_proj.gen",
            "rule_text": "Warm colors work better for female audience 25-34",
            "confidence": 0.7,
            "tags": ["visual", "audience"],
        },
    )
    assert resp.status_code == 201
    rule_id = resp.json()["id"]

    # List rules
    resp = await client.get("/api/v1/rules", params={"module_id": "rule_proj.gen"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Update rule
    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        json={"confidence": 0.85, "rule_text": "Updated rule text"},
    )
    assert resp.status_code == 200
    assert resp.json()["confidence"] == 0.85

    # Deactivate
    resp = await client.patch(f"/api/v1/rules/{rule_id}", json={"active": False})
    assert resp.status_code == 200
    assert resp.json()["active"] is False

    # Filtered out from active list
    resp = await client.get(
        "/api/v1/rules", params={"module_id": "rule_proj.gen", "active_only": True}
    )
    assert all(r["active"] for r in resp.json())


@pytest.mark.asyncio
async def test_feedback_validation(client: AsyncClient):
    # Setup
    await client.post("/api/v1/projects", json={"id": "val_proj", "name": "P"})
    await client.post(
        "/api/v1/modules",
        json={
            "id": "val_proj.gen",
            "project_id": "val_proj",
            "name": "Gen",
            "module_type": "generation",
        },
    )
    resp = await client.post(
        "/api/v1/episodes",
        json={
            "module_id": "val_proj.gen",
            "action": "test",
            "input_data": {},
            "output_data": {},
        },
    )
    episode_id = resp.json()["id"]

    # Score out of range
    resp = await client.post(
        f"/api/v1/episodes/{episode_id}/feedback",
        json={"score": 1.5, "feedback_type": "human"},
    )
    assert resp.status_code == 422

    # Invalid feedback type
    resp = await client.post(
        f"/api/v1/episodes/{episode_id}/feedback",
        json={"score": 0.5, "feedback_type": "invalid_type"},
    )
    assert resp.status_code == 422
