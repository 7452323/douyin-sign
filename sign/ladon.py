"""
X-Ladon token generation.
RC4-encrypted concatenation of various fields.
Direct translation from armxe Mobile/metasec.py ladon_encode() and helpers/ladon.py.
"""

import base64
import hashlib
import random

from .native import ror, validate, validate_32


def _ladon_calculation(x9: int, x8: int, x22: int):
    """Ladon internal calculation."""
    r_shifted = ror(x8, 8)
    r_res = ((r_shifted + x9) ^ x22) & 0xFFFFFFFFFFFFFFFF
    l_value_shifted = ((x9 >> (32 + 29)) | (x9 << 3)) & 0xFFFFFFFFFFFFFFFF
    l_res = l_value_shifted ^ r_res
    return r_res, l_res


def get_ladon_keys(app_id: bytes) -> list:
    """
    Generate Ladon key list from app_id hash.

    Args:
        app_id: MD5 hash bytes (16 bytes)

    Returns:
        List of 34 uint64 values
    """
    md5_1 = int.from_bytes(app_id[0:4], byteorder="little")
    md5_2 = int.from_bytes(app_id[4:8], byteorder="little")
    md5_3 = int.from_bytes(app_id[8:12], byteorder="little")
    md5_4 = int.from_bytes(app_id[12:16], byteorder="little")

    R0_list = [md5_2, md5_3, md5_4]
    L0_list = [md5_1]

    for i in range(33):
        l_val, r_val = _ladon_calculation(L0_list[i], R0_list[i], i)
        L0_list.append(validate(r_val))
        R0_list.append(validate(l_val))

    return L0_list


def encode_ladon(
    keys: list,
    da7c: int,
    da84: int,
    da88: int,
    da8c: int,
):
    """
    Ladon encode using key list and 4 uint32 values.

    Args:
        keys: List of uint64 keys
        da7c, da84, da88, da8c: uint32 input values

    Returns:
        (first_bytes, second_bytes) tuple of 8-byte each
    """
    for key in keys:
        da70 = validate_32(da84 >> 8)
        da94 = validate_32(da88 << 0x18)
        da70 = validate_32(da70 | da94)
        da94 = validate_32(da8c + da70)

        if da70 < da94:
            da70 = 0
        else:
            da70 = 1

        da84 = validate_32(da84 << 0x18)
        da88 = validate_32(da88 >> 8)
        da84 = validate_32(da88 | da84)
        da84 = validate_32(da84 + da7c)
        da70 = validate_32(da70 + da84)

        da84 = validate_32(key & 0xFFFFFFFF)
        da84 = validate_32(da94 ^ da84)
        da88 = validate_32(key >> 32)
        da90 = validate_32(da8c << 3)
        da94 = validate_32(da7c >> 0x1d)
        da90 = validate_32(da90 | da94)
        da90 = validate_32(da90 ^ da84)
        da88 = validate_32(da88 ^ da70)
        da70 = validate_32(da8c >> 0x1d)
        da7c = validate_32(da7c << 3)
        da70 = validate_32(da70 | da7c)
        da7c = validate_32(da70 ^ da88)
        da8c = validate_32(da90 | 0x0)

    first = da8c.to_bytes(4, byteorder="little") + da7c.to_bytes(4, byteorder="little")
    second = da84.to_bytes(4, byteorder="little") + da88.to_bytes(4, byteorder="little")

    return first, second


def make_x_ladon(app_id: int, license_id: int, ts: int) -> str:
    """
    Generate X-Ladon token.

    Args:
        app_id:     Application ID (e.g., 1233)
        license_id: License ID (e.g., 1611921764)
        ts:         Unix timestamp

    Returns:
        Base64-encoded X-Ladon string
    """
    signature = f"{ts}-{license_id}-{app_id}".encode("utf-8")
    fill = 32 - len(signature)

    buffer = list(signature)
    for _ in range(fill):
        buffer.append(fill)

    random_bytes = random.randint(0, 0x7fffffff).to_bytes(4, byteorder="little")
    app_id_encoded = hashlib.md5(random_bytes + str(app_id).encode("utf-8")).digest()
    key_list = get_ladon_keys(app_id=app_id_encoded)

    # First round (bytes 0-15)
    f1, s1 = encode_ladon(
        key_list,
        int.from_bytes(buffer[4:8], byteorder="little"),
        int.from_bytes(buffer[8:12], byteorder="little"),
        int.from_bytes(buffer[12:16], byteorder="little"),
        int.from_bytes(buffer[0:4], byteorder="little"),
    )
    encoded = f1 + s1

    # Second round (bytes 16-31)
    f2, s2 = encode_ladon(
        key_list,
        int.from_bytes(buffer[20:24], byteorder="little"),
        int.from_bytes(buffer[24:28], byteorder="little"),
        int.from_bytes(buffer[28:32], byteorder="little"),
        int.from_bytes(buffer[16:20], byteorder="little"),
    )
    encoded = encoded + f2 + s2

    return base64.b64encode(random_bytes + encoded).decode()
