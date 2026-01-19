"""EMTP reference implementation (v1.0).

This is a reference implementation intended to be:
- Auditable
- Deterministic
- Easy to port to other languages

See spec.md for normative behavior.
"""

import base64
import hashlib
import hmac
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

# Domain separation prefix for EMTP v1
DOMAIN_PREFIX = "emtp|v1|"

# Maximum tuples per person (per spec section 5.4)
MAX_TUPLES = 256

# Honorifics to remove (lowercase)
HONORIFICS = {"mr", "mrs", "ms", "miss", "dr", "prof", "rev", "sir", "madam"}

# Suffixes to detect and normalize
SUFFIX_MAP = {
    "jr": "jr",
    "junior": "jr",
    "sr": "sr",
    "senior": "sr",
    "i": "i",
    "ii": "ii",
    "iii": "iii",
    "iv": "iv",
    "v": "v",
    "vi": "vi",
}


def normalize_string(s: str) -> str:
    """Apply general string normalization per spec section 4.1.

    1. Unicode normalize to NFKD
    2. Strip diacritics (remove combining characters)
    3. Lowercase all ASCII characters
    4. Replace all non-alphanumeric characters with a single space
    5. Collapse repeated whitespace to single space
    6. Trim leading and trailing whitespace
    """
    # NFKD normalization
    s = unicodedata.normalize("NFKD", s)

    # Strip diacritics (combining characters)
    s = "".join(c for c in s if not unicodedata.combining(c))

    # Lowercase
    s = s.lower()

    # Replace non-alphanumeric with space
    s = re.sub(r"[^a-z0-9]", " ", s)

    # Collapse whitespace and trim
    s = re.sub(r"\s+", " ", s).strip()

    return s


@dataclass
class ParsedName:
    """Parsed name components."""
    first: str
    middles: List[str]
    last: str
    suffix: str

    @property
    def full(self) -> str:
        """Full name without suffix."""
        parts = [self.first] + self.middles + [self.last]
        return " ".join(parts)

    @property
    def first_last(self) -> str:
        """First and last name only."""
        return f"{self.first} {self.last}"

    @property
    def first_last_suffix(self) -> str:
        """First, last, and suffix."""
        if self.suffix:
            return f"{self.first} {self.last} {self.suffix}"
        return self.first_last

    @property
    def first_initial_last(self) -> str:
        """First initial and last name."""
        if self.first:
            return f"{self.first[0]} {self.last}"
        return self.last


def normalize_name(name: str) -> ParsedName:
    """Normalize and parse a name per spec section 4.2.

    Returns a ParsedName with first, middles, last, and suffix.
    """
    # Apply general normalization
    name = normalize_string(name)

    tokens = name.split()
    if not tokens:
        return ParsedName(first="", middles=[], last="", suffix="")

    # Remove leading honorific (unless name would become just one token)
    if len(tokens) > 2 and tokens[0] in HONORIFICS:
        tokens = tokens[1:]

    # Detect and extract suffix from end
    suffix = ""
    if len(tokens) > 1 and tokens[-1] in SUFFIX_MAP:
        suffix = SUFFIX_MAP[tokens[-1]]
        tokens = tokens[:-1]

    # Parse into first/middles/last
    if len(tokens) == 0:
        return ParsedName(first="", middles=[], last="", suffix=suffix)
    elif len(tokens) == 1:
        return ParsedName(first=tokens[0], middles=[], last=tokens[0], suffix=suffix)
    else:
        return ParsedName(
            first=tokens[0],
            middles=tokens[1:-1],
            last=tokens[-1],
            suffix=suffix
        )


def normalize_dob(dob: str) -> str:
    """Normalize date of birth per spec section 4.3.

    Validates and returns YYYY-MM-DD format.
    """
    dob = dob.strip()

    # Basic validation
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", dob):
        raise ValueError(f"Invalid DOB format: {dob}. Expected YYYY-MM-DD")

    year, month, day = map(int, dob.split("-"))

    if not (1800 <= year <= 2100):
        raise ValueError(f"Invalid year: {year}")
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month: {month}")
    if not (1 <= day <= 31):
        raise ValueError(f"Invalid day: {day}")

    return dob


def normalize_phone(phone: str) -> str:
    """Normalize phone number per spec section 4.4.

    Returns digit-only string, stripping US country code if present.
    """
    # Extract digits only
    digits = re.sub(r"\D", "", phone)

    # Strip leading 1 for 11-digit US numbers
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    return digits


def phone_variants(phone: str) -> List[str]:
    """Generate phone variants per spec section 4.4."""
    normalized = normalize_phone(phone)
    variants = [normalized]

    # Last 10 digits
    if len(normalized) >= 10:
        last10 = normalized[-10:]
        if last10 != normalized:
            variants.append(last10)

    return list(set(variants))


def normalize_address(address: str) -> str:
    """Normalize address per spec section 4.5."""
    return normalize_string(address)


def address_variants(address: str) -> List[str]:
    """Generate address variants per spec section 4.5."""
    normalized = normalize_address(address)
    variants = [normalized]

    # Address without unit (split at apt/unit/#/ste)
    no_unit = re.split(r"\b(apt|unit|ste)\b", normalized)[0].strip()
    # Also handle # as unit designator
    no_unit = re.split(r"\s+\d+\s*$", no_unit)[0].strip()

    if no_unit and no_unit != normalized:
        variants.append(no_unit)

    return list(set(variants))


def normalize_idno(idno: str) -> List[str]:
    """Extract ID number variants per spec section 4.6.

    Extracts digit sequences >= 4 chars and generates last4/last5/last6.
    """
    # Find all digit sequences of length >= 4
    sequences = re.findall(r"\d{4,}", idno)

    variants = set()
    for seq in sequences:
        length = len(seq)
        if length >= 4:
            variants.add(seq[-4:])  # last4
        if length >= 5:
            variants.add(seq[-5:])  # last5
        if length >= 6:
            variants.add(seq[-6:])  # last6

    return sorted(variants)


def build_tuple(fields: Dict[str, str]) -> str:
    """Build a tuple string per spec section 5.1.

    Fields are joined in canonical order: name, dob, phone, address, id
    """
    order = ["name", "dob", "phone", "address", "id"]
    parts = []

    for field in order:
        if field in fields and fields[field]:
            parts.append(f"{field}={fields[field]}")

    return "|".join(parts)


def generate_tuples(
    name: ParsedName,
    dob: str,
    phones: Optional[List[str]] = None,
    addresses: Optional[List[str]] = None,
    idnos: Optional[List[str]] = None,
) -> List[str]:
    """Generate all tuple variants per spec section 5.2-5.4.

    Returns up to MAX_TUPLES unique tuples.
    """
    tuples: Set[str] = set()

    # Generate name variants
    name_variants = set()
    name_variants.add(name.full)
    name_variants.add(name.first_last)
    if name.suffix:
        name_variants.add(name.first_last_suffix)
    name_variants.add(name.first_initial_last)

    # Collapse initials variant (j r r -> jrr)
    if name.middles:
        initials = "".join([name.first[0]] + [m[0] for m in name.middles if m])
        collapsed_initials = f"{initials} {name.last}"
        name_variants.add(collapsed_initials)

    # Remove empty variants
    name_variants = {n for n in name_variants if n.strip()}

    # Generate phone variants
    phone_vars = []
    if phones:
        for p in phones:
            phone_vars.extend(phone_variants(p))
        phone_vars = list(set(phone_vars))

    # Generate address variants
    addr_vars = []
    if addresses:
        for a in addresses:
            addr_vars.extend(address_variants(a))
        addr_vars = list(set(addr_vars))

    # Generate ID variants
    id_vars = []
    if idnos:
        for i in idnos:
            id_vars.extend(normalize_idno(i))
        id_vars = list(set(id_vars))

    # Required tuple families (spec section 5.2)

    # Name + DOB
    for nv in name_variants:
        tuples.add(build_tuple({"name": nv, "dob": dob}))

    # Phone + DOB
    for pv in phone_vars:
        tuples.add(build_tuple({"dob": dob, "phone": pv}))

    # Address + DOB
    for av in addr_vars:
        tuples.add(build_tuple({"dob": dob, "address": av}))

    # Name + DOB + Phone
    for nv in name_variants:
        for pv in phone_vars:
            tuples.add(build_tuple({"name": nv, "dob": dob, "phone": pv}))

    # Name + DOB + Address
    for nv in name_variants:
        for av in addr_vars:
            tuples.add(build_tuple({"name": nv, "dob": dob, "address": av}))

    # Optional tuple families with ID (spec section 5.3)
    if id_vars:
        # Name + DOB + ID
        for nv in name_variants:
            for iv in id_vars:
                tuples.add(build_tuple({"name": nv, "dob": dob, "id": iv}))

        # DOB + ID
        for iv in id_vars:
            tuples.add(build_tuple({"dob": dob, "id": iv}))

        # Phone + DOB + ID
        for pv in phone_vars:
            for iv in id_vars:
                tuples.add(build_tuple({"dob": dob, "phone": pv, "id": iv}))

    # Cap at MAX_TUPLES
    result = sorted(tuples)[:MAX_TUPLES]
    return result


def compute_token(key: bytes, tuple_str: str) -> str:
    """Compute HMAC-SHA256 token with domain separation per spec section 6.

    Returns lowercase hex string (64 characters).
    """
    message = DOMAIN_PREFIX + tuple_str
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_tokens(
    keys: List[bytes],
    tuples: List[str],
) -> Set[str]:
    """Generate all tokens for given keys and tuples."""
    tokens: Set[str] = set()

    for key in keys:
        for t in tuples:
            tokens.add(compute_token(key, t))

    return tokens


def process_record(
    full_name: str,
    dob: str,
    phones: Optional[List[str]] = None,
    addresses: Optional[List[str]] = None,
    idnos: Optional[List[str]] = None,
    keys: Optional[List[bytes]] = None,
) -> Dict:
    """Process a full EMTP record.

    Returns a dict with normalized values, tuples, and optionally tokens.
    """
    # Normalize inputs
    parsed_name = normalize_name(full_name)
    normalized_dob = normalize_dob(dob)

    # Generate tuples
    tuples = generate_tuples(
        name=parsed_name,
        dob=normalized_dob,
        phones=phones,
        addresses=addresses,
        idnos=idnos,
    )

    result = {
        "normalized_name": {
            "first": parsed_name.first,
            "middles": parsed_name.middles,
            "last": parsed_name.last,
            "suffix": parsed_name.suffix,
            "full": parsed_name.full,
        },
        "normalized_dob": normalized_dob,
        "tuples": tuples,
        "tuple_count": len(tuples),
    }

    # Generate tokens if keys provided
    if keys:
        tokens = generate_tokens(keys, tuples)
        result["tokens"] = sorted(tokens)
        result["token_count"] = len(tokens)

    return result


def decode_key_hex(key_hex: str) -> bytes:
    """Decode hex-encoded key."""
    return bytes.fromhex(key_hex)


def decode_key_b64(key_b64: str) -> bytes:
    """Decode base64-encoded key."""
    return base64.b64decode(key_b64)


# Example usage and test
if __name__ == "__main__":
    # Test with Tolkien example from spec
    test_key = decode_key_hex(
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )

    result = process_record(
        full_name="MR. JRR Tolkien",
        dob="1892-01-03",
        phones=["(212) 555-0100"],
        addresses=["20 Northmoor Rd, Oxford"],
        keys=[test_key],
    )

    print("Normalized name:", result["normalized_name"])
    print("Tuple count:", result["tuple_count"])
    print("\nSample tuples:")
    for t in result["tuples"][:5]:
        print(f"  {t}")

    print("\nToken count:", result["token_count"])
    print("\nSample tokens:")
    for t in sorted(result["tokens"])[:3]:
        print(f"  {t}")

    # Verify test vector
    test_tuple = "name=jrr tolkien|dob=1892-01-03"
    test_token = compute_token(test_key, test_tuple)
    print(f"\nTest vector verification:")
    print(f"  Tuple: {test_tuple}")
    print(f"  Token: {test_token}")
    expected = "17d878e5adfb971b9aad5c15b0aa85fbdd74605a4809423bb3cc41399d2ac427"
    print(f"  Expected: {expected}")
    print(f"  Match: {test_token == expected}")
