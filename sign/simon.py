"""
SIMON-128/128 cipher implementation.
Direct translation from armxe Mobile/cipher/SIMON.py.
"""

from .native import rotate_left, rotate_right, get_bit, validate


class SIMON(object):
    """
    SIMON-128/128 block cipher.
    Encrypts 128-bit blocks (two 64-bit words) using a 128-bit key (four 64-bit words).
    """

    def encode(self, pt, k, c=0):
        """
        Encrypt a 128-bit block.

        Args:
            pt: list of 2 uint64 values [pt0, pt1]
            k:  list of 4 uint64 values [k0, k1, k2, k3]
            c:  mode flag (0 = standard, 1 = variant)

        Returns:
            list of 2 uint64 values [ct0, ct1]
        """
        tmp = 0
        f = 0

        key = [0] * 72
        key[0] = k[0]
        key[1] = k[1]
        key[2] = k[2]
        key[3] = k[3]

        key = self.key_expansion(key=key)

        x_i = pt[0]
        x_i1 = pt[1]

        for i in range(72):
            tmp = x_i1
            if c == 1:
                f = rotate_left(x_i1, 1)
            else:
                f = rotate_left(x_i1, 1) & rotate_left(x_i1, 8)
            x_i1 = ((x_i ^ f) ^ rotate_left(x_i1, 2)) ^ key[i]
            x_i1 = x_i1 & 0xFFFFFFFFFFFFFFFF
            x_i = tmp

        return [x_i, x_i1]

    @staticmethod
    def key_expansion(key):
        """
        Expand the 128-bit key (4 words) into 72 round keys.
        """
        tmp = 0
        for i in range(4, 72):
            tmp = rotate_right(key[i - 1], 3)
            tmp = tmp ^ key[i - 3]
            tmp = tmp ^ rotate_right(tmp, 1)
            key[i] = validate((~key[i - 4] & 0xFFFFFFFFFFFFFFFF) ^ tmp ^ get_bit(0x3DC94C3A046D678B, (i - 4) % 62) ^ 3)
        return key
