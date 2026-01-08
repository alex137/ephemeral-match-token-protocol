# EMTP Schema: emtp_v1

This document defines canonicalization + variant expansion rules for EMTP v1.

## Canonical fields

- `full_name`
- `dob` (YYYY-MM-DD)
- `phone`
- `address`

## Canonicalization rules (minimum)

- lowercase
- trim whitespace
- collapse repeated spaces
- remove punctuation except inside apartment/unit strings
- phone: digits only, strip leading `+` and separators
- address: normalize common abbreviations if available

## Variant expansion (minimum)

- name:
  - full name as given
  - remove middle name / initial
  - swap first/last when comma-separated
- phone:
  - full normalized
  - last 10 digits (if longer)
- address:
  - with unit
  - without unit

Implementations MAY include additional deterministic variants.

