"""
Tests for the douyin-sign package.

Verifies that import works, sign_all() returns expected headers with
correct formats, and constants load correctly.
"""

import json
import re
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
CONSTANTS_CURRENT = ROOT / "constants" / "current"


def test_import_sign():
    """Verify the sign package can be imported."""
    import sign
    assert sign is not None
    assert hasattr(sign, "sign_all")


def test_sign_all_returns_dict():
    """Verify sign_all() returns a dict with expected headers."""
    from sign import sign_all

    headers = sign_all(
        method="POST",
        url="https://example.com/api/test",
        body=b'{"foo": "bar"}',
        cookies="session=abc123",
    )

    assert isinstance(headers, dict), "sign_all() must return a dict"
    assert len(headers) > 0, "headers dict must not be empty"


def test_x_khronos_format():
    """Verify X-Khronos is a non-empty hex string (unix timestamp)."""
    from sign import sign_all

    headers = sign_all(
        method="GET",
        url="https://example.com/api/test",
        body=b"",
        cookies="",
    )

    khronos = headers.get("X-Khronos")
    assert khronos is not None, "X-Khronos header missing"
    assert isinstance(khronos, str), "X-Khronos must be a string"
    assert len(khronos) > 0, "X-Khronos must not be empty"
    int(khronos, 16)  # must be valid hex


def test_x_ss_stub_format():
    """Verify X-SS-STUB is a valid 32-char hex string."""
    from sign import sign_all

    headers = sign_all(
        method="POST",
        url="https://example.com/api/test",
        body=b'{"test": "data"}',
        cookies="",
    )

    stub = headers.get("X-SS-STUB")
    assert stub is not None, "X-SS-STUB header missing"
    assert isinstance(stub, str), "X-SS-STUB must be a string"
    assert re.fullmatch(r"[0-9a-f]{32}", stub), (
        f"X-SS-STUB '{stub}' must match 32-char lowercase hex pattern"
    )


def test_x_gorgon_format():
    """Verify X-Gorgon is a non-empty hex string (signature)."""
    from sign import sign_all

    headers = sign_all(
        method="POST",
        url="https://example.com/api/test",
        body=b"",
        cookies="session=test",
    )

    gorgon = headers.get("X-Gorgon")
    assert gorgon is not None, "X-Gorgon header missing"
    assert isinstance(gorgon, str), "X-Gorgon must be a string"
    assert len(gorgon) > 0, "X-Gorgon must not be empty"
    int(gorgon, 16)  # must be valid hex


def test_constants_sign_key():
    """Verify sign_key.b64 loads and is valid base64."""
    import base64

    path = CONSTANTS_CURRENT / "sign_key.b64"
    assert path.exists(), f"sign_key.b64 not found at {path}"

    content = path.read_text().strip()
    assert len(content) == 44, (
        f"sign_key.b64 must be 44 characters, got {len(content)}"
    )
    assert content.endswith("="), "sign_key.b64 must end with ="

    # Verify it decodes as valid base64
    decoded = base64.b64decode(content)
    assert len(decoded) == 32, (
        f"sign_key must decode to 32 bytes, got {len(decoded)}"
    )


def test_constants_gorgon_table():
    """Verify gorgon_table.hex is valid hex."""
    path = CONSTANTS_CURRENT / "gorgon_table.hex"
    assert path.exists(), f"gorgon_table.hex not found at {path}"

    content = path.read_text().strip()
    assert len(content) == 40, (
        f"gorgon_table.hex must be 40 hex chars, got {len(content)}"
    )

    # Verify it's valid hex
    int(content, 16)


def test_constants_protobuf_fields():
    """Verify protobuf_fields.json is valid JSON with expected fields."""
    path = CONSTANTS_CURRENT / "protobuf_fields.json"
    assert path.exists(), f"protobuf_fields.json not found at {path}"

    data = json.loads(path.read_text())
    assert isinstance(data, dict), "protobuf_fields must be a dict"

    # Spot-check known fields
    expected_fields = [
        "client_ip", "app_version", "device_id", "timestamp",
        "req_id", "user_agent", "os", "os_version",
        "device_brand", "device_model", "resolution",
    ]
    for field in expected_fields:
        assert field in data, f"Missing required field: {field}"
        assert isinstance(data[field], int), (
            f"Field '{field}' value must be an integer"
        )

    # Verify all values are unique (no duplicate field numbers)
    values = list(data.values())
    assert len(values) == len(set(values)), (
        "Duplicate protobuf field numbers detected"
    )
