# Intel 8255A programmable peripheral interface

## Function

Three 8-bit ports (A, B, C) in mode 0 (basic input / output), mode 1 (strobed) or mode 2
(bidirectional port A), with bit set / reset on port C.

## Pinout

`record.md`, PPI-20 (40-pin DIP).

## Model status

`rtl/intel_8255a.v` (module `intel_8255a`), `tb/tb_vv55.v` and `faults/` are the owner's, written
to the Intel data sheet. Manifest `component.toml`.

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| КР580ВВ55А | `kr580vv55a` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

- RTL, TB, faults and `component.toml`: BSD-3-Clause, the owner.
- The docs of this folder (the Markdown files): CC BY 4.0, the owner (`NOTICE`).
- Data sheets: third-party documents with their own status (`datasheets/index.md`).
