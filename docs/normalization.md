# Normalization Guide

This document provides additional examples and guidance for EMTP normalization. For the normative specification, see [spec.md](../spec.md) Section 4.

## Overview

EMTP normalization ensures that different representations of the same person produce matching tokens. The normalization rules are designed to be:

- **Deterministic**: Same input always produces same output
- **Tolerant**: Handles common variations in data entry
- **Portable**: Simple enough to implement identically across languages

## Name Normalization Examples

### Honorific Handling

| Input | Normalized | Notes |
|-------|------------|-------|
| `MR. JRR Tolkien` | `jrr tolkien` | Honorific removed |
| `Dr. Jane Smith` | `jane smith` | Honorific removed |
| `Mr Smith` | `mr smith` | Honorific kept (only 2 tokens) |

### Suffix Handling

| Input | Normalized | Suffix |
|-------|------------|--------|
| `John Tolkien Sr.` | `john tolkien` | `sr` |
| `John Tolkien Senior` | `john tolkien` | `sr` |
| `John Smith III` | `john smith` | `iii` |
| `Mary Jones, Jr.` | `mary jones` | `jr` |

### Initial Handling

| Input | Full Normalized | First+Last Variant |
|-------|-----------------|-------------------|
| `J. R. R. Tolkien` | `j r r tolkien` | `j tolkien` |
| `JRR Tolkien` | `jrr tolkien` | `jrr tolkien` |
| `John Ronald Tolkien` | `john ronald tolkien` | `john tolkien` |

### Variant Expansion

For a name like `John Ronald Reuel Tolkien Sr`, the implementation generates variants including:

- `john ronald reuel tolkien` (full, no suffix)
- `john tolkien` (first + last)
- `john tolkien sr` (first + last + suffix)
- `j tolkien` (first initial + last)
- `jrr tolkien` (collapsed initials + last)

## Phone Normalization Examples

| Input | Normalized | Variants |
|-------|------------|----------|
| `(212) 555-0100` | `2125550100` | `2125550100` |
| `+1-212-555-0100` | `2125550100` | `2125550100` |
| `+44 20 7946 0958` | `442079460958` | `442079460958`, `2079460958` |

Note: US numbers with leading `1` (11 digits) have the `1` stripped.

## Address Normalization Examples

| Input | Normalized | No-Unit Variant |
|-------|------------|-----------------|
| `20 Northmoor Rd, Oxford` | `20 northmoor rd oxford` | (same) |
| `123 Main St Apt 5` | `123 main st apt 5` | `123 main st` |
| `456 Oak Ave Unit 2B` | `456 oak ave unit 2b` | `456 oak ave` |

## ID Number Normalization Examples

| Input | Variants Generated |
|-------|-------------------|
| `SSN 123-45-6789` | `6789`, `56789`, `456789` |
| `DL# A1234567` | `4567`, `34567`, `234567` |
| `Acct: 987654` | `7654`, `87654`, `987654` |
| `1234` | `1234` |

ID normalization extracts digit sequences of 4+ characters and generates last-4, last-5, and last-6 variants.

## Implementation Notes

1. **Unicode**: Always normalize to NFKD and strip combining characters before other processing
2. **Order matters**: Apply normalization steps in the order specified in the spec
3. **Empty handling**: Skip empty fields; don't include them in tuples
4. **Tuple cap**: Limit to 256 tuples per person to prevent explosion
