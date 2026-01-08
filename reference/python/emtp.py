"""EMTP reference implementation (minimal, illustrative).

This is not production-hardening. It is intended to be:
- auditable
- deterministic
- easy to port to other languages

See docs/spec.md and schemas/emtp_v1.md for normative behavior.
"""

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple


def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def canonicalize_name(name: str) -> str:
    name = _norm_spaces(name.lower())
    name = re.sub(r"[\.,]", "", name)
    return name


def canonicalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return digits


def canonicalize_address(addr: str) -> str:
    addr = _norm_spaces(addr.lower())
    addr = re.sub(r"[\.,]", "", addr)
    return addr


def canonicalize_dob(dob: str) -> str:
    # assume already YYYY-MM-DD; real impl should validate
    return dob.strip()


def expand_variants(full_name: str, dob: str, phone: str, address: str) -> List[bytes]:
    """Return deterministic tuple variants as bytes."""
    name_c = canonicalize_name(full_name)
    dob_c = canonicalize_dob(dob)
    phone_c = canonicalize_phone(phone)
    addr_c = canonicalize_address(address)

    variants: Set[Tuple[str, str, str, str]] = set()
    variants.add((name_c, dob_c, phone_c, addr_c))

    # remove middle initial/name (very naive)
    name_parts = name_c.split()
    if len(name_parts) >= 3:
        variants.add((" ".join([name_parts[0], name_parts[-1]]), dob_c, phone_c, addr_c))

    # phone last-10
    if len(phone_c) > 10:
        variants.add((name_c, dob_c, phone_c[-10:], addr_c))

    # address without unit (naive: drop tokens after 'apt' or 'unit')
    addr_no_unit = re.split(r"\b(apt|unit|#)\b", addr_c)[0].strip()
    if addr_no_unit and addr_no_unit != addr_c:
        variants.add((name_c, dob_c, phone_c, addr_no_unit))

    # bytes encoding: pipe-joined
    out = []
    for t in sorted(variants):
        out.append(("|".join(t)).encode("utf-8"))
    return out


def hmac_tokens(variants: Iterable[bytes], keys: Iterable[bytes]) -> Set[str]:
    tokens: Set[str] = set()
    for k in keys:
        for t in variants:
            tokens.add(hmac.new(k, t, hashlib.sha256).hexdigest())
    return tokens


def decode_key_b64(key_b64: str) -> bytes:
    return base64.b64decode(key_b64)


