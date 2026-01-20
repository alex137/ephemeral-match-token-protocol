# Ephemeral Match Token Protocol (EMTP) — Specification (Draft v0.3)

**Status:** Draft  
**Last updated:** 2026-01-08  
**Authors:** community

> EMTP is a privacy-preserving matching primitive: two parties can determine whether they are referring to the same individual **without exchanging raw identifiers**, using rotating shared HMAC keys and deterministic normalization + tuple expansion.

This document defines:
1) the **input model** (identifier fields),  
2) **normalization** rules,  
3) **tuple expansion**,  
4) **token generation** (HMAC construction),  
5) **key distribution + rotation**, and  
6) security/privacy properties and interoperability requirements.

---

## 1. Goals and non-goals

### 1.1 Goals
- **Match without sharing identifiers:** allow parties to compute matchable tokens locally without revealing raw demographics to a central registry.
- **Ephemeral identifiers:** tokens MUST change over time to prevent creation of persistent identifiers or correlation across periods.
- **Robust to messy data:** tolerate capitalization, punctuation, honorifics, missing middle names, suffixes, nickname-like variants, formatting differences in phones/addresses, etc.
- **Deterministic and auditable:** token generation MUST be deterministic given the same inputs and keys.
- **Composable transport:** token sets can be exchanged over any transport (e.g., STP/SyncURL, HTTPS APIs, files).

### 1.2 Non-goals
- EMTP is **not** an identity-proofing or KYC protocol.
- EMTP does not define authorization, consent, access control, or PHI exchange.
- EMTP does not guarantee perfect uniqueness; collisions are possible and must be managed by downstream workflows.

---

## 2. Terminology

- **Participant:** an entity computing EMTP tokens (payer/provider/hub/bank/fintech/etc.).
- **Key Server:** a service distributing time-scoped HMAC keys to authorized Participants.
- **Credentialed Participant:** a Participant authorized to retrieve EMTP keys.
- **Token:** an HMAC of a normalized identifier tuple under a specific time-scoped key.
- **Tuple:** an ordered list of normalized identifier components (e.g., name + DOB + phone).
- **Tuple expansion:** generating multiple tuples per individual to improve match recall.
- **Key epoch:** the time window for which a given key is valid (e.g., month).
- **Overlap window:** a period where both current and prior epoch keys are valid for continuity.

---

## 3. Inputs (Identifier Fields)

EMTP accepts an **input record** containing zero or more of the following fields:

### 3.1 Required
- **date_of_birth** (`DOB`): `YYYY-MM-DD` (Gregorian calendar).

> Rationale: Without DOB, false positives rise dramatically. Implementations MAY support token generation without DOB, but MUST label resulting token sets as “weak”.

### 3.2 Name
- **full_name**: a free-form string that may include honorifics, initials, middle names, suffixes.

The EMTP library MUST parse `full_name` into:
- `given` (first token(s))
- `middles` (0..n tokens)
- `family` (last name token(s))
- `suffix` (optional, standardized; e.g., `JR`, `SR`, `II`, `III`, `IV`)

> Note: suffix parsing MUST be handled by the EMTP library (do not require upstream separation).

### 3.3 Phone(s)
- **phones**: list of strings.  
Implementations MUST normalize to E.164 where possible and also support national formats.

### 3.4 Address(es)
- **addresses**: list of postal addresses, each containing:
  - `line1`, `line2` (optional), `city`, `state`/`region`, `postal_code`, `country`
Implementations SHOULD accept a single free-form address string as well.

### 3.5 ID fragments (optional)
- **id_numbers**: list of strings containing ≥4 digits from any identifier system (SSN, DL, member IDs, etc.).
Implementations MUST normalize and derive suffix fragments:
- last4, last5, last6 (when available)

> Rationale: used only for disambiguation and collision resolution; not required by default.

---

## 4. Normalization

All normalization MUST be deterministic.

### 4.1 Unicode, case, and punctuation
For all string fields:
1) Unicode normalize to **NFKD**
2) Strip diacritics
3) Uppercase ASCII
4) Replace all non-alphanumeric characters with a single space
5) Collapse repeated whitespace
6) Trim leading/trailing whitespace

### 4.2 Name normalization

#### 4.2.1 Honorific removal
Honorifics (case-insensitive) SHOULD be removed when present as leading tokens, including:
`MR`, `MRS`, `MS`, `MISS`, `DR`, `PROF`, `REV`, etc.

If a name consists solely of honorific + one token, honorific removal MUST NOT drop the only identifier token.

#### 4.2.2 Initials and tokenization
- Split name into tokens.
- Treat tokens like `J.R.R.` as initials `J`, `R`, `R`.
- Remove empty tokens.

#### 4.2.3 Suffix parsing
Suffixes MUST be detected and separated if present at end of name:
`JR`, `SR`, `II`, `III`, `IV`, `V` (optionally extendable).
Common variants (`JUNIOR`, `SENIOR`) MUST be mapped to `JR`, `SR`.

Suffix detection MUST tolerate punctuation (e.g., `Sr.`) and commas.

#### 4.2.4 Family name handling
Implementations MUST treat the final non-suffix token(s) as family name.
Multi-part family names (e.g., `DE LA CRUZ`) SHOULD be supported by heuristics, but are not required in v0.3.

### 4.3 DOB normalization
- MUST be strict `YYYY-MM-DD`.
- If only year/month known, implementations MAY generate “weak tokens” but MUST label them.

### 4.4 Phone normalization
- Strip all non-digits.
- If number begins with country code, format as E.164: `+<countrycode><nationalnumber>`.
- Otherwise, if default country is known, prepend it.
- Generate variants:
  - full E.164
  - last10 (US-style) when length ≥10
  - last7 when length ≥7 (optional; discouraged due to collisions)

### 4.5 Address normalization
Address normalization SHOULD:
- Normalize abbreviations: `STREET→ST`, `AVENUE→AVE`, `ROAD→RD`, etc.
- Normalize unit designators: `APT`, `UNIT`, `#`.
- Uppercase and whitespace collapse per §4.1.
- Postal code normalization:
  - US: keep 5-digit base; optionally include ZIP+4 variant.

Generate address variants:
- `LINE1 + POSTAL_CODE`
- `LINE1 + CITY + STATE`
- `LINE1 + CITY + STATE + POSTAL_CODE`

### 4.6 ID fragment normalization
For each id_number string:
- Extract contiguous digit sequences.
- For each extracted sequence with length L:
  - if L ≥ 4, include last4
  - if L ≥ 5, include last5
  - if L ≥ 6, include last6
Optionally include full sequence only if L ≤ 12 (implementation choice).

---

## 5. Tuple construction and expansion

The EMTP library MUST generate a **set of tuples** from available identifiers.

### 5.1 Tuple schema
A tuple is an ordered list of fields joined with a delimiter:
- `|` MUST be used as the join delimiter
- fields MUST already be normalized
- missing fields MUST NOT be represented as empty slots (i.e., tuple schemas are explicit)

### 5.2 Required tuple families
Implementations MUST generate at least the following tuple families when inputs are available:

**Name + DOB**
- `NAME_FULL|DOB`
- `NAME_GIVEN_FAMILY|DOB`
- `NAME_INITIALS_FAMILY|DOB` (e.g., `J R R TOLKIEN|DOB`)

**Phone + DOB**
- `PHONE_E164|DOB`
- `PHONE_LAST10|DOB` (when derivable)

**Address + DOB**
- `ADDR_LINE1_POSTAL|DOB`
- `ADDR_LINE1_CITY_STATE|DOB`

**Name + DOB + Address**
- `NAME_GIVEN_FAMILY|DOB|ADDR_LINE1_POSTAL`

### 5.3 Optional tuple families
If `id_numbers` are present:
- `NAME_GIVEN_FAMILY|DOB|ID_LAST4`
- `DOB|ID_LAST4`
- `PHONE_LAST10|DOB|ID_LAST4`

> Implementations SHOULD treat ID fragment tuples as “high precision” and prioritize them when resolving collisions.

### 5.4 Variant expansion guidance
Implementations SHOULD generate additional variants:
- drop middle names
- include one middle initial
- include all initials
- remove suffix
- include suffix
- nickname mapping (optional; locale-specific)

However, implementations MUST cap expansions to avoid combinatorial explosion. A recommended cap is **≤256 tuples per person**.

---

## 6. Token generation

### 6.1 HMAC algorithm
Default:
- **HMAC-SHA256**

Output:
- **hex-encoded** lowercase string (64 hex chars)

### 6.2 Token computation
For each tuple `t` and key `k`:
```
token = HMAC_SHA256(key=k, message=t)
```

### 6.3 Token namespace (domain separation)
Keys MUST be domain-separated by including a **purpose string** in the key derivation or message.

Required approach (message prefix):
```
message = "EMTP|" + schema_id + "|" + t
token = HMAC_SHA256(k, message)
```

Where:
- `schema_id` identifies the tuple family/version set (e.g., `v1`)
- `schema_id` MUST be stable across Participants for interoperability

### 6.4 Returned token set
The EMTP function returns:
- a set of `(key_epoch_id, token)` pairs, OR
- a set of tokens where key_epoch_id is implied by key set used

Implementations SHOULD include key_epoch_id to aid debugging and overlap handling.

---

## 7. Key distribution and rotation

### 7.1 Key server requirements
The Key Server MUST:
- Authenticate Participants (e.g., mTLS, OIDC, API keys for credentialed users).
- Serve current and prior epoch keys (at least 2 epochs) to support continuity.
- Support revocation: deny key access to misbehaving Participants.
- Publish key metadata (epoch id, validity range) alongside keys.

### 7.2 Rotation cadence
Rotation cadence is configurable (monthly recommended for healthcare).
- Epoch duration: **1 month** (recommended default)
- Overlap: Key server MUST distribute at least current + previous epoch keys

Shorter cadence (weekly/daily) MAY be used for higher privacy at cost of more frequent recomputation.

### 7.3 Key identifiers
Keys MUST be labeled with:
- `epoch_id` (e.g., `2026-01`)
- `not_before`, `not_after` timestamps

### 7.4 Key material security
- Keys MUST be generated using a cryptographically secure RNG.
- Keys MUST be at least **256 bits** of entropy.
- Keys MUST be stored and distributed over TLS.
- Keys MUST NOT be embedded in client code or published.

---

## 8. Interoperability requirements

Participants MUST:
- Implement normalization and tuple expansion per this spec
- Use the same `schema_id` and tuple family definitions
- Use HMAC-SHA256 and message prefixing as defined
- Support at least two-epoch key overlap
- Treat token sets as **ephemeral** and avoid persistence beyond necessary matching windows

---

## 9. Security and privacy properties

### 9.1 Privacy properties
- The Key Server never receives demographics as part of normal operation.
- Tokens rotate with key epochs, preventing long-term correlation.
- Variant expansion reduces false negatives while keeping inputs local.

### 9.2 Threat model notes
- If an attacker obtains keys, they can mount dictionary attacks. Therefore:
  - restrict key distribution to Credentialed Participants
  - support revocation
  - rotate keys frequently enough for acceptable risk

- EMTP does not prevent collusion between Participants who exchange raw identifiers.

### 9.3 Collision handling
Collisions are expected in edge cases (e.g., Sr/Jr with same DOB/address).
Downstream systems SHOULD:
- treat matches as **candidates**, not certainty
- use secondary confirmation (ID fragments, payer confirmation, user approval workflows)
- allow disambiguation by requesting additional identifiers (e.g., last4/last5)

---

## 10. Versioning

This document is versioned as `v0.3`. Implementations MUST:
- expose a library version
- expose supported schema_id values
- include schema_id and version fields in any published code/test vectors

---

## 11. Test vectors (required)

A conforming EMTP implementation MUST provide:
- canonical normalization test vectors (name/phone/address/id fragments)
- canonical tuple expansion vectors
- canonical HMAC vectors with fixed keys

---

## Appendix A: Example (informative)

**Input A:**  
`"MR. JRR TOlkein"`  
`DOB=1892-01-03`  
`Address="20 Northmoor Road, Oxford"`  

**Input B:**  
`"John R. R. Tolkien Sr"`  
`DOB=1892-01-03`  
`Address="20 NORTHMOOR RD, Oxford"`  

After normalization and tuple expansion, both inputs produce at least one shared tuple:
`J R R TOLKIEN|1892-01-03|20 NORTHMOOR RD|OXFORD|...`

Therefore they share at least one token under the same epoch key.

---

## Appendix B: Recommended schema_id definitions (informative)

- `schema_id=v1` includes the tuple families in §5.2 and §5.3.
- Future schema versions MUST be backward compatible via multi-schema support.
