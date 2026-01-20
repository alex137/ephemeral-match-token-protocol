# Normalization Guide (v0.3)

## Goals
EMTP must match messy real-world identity strings:
- "MR. JRR TOlkein"
- "John Tolkien Sr"
- "J. R. R. Tolkien"

…while avoiding over-linkage and preserving privacy.

---

## Name normalization

### Canonicalization steps
1. Uppercase
2. Strip punctuation
3. Collapse whitespace
4. Remove honorific prefixes when present:
   - MR, MRS, MS, MISS, DR, PROF, SIR, MADAM, etc.
5. Parse suffix tokens from end:
   - JR, SR, I, II, III, IV, V, VI
6. Split remaining tokens into:
   - FIRST + MIDDLE(S) + LAST

### Variant expansion
Generate variants including:
- first + last (drop middles)
- first initial + last
- collapse multiple initials:
  - "J R R" → "JRR"
- include/exclude suffix

---

## Identifier suffixes (`id_numbers`)
`id_numbers` may contain:
- "1234"
- "01234"
- "acct: 987654"
- "X-1234"

Extract the longest digit sequence length ≥ 4, then generate:
- id4, id5, (optional id6)

This allows parties suffering collisions to add identifier suffixes to disambiguate, without typing the ID type (SSN vs DL etc).
