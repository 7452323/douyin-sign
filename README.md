# douyin-sign / 抖音全算法签名包

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 中文介绍

### 概述

**douyin-sign** 是一个纯 Python 实现的抖音/TikTok 全算法签名包。它封装了抖音移动端 App 中使用的全部签名算法，帮助开发者一站式生成请求所需的签名头。

### 功能特性

- ✅ **X-Gorgon** — 请求签名 (0404/0405/0407 等版本)
- ✅ **X-Argus** — 风控/设备指纹签名
- ✅ **X-Ladon** — 附加风控签名
- ✅ **X-Khronos** — 请求时间戳签名
- ✅ **X-SS-STUB** — 请求体 MD5 摘要签名
- ✅ **X-Bogus** — 网页端/轻量签名
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

### 版本策略

本包的版本号跟随抖音/TikTok 的 App 版本号（如 `38.3.0`）。初始版本为 `1.0.0`。当 TikTok App 发布新版本时，`update.py` 脚本可用于自动提取并更新常量。

### 许可证

MIT

---

## English

### Overview

**douyin-sign** is a pure Python implementation of the complete TikTok/Douyin signature algorithm suite. It encapsulates all signature algorithms used in the TikTok mobile app, helping developers generate the required signature headers for API requests in one stop.

### Features

- ✅ **X-Gorgon** — Request signing (0404/0405/0407 variants)
- ✅ **X-Argus** — Risk control / device fingerprint signing
- ✅ **X-Ladon** — Additional risk control signature
- ✅ **X-Khronos** — Request timestamp signature
- ✅ **X-SS-STUB** — Request body MD5 digest signature
- ✅ **X-Bogus** — Web / lightweight signature
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

### Versioning Policy

This package version follows TikTok app version numbers (e.g., `38.3.0`). The initial release is `1.0.0`. When TikTok releases a new app version, the `update.py` script can be used to automatically extract and update the constants.

### License

MIT
