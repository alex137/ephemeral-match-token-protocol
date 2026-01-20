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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Union

# Domain separation prefix for EMTP v1
DOMAIN_PREFIX = "EMTP|v1|"

# Maximum tuples per person (per spec section 5.4)
MAX_TUPLES = 256

# Honorifics to remove (after uppercasing)
HONORIFICS = {"MR", "MRS", "MS", "MISS", "DR", "PROF", "REV", "SIR", "MADAM"}

# Suffixes to detect and normalize
SUFFIX_MAP = {
    "JR": "JR",
    "JUNIOR": "JR",
    "SR": "SR",
    "SENIOR": "SR",
    "I": "I",
    "II": "II",
    "III": "III",
    "IV": "IV",
    "V": "V",
    "VI": "VI",
}

# Address abbreviations (bidirectional normalization)
ADDR_ABBREVS = {
    "STREET": "ST",
    "AVENUE": "AVE",
    "ROAD": "RD",
    "BOULEVARD": "BLVD",
    "DRIVE": "DR",
    "LANE": "LN",
    "COURT": "CT",
    "PLACE": "PL",
    "APARTMENT": "APT",
    "SUITE": "STE",
}


def normalize_string(s: str) -> str:
    """Apply general string normalization per spec section 4.1.

    1. Unicode normalize to NFKD
    2. Strip diacritics (remove combining characters)
    3. Uppercase all ASCII characters
    4. Replace all non-alphanumeric characters with a single space
    5. Collapse repeated whitespace to single space
    6. Trim leading and trailing whitespace
    """
    # NFKD normalization
    s = unicodedata.normalize("NFKD", s)

    # Strip diacritics (combining characters)
    s = "".join(c for c in s if not unicodedata.combining(c))

    # Uppercase
    s = s.upper()

    # Replace non-alphanumeric with space
    s = re.sub(r"[^A-Z0-9]", " ", s)

    # Collapse whitespace and trim
    s = re.sub(r"\s+", " ", s).strip()

    return s


@dataclass
class ParsedName:
    """Parsed name components."""
    given: str
    middles: List[str]
    family: str
    suffix: str

    @property
    def full(self) -> str:
        """Full name without suffix."""
        parts = [self.given] + self.middles + [self.family]
        return " ".join(p for p in parts if p)

    @property
    def given_family(self) -> str:
        """Given and family name only."""
        return f"{self.given} {self.family}".strip()

    @property
    def given_family_suffix(self) -> str:
        """Given, family, and suffix."""
        if self.suffix:
            return f"{self.given} {self.family} {self.suffix}".strip()
        return self.given_family

    @property
    def initials_family(self) -> str:
        """All initials + family name."""
        initials = [self.given[0]] if self.given else []
        initials.extend(m[0] for m in self.middles if m)
        return " ".join(initials + [self.family]).strip()

    @property
    def given_initial_family(self) -> str:
        """Given + middle initials + family."""
        parts = [self.given] if self.given else []
        parts.extend(m[0] for m in self.middles if m)
        parts.append(self.family)
        return " ".join(p for p in parts if p)


def normalize_name(name: str) -> ParsedName:
    """Normalize and parse a name per spec section 4.2.

    Returns a ParsedName with given, middles, family, and suffix.
    """
    # Apply general normalization
    name = normalize_string(name)

    tokens = name.split()
    if not tokens:
        return ParsedName(given="", middles=[], family="", suffix="")

    # Remove leading honorific (unless name would become just one token)
    if len(tokens) > 2 and tokens[0] in HONORIFICS:
        tokens = tokens[1:]

    # Detect and extract suffix from end
    suffix = ""
    if len(tokens) > 1 and tokens[-1] in SUFFIX_MAP:
        suffix = SUFFIX_MAP[tokens[-1]]
        tokens = tokens[:-1]

    # Parse into given/middles/family
    if len(tokens) == 0:
        return ParsedName(given="", middles=[], family="", suffix=suffix)
    elif len(tokens) == 1:
        return ParsedName(given=tokens[0], middles=[], family=tokens[0], suffix=suffix)
    else:
        return ParsedName(
            given=tokens[0],
            middles=tokens[1:-1],
            family=tokens[-1],
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


def normalize_phone(phone: str, default_country: str = "US") -> str:
    """Normalize phone number to E.164 format per spec section 4.4.

    Returns E.164 format with + prefix.
    """
    # Extract digits only
    digits = re.sub(r"\D", "", phone)

    if not digits:
        return ""

    # Handle US numbers
    if default_country == "US":
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        elif len(digits) == 10:
            return f"+1{digits}"

    # If already has country code (starts with non-0, non-1 for international)
    if len(digits) >= 10:
        # Assume it might be international
        return f"+{digits}"

    return digits


def phone_variants(phone: str, default_country: str = "US") -> Dict[str, str]:
    """Generate phone variants per spec section 4.4."""
    e164 = normalize_phone(phone, default_country)
    digits = re.sub(r"\D", "", phone)

    variants = {}

    if e164:
        variants["PHONE_E164"] = e164

    # National (without +country code)
    if e164.startswith("+1") and len(e164) == 12:
        variants["PHONE_NATIONAL"] = e164[2:]  # Remove +1
    elif digits:
        variants["PHONE_NATIONAL"] = digits

    # Last 10 digits
    if len(digits) >= 10:
        variants["PHONE_LAST10"] = digits[-10:]

    return variants


@dataclass
class StructuredAddress:
    """Structured address per spec section 3.3."""
    line1: str
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


def parse_address(address: Union[str, dict]) -> StructuredAddress:
    """Parse address from string or dict."""
    if isinstance(address, dict):
        return StructuredAddress(
            line1=address.get("line1", ""),
            line2=address.get("line2", ""),
            city=address.get("city", ""),
            state=address.get("state", ""),
            postal_code=address.get("postal_code", ""),
            country=address.get("country", "US"),
        )

    # Simple heuristic parsing for free-form addresses
    normalized = normalize_string(address)
    parts = [p.strip() for p in normalized.split(",") if p.strip()]

    if len(parts) >= 3:
        # Assume: line1, city, state/postal
        line1 = parts[0]
        city = parts[1] if len(parts) > 1 else ""
        state_postal = parts[2] if len(parts) > 2 else ""
        # Try to extract postal code (digits at end)
        postal_match = re.search(r"([A-Z0-9]{2,})\s*$", state_postal)
        postal_code = postal_match.group(1) if postal_match else ""
        state = state_postal.replace(postal_code, "").strip() if postal_code else state_postal
        return StructuredAddress(line1=line1, city=city, state=state, postal_code=postal_code)
    elif len(parts) == 2:
        return StructuredAddress(line1=parts[0], city=parts[1])
    elif len(parts) == 1:
        return StructuredAddress(line1=parts[0])

    return StructuredAddress(line1=normalized)


def normalize_address_component(s: str) -> str:
    """Normalize address component with abbreviation handling."""
    normalized = normalize_string(s)

    # Apply abbreviations (expand to canonical short form)
    for long_form, short_form in ADDR_ABBREVS.items():
        normalized = re.sub(rf"\b{long_form}\b", short_form, normalized)

    return normalized


def address_variants(address: Union[str, dict]) -> Dict[str, str]:
    """Generate address variants per spec section 4.5."""
    parsed = parse_address(address)

    line1 = normalize_address_component(parsed.line1)
    city = normalize_string(parsed.city)
    state = normalize_string(parsed.state)
    postal = normalize_string(parsed.postal_code)

    variants = {}

    if line1 and postal:
        variants["ADDR_LINE1_POSTAL"] = f"{line1}|{postal}"

    if line1 and city and state:
        variants["ADDR_LINE1_CITY_STATE"] = f"{line1}|{city}|{state}"

    if line1 and city and state and postal:
        variants["ADDR_LINE1_CITY_STATE_POSTAL"] = f"{line1}|{city}|{state}|{postal}"

    # Address without unit
    no_unit = re.split(r"\b(APT|UNIT|STE)\b", line1)[0].strip()
    if no_unit and no_unit != line1:
        variants["ADDR_NO_UNIT"] = no_unit

    return variants


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

    Fields are joined in canonical order: NAME, DOB, PHONE, ADDR, ID
    """
    order = ["NAME", "DOB", "PHONE", "ADDR", "ID"]
    parts = []

    for field_name in order:
        if field_name in fields and fields[field_name]:
            parts.append(f"{field_name}={fields[field_name]}")

    return "|".join(parts)


def generate_tuples(
    name: ParsedName,
    dob: str,
    phones: Optional[List[str]] = None,
    addresses: Optional[List[Union[str, dict]]] = None,
    idnos: Optional[List[str]] = None,
) -> List[str]:
    """Generate all tuple variants per spec section 5.2-5.4.

    Returns up to MAX_TUPLES unique tuples.
    """
    tuples: Set[str] = set()

    # Generate name variants
    name_variants = {
        "full": name.full,
        "given_family": name.given_family,
        "initials_family": name.initials_family,
    }
    if name.suffix:
        name_variants["given_family_suffix"] = name.given_family_suffix

    # Add collapsed initials variant if there are middles
    if name.middles and name.given:
        collapsed = "".join([name.given[0]] + [m[0] for m in name.middles if m])
        name_variants["collapsed_initials"] = f"{collapsed} {name.family}"

    # Remove empty variants
    name_variants = {k: v for k, v in name_variants.items() if v.strip()}

    # Generate phone variants
    phone_vars_list = []
    if phones:
        for p in phones:
            pvars = phone_variants(p)
            phone_vars_list.append(pvars)

    # Generate address variants
    addr_vars_list = []
    if addresses:
        for a in addresses:
            avars = address_variants(a)
            addr_vars_list.append(avars)

    # Generate ID variants
    id_vars = []
    if idnos:
        for i in idnos:
            id_vars.extend(normalize_idno(i))
        id_vars = list(set(id_vars))

    # Required tuple families (spec section 5.2)

    # Name + DOB tuples
    for nv in name_variants.values():
        tuples.add(build_tuple({"NAME": nv, "DOB": dob}))

    # Phone + DOB tuples
    for pvars in phone_vars_list:
        for phone_type in ["PHONE_E164", "PHONE_LAST10"]:
            if phone_type in pvars:
                tuples.add(build_tuple({"DOB": dob, "PHONE": pvars[phone_type]}))

    # Address + DOB tuples
    for avars in addr_vars_list:
        for addr_type in ["ADDR_LINE1_POSTAL", "ADDR_LINE1_CITY_STATE"]:
            if addr_type in avars:
                tuples.add(build_tuple({"DOB": dob, "ADDR": avars[addr_type]}))

    # Combined: Name + DOB + Phone
    for nv in name_variants.values():
        for pvars in phone_vars_list:
            for phone_type in ["PHONE_E164", "PHONE_NATIONAL"]:
                if phone_type in pvars:
                    tuples.add(build_tuple({
                        "NAME": nv,
                        "DOB": dob,
                        "PHONE": pvars[phone_type]
                    }))

    # Combined: Name + DOB + Address
    for nv in name_variants.values():
        for avars in addr_vars_list:
            for addr_type in ["ADDR_LINE1_POSTAL", "ADDR_LINE1_CITY_STATE"]:
                if addr_type in avars:
                    tuples.add(build_tuple({
                        "NAME": nv,
                        "DOB": dob,
                        "ADDR": avars[addr_type]
                    }))

    # Optional tuple families with ID (spec section 5.3)
    if id_vars:
        # Name + DOB + ID
        for nv in [name_variants.get("given_family", name.given_family)]:
            if nv:
                for iv in id_vars:
                    tuples.add(build_tuple({"NAME": nv, "DOB": dob, "ID": iv}))

        # DOB + ID
        for iv in id_vars:
            tuples.add(build_tuple({"DOB": dob, "ID": iv}))

        # Phone + DOB + ID
        for pvars in phone_vars_list:
            if "PHONE_LAST10" in pvars:
                for iv in id_vars:
                    tuples.add(build_tuple({
                        "DOB": dob,
                        "PHONE": pvars["PHONE_LAST10"],
                        "ID": iv
                    }))

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
    addresses: Optional[List[Union[str, dict]]] = None,
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
            "given": parsed_name.given,
            "middles": parsed_name.middles,
            "family": parsed_name.family,
            "suffix": parsed_name.suffix,
            "full": parsed_name.full,
            "given_family": parsed_name.given_family,
            "initials_family": parsed_name.initials_family,
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
        addresses=[{
            "line1": "20 Northmoor Rd",
            "city": "Oxford",
            "state": "OX",
            "postal_code": "OX2 6"
        }],
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
    test_tuple = "NAME=JRR TOLKIEN|DOB=1892-01-03"
    test_token = compute_token(test_key, test_tuple)
    print(f"\nTest vector verification:")
    print(f"  Tuple: {test_tuple}")
    print(f"  Message: {DOMAIN_PREFIX}{test_tuple}")
    print(f"  Token: {test_token}")
