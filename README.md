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
    └── protobuf_fields.json  # Protobuf 字段编号映射表
```

常量文件随抖音 App 版本更新。`current/` 目录始终指向最新已验证的常量集。历史常量保存在带版本号的目录中（例如 `constants/v38.3.0/`）。

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
    └── protobuf_fields.json  # Protobuf field number mapping table
```

Constants are updated alongside TikTok app versions. The `current/` directory always points to the latest verified set of constants. Historical constants are kept in versioned directories (e.g., `constants/v38.3.0/`).

### Versioning Policy

This package version follows TikTok app version numbers (e.g., `38.3.0`). The initial release is `1.0.0`. When TikTok releases a new app version, the `update.py` script can be used to automatically extract and update the constants.

### License

MIT
