"""
Constants for the douyin-sign package.
Load from JSON/hex files in constants/current/ with fallback defaults.
"""

import json
import os
import base64

# Default paths
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONSTANTS_DIR = os.path.join(_BASE_DIR, 'constants', 'current')

# Default values
DEFAULT_SIGN_KEY_B64 = "wC8lD4bMTxmNVwY5jSkqi3QWmrphr/58ugLko7UZgWM="
DEFAULT_SIGN_KEY = base64.b64decode(DEFAULT_SIGN_KEY_B64)

DEFAULT_GORGON_TABLE = bytes.fromhex("ce7c47e421ff095cc9da81690147cba1ed6cc4b1")

DEFAULT_GORGON_PREFIX_ARM64 = bytes.fromhex("8404a0ae1000")
DEFAULT_GORGON_PREFIX = bytes.fromhex("0404a0ae1000")

# Protobuf field configuration
DEFAULT_PROTOBUF_FIELDS = {
    "f1_value": 0x20200929,
    "f2_value": 2,
    "f21_value": 312,
    "f23_device_type_value": 5,
    "f23_channel": "googleplay",
    "f23_dpi": 209748992,
    "f25_value": 1,
    "f28_value": 1008,
    "f29_default": 516112,
    "f30_default": 6,
    "f31_default": 620944317,
}


def _load_hex_file(filename: str) -> bytes:
    """Load a hex file from constants/current/"""
    path = os.path.join(_CONSTANTS_DIR, filename)
    if os.path.isfile(path):
        with open(path, 'r') as f:
            return bytes.fromhex(f.read().strip())
    return None


def _load_json_file(filename: str) -> dict:
    """Load a JSON file from constants/current/"""
    path = os.path.join(_CONSTANTS_DIR, filename)
    if os.path.isfile(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None


def get_sign_key() -> bytes:
    """
    Get the sign key from constants/current/ or return default.
    Expected file: sign_key.hex containing base64 string or hex bytes.
    """
    # Try sign_key.hex first (hex format)
    hex_data = _load_hex_file('sign_key.hex')
    if hex_data:
        return hex_data

    # Try sign_key.json
    json_data = _load_json_file('sign_key.json')
    if json_data and 'key' in json_data:
        return base64.b64decode(json_data['key'])

    # Fallback to default
    return DEFAULT_SIGN_KEY


def get_gorgon_table() -> bytes:
    """
    Get the Gorgon XOR table from constants/current/ or return default.
    Expected file: gorgon_table.hex
    """
    hex_data = _load_hex_file('gorgon_table.hex')
    if hex_data:
        return hex_data
    return DEFAULT_GORGON_TABLE


def get_gorgon_prefix(is_arm64: bool = True) -> bytes:
    """Get the Gorgon prefix for the given architecture."""
    return DEFAULT_GORGON_PREFIX_ARM64 if is_arm64 else DEFAULT_GORGON_PREFIX


def get_protobuf_fields() -> dict:
    """
    Get protobuf field configuration from constants/current/ or return default.
    Expected file: protobuf_fields.json
    """
    json_data = _load_json_file('protobuf_fields.json')
    if json_data:
        return json_data
    return DEFAULT_PROTOBUF_FIELDS
