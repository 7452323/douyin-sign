"""
X-SS-STUB generation - MD5 of request body.
"""

import hashlib
from typing import Union


def make_x_ss_stub(body: Union[bytes, str, None] = None) -> str:
    """
    Generate X-SS-STUB header value.

    Args:
        body: Request body (bytes, str, or None)

    Returns:
        MD5 hex digest (32 char lowercase hex string)
    """
    if body is None or body == b'' or body == '':
        return hashlib.md5(b'').hexdigest()
    if isinstance(body, str):
        body = body.encode('utf-8')
    return hashlib.md5(body).hexdigest()
