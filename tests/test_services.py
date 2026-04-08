"""Tests for services: injection, A/B testing, PII, confidence."""

import pytest

from aml.services.ab_testing import (
    filter_rules_for_request,
    is_control_group,
    should_apply_rule,
)
from aml.services.injection import evaluate_condition
from aml.services.pii import sanitize_data


# ── A/B Testing ──


def test_control_group_deterministic():
    """Same request_id always gives same result."""
    result1 = is_control_group("req-123")
    result2 = is_control_group("req-123")
    assert result1 == result2


def test_control_group_distribution():
    """Roughly 10% should be in control group."""
    control = sum(1 for i in range(1000) if is_control_group(f"req-{i}"))
    assert 30 < control < 170  # ~10% with generous margin


class FakeRule:
    def __init__(self, confidence, id="rule-1"):
        self.confidence = confidence
        self.id = id


def test_strong_rule_always_applies():
    rule = FakeRule(confidence=0.8)
    assert should_apply_rule(rule, "any-request") is True


def test_weak_rule_always_applies():
    rule = FakeRule(confidence=0.4)
    assert should_apply_rule(rule, "any-request") is True


def test_hypothesis_rule_ab_tested():
    """Hypothesis rules (confidence < 0.3) should apply to ~10% of traffic."""
    rule = FakeRule(confidence=0.1)
    applied = sum(1 for i in range(1000) if should_apply_rule(rule, f"req-{i}"))
    assert 30 < applied < 170  # ~10% with margin


def test_filter_rules_control_group():
    """Control group should get empty rules."""
    # Find a request_id that IS in control group
    control_id = None
    for i in range(1000):
        if is_control_group(f"ctrl-{i}"):
            control_id = f"ctrl-{i}"
            break
    assert control_id is not None
    rules = [FakeRule(0.9), FakeRule(0.5)]
    assert filter_rules_for_request(rules, control_id) == []


# ── Condition Evaluation ──


def test_evaluate_condition_string():
    assert evaluate_condition("category=swimwear", {"category": "swimwear"}) is True
    assert evaluate_condition("category=swimwear", {"category": "formal"}) is False


def test_evaluate_condition_dict():
    cond = {"field": "age", "op": "gte", "value": 25}
    assert evaluate_condition(cond, {"age": 30}) is True
    assert evaluate_condition(cond, {"age": 20}) is False


def test_evaluate_condition_in():
    cond = {"field": "size", "op": "in", "value": ["S", "M", "L"]}
    assert evaluate_condition(cond, {"size": "M"}) is True
    assert evaluate_condition(cond, {"size": "XXL"}) is False


def test_evaluate_condition_missing_field():
    cond = {"field": "nonexistent", "op": "eq", "value": "x"}
    assert evaluate_condition(cond, {}) is False


# ── PII Handling ──


def test_pii_strip():
    data = {
        "user": "John",
        "email": "john@example.com",
        "phone": "+1234567890",
        "query": "buy shoes",
    }
    result = sanitize_data(data, policy="strip", scan_values=False)
    assert result["email"] == "***REDACTED***"
    assert result["phone"] == "***REDACTED***"
    assert result["query"] == "buy shoes"


def test_pii_hash():
    data = {"email": "test@test.com", "name": "Alice"}
    result = sanitize_data(data, policy="hash", scan_values=False)
    assert result["email"].startswith("sha256:")
    assert result["name"].startswith("sha256:")


def test_pii_none_passthrough():
    data = {"email": "test@test.com"}
    result = sanitize_data(data, policy="none")
    assert result["email"] == "test@test.com"


def test_pii_nested():
    data = {"user": {"email": "a@b.com", "settings": {"theme": "dark"}}}
    result = sanitize_data(data, policy="strip", scan_values=False)
    assert result["user"]["email"] == "***REDACTED***"
    assert result["user"]["settings"]["theme"] == "dark"


def test_pii_custom_fields():
    data = {"ssn": "123-45-6789", "email": "ok@test.com"}
    result = sanitize_data(data, policy="strip", pii_fields={"ssn"}, scan_values=False)
    assert result["ssn"] == "***REDACTED***"
    assert result["email"] == "ok@test.com"  # not in custom fields
