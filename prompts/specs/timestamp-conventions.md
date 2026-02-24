# Shared Timestamp Specification

Context: distilled from conversation dated 2026-02-24.

## Purpose
Define consistent, language-agnostic rules for timestamp representation in internal data, user-facing displays, filenames, and logs.

## Scope
Applies to timestamp strings and timestamp-related naming in application code, logs, and generated filenames.

## Terms
- Internal timestamp: machine-oriented timestamp used for storage, roundtrip serialization, and system correlation.
- User-facing timestamp: display-oriented timestamp shown to end users.
- High precision: sub-second precision suitable for ordering near-simultaneous events.

## Requirements

### Internal Timestamps
- MUST use UTC.
- MUST use a roundtrip-safe format with explicit UTC marker (`Z` or equivalent explicit UTC indicator).
- MUST be high precision.
- MUST include `utc` in variable/key names when the value is UTC.

### User-Facing Timestamps
- MUST default to local time.
- MUST omit timezone specifiers by default (for example, no `JST`, `+09:00`) unless explicitly requested.
- SHOULD use a human-readable date/time format.

### Naming Rules (Local vs UTC)
- `utc` is REQUIRED for UTC variables/keys.
- `local` or timezone abbreviations (for example, `jst`) are OPTIONAL, not mandatory.
- `local`/timezone labels SHOULD be used only when disambiguation is needed in the same context as UTC values.
- In contexts without UTC counterparts, local labels SHOULD be omitted to avoid redundancy.

### Filename Timestamps
- MUST separate semantic groups with underscores (`_`).
- SHOULD separate components inside a group with hyphens (`-`) for readability.
- SHOULD follow this pattern: `YYYY-MM-DD_HH-MM-SS_<semantic-group>.<ext>`.
- MAY use compact forms without hyphens only when readability is not a concern.

### Logging
- MUST use high-precision timestamps.
- SHOULD default to the same internal UTC roundtrip format for simplicity.
- If logs are strongly user-facing, MAY use high-precision local time WITH explicit timezone identifier.

## Decision Tables

| Context | Required Time Basis | Timezone Marker in String | Naming Requirement |
|---|---|---|---|
| Internal data/serialization | UTC | Required explicit UTC marker | Must include `utc` |
| User-facing display | Local | Omit by default | `local`/`jst` optional |
| User-facing display with explicit dev request | Local (or requested basis) | Include as requested | Name based on context |
| Logs (default) | UTC | Required explicit UTC marker | Internal naming rules apply |
| Logs (user-facing exception) | Local | Required timezone identifier | Clarify local basis when needed |

## Conformance Examples
- Internal UTC field: `created_utc = "2026-02-24T03:52:12.779788Z"`
- Local display field (single-context local): `created_at = "2026-02-24 12:52:12"`
- Disambiguated pair in same context: `created_at`, `created_utc`
- Filename: `2026-02-24_12-52-12_shared-specs.md`

## Out of Scope
- Language-specific APIs and library choices.
- Timezone conversion implementation details.
- Storage engine/schema design beyond timestamp string contracts.

## Open Questions
- Minimum accepted precision for "high precision" is not numerically fixed (for example, milliseconds vs microseconds).
- Exact user-facing format standardization (`YYYY-MM-DD HH:MM` vs `YYYY-MM-DD HH:MM:SS`) is not fully fixed.
