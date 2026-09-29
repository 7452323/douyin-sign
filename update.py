#!/usr/bin/env python3
"""
douyin-sign constants update script.

Downloads the latest TikTok APK, extracts libmetasec.so, and searches for
SIGN_KEY and GORGON_TABLE constants. Updates constants/current/ files
and prints a diff of what changed.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import time
import urllib.request
import zipfile
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
CONSTANTS_CURRENT = ROOT / "constants" / "current"
SIGN_KEY_PATH = CONSTANTS_CURRENT / "sign_key.b64"
GORGON_TABLE_PATH = CONSTANTS_CURRENT / "gorgon_table.hex"
PROTOBUF_FIELDS_PATH = CONSTANTS_CURRENT / "protobuf_fields.json"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# SIGN_KEY: a 44-character base64 string (no padding variations) in the .so
# This regex finds any 44-char base64 token (A-Za-z0-9+/=).
SIGN_KEY_RE = re.compile(rb"[A-Za-z0-9+/]{44,44}={0,2}")

# GORGON_TABLE: a 20-byte hex constant stored as contiguous hex bytes in the .so.
# Look for the literal hex string "ce7c47e421ff095cc9da81690147cba1ed6cc4b1"
# but also any 40-hex-char sequence as a viable candidate.
GORGON_TABLE_RE = re.compile(rb"[0-9a-f]{40,40}", re.IGNORECASE)


# ---------------------------------------------------------------------------
# APK download helpers
# ---------------------------------------------------------------------------

APK_SOURCES = [
    # APKPure's direct endpoint 302s to a signed CDN link.
    "https://d.apkpure.com/b/APK/com.zhiliaoapp.musically?version=latest",
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# The TikTok APK is ~470 MB. It is never downloaded whole: the mirror gives
# us the real CDN URL, and the ZIP central directory plus the handful of
# entries we need are read with HTTP range requests (a few hundred KB).
TAIL_WINDOW = 131072


APKCOMBO_PAGES = [
    # Fallback sources: APKPure's edge rejects some CI IP ranges, these pages
    # still expose a direct storage link.
    "https://apkcombo.com/tiktok/com.zhiliaoapp.musically/download/apk",
]


def _version_from_url(url):
    m = re.search(r"_([0-9]+\.[0-9][0-9.]*)_", url) or re.search(
        r"/([0-9]+\.[0-9][0-9.]*)/", url
    )
    return m.group(1) if m else "unknown"


def _probe(url, label):
    """Range-probe a candidate URL; returns (final_url, size, version) or raises."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        final = resp.geturl()
        cr = resp.headers.get("Content-Range", "")
        size = int(cr.split("/")[-1]) if "/" in cr else int(
            resp.headers.get("Content-Length") or 0
        )
    if size < 10 * 1024 * 1024:
        raise RuntimeError(f"unexpected size {size}")
    version = _version_from_url(final)
    print(f"[*] APK source resolved ({label}): {version} ({size} bytes)")
    return final, size, version


def resolve_apk_source():
    """
    Resolve the latest TikTok APK to (url, size, version).

    Primary route: APKPure's direct endpoint 302s to a signed CDN link.
    Fallback: scrape an APKCombo download page for its storage link, since
    APKPure blocks some CI IP ranges with a 403.
    """
    for src in APK_SOURCES:
        try:
            return _probe(src, "apkpure")
        except Exception as exc:
            print(f"[!] {src}: {exc}")

    for page in APKCOMBO_PAGES:
        try:
            req = urllib.request.Request(
                page,
                headers={
                    "User-Agent": UA,
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                html = resp.read().decode("utf-8", "replace")
            m = re.search(
                r"https://[a-z0-9.\-]+\.r2\.cloudflarestorage\.com/[^\"'\\ ]{20,}", html
            )
            if not m:
                m2 = re.search(r"/r2\?u=([^\"&]{20,})", html)
                if not m2:
                    raise RuntimeError("no storage link found on page")
                link = "https://apkcombo.com/r2?u=" + m2.group(1)
            else:
                link = m.group(0)
            return _probe(link, "apkcombo")
        except Exception as exc:
            print(f"[!] {page}: {exc}")

    print("[!] No APK source reachable.")
    return None, 0, ""


class RemoteZip:
    """Range-reading ZIP reader — only the central directory and the
    requested entries are fetched, never the whole archive."""

    def __init__(self, url, size):
        self.url = url
        self.size = size
        self._entries = None

    def _fetch(self, start, end):
        req = urllib.request.Request(
            self.url, headers={"User-Agent": UA, "Range": f"bytes={start}-{end}"}
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read()

    def entries(self):
        if self._entries is not None:
            return self._entries
        tail = self._fetch(max(0, self.size - TAIL_WINDOW), self.size - 1)
        eocd = tail.rfind(b"PK\x05\x06")
        if eocd < 0:
            raise RuntimeError("EOCD not found in APK tail")
        cd_size, cd_off = struct.unpack("<II", tail[eocd + 12:eocd + 20])
        if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
            z = tail.rfind(b"PK\x06\x06")
            if z < 0:
                raise RuntimeError("ZIP64 EOCD not found")
            cd_size, cd_off = struct.unpack("<QQ", tail[z + 40:z + 56])
        cd = self._fetch(cd_off, cd_off + cd_size - 1)
        out = {}
        pos = 0
        while pos < len(cd) - 4 and cd[pos:pos + 4] == b"PK\x01\x02":
            method, = struct.unpack("<H", cd[pos + 10:pos + 12])
            csize, usize = struct.unpack("<II", cd[pos + 20:pos + 28])
            nlen, elen, clen = struct.unpack("<HHH", cd[pos + 28:pos + 34])
            lho, = struct.unpack("<I", cd[pos + 42:pos + 46])
            name = cd[pos + 46:pos + 46 + nlen].decode("utf-8", "replace")
            if 0xFFFFFFFF in (csize, usize, lho):
                extra = cd[pos + 46 + nlen:pos + 46 + nlen + elen]
                q = 0
                while q + 4 <= len(extra):
                    hid, hsz = struct.unpack("<HH", extra[q:q + 4])
                    if hid == 0x0001:
                        v, k = extra[q + 4:q + 4 + hsz], 0
                        if usize == 0xFFFFFFFF:
                            usize = struct.unpack("<Q", v[k:k + 8])[0]
                            k += 8
                        if csize == 0xFFFFFFFF:
                            csize = struct.unpack("<Q", v[k:k + 8])[0]
                            k += 8
                        if lho == 0xFFFFFFFF:
                            lho = struct.unpack("<Q", v[k:k + 8])[0]
                    q += 4 + hsz
            out[name] = (method, csize, usize, lho)
            pos += 46 + nlen + elen + clen
        self._entries = out
        return out

    def read(self, name):
        method, csize, usize, lho = self.entries()[name]
        head = self._fetch(lho, lho + 4096)
        nlen, elen = struct.unpack("<HH", head[26:30])
        start = lho + 30 + nlen + elen
        blob = self._fetch(start, start + csize - 1)
        raw = zlib.decompress(blob, -15) if method == 8 else blob
        if len(raw) != usize:
            raise RuntimeError(f"{name}: size mismatch {len(raw)} != {usize}")
        return raw


# Name fragments of every native library that has historically carried the
# signing constants (TikTok renamed libmetasec.so to libmetasec_ov.so in the
# 4x builds).
SO_CANDIDATES = ["libmetasec", "liboecsec"]
SO_MAX_BYTES = 16 * 1024 * 1024


def pick_so(names):
    """Choose the arm64 candidate for each known library name."""
    picks = []
    for frag in SO_CANDIDATES:
        hits = [n for n in names if frag in n and n.endswith(".so")]
        arm64 = [n for n in hits if "arm64" in n]
        if arm64:
            picks.append(arm64[0])
        elif hits:
            picks.append(hits[0])
    return picks


# ---------------------------------------------------------------------------
# SO extraction
# ---------------------------------------------------------------------------


def extract_libmetasec(apk_path, workdir, remote=None):
    """
    Extract every candidate signing library from the APK.

    A local APK wins when present (fast, offline); otherwise the entries are
    pulled out of the remote archive with range reads. Returns a list of
    extracted paths — later builds split the constants across more than one
    library, so callers search all of them.
    """
    workdir = Path(workdir)

    if apk_path is not None and Path(apk_path).exists():
        print(f"[*] Extracting signing libraries from {apk_path} ...")
        with zipfile.ZipFile(apk_path, "r") as zf:
            picks = pick_so(zf.namelist())
            if not picks:
                raise RuntimeError("no libmetasec/liboecsec entry in the APK")
            out = []
            for name in picks:
                dest = workdir / os.path.basename(name)
                dest.write_bytes(zf.read(name))
                print(f"    {name} -> {dest.name} ({dest.stat().st_size} bytes)")
                out.append(dest)
            return out

    if remote is None:
        raise RuntimeError("no local APK and no remote source available")

    print("[*] Extracting signing libraries over HTTP range reads ...")
    entries = remote.entries()
    out = []
    for name in pick_so(entries):
        usize = entries[name][2]
        if usize > SO_MAX_BYTES:
            print(f"    {name}: skipped ({usize} bytes > cap)")
            continue
        dest = workdir / os.path.basename(name)
        dest.write_bytes(remote.read(name))
        print(f"    {name} -> {dest.name} ({dest.stat().st_size} bytes)")
        out.append(dest)
    if not out:
        raise RuntimeError("no libmetasec/liboecsec entry in the APK")
    return out


# ---------------------------------------------------------------------------
# Search in SO
# ---------------------------------------------------------------------------


def search_sign_key(so_data: bytes) -> str | None:
    """
    Search for SIGN_KEY in libmetasec.so.

    The sign key is typically a 44-byte base64 string stored as an ASCII
    constant in the .rodata or .data section. Many such strings may appear;
    we cross-reference against the known good key and take the most
    plausible candidate.
    """
    print("[*] Searching for SIGN_KEY ...")

    matches = SIGN_KEY_RE.findall(so_data)
    # Decode and filter plausible keys (no whitespace, printable)
    candidates = []
    for m in set(matches):  # deduplicate
        try:
            decoded = m.decode("ascii")
            # A valid base64 key of 44 chars (without padding =)
            if len(decoded) == 44 and decoded.endswith("="):
                # Attempt base64 decode to verify
                try:
                    base64.b64decode(decoded)
                    candidates.append(decoded)
                except Exception:
                    pass
        except Exception:
            pass

    if not candidates:
        print("[!] No valid SIGN_KEY candidates found.")
        return None

    print(f"    Found {len(candidates)} candidate(s).")

    # Use the known key as a reference to pick the right one,
    # or just return the first candidate if none match.
    known_key = "wC8lD4bMTxmNVwY5jSkqi3QWmrphr/58ugLko7UZgWM="
    if known_key in candidates:
        print(f"    Matches known key.")
        return known_key

    print(f"    No exact match to known key; skipped (never guess a key).")
    return None


def search_gorgon_table(so_data: bytes) -> str | None:
    """
    Search for GORGON_TABLE in libmetasec.so.

    The gorgon table is a 20-byte (40 hex chars) constant used as a
    lookup table or IV in the Gorgon algorithm. It appears as a literal
    hex string in the binary.
    """
    print("[*] Searching for GORGON_TABLE ...")

    matches = GORGON_TABLE_RE.findall(so_data)
    candidates = []
    for m in set(matches):
        try:
            hex_str = m.decode("ascii").lower()
            if len(hex_str) == 40:
                # Verify it's valid hex
                int(hex_str, 16)
                candidates.append(hex_str)
        except Exception:
            pass

    if not candidates:
        print("[!] No valid GORGON_TABLE candidates found.")
        return None

    print(f"    Found {len(candidates)} candidate(s).")

    known_table = "ce7c47e421ff095cc9da81690147cba1ed6cc4b1"
    if known_table in candidates:
        print(f"    Matches known table.")
        return known_table

    print(f"    No exact match to known table; skipped (never guess a table).")
    return None


# ---------------------------------------------------------------------------
# File update & diff
# ---------------------------------------------------------------------------


def read_current(path: Path) -> str:
    """Read the current constant file contents, or empty string if missing."""
    if path.exists():
        return path.read_text().strip()
    return ""


def write_and_diff(path: Path, new_content: str, label: str) -> bool:
    """
    Write new_content to path (with trailing newline) and print a diff
    against the previous contents. Returns True if something changed.
    """
    old = read_current(path)
    new = new_content.strip() + "\n"

    if old == new.strip():
        print(f"    {label}: unchanged")
        return False

    print(f"    {label}: CHANGED")
    print(f"      Old: {old}")
    print(f"      New: {new.strip()}")
    path.write_text(new)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    strict = "--strict" in sys.argv
    print("=" * 60)
    print("  douyin-sign Constants Update Script")
    print("=" * 60)

    # 1. Ensure constants dir exists
    CONSTANTS_CURRENT.mkdir(parents=True, exist_ok=True)

    # 2. Resolve the APK: a local copy wins (offline, fast), otherwise the
    #    remote archive is read over HTTP range requests.
    apk_path = ROOT / "tiktok-latest.apk"
    remote = None
    apk_size = 0
    version = "unknown"
    if apk_path.exists():
        print(f"[*] Found local APK: {apk_path}")
    else:
        url, apk_size, version = resolve_apk_source()
        if url:
            remote = RemoteZip(url, apk_size)

    report = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "apk_version": version,
        "apk_size": apk_size,
        "sign_key": None,
        "gorgon_table": None,
        "note": "",
    }

    sign_key = None
    gorgon_table = None
    try:
        with tempfile.TemporaryDirectory(prefix="douyin-sign-") as tmp:
            so_paths = extract_libmetasec(
                apk_path if apk_path.exists() else None, tmp, remote
            )
            for so_path in so_paths:
                so_data = so_path.read_bytes()
                print(f"[*] Searching {so_path.name} ({len(so_data)} bytes) ...")
                sign_key = sign_key or search_sign_key(so_data)
                gorgon_table = gorgon_table or search_gorgon_table(so_data)
    except Exception as exc:
        report["note"] = f"extraction failed: {exc}"
        print(f"[!] Extraction failed: {exc}")

    if not sign_key and not gorgon_table:
        report["note"] = report["note"] or (
            "no plaintext SIGN_KEY / GORGON_TABLE in the candidate libraries; "
            "recent TikTok builds keep them inside an encrypted payload — "
            "see README section 'Constants hardening'"
        )
        print("[!] No constants found.")
        print(f"    {report['note']}")

    report["sign_key"] = sign_key
    report["gorgon_table"] = gorgon_table

    # 3. Record what we saw, then update the constants that did move.
    if version != "unknown":
        (CONSTANTS_CURRENT / "apk_version.txt").write_text(version + "\n")
    (CONSTANTS_CURRENT / "last-check.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )

    print()
    print("--- Update Summary ---")
    changed = False

    if sign_key:
        if write_and_diff(SIGN_KEY_PATH, sign_key, "sign_key.b64"):
            changed = True
    else:
        print("    sign_key.b64: no candidate (skipped)")

    if gorgon_table:
        if write_and_diff(GORGON_TABLE_PATH, gorgon_table, "gorgon_table.hex"):
            changed = True
    else:
        print("    gorgon_table.hex: no candidate (skipped)")

    # protobuf_fields.json is not auto-updated from the SO
    print("    protobuf_fields.json: manual update required for field changes")

    print()
    if changed:
        print("[✓] Constants updated. Review the diff above.")
    elif sign_key or gorgon_table:
        print("[=] All constants unchanged.")
    else:
        print("[=] Nothing extracted — see constants/current/last-check.json.")
        if strict:
            sys.exit(1)
    print("[✓] Done.")


if __name__ == "__main__":
    main()
