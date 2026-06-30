"""
douyin-sign — TikTok/Douyin All-in-One Signature Package.

Provides sign_all() for header generation and sign_mobile_request()
for end-to-end signed Mobile API calls.
"""

import asyncio
import json
import time
from typing import Optional

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
from .device import Device, register_device, make_seed_device

MOBILE_API_BASE = "https://api.douyin.com"


def sign_all(method="GET", url="", body=b"", cookies="", device=None):
    """生成一次请求所需的所有签名头。

    Args:
        method:  HTTP method
        url:     完整请求 URL
        body:    请求体 bytes
        cookies: Cookie 字符串（或 Encoding 字符串）
        device:  Device 对象（传入后用于 X-Argus 等设备指纹签名）

    Returns:
        dict of header name -> header value
    """
    headers = {}

    headers["X-Khronos"] = khronos.make_x_khronos()

    body_bytes = body if isinstance(body, bytes) else body.encode() if body else b""
    headers["X-SS-STUB"] = ssstub.make_x_ss_stub(body_bytes)

    url_str = url if isinstance(url, str) else url.decode()
    params_bytes = (url_str.split("?", 1)[1].encode() if "?" in url_str else b"")
    cookies_str = cookies if isinstance(cookies, str) else (cookies.decode() if cookies else "")
    cookies_bytes = cookies_str.encode()

    ts = round(time.time())
    headers["X-Gorgon"] = gorgon.make_x_gorgon(
        params=params_bytes,
        payload=body_bytes,
        cookies=cookies_bytes,
        ts=ts,
        is_arm64=True,
    )

    # X-Argus（需 device info）
    if device is not None and device.device_id:
        try:
            headers["X-Argus"] = make_x_argus_default(
                params=params_bytes,
                payload=body_bytes,
                ts=ts,
                device=device,
            )
        except Exception:
            pass  # Argus 不阻塞主流程

    return headers


def sign_mobile_request(
    method: str = "GET",
    path: str = "",
    body: dict = None,
    device: Optional[Device] = None,
    params: dict = None,
    *,
    return_headers: bool = False,
) -> dict:
    """向 Mobile API 发签名请求。

    使用 ``api.douyin.com``（而非 www.douyin.com/aweme/v1/web/）
    Mobile API 端点。自动算签名、带设备信息、发请求。

    Args:
        method:        HTTP method (GET / POST)
        path:          API 路径，如 ``/aweme/v1/aweme/post/``
        body:          JSON 请求体 dict
        device:        Device 对象（缺省用 seed 设备）
        params:        URL 查询参数 dict
        return_headers: 如果 True，只返回签名头不实际发请求

    Returns:
        返回响应 JSON（dict），或签名头 dict（``return_headers=True``）

    Example:
        >>> result = sign_mobile_request(
        ...     "GET",
        ...     "/aweme/v1/aweme/post/",
        ...     params={"sec_user_id": "MS4wLjAB..."},
        ... )
        >>> result["aweme_list"]
    """
    import httpx

    d = device or make_seed_device()

    # Build full URL
    qs = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    url = f"{MOBILE_API_BASE}{path}"
    if qs:
        url += f"?{qs}"

    # Body
    body_bytes = json.dumps(body, separators=(",", ":")).encode() if body else b""

    # Cookie from device
    cookies_str = d.to_cookie()

    # Sign
    sig_headers = sign_all(
        method=method,
        url=url,
        body=body_bytes,
        cookies=cookies_str,
        device=d,
    )

    if return_headers:
        return sig_headers

    # Real request
    req_headers = {
        **d.to_headers(),
        **sig_headers,
        "Content-Type": "application/json; charset=utf-8",
    }

    resp = httpx.request(
        method=method,
        url=url,
        headers=req_headers,
        content=body_bytes if method == "POST" else None,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def make_x_argus_default(
    params: bytes,
    payload: bytes,
    ts: int,
    device: Device,
    sign_key: bytes = None,
    dyn_version: int = 8,
) -> str:
    """用 Device 信息生成 X-Argus（默认参数）。"""
    from .argus import make_x_argus

    return make_x_argus(
        params=params,
        payload=payload,
        ts=ts,
        app_id=1128,
        app_version=device.app_version,
        app_launch_time=int(time.time() * 1000 - 60000),
        device_type=device.device_type,
        sdk_version="3.0.0",
        sdk_version_code=380500,
        license_id=12345,
        device_id=device.device_id,
        device_token=device.install_id,
        dyn_seed="default",
        dyn_version=dyn_version,
        sign_key=sign_key,
    )


__all__ = ["sign_all", "sign_mobile_request", "Device", "register_device", "make_seed_device"]
