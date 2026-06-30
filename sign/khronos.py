"""
X-Khronos generation - timestamp-based header.
Returns hex string of unix timestamp * 1000.
"""

import time


def make_x_khronos() -> str:
    """
    Generate X-Khronos value.
    Returns: hex string of the current unix timestamp (8 hex chars).
    """
    ts = round(time.time())
    return hex(ts)[2:]
