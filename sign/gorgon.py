"""
X-Gorgon generation.
Parameter string → XOR GORGON_TABLE → nibble swap → XOR cascade → reverse bits XOR 0xeb → 20-byte result.
"""

from .constants import get_gorgon_table, get_gorgon_prefix
from .native import reverse_bits


def make_x_gorgon(
    params: bytes,
    payload: bytes,
    cookies: bytes,
    ts: int,
    is_arm64: bool = True,
) -> str:
    """
    Generate X-Gorgon header value.

    Args:
        params:   URL query string bytes (without ?)
        payload:  Request body bytes (or 16 bytes of zeros)
        cookies:  Cookie string bytes (or 16 bytes of zeros)
        ts:       Unix timestamp
        is_arm64: True for arm64 prefix (8404...), False for arm (0404...)

    Returns:
        Hex string of the complete X-Gorgon value
    """
    gorgon_table = get_gorgon_table()
    prefix = get_gorgon_prefix(is_arm64)

    ts_bytes = ts.to_bytes(4, byteorder="big")

    # Pad to at least 4 bytes, take first 4
    params_padded = (params + b'\x00' * 4)[:4]
    payload_padded = (payload + b'\x00' * 4)[:4]
    cookies_padded = (cookies + b'\x00' * 4)[:4]

    # Build buffer: 4 + 4 + 4 + 4 + 4 = 20 bytes
    buffer = bytearray(
        params_padded + payload_padded + cookies_padded +
        bytes.fromhex("20040204") + ts_bytes
    )

    # Step 1: XOR with GORGON_TABLE
    for i in range(len(buffer)):
        buffer[i] ^= gorgon_table[i]

    # Step 2: Nibble swap + XOR cascade
    for i in range(len(buffer) - 1):
        buffer[i] = ((buffer[i] >> 4) & 0xf) | ((buffer[i] << 4) & 0xff)
        buffer[i] ^= buffer[i + 1]

    # Step 3: reverse_bits ^ 0xeb (for all but last byte)
    for i in range(len(buffer) - 1):
        buffer[i] = reverse_bits(buffer[i]) ^ 0xeb

    # Step 4: Special handling for last byte
    buffer[19] = ((buffer[19] >> 4) & 0xf) | ((buffer[19] << 4) & 0xff)
    buffer[19] ^= buffer[0]
    buffer[19] = reverse_bits(buffer[19]) ^ 0xeb

    return (prefix + buffer).hex()
