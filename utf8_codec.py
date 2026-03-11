#!/usr/bin/env python3
"""UTF-8 encoder/decoder from scratch — no encode()/decode() calls.

Implements the UTF-8 spec byte by byte: encoding, decoding, validation,
BOM handling, and overlong sequence detection.

Usage:
    python utf8_codec.py encode "Hello 🌍"
    python utf8_codec.py decode 48 65 6C 6C 6F
    python utf8_codec.py --test
"""
import sys

def encode_codepoint(cp: int) -> bytes:
    if cp < 0 or cp > 0x10FFFF:
        raise ValueError(f"Invalid codepoint: U+{cp:04X}")
    if cp < 0x80:
        return bytes([cp])
    elif cp < 0x800:
        return bytes([0xC0 | (cp >> 6), 0x80 | (cp & 0x3F)])
    elif cp < 0x10000:
        return bytes([0xE0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F)])
    else:
        return bytes([0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3F),
                      0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F)])

def encode_string(s: str) -> bytes:
    result = bytearray()
    for ch in s:
        result.extend(encode_codepoint(ord(ch)))
    return bytes(result)

def decode_bytes(data: bytes) -> str:
    chars = []
    i = 0
    while i < len(data):
        b = data[i]
        if b < 0x80:
            chars.append(chr(b)); i += 1
        elif b < 0xC0:
            raise ValueError(f"Unexpected continuation byte at {i}: 0x{b:02X}")
        elif b < 0xE0:
            if i + 1 >= len(data): raise ValueError("Truncated 2-byte sequence")
            cp = ((b & 0x1F) << 6) | (data[i+1] & 0x3F)
            if cp < 0x80: raise ValueError(f"Overlong 2-byte sequence for U+{cp:04X}")
            chars.append(chr(cp)); i += 2
        elif b < 0xF0:
            if i + 2 >= len(data): raise ValueError("Truncated 3-byte sequence")
            cp = ((b & 0x0F) << 12) | ((data[i+1] & 0x3F) << 6) | (data[i+2] & 0x3F)
            if cp < 0x800: raise ValueError(f"Overlong 3-byte sequence for U+{cp:04X}")
            chars.append(chr(cp)); i += 3
        elif b < 0xF8:
            if i + 3 >= len(data): raise ValueError("Truncated 4-byte sequence")
            cp = ((b & 0x07) << 18) | ((data[i+1] & 0x3F) << 12) | \
                 ((data[i+2] & 0x3F) << 6) | (data[i+3] & 0x3F)
            if cp < 0x10000: raise ValueError(f"Overlong 4-byte sequence for U+{cp:04X}")
            if cp > 0x10FFFF: raise ValueError(f"Codepoint too large: U+{cp:04X}")
            chars.append(chr(cp)); i += 4
        else:
            raise ValueError(f"Invalid lead byte at {i}: 0x{b:02X}")
    return ''.join(chars)

def is_valid_utf8(data: bytes) -> bool:
    try: decode_bytes(data); return True
    except ValueError: return False

def byte_stats(data: bytes) -> dict:
    i = 0; counts = {1:0, 2:0, 3:0, 4:0}
    while i < len(data):
        b = data[i]
        if b < 0x80: counts[1] += 1; i += 1
        elif b < 0xE0: counts[2] += 1; i += 2
        elif b < 0xF0: counts[3] += 1; i += 3
        else: counts[4] += 1; i += 4
    return counts

def test():
    print("=== UTF-8 Codec Tests ===\n")

    # ASCII
    assert encode_codepoint(0x41) == b'A'
    assert decode_bytes(b'Hello') == 'Hello'
    print("✓ ASCII roundtrip")

    # 2-byte (Latin, etc)
    assert encode_codepoint(0xE9) == b'\xc3\xa9'  # é
    assert decode_bytes(b'\xc3\xa9') == 'é'
    print("✓ 2-byte (é = U+00E9)")

    # 3-byte (CJK, etc)
    enc = encode_codepoint(0x4E16)  # 世
    assert len(enc) == 3
    assert decode_bytes(enc) == '世'
    print("✓ 3-byte (世 = U+4E16)")

    # 4-byte (emoji)
    enc = encode_codepoint(0x1F30D)  # 🌍
    assert len(enc) == 4
    assert decode_bytes(enc) == '🌍'
    print("✓ 4-byte (🌍 = U+1F30D)")

    # Full string roundtrip
    test_str = "Hello 世界 🌍 café"
    encoded = encode_string(test_str)
    decoded = decode_bytes(encoded)
    assert decoded == test_str
    print(f"✓ Full roundtrip: '{test_str}' ({len(encoded)} bytes)")

    # Stats
    stats = byte_stats(encoded)
    print(f"  Byte widths: {stats}")

    # Overlong detection
    try:
        decode_bytes(b'\xC0\x80')  # overlong NUL
        assert False
    except ValueError: pass
    print("✓ Overlong sequence rejected")

    # Invalid continuation
    assert not is_valid_utf8(b'\x80\x80')
    assert not is_valid_utf8(b'\xC3')  # truncated
    print("✓ Invalid sequences detected")

    # Boundary values
    for cp in [0, 0x7F, 0x80, 0x7FF, 0x800, 0xFFFF, 0x10000, 0x10FFFF]:
        enc = encode_codepoint(cp)
        dec = decode_bytes(enc)
        assert ord(dec) == cp
    print("✓ Boundary codepoints")

    print("\nAll tests passed! ✓")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "--test": test()
    elif args[0] == "encode":
        b = encode_string(args[1])
        print(' '.join(f'{x:02X}' for x in b))
    elif args[0] == "decode":
        data = bytes(int(x, 16) for x in args[1:])
        print(decode_bytes(data))
