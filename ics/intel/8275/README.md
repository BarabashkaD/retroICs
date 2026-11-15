# Intel 8275 programmable CRT controller

## Function

CRT controller: two row buffers filled by DMA, character, line and row counters, HRTC and VRTC,
cursor, light pen, character and field attributes.

## Pinout

`record.md`, CRT-40 (40-pin DIP).

## Model status

`rtl/intel_8275.v` was rewritten by the owner to the Intel 8275 data sheets (2026) from Dmitry
Tselikov's `k580vg75.sv` with Sorgelig's modifications, of MiSTer-devel/Apogee_MiSTer at
`4b37da2`; kept from that base: the two row buffers and FIFOs indexed by the buffer select, the
parameter state machine, the status byte layout; the module renamed (`k580vg75` to `intel_8275`,
in comments too). It stays under Tselikov's licence as a derived work. `tb/tb_vg75.v`,
`tb/tb_vg75_dma.v`, `tb/tb_vg75_attr.v` and `faults/` are the owner's. Manifest `component.toml`.

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| КР580ВГ75 | `kr580vg75` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

- `rtl/intel_8275.v`: LicenseRef-Tselikov-BSD (`LICENSES/LicenseRef-Tselikov-BSD.txt`), Dmitry
  Tselikov 2011, Sorgelig's modifications (named as a contributor in the header) and the owner's
  rewrite 2026; Tselikov's notice kept in its header.
- TBs and `component.toml`: BSD-3-Clause, the owner. Faults: each under the licence of the file
  it patches.
- The docs of this folder (the Markdown files): CC BY 4.0, the owner (`NOTICE`).
- Data sheets: third-party documents with their own status (`datasheets/index.md`).
