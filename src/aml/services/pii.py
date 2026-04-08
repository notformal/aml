"""PII handling — strip, hash, or encrypt sensitive fields before storage."""

import hashlib
import re
from typing import Any

# Common PII patterns
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\+?\d[\d\s\-()]{8,}\d"),
    "ip": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
}

# Default fields that may contain PII
DEFAULT_PII_FIELDS = {"email", "phone", "name", "first_name", "last_name", "ip", "address"}


def _hash_value(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def _strip_value(value: str) -> str:
    return "***REDACTED***"


def sanitize_data(
    data: dict,
    policy: str = "strip",
    pii_fields: set[str] | None = None,
    scan_values: bool = True,
) -> dict:
    """Sanitize PII from a dict.

    policy: 'strip' (replace with ***), 'hash' (one-way hash), 'none' (passthrough)
    pii_fields: field names to always sanitize
    scan_values: if True, also regex-scan all string values for email/phone/etc.
    """
    if policy == "none":
        return data

    fields = pii_fields or DEFAULT_PII_FIELDS
    transform = _hash_value if policy == "hash" else _strip_value

    return _sanitize_recursive(data, fields, transform, scan_values)


def _sanitize_recursive(
    data: Any,
    fields: set[str],
    transform: callable,
    scan_values: bool,
) -> Any:
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key.lower() in fields:
                if isinstance(value, str):
                    result[key] = transform(value)
                else:
                    result[key] = transform(str(value))
            else:
                result[key] = _sanitize_recursive(value, fields, transform, scan_values)
        return result

    if isinstance(data, list):
        return [_sanitize_recursive(item, fields, transform, scan_values) for item in data]

    if isinstance(data, str) and scan_values:
        result = data
        for name, pattern in PII_PATTERNS.items():
            match = pattern.search(result)
            if match:
                result = pattern.sub(transform(match.group()), result)
            if result != data:
                break
        return result

    return data
