# douyin-sign / 抖音全算法签名包

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 中文介绍

### 概述

**douyin-sign** 是一个纯 Python 实现的抖音/TikTok 全算法签名包。它封装了抖音移动端 App 中使用的全部签名算法，帮助开发者一站式生成请求所需的签名头。

### 功能特性

- ✅ **X-Gorgon** — 请求签名（`8404a0ae1000` arm64 / `0404a0ae1000` arm 前缀）
- ✅ **X-Argus** — 风控/设备指纹签名（protobuf + SIMON + AES）
- ✅ **X-Ladon** — 附加风控签名
- ✅ **X-Khronos** — 请求时间戳签名
- ✅ **X-SS-STUB** — 请求体 MD5 摘要签名
- ✅ **X-Bogus** — 网页端/轻量签名
- ✅ **X-Gnarly** — 网页端新版签名
- ✅ **A-Bogus** — SM3 派生的网页端签名
- ✅ **x-secsdk-web-signature** — 网页端风控签名（ArgusSecurityPlugin）
- ✅ **TTEncrypt** — TikTok 自定义加密算法

### 安装

```bash
pip install douyin-sign
```

### 快速开始

```python
from sign import sign_all

headers = sign_all(
    method='POST',
    url='https://...',
    body=b'...',
    cookies='...',
)

# headers 现在包含 X-Gorgon, X-Khronos, X-SS-STUB 等
```

### 常量目录结构

```
constants/
└── current/
    ├── sign_key.b64          # Base64 编码的签名密钥（44 字节）
    ├── gorgon_table.hex      # Gorgon 算法使用的十六进制查表常量（20 字节）
    ├── protobuf_fields.json  # Protobuf 字段编号映射表
    ├── apk_version.txt       # 最近一次检查对应的 TikTok 版本
    └── last-check.json       # 最近一次检查的时间 / 版本 / 结果（审计用）
```

常量文件随抖音 App 版本更新。`current/` 目录始终指向最新已验证的常量集。历史常量保存在带版本号的目录中（例如 `constants/v38.3.0/`）。

### 常量加固（Constants hardening）

自 TikTok 4x 版本起，APK 内的常量不再以明文形式存在：

- `libmetasec.so` 更名为 `libmetasec_ov.so`，内部载荷被加密/压缩——字符串表里既没有 `SIGN_KEY`／`GORGON`，也没有任何 44 字符 base64 或 40 字符 hex 常量；
- 同族库 `liboecsec_ov.so`、`libpns_crypto.so`、`libttcrypto.so` 实测同样不含明文常量；
- 因此 `update.py` 在最新 APK 上会**报告「未提取到常量」并以 0 退出**（而不是让 CI 变红），检查结论写入 `constants/current/last-check.json`。

`update.py` 的行为约定：

- 有本地 `tiktok-latest.apk` 时离线提取；否则经 APKPure 的重定向解析出 CDN 地址，**只读 ZIP 中央目录与目标库**（几 MB，而不是整包 ~470 MB）；
- **绝不猜常量**：候选值必须与仓库现有值完全一致才会写回，否则只打印候选供人工审阅——写错一个字节会让所有签名失效。

若要恢复自动提取，需要先对 `libmetasec_ov.so` 内的加密载荷脱壳（Skanda/komprese 壳），或改用仍含明文常量的版本作为来源。

### 常量何时会失效

`sign_key.b64` / `gorgon_table.hex` 是**静态**的：它们来自某个 `libmetasec_ov.so` 构建，**不随 App 版本号走，只随 native MSSDK 变**。判据是 `mssdk_ver_code`——当前 `83952160` 在 37.x 与 46.x 之间共享，所以这组常量在 4x 上依然有效（已由第三方在 v46 上实测：连续 15 次搜索全部成功、150 条结果）。

失效是**静默**的：签名格式完全合法、HTTP 200，风控只是返回空结果。判别方法：把签名切到任一线下服务跑同一条请求——付费签名也空 → 身份/风控问题；只有本地签名空 → 常量过期。

当前参数（v46）：

| 参数 | 值 |
|---|---|
| `app_version` | `46.0.42` |
| `mssdk_ver_code` | `83952160` |
| `mssdk_ver_str` | `v05.01.02-alpha.7-ov-android` |
| `license_id` | `2142840551` |
| `aid` | `1233` |

以上在 `sign/device.py` 中导出（`APP_VERSIONS` / `MSSDK_VER_CODE` / `MSSDK_VER_STR` / `LICENSE_ID` / `APP_ID`）。

### 尚未覆盖

字节系较新的 `X-Medusa` / `X-Helios`（番茄小说、红果等国内 App 在用）尚未实现——本包已覆盖 TikTok 国际版移动端 4 头（Khronos / SS-STUB / Gorgon / Ladon / Argus）+ Web 端（Bogus / Gnarly / A-Bogus / x-secsdk-web-signature）+ TTEncrypt。

### Web 端风控签名

抖音网页版对被保护的接口（`/aweme/v1/web/aweme/detail/` 等，见 `sign/websign.py` 的 `PROTECTED_PATHS_GET`）会校验 `x-secsdk-web-signature`：缺 `uifid` 头报 `403 Uifid Not Found`，有 `uifid` 但没签名报 `403 Signature Not Found`。

```python
from sign import websign_sign

signed_query, sig = websign_sign("device_platform=webapp&aid=6383&aweme_id=...", uifid)
url = "https://www.douyin.com/aweme/v1/web/aweme/detail/?" + signed_query
```

签名是 `md5(f"{uifid}_{timestamp}_{SALT}_{canonical_query}")`，`SALT` 是 secsdk VM 字符串表里的常量（`runtime_bundler_34.js`，project-id 34），**与账号无关**。三条不可省的规则：`uifid` 只在 query 里没有时才追加到末尾；`timestamp`（整秒）追加在 `uifid` 之后；**被哈希的 query 必须与线上发送的字节完全一致**。

`uifid` 取自浏览器种下的 `UIFID` cookie（320 位十六进制）。它不是本地算出来的，而是 secsdk + 服务端签发的访客身份串，所以仍然需要一次真实浏览器会话来取得它。

### 版本策略

本包的版本号跟随抖音/TikTok 的 App 版本号（如 `38.3.0`）。初始版本为 `1.0.0`。当 TikTok App 发布新版本时，`update.py` 脚本可用于自动提取并更新常量。

### 许可证

MIT

---

## English

### Overview

**douyin-sign** is a pure Python implementation of the complete TikTok/Douyin signature algorithm suite. It encapsulates all signature algorithms used in the TikTok mobile app, helping developers generate the required signature headers for API requests in one stop.

### Features

- ✅ **X-Gorgon** — Request signing (`8404a0ae1000` arm64 / `0404a0ae1000` arm prefix)
- ✅ **X-Argus** — Risk control / device fingerprint signing (protobuf + SIMON + AES)
- ✅ **X-Ladon** — Additional risk control signature
- ✅ **X-Khronos** — Request timestamp signature
- ✅ **X-SS-STUB** — Request body MD5 digest signature
- ✅ **X-Bogus** — Web / lightweight signature
- ✅ **X-Gnarly** — Newer web signature
- ✅ **A-Bogus** — SM3-derived web signature
- ✅ **TTEncrypt** — TikTok custom encryption algorithm

### Installation

```bash
pip install douyin-sign
```

### Quick Start

```python
from sign import sign_all

headers = sign_all(
    method='POST',
    url='https://...',
    body=b'...',
    cookies='...',
)

# headers now contains X-Gorgon, X-Khronos, X-SS-STUB, etc.
```

### Constants Directory Structure

```
constants/
└── current/
    ├── sign_key.b64          # Base64-encoded signing key (44 bytes)
    ├── gorgon_table.hex      # Hex lookup table constant used by Gorgon algorithm (20 bytes)
    ├── protobuf_fields.json  # Protobuf field number mapping table
    ├── apk_version.txt       # TikTok version of the last check
    └── last-check.json       # Timestamp / version / result of the last check
```

Constants are updated alongside TikTok app versions. The `current/` directory always points to the latest verified set of constants. Historical constants are kept in versioned directories (e.g., `constants/v38.3.0/`).

### Constants hardening

Since the TikTok 4x builds the constants are no longer extractable as plaintext:

- `libmetasec.so` was renamed to `libmetasec_ov.so` and its payload is encrypted/compressed — no `SIGN_KEY` / `GORGON` string, no 44-char base64 and no 40-char hex constant survives a string scan;
- the sibling libraries `liboecsec_ov.so`, `libpns_crypto.so` and `libttcrypto.so` were checked as well and carry no plaintext constants either;
- `update.py` therefore **reports "no constants extracted" and exits 0** on the latest APK (no more red nightly CI) and records the outcome in `constants/current/last-check.json`.

`update.py` contract:

- with a local `tiktok-latest.apk` it extracts offline; otherwise it resolves the CDN URL through APKPure's redirect and **reads only the ZIP central directory plus the target libraries** (a few MB instead of the full ~470 MB);
- it **never guesses**: a candidate is written back only when it matches the shipped value byte for byte, otherwise candidates are printed for manual review — a single wrong byte breaks every signature.

Restoring automatic extraction means unpacking the encrypted payload inside `libmetasec_ov.so` (Skanda/komprese) or sourcing constants from a build that still ships them in plaintext.

### When the constants go stale

`sign_key.b64` / `gorgon_table.hex` are **static**: they come from one specific `libmetasec_ov.so` build and do **not** follow the app version number — they follow the native MSSDK. The discriminator is `mssdk_ver_code`; the current `83952160` is shared between the 37.x and 46.x builds, which is why this pair still signs v46 traffic (third-party measurement: 15/15 consecutive searches, 150 records, zero rejects).

Staleness is **silent**: the signature stays well-formed, the request returns HTTP 200, and risk control simply hands back an empty result set. To tell it apart from an identity block, sign the same request through a hosted signer: empty there too → identity; empty only locally → stale key.

Current v46 parameters:

| Parameter | Value |
|---|---|
| `app_version` | `46.0.42` |
| `mssdk_ver_code` | `83952160` |
| `mssdk_ver_str` | `v05.01.02-alpha.7-ov-android` |
| `license_id` | `2142840551` |
| `aid` | `1233` |

They are exported from `sign/device.py` (`APP_VERSIONS` / `MSSDK_VER_CODE` / `MSSDK_VER_STR` / `LICENSE_ID` / `APP_ID`).

### Not covered yet

The newer ByteDance headers `X-Medusa` / `X-Helios` (used by mainland apps such as Fanqie and Hongguo) are not implemented — everything else is: the four TikTok-mobile headers (Khronos / SS-STUB / Gorgon / Ladon / Argus), the web signers (Bogus / Gnarly / A-Bogus / x-secsdk-web-signature) and TTEncrypt.

### The web risk-control signature

Douyin's web front end sign-protects a subset of its API (see `PROTECTED_PATHS_GET` in `sign/websign.py`). A request without `x-secsdk-web-signature` is refused with `403 Blocked by ArgusSecurityPlugin Signature Not Found`; without the `uifid` header it fails one step earlier, with `... Uifid Not Found`.

```python
from sign import websign_sign

signed_query, sig = websign_sign("device_platform=webapp&aid=6383&aweme_id=...", uifid)
url = "https://www.douyin.com/aweme/v1/web/aweme/detail/?" + signed_query
```

The signature is `md5(f"{uifid}_{timestamp}_{SALT}_{canonical_query}")`, where `SALT` is a constant in secsdk's VM string table (`runtime_bundler_34.js`, project-id 34) and is **not bound to an account**. Three rules that are not optional: `uifid` is appended to the end of the query only when it is not already there; `timestamp` (whole seconds) goes after it; and **the query that is hashed must be byte-identical to the query on the wire**.

`uifid` comes from the `UIFID` cookie a browser session mints (320 hex characters). It is not computed locally — secsdk and the server issue it — so one real browser session is still needed to obtain it.

### Versioning Policy

This package version follows TikTok app version numbers (e.g., `38.3.0`). The initial release is `1.0.0`. When TikTok releases a new app version, the `update.py` script can be used to automatically extract and update the constants.

### License

MIT
