"""Built-in A/B testing engine for rules.

- Hypothesis rules (confidence < 0.3) are tested on 10% of traffic
- 10% of all requests are processed WITHOUT any rules (control group)
"""

import hashlib
import logging

from aml.config import settings
from aml.models.rule import Rule

logger = logging.getLogger(__name__)


def _bucket(request_id: str, salt: str = "") -> int:
    """Deterministic bucket assignment (0-99) based on request_id."""
    h = hashlib.md5(f"{request_id}{salt}".encode()).hexdigest()
    return int(h[:8], 16) % 100


def is_control_group(request_id: str) -> bool:
    """Check if this request is in the control group (no rules applied).

    Returns True for control_group_pct % of requests.
    """
    bucket = _bucket(request_id, salt="control")
    return bucket < settings.control_group_pct


def should_apply_rule(rule: Rule, request_id: str) -> bool:
    """Determine if a rule should be applied to this request.

    - confidence >= 0.6: always apply (strong rule)
    - confidence 0.3-0.6: always apply as hint (weak rule)
    - confidence < 0.3: A/B test on 10% of traffic (hypothesis)
    """
    if rule.confidence >= 0.3:
        return True

    # Hypothesis — A/B test
    bucket = _bucket(request_id, salt=str(rule.id))
    return bucket < 10  # 10% of traffic sees the hypothesis


def filter_rules_for_request(rules: list[Rule], request_id: str) -> list[Rule]:
    """Filter rules based on A/B testing logic.

    Returns empty list for control group requests.
    Filters out hypothesis rules not in test bucket.
    """
    if is_control_group(request_id):
        return []

    return [r for r in rules if should_apply_rule(r, request_id)]
