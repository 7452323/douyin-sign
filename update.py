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
import sys
import tempfile
import urllib.request
import zipfile
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

APKCOMBO_URL_TEMPLATES = [
    # Try multiple mirrors/sources
    "https://apkcombo.com/tiktok/com.zhiliaoapp.musically/download/apk",
    "https://apkpure.com/tiktok/com.zhiliaoapp.musically/download",
    "https://apps.apple.com/us/app/tiktok/id123456789",  # placeholder
]


def download_latest_apk(dest: Path) -> Path:
    """
    Download the latest TikTok APK from apkcombo or similar sources.

    NOTE: APK download sources frequently change their URLs and download
    mechanisms. This is a best-effort implementation. If download fails,
    you may need to manually download the APK and place it at:
        constants/current/tiktok-latest.apk
    """
    print("[*] Attempting to download latest TikTok APK...")

    # --- Placeholder / manual path ---
    # In a real implementation, you would:
    # 1. Scrape the download page for the actual APK download link
    # 2. Handle redirects and cookies
    # 3. Verify the APK signature

    # For now, check if a local APK already exists
    local_apk = ROOT / "tiktok-latest.apk"
    if local_apk.exists():
        print(f"[*] Found local APK: {local_apk}")
        return local_apk

    print("[!] Automatic APK download not implemented.")
    print("[!] Please manually download TikTok APK and place it at:")
    print(f"    {local_apk}")
    print("[!] Then re-run this script.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# SO extraction
# ---------------------------------------------------------------------------


def extract_libmetasec(apk_path: Path, workdir: Path) -> Path:
    """
    Extract libmetasec.so from the APK.

    The library is typically found under:
        lib/arm64-v8a/libmetasec.so
        or
        lib/armeabi-v7a/libmetasec.so
    """
    print(f"[*] Extracting libmetasec.so from {apk_path} ...")

    with zipfile.ZipFile(apk_path, "r") as zf:
        candidates = [
            name for name in zf.namelist()
            if "libmetasec" in name and name.endswith(".so")
        ]

        if not candidates:
            print("[!] libmetasec.so not found in APK!")
            print("    Candidates searched: any path containing 'libmetasec'")
            sys.exit(1)

        # Prefer arm64-v8a, fall back to any
        chosen = None
        for c in candidates:
            if "arm64-v8a" in c:
                chosen = c
                break
        if not chosen:
            chosen = candidates[0]

        print(f"    Found: {chosen}")
        zf.extract(chosen, workdir)
        so_path = workdir / chosen
        return so_path


# ---------------------------------------------------------------------------
# Search in SO
# ---------------------------------------------------------------------------


def search_sign_key(so_data: bytes) -> str:
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

    print(f"    No exact match to known key; returning first candidate.")
    return candidates[0]


def search_gorgon_table(so_data: bytes) -> str:
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

    print(f"    No exact match to known table; returning first candidate.")
    return candidates[0]


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
    print("=" * 60)
    print("  douyin-sign Constants Update Script")
    print("=" * 60)

    # 1. Ensure constants dir exists
    CONSTANTS_CURRENT.mkdir(parents=True, exist_ok=True)

    # 2. Download APK
    apk_path = download_latest_apk(ROOT / "tiktok-latest.apk")

    # 3. Work in a temp directory
    with tempfile.TemporaryDirectory(prefix="douyin-sign-") as tmp:
        workdir = Path(tmp)

        # 4. Extract libmetasec.so
        so_path = extract_libmetasec(apk_path, workdir)
        so_data = so_path.read_bytes()

        # 5. Search for constants
        sign_key = search_sign_key(so_data)
        gorgon_table = search_gorgon_table(so_data)
        # Note: protobuf_fields are not extracted from the SO; they come
        # from static analysis of the app's protobuf definitions. Update
        # them manually when TikTok adds/changes fields.

        if not sign_key and not gorgon_table:
            print("[!] No constants found. Nothing to update.")
            sys.exit(1)

    # 6. Update files and show diffs
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
    else:
        print("[=] All constants unchanged.")

    print("[✓] Done.")


if __name__ == "__main__":
    main()
