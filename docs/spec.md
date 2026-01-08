# EMTP Specification (v0.3)

## 1. Overview
EMTP enables privacy-preserving person matching by sharing ephemeral HMAC tokens derived from normalized identifier tuples.

Participants:
- **normalize** demographics and optional identifier suffixes into tuple variants
- **compute tokens** using rotating HMAC keys from a Key Server
- **share tokens** (never demographics) via any transport

## 2. Inputs
Canonical input fields:

- `name` (string): may include honorifics/suffixes
- `dob` (YYYY-MM-DD)
- `phones` (array of strings)
- `addresses` (array of strings)
- `id_numbers` (array of strings; optional)

### 2.1 Name parsing rules
Implementations MUST:
- uppercase for canonicalization
- remove punctuation
- collapse repeated whitespace
- remove honorific prefixes when present (MR, MRS, MS, DR, PROF, etc.)
- parse recognized suffixes from the tail (JR, SR, I, II, III, IV, V, VI)
- retain suffix as an explicit structured component for tuple generation

Implementations SHOULD attempt to detect and drop leading honorifics even if embedded in the name field (e.g., "Mr. J R R Tolkien").

### 2.2 Identifier suffixes (`id_numbers`)
Participants MAY provide `id_numbers`: strings containing **4+ digits** that represent suffixes of any identifier.

Implementations MUST:
1. Extract the longest contiguous digit sequence of length ≥ 4 from each entry.
2. Generate suffix components:
   - `id4:<last4>`
   - `id5:<last5>` if available
3. SHOULD generate:
   - `id6:<last6>` if available

Identifier types MUST be ignored.

These suffix components are included in tuple variants (see §3).

## 3. Tuple variant generation
The canonical tuple includes:

- normalized name components (first, middle(s), last, suffix)
- dob
- optional phone variants
- optional address variants
- optional id suffix components (id4/id5/id6)

Participants generate multiple variants by:
- using initials vs expanded segments
- including/excluding middle names
- phone with/without country code
- address line token variants

## 4. Token computation
For each tuple variant and each active key:

```
token = HMAC(key, canonical_tuple_bytes)
```

Output tokens MUST be encoded as lowercase hex.

## 5. Rotation + overlap
Key Server returns at least:
- `key_current`
- `key_prior`

Participants MUST compute tokens with both to maintain match continuity across rotation.

## 6. Matching semantics
Two parties match if the intersection of token sets is non-empty.

Tokens that include `id5` or `id6` SHOULD be treated as higher-confidence than demographic-only matches.

## 7. Privacy properties
- No demographics are transmitted in the protocol
- Tokens expire with key rotation and cannot serve as persistent IDs
- Restricted key access enables revocation for misuse circuit-breaker
