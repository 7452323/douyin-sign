"""
douyin-sign - TikTok/Douyin All-in-One Signature Package.

Provides sign_all() to generate all required signature headers.
"""

import time

from . import khronos
from . import ssstub
from . import gorgon
from . import constants as const
from . import protobuf
from . import native
from . import aes
from . import rc4
from . import simon
from . import dyn_encode


def sign_all(method="GET", url="", body=b"", cookies=""):
    """
    Generate all required signature headers for a TikTok/Douyin API request.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full request URL
        body: Request body as bytes
        cookies: Cookie string

    Returns:
        dict of header name -> header value
    """
    headers = {}

    # X-Khronos: timestamp header (hex string of unix time)
    headers["X-Khronos"] = khronos.make_x_khronos()

    # X-SS-STUB: MD5 of request body
    headers["X-SS-STUB"] = ssstub.make_x_ss_stub(body)

    # Parse URL components for gorgon params
    url_str = url if isinstance(url, str) else url.decode()
    params_bytes = b""
    if "?" in url_str:
        params_bytes = url_str.split("?", 1)[1].encode()
    payload_bytes = body if isinstance(body, bytes) else (body.encode() if body else b"")
    cookies_bytes = cookies.encode() if isinstance(cookies, str) else (cookies if cookies else b"")

    # X-Gorgon: full request signature
    ts = round(time.time())
    headers["X-Gorgon"] = gorgon.make_x_gorgon(
        params=params_bytes,
        payload=payload_bytes,
        cookies=cookies_bytes,
        ts=ts,
        is_arm64=True,
    )

    # Note: X-Argus, X-Ladon, X-Bogus require additional context
    # (device fingerprints, page-specific parameters) and are added
    # by higher-level wrappers that call sign_all().

    return headers


__all__ = ["sign_all"]
