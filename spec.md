# Ephemeral Match Token Protocol (EMTP) Specification

**Version:** 1.0
**Status:** Draft
**Last updated:** 2026-01-20

---

## Abstract

EMTP (Ephemeral Match Token Protocol) enables privacy-preserving person matching: two parties can determine whether they refer to the same individual **without exchanging raw identifiers**. The protocol uses rotating shared HMAC keys and deterministic normalization to produce short-lived match tokens.

This specification defines:
1. The **input model** (identifier fields)
2. **Normalization** rules
3. **Tuple construction** and expansion
4. **Token generation** (HMAC construction with domain separation)
5. **Key distribution** and rotation
6. Security, privacy, and interoperability requirements

---

## 1. Goals and Non-Goals

### 1.1 Goals

- **Match without sharing identifiers:** Parties compute matchable tokens locally without revealing raw demographics to a central registry.
- **Ephemeral identifiers:** Tokens MUST change over time (via key rotation) to prevent creation of persistent identifiers or cross-period correlation.
- **Robust to messy data:** Tolerate capitalization, punctuation, honorifics, missing middle names, suffixes, nickname-like variants, and formatting differences in phones/addresses.
- **Deterministic and auditable:** Token generation MUST be deterministic given the same inputs and keys. Implementations can be verified against test vectors.
- **Composable transport:** Token sets can be exchanged over any transport (STP, HTTPS APIs, files, etc.).

### 1.2 Non-Goals

- EMTP is **not** an identity-proofing or KYC protocol.
- EMTP does not define authorization, consent, access control, or PHI exchange.
- EMTP does not guarantee uniqueness; collisions are possible and must be managed by downstream workflows.

---

## 2. Terminology

| Term | Definition |
|------|------------|
| **Participant** | An entity computing EMTP tokens (payer, provider, hub, fintech, etc.). |
| **Key Server** | A service distributing time-scoped HMAC keys to authorized Participants. |
| **Credentialed Participant** | A Participant authorized to retrieve EMTP keys. |
| **Token** | An HMAC of a normalized tuple under a specific time-scoped key. |
| **Tuple** | A canonical string representing a combination of normalized identifier fields. |
| **Tuple expansion** | Generating multiple tuples per individual to improve match recall. |
| **Key epoch** | The time window for which a given key is valid (e.g., one month). |
| **Overlap window** | A period where both current and prior epoch keys are valid. |
| **Weak token** | A token generated without DOB; has higher false-positive risk. |

---

## 3. Inputs (Identifier Fields)

An EMTP input record contains the following fields:

### 3.1 Required Fields

| Field | Format | Description |
|-------|--------|-------------|
| `dob` | `YYYY-MM-DD` | Date of birth (Gregorian calendar). Required for standard tokens. |
| `full_name` | string | Full name, may include honorifics, initials, middle names, suffixes. |

> **Rationale:** Without DOB, false-positive rates rise dramatically. Implementations MAY support token generation without DOB but MUST label resulting tokens as **weak tokens**.

### 3.2 Optional Fields

| Field | Format | Description |
|-------|--------|-------------|
| `phones` | array of strings | Phone numbers in any format (will be normalized to E.164). |
| `addresses` | array of objects or strings | Postal addresses (structured or free-form). |
| `idnos` | array of strings | Identifier fragments (SSN, DL, member IDs, etc.) containing digits. |

### 3.3 Structured Address Format

When addresses are provided as objects, implementations MUST support:

| Field | Required | Description |
|-------|----------|-------------|
| `line1` | Yes | Street address |
| `line2` | No | Additional address line (apt, suite, etc.) |
| `city` | Yes | City name |
| `state` | Yes | State/province/region code |
| `postal_code` | Yes | Postal/ZIP code |
| `country` | No | ISO 3166-1 alpha-2 country code (default: `US`) |

Implementations MUST also accept a single free-form address string and parse it.

---

## 4. Normalization

All normalization MUST be deterministic. Two implementations given the same input MUST produce identical normalized output.

### 4.1 General String Normalization

For all string fields, apply these steps **in order**:

1. **Unicode normalize** to NFKD
2. **Strip diacritics** (remove combining characters)
3. **Uppercase** all ASCII characters
4. **Replace** all non-alphanumeric characters with a single space
5. **Collapse** repeated whitespace to single space
6. **Trim** leading and trailing whitespace

**Example:**
```
Input:  "Mr. José García-López"
Output: "MR JOSE GARCIA LOPEZ"
```

### 4.2 Name Normalization

After general string normalization:

#### 4.2.1 Honorific Removal

Remove leading honorific tokens (case-insensitive):
`MR`, `MRS`, `MS`, `MISS`, `DR`, `PROF`, `REV`, `SIR`, `MADAM`

If a name consists solely of an honorific plus one token, do NOT remove the honorific.

#### 4.2.2 Suffix Parsing

Detect and separate suffixes at end of name:
- `JR`, `SR`, `JUNIOR`, `SENIOR` → normalize to `JR` or `SR`
- `I`, `II`, `III`, `IV`, `V`, `VI`

Suffix detection MUST tolerate punctuation and commas (e.g., `SR.`, `TOLKIEN, JR.`).

#### 4.2.3 Name Tokenization

Split the remaining name into tokens:
- **given**: first token (first name)
- **middles**: zero or more middle tokens
- **family**: final token(s) before suffix (last name)
- **suffix**: normalized suffix or empty

Handle initials:
- Tokens like `J.R.R.` become separate initials: `J`, `R`, `R`
- Single-letter tokens are treated as initials

#### 4.2.4 Canonical Name Forms

Generate these canonical name strings:

| Form | Construction | Example |
|------|--------------|---------|
| `NAME_FULL` | all tokens joined with space | `JOHN RONALD REUEL TOLKIEN` |
| `NAME_GIVEN_FAMILY` | given + family only | `JOHN TOLKIEN` |
| `NAME_GIVEN_FAMILY_SUFFIX` | given + family + suffix | `JOHN TOLKIEN SR` |
| `NAME_INITIALS_FAMILY` | all initials + family | `J R R TOLKIEN` |
| `NAME_GIVEN_INITIAL_FAMILY` | given + middle initials + family | `JOHN R R TOLKIEN` |

### 4.3 DOB Normalization

- MUST output strict `YYYY-MM-DD` format
- MUST validate: year 1800-2100, month 01-12, day 01-31 (with month-appropriate day validation)
- Invalid DOB MUST cause the record to be rejected or flagged
- If only year/month known, implementations MAY generate weak tokens but MUST label them

### 4.4 Phone Normalization

1. Strip all non-digit characters
2. Normalize to **E.164 format** where possible:
   - If number starts with country code, format as `+<countrycode><number>`
   - If 11 digits starting with `1`, treat as US: `+1<10digits>`
   - If 10 digits and default country is US, format as `+1<10digits>`
3. Store both E.164 and national formats

Generate variants:
- `PHONE_E164`: full E.164 format (e.g., `+12125550100`)
- `PHONE_NATIONAL`: national number without country code (e.g., `2125550100`)
- `PHONE_LAST10`: last 10 digits (when length ≥ 10)
- `PHONE_LAST7`: last 7 digits (optional; high collision risk, discouraged)

### 4.5 Address Normalization

#### 4.5.1 Structured Address Normalization

After general string normalization, apply:

1. **Abbreviation expansion/normalization** (bidirectional):
   - `STREET` ↔ `ST`
   - `AVENUE` ↔ `AVE`
   - `ROAD` ↔ `RD`
   - `BOULEVARD` ↔ `BLVD`
   - `DRIVE` ↔ `DR`
   - `LANE` ↔ `LN`
   - `APARTMENT` ↔ `APT`
   - `SUITE` ↔ `STE`
   - `UNIT` ↔ `UNIT`

2. **Postal code normalization**:
   - US: Keep 5-digit base; optionally include ZIP+4 variant
   - Other countries: Normalize per country rules

#### 4.5.2 Address Variants

Generate these address tuple components:

| Variant | Construction |
|---------|--------------|
| `ADDR_LINE1_POSTAL` | `line1 \| postal_code` |
| `ADDR_LINE1_CITY_STATE` | `line1 \| city \| state` |
| `ADDR_LINE1_CITY_STATE_POSTAL` | `line1 \| city \| state \| postal_code` |
| `ADDR_NO_UNIT` | `line1` with unit info removed |

### 4.6 ID Number Normalization

For each `idno` string:

1. Extract all contiguous digit sequences of length ≥ 4
2. For each extracted sequence of length L, generate:
   - `ID_LAST4`: last 4 digits (if L ≥ 4)
   - `ID_LAST5`: last 5 digits (if L ≥ 5)
   - `ID_LAST6`: last 6 digits (if L ≥ 6)
3. Optionally include full sequence if L ≤ 12

> **Rationale:** ID fragments enable disambiguation without revealing full identifiers or ID types.

---

## 5. Tuple Construction

### 5.1 Tuple Format

A tuple is a string of labeled, pipe-delimited fields:

```
field=value|field=value|field=value
```

**Requirements:**
- Field names MUST be UPPERCASE ASCII
- Field names MUST be one of: `NAME`, `DOB`, `PHONE`, `ADDR`, `ID`
- Values MUST be normalized per Section 4
- Fields MUST appear in this canonical order: `NAME`, `DOB`, `PHONE`, `ADDR`, `ID`
- Empty/missing fields MUST be omitted (not included as empty)

**Example:**
```
NAME=JOHN TOLKIEN|DOB=1892-01-03|PHONE=+12125550100
```

### 5.2 Required Tuple Families

Implementations MUST generate these tuple families when the required inputs are available:

#### Name + DOB Tuples

| Tuple ID | Fields | Purpose |
|----------|--------|---------|
| `NAME_FULL_DOB` | `NAME` (full), `DOB` | Primary match |
| `NAME_GIVEN_FAMILY_DOB` | `NAME` (given+family), `DOB` | Handles middle name variations |
| `NAME_INITIALS_FAMILY_DOB` | `NAME` (initials+family), `DOB` | Handles initial variations |

#### Phone + DOB Tuples

| Tuple ID | Fields | Purpose |
|----------|--------|---------|
| `PHONE_E164_DOB` | `PHONE` (E.164), `DOB` | International phone match |
| `PHONE_LAST10_DOB` | `PHONE` (last10), `DOB` | National phone match |

#### Address + DOB Tuples

| Tuple ID | Fields | Purpose |
|----------|--------|---------|
| `ADDR_LINE1_POSTAL_DOB` | `ADDR` (line1+postal), `DOB` | Address match |
| `ADDR_LINE1_CITY_STATE_DOB` | `ADDR` (line1+city+state), `DOB` | Address match without postal |

#### Combined Tuples

| Tuple ID | Fields | Purpose |
|----------|--------|---------|
| `NAME_DOB_PHONE` | `NAME`, `DOB`, `PHONE` | Higher precision |
| `NAME_DOB_ADDR` | `NAME`, `DOB`, `ADDR` | Higher precision |

### 5.3 Optional Tuple Families (with ID fragments)

If `idnos` are provided, generate high-precision disambiguation tuples:

| Tuple ID | Fields | Purpose |
|----------|--------|---------|
| `NAME_DOB_ID` | `NAME` (given+family), `DOB`, `ID` (last4) | Disambiguation |
| `DOB_ID` | `DOB`, `ID` (last4) | High-precision disambiguation |
| `PHONE_DOB_ID` | `PHONE` (last10), `DOB`, `ID` (last4) | High-precision disambiguation |

> Implementations SHOULD treat ID fragment tuples as **high precision** and prioritize them when resolving collisions.

### 5.4 Variant Expansion

For each tuple family, generate variants by combining:
- Different name forms (full, given+family, initials+family, with/without suffix)
- Different phone forms (E.164, national, last10)
- Different address forms (with/without unit, different components)
- Different ID forms (last4, last5, last6)

**Expansion cap:** Implementations MUST limit expansion to at most **256 tuples per person** to prevent combinatorial explosion.

### 5.5 Weak Tuples

Tuples generated without DOB are **weak tuples**. Implementations:
- MAY generate weak tuples when DOB is unavailable
- MUST label weak tuples/tokens distinctly
- SHOULD warn users about higher false-positive rates

---

## 6. Token Generation

### 6.1 Algorithm

EMTP uses **HMAC-SHA256** for token generation.

### 6.2 Domain Separation

All HMAC inputs MUST include a domain separation prefix:

```
message = "EMTP|" + schema_id + "|" + tuple
```

Where:
- `schema_id` is `v1` for this specification version
- `tuple` is the constructed tuple string from Section 5

**Example message:**
```
EMTP|v1|NAME=JOHN TOLKIEN|DOB=1892-01-03|PHONE=+12125550100
```

### 6.3 Token Computation

```
token = hex(HMAC-SHA256(key, message))
```

Where:
- `key` is the raw key bytes (32 bytes / 256 bits)
- `message` is the UTF-8 encoded domain-separated string
- `hex()` outputs lowercase hexadecimal (64 characters)

### 6.4 Output Token Set

For a given input record and set of active keys, the output is:

```
tokens = { (epoch_id, HMAC(k, msg(t))) for each key k, for each tuple t }
```

Implementations SHOULD include key epoch identifiers with tokens to aid debugging and overlap handling.

---

## 7. Key Distribution and Rotation

### 7.1 Key Server Requirements

The Key Server MUST:
- Authenticate Participants (mTLS, OIDC, API keys, or equivalent)
- Serve current and prior epoch keys (minimum 2 epochs) for continuity
- Support revocation: deny key access to misbehaving Participants
- Publish key metadata alongside keys

### 7.2 Key Manifest

Each key MUST be described by a manifest containing:

| Field | Type | Description |
|-------|------|-------------|
| `kid` | string | Unique key identifier (e.g., `2026-01`) |
| `key` | bytes | 256-bit key material (base64 encoded for transport) |
| `algorithm` | string | `hmac-sha256` |
| `not_before` | RFC3339 | Start of validity window |
| `not_after` | RFC3339 | End of validity window |

### 7.3 Rotation Cadence

- **Recommended epoch duration:** 1 month
- **Overlap requirement:** Key Server MUST distribute at least current + previous epoch keys
- Shorter cadences (weekly/daily) MAY be used for higher privacy at cost of more frequent recomputation

### 7.4 Key Security Requirements

- Keys MUST be generated using cryptographically secure RNG
- Keys MUST have at least 256 bits of entropy
- Keys MUST be distributed only over TLS
- Keys MUST NOT be embedded in client code or published
- Key material MUST be treated as sensitive and access-controlled

### 7.5 STP-Based Distribution (Informative)

Keys MAY be distributed via STP (State Transfer Protocol) streams:

**Code Distribution Stream:** Maps languages to code manifests
- Primary key: `language` (e.g., `python`, `go`, `js`)
- Record: `code_manifest_surl` pointing to versioned implementation

**Key Distribution Stream:** Lists active key manifests
- Primary key: `key_manifest_surl`
- Record: `expires_at` (RFC3339)
- Revocation: Delete row (action `-`) for immediate revocation

---

## 8. Interoperability Requirements

For two implementations to produce matching tokens, they MUST:

1. Implement normalization exactly as specified in Section 4
2. Use the same tuple format (Section 5.1)
3. Generate at minimum the required tuple families (Section 5.2)
4. Use domain separation with `schema_id=v1` (Section 6.2)
5. Use HMAC-SHA256 with lowercase hex output
6. Support at least two-epoch key overlap

Implementations SHOULD provide a **compliance mode** that outputs intermediate values (normalized fields, tuples) for debugging interoperability issues.

---

## 9. Security and Privacy Properties

### 9.1 Privacy Properties

- **No raw demographics to central service:** Only tokens are exchanged for matching
- **Ephemeral tokens:** Key rotation prevents tokens from becoming persistent identifiers
- **Local computation:** Normalization and tuple expansion happen locally; inputs never leave the Participant

### 9.2 Threat Model

**Assumptions:**
- Participants are credentialed and trusted not to misuse keys
- Key Server access is controlled and audited
- Transport is encrypted (TLS)

**Mitigations:**
- If keys are compromised, attacker can mount dictionary attacks on tokens. Mitigate via:
  - Restricting key distribution to credentialed Participants
  - Supporting rapid revocation
  - Rotating keys frequently
- EMTP does not prevent collusion between Participants who share raw identifiers outside the protocol

### 9.3 Collision Handling

Collisions are expected, especially for:
- Common names with same DOB
- Family members with same DOB/address (e.g., twins)
- Sr/Jr with overlapping identifiers

Downstream systems SHOULD:
- Treat matches as **candidates**, not certainty
- Use secondary confirmation (ID fragments, manual review, user approval)
- Support requesting additional identifiers for disambiguation

---

## 10. Versioning

This document defines EMTP version 1.0 with `schema_id=v1`.

Implementations MUST:
- Expose library version
- Expose supported `schema_id` values
- Include `schema_id` in any published artifacts or test vectors

Future versions:
- New `schema_id` values may be introduced for tuple schema changes
- Key manifests may specify multiple supported schema IDs
- Implementations SHOULD support multiple schema versions for backward compatibility

---

## 11. Conformance and Test Vectors

A conforming EMTP implementation MUST:

1. Pass all normalization test vectors
2. Pass all tuple construction test vectors
3. Pass all token generation test vectors (given fixed keys)
4. Limit tuple expansion to 256 per person
5. Support at least two concurrent key epochs

Test vectors are provided in `/test_vectors/emtp_v1_vectors.json`.

---

## Appendix A: Complete Example

### Input A
```json
{
  "full_name": "MR. JRR Tolkien",
  "dob": "1892-01-03",
  "phones": ["(212) 555-0100"],
  "addresses": [{
    "line1": "20 Northmoor Rd",
    "city": "Oxford",
    "state": "OX",
    "postal_code": "OX2 6"
  }]
}
```

### Input B
```json
{
  "full_name": "J. R. R. Tolkien",
  "dob": "1892-01-03",
  "phones": ["+1-212-555-0100"],
  "addresses": ["20 NORTHMOOR ROAD, Oxford, OX2 6"]
}
```

### Normalization Results

| Field | Input A | Input B |
|-------|---------|---------|
| NAME_FULL | `JRR TOLKIEN` | `J R R TOLKIEN` |
| NAME_GIVEN_FAMILY | `JRR TOLKIEN` | `J TOLKIEN` |
| NAME_INITIALS_FAMILY | `J R R TOLKIEN` | `J R R TOLKIEN` |
| DOB | `1892-01-03` | `1892-01-03` |
| PHONE_E164 | `+12125550100` | `+12125550100` |
| PHONE_NATIONAL | `2125550100` | `2125550100` |
| ADDR_LINE1_POSTAL | `20 NORTHMOOR RD\|OX2 6` | `20 NORTHMOOR RD\|OX2 6` |

### Shared Tuples

Both inputs produce these tuples (among others):
```
NAME=J R R TOLKIEN|DOB=1892-01-03
NAME=J R R TOLKIEN|DOB=1892-01-03|PHONE=+12125550100
NAME=JRR TOLKIEN|DOB=1892-01-03|ADDR=20 NORTHMOOR RD|OX2 6
```

### Token Generation

With domain separation and key `k`:
```
message = "EMTP|v1|NAME=J R R TOLKIEN|DOB=1892-01-03"
token = HMAC-SHA256(k, message)  // lowercase hex output
```

Both inputs produce this shared token, enabling the match.

---

## Appendix B: Reference Implementation Notes

The reference implementation in `/reference/python/emtp.py`:
- Demonstrates all normalization rules
- Generates required tuple families
- Applies domain separation
- Is intentionally minimal for portability

Production implementations should additionally:
- Handle edge cases (empty inputs, malformed data)
- Implement full address parsing and abbreviation normalization
- Support structured address input
- Provide detailed error reporting
- Optimize for performance at scale

---

## Appendix C: Changelog

### v1.0 (2026-01-20)
- Consolidated from draft v0.3 and alternative drafts
- Standardized on UPPERCASE normalization
- Added structured address support with variants
- Added E.164 phone format support
- Added "weak token" concept for missing DOB
- Specified labeled tuple format with canonical field order
- Added domain separation prefix requirement
- Defined key manifest format
- Added conformance requirements
- Provided complete worked example with structured addresses
