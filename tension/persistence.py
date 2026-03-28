"""
Persistence for Rayon tension objects.

Save/load RayonInt and RayonArray states including ? bits and tension.

Binary format (compact):
  Header: 1 byte type tag + 4 bytes width/length
  RayonInt: 2 bits per bit-position (00=zero, 01=one, 10=unknown), packed.
  RayonArray: element count + name + sequence of serialized RayonInts.

JSON format (human-readable):
  RayonInt: {"type": "RayonInt", "width": N, "bits": [0, 1, null, ...]}
  RayonArray: {"type": "RayonArray", "name": "...", "width": N, "elements": [...]}
  ? bits shown as null.
"""

import sys
import os

# The local types.py shadows stdlib types, which breaks json/re/enum imports.
# Temporarily remove the tension directory from sys.path, import stdlib modules,
# then restore it.
_this_dir = os.path.dirname(os.path.abspath(__file__))
_orig_path = sys.path[:]
sys.path = [p for p in sys.path if os.path.abspath(p) != _this_dir]

import struct
import json
import math

sys.path = _orig_path
sys.path.insert(0, _this_dir)

from rayon_numbers import RayonInt
from memory import RayonArray


# ════════════════════════════════════════════════════════════
# TYPE TAGS
# ════════════════════════════════════════════════════════════

TAG_RAYON_INT = 0x01
TAG_RAYON_ARRAY = 0x02

# Tri-state encoding: 2 bits per bit-position
#   00 = 0
#   01 = 1
#   10 = ? (unknown / None)
#   11 = reserved

_ENC_ZERO = 0b00
_ENC_ONE  = 0b01
_ENC_UNK  = 0b10


# ════════════════════════════════════════════════════════════
# BINARY SERIALIZATION
# ════════════════════════════════════════════════════════════

def _encode_bits(bits):
    """Pack a list of {0, 1, None} into bytes, 2 bits each."""
    # Number of bytes needed: ceil(len(bits) * 2 / 8)
    n = len(bits)
    nbytes = math.ceil(n * 2 / 8)
    result = bytearray(nbytes)
    for i, b in enumerate(bits):
        if b is None:
            code = _ENC_UNK
        elif b == 1:
            code = _ENC_ONE
        else:
            code = _ENC_ZERO
        byte_idx = (i * 2) // 8
        bit_offset = (i * 2) % 8
        result[byte_idx] |= (code << bit_offset)
    return bytes(result)


def _decode_bits(data, count):
    """Unpack `count` tri-state bits from packed bytes."""
    bits = []
    for i in range(count):
        byte_idx = (i * 2) // 8
        bit_offset = (i * 2) % 8
        code = (data[byte_idx] >> bit_offset) & 0x03
        if code == _ENC_UNK:
            bits.append(None)
        elif code == _ENC_ONE:
            bits.append(1)
        else:
            bits.append(0)
    return bits


def _serialize_rayonint(obj):
    """Serialize a single RayonInt to bytes."""
    width = obj.width
    packed = _encode_bits(obj.bits[:width])
    # Tag(1) + Width(4) + packed bits
    return struct.pack('<BI', TAG_RAYON_INT, width) + packed


def _serialize_rayonarray(obj):
    """Serialize a RayonArray to bytes."""
    name_bytes = obj.name.encode('utf-8')
    name_len = len(name_bytes)
    n_elems = len(obj.elements)
    width = obj.width

    # Tag(1) + name_len(2) + name + width(4) + n_elems(4) + elements
    header = struct.pack('<BHI I', TAG_RAYON_ARRAY, name_len, width, n_elems)
    parts = [header, name_bytes]
    for elem in obj.elements:
        packed = _encode_bits(elem.bits[:elem.width])
        parts.append(packed)
    return b''.join(parts)


def serialize(obj):
    """Serialize a RayonInt, RayonArray, or other tension object to bytes."""
    if isinstance(obj, RayonInt):
        return _serialize_rayonint(obj)
    elif isinstance(obj, RayonArray):
        return _serialize_rayonarray(obj)
    else:
        raise TypeError(f"Cannot serialize {type(obj).__name__}")


def deserialize(data):
    """Deserialize bytes back to a tension object."""
    if not data or len(data) < 1:
        raise ValueError("Empty data")
    tag = data[0]

    if tag == TAG_RAYON_INT:
        return _deserialize_rayonint(data)
    elif tag == TAG_RAYON_ARRAY:
        return _deserialize_rayonarray(data)
    else:
        raise ValueError(f"Unknown type tag: 0x{tag:02x}")


def _deserialize_rayonint(data):
    """Deserialize a RayonInt from bytes."""
    tag, width = struct.unpack_from('<BI', data, 0)
    offset = 5  # 1 + 4
    nbytes = math.ceil(width * 2 / 8)
    packed = data[offset:offset + nbytes]
    bits = _decode_bits(packed, width)
    return RayonInt(bits=bits, width=width)


def _deserialize_rayonarray(data):
    """Deserialize a RayonArray from bytes."""
    # Tag(1) + name_len(2) + width(4) + n_elems(4) = 11 bytes header
    tag, name_len, width, n_elems = struct.unpack_from('<BHI I', data, 0)
    offset = 11
    name = data[offset:offset + name_len].decode('utf-8')
    offset += name_len

    nbytes_per_elem = math.ceil(width * 2 / 8)
    elements = []
    for _ in range(n_elems):
        packed = data[offset:offset + nbytes_per_elem]
        bits = _decode_bits(packed, width)
        elements.append(RayonInt(bits=bits, width=width))
        offset += nbytes_per_elem

    return RayonArray(name, elements, width=width)


# ════════════════════════════════════════════════════════════
# FILE I/O
# ════════════════════════════════════════════════════════════

def save_file(obj, path):
    """Serialize a tension object and write to a binary file."""
    data = serialize(obj)
    with open(path, 'wb') as f:
        f.write(data)


def load_file(path):
    """Read a binary file and deserialize to a tension object."""
    with open(path, 'rb') as f:
        data = f.read()
    return deserialize(data)


# ════════════════════════════════════════════════════════════
# JSON EXPORT / IMPORT
# ════════════════════════════════════════════════════════════

def _rayonint_to_dict(obj):
    """Convert RayonInt to a JSON-friendly dict. ? bits become null."""
    return {
        'type': 'RayonInt',
        'width': obj.width,
        'bits': [b if b is not None else None for b in obj.bits[:obj.width]],
        'tension': obj.tension,
    }


def _rayonarray_to_dict(obj):
    """Convert RayonArray to a JSON-friendly dict."""
    return {
        'type': 'RayonArray',
        'name': obj.name,
        'width': obj.width,
        'elements': [_rayonint_to_dict(e) for e in obj.elements],
        'tension': obj.tension,
    }


def to_json(obj, indent=2):
    """Convert a tension object to a JSON string. ? bits shown as null."""
    if isinstance(obj, RayonInt):
        d = _rayonint_to_dict(obj)
    elif isinstance(obj, RayonArray):
        d = _rayonarray_to_dict(obj)
    else:
        raise TypeError(f"Cannot convert {type(obj).__name__} to JSON")
    return json.dumps(d, indent=indent)


def from_json(data):
    """Parse a JSON string back to a tension object."""
    if isinstance(data, str):
        d = json.loads(data)
    else:
        d = data  # already a dict

    typ = d.get('type')
    if typ == 'RayonInt':
        return _dict_to_rayonint(d)
    elif typ == 'RayonArray':
        return _dict_to_rayonarray(d)
    else:
        raise ValueError(f"Unknown JSON type: {typ}")


def _dict_to_rayonint(d):
    width = d['width']
    bits = [b if b is not None else None for b in d['bits']]
    return RayonInt(bits=bits, width=width)


def _dict_to_rayonarray(d):
    name = d['name']
    width = d['width']
    elements = [_dict_to_rayonint(e) for e in d['elements']]
    return RayonArray(name, elements, width=width)


# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════

def _bits_equal(a, b):
    """Check two RayonInts have identical bit-for-bit state (including ? positions)."""
    if a.width != b.width:
        return False
    for i in range(a.width):
        ab = a.bits[i]
        bb = b.bits[i]
        if ab is None and bb is None:
            continue
        if ab != bb:
            return False
    return True


def _arrays_equal(a, b):
    """Check two RayonArrays have identical state."""
    if a.name != b.name or a.width != b.width or len(a) != len(b):
        return False
    return all(_bits_equal(ae, be) for ae, be in zip(a.elements, b.elements))


# ════════════════════════════════════════════════════════════
# TESTS
# ════════════════════════════════════════════════════════════

def _mark(ok):
    return '\u2713' if ok else '\u2717'


def test():
    import tempfile
    print("PERSISTENCE TESTS")
    print("=" * 55)
    W = 8  # 8-bit width for speed

    # ── Test 1: RayonInt fully known, binary round-trip ──
    a = RayonInt.known(42, W)
    data = serialize(a)
    a2 = deserialize(data)
    ok = _bits_equal(a, a2) and a2.value == 42
    print(f"  {_mark(ok)} RayonInt known(42) binary round-trip (value={a2.value})")

    # ── Test 2: RayonInt fully unknown ──
    b = RayonInt.unknown(W)
    data = serialize(b)
    b2 = deserialize(data)
    ok = _bits_equal(b, b2) and b2.tension == W
    print(f"  {_mark(ok)} RayonInt unknown binary round-trip (tension={b2.tension})")

    # ── Test 3: RayonInt partial ? bits ──
    c = RayonInt.partial(0b10100000, 0b00001111, W)  # top 4 known, bottom 4 = ?
    data = serialize(c)
    c2 = deserialize(data)
    ok = _bits_equal(c, c2) and c2.tension == 4
    # Verify exact ? positions
    for i in range(W):
        if c.bits[i] != c2.bits[i]:
            ok = False
            break
    print(f"  {_mark(ok)} RayonInt partial(4 known + 4 ?) binary round-trip (tension={c2.tension})")

    # ── Test 4: RayonInt partial, JSON round-trip ──
    js = to_json(c)
    c3 = from_json(js)
    ok = _bits_equal(c, c3)
    # Verify null in JSON for ? bits
    d = json.loads(js)
    nulls = sum(1 for x in d['bits'] if x is None)
    ok = ok and nulls == 4
    print(f"  {_mark(ok)} RayonInt partial JSON round-trip (nulls in JSON={nulls})")

    # ── Test 5: RayonArray known, binary round-trip ──
    arr = RayonArray.known('data', [10, 20, 30, 40], W)
    data = serialize(arr)
    arr2 = deserialize(data)
    ok = _arrays_equal(arr, arr2)
    vals = [e.value for e in arr2.elements]
    print(f"  {_mark(ok)} RayonArray known binary round-trip (vals={vals})")

    # ── Test 6: RayonArray partial, binary round-trip ──
    parr = RayonArray.partial('W', [0x41, 0x42, 0, 0],
                              [False, False, True, True], W)
    data = serialize(parr)
    parr2 = deserialize(data)
    ok = _arrays_equal(parr, parr2)
    ok = ok and parr2.elements[0].value == 0x41
    ok = ok and parr2.elements[2].tension == W
    print(f"  {_mark(ok)} RayonArray partial binary round-trip (known={parr2.known_count}, unknown={len(parr2)-parr2.known_count})")

    # ── Test 7: RayonArray JSON round-trip ──
    js = to_json(parr)
    parr3 = from_json(js)
    ok = _arrays_equal(parr, parr3)
    print(f"  {_mark(ok)} RayonArray partial JSON round-trip")

    # ── Test 8: File save/load RayonInt ──
    with tempfile.NamedTemporaryFile(suffix='.rayon', delete=False) as f:
        path = f.name
    try:
        save_file(c, path)
        c4 = load_file(path)
        ok = _bits_equal(c, c4)
        fsize = os.path.getsize(path)
        print(f"  {_mark(ok)} RayonInt save_file/load_file ({fsize} bytes on disk)")
    finally:
        os.unlink(path)

    # ── Test 9: File save/load RayonArray ──
    with tempfile.NamedTemporaryFile(suffix='.rayon', delete=False) as f:
        path = f.name
    try:
        save_file(parr, path)
        parr4 = load_file(path)
        ok = _arrays_equal(parr, parr4)
        fsize = os.path.getsize(path)
        print(f"  {_mark(ok)} RayonArray save_file/load_file ({fsize} bytes on disk)")
    finally:
        os.unlink(path)

    # ── Test 10: Verify ? positions survive exactly ──
    # Construct a tricky pattern: alternating known/unknown bits
    bits = [0, None, 1, None, 0, None, 1, None]  # 0?1?0?1?
    tricky = RayonInt(bits=bits, width=W)
    data = serialize(tricky)
    tricky2 = deserialize(data)
    ok = True
    for i in range(W):
        if tricky.bits[i] is None:
            if tricky2.bits[i] is not None:
                ok = False
        else:
            if tricky2.bits[i] != tricky.bits[i]:
                ok = False
    print(f"  {_mark(ok)} Alternating ?-pattern [0?1?0?1?] exact bit verification")

    # ── Test 11: Compact binary size check ──
    # 8-bit RayonInt should serialize to 5 (header) + 2 (packed bits) = 7 bytes
    data = serialize(RayonInt.known(0, W))
    ok = len(data) == 7
    print(f"  {_mark(ok)} Binary compactness: 8-bit RayonInt = {len(data)} bytes (expected 7)")

    # ── Test 12: Tension preserved after round-trip ──
    mixed = RayonInt.partial(0b11000000, 0b00111100, W)  # bits 2-5 unknown
    t_before = mixed.tension
    mixed2 = deserialize(serialize(mixed))
    t_after = mixed2.tension
    ok = t_before == t_after and t_before == 4
    print(f"  {_mark(ok)} Tension preserved: before={t_before}, after={t_after}")

    print()
    print("=" * 55)
    print("All persistence tests complete.")


if __name__ == '__main__':
    test()
