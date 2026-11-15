# Intel 8257 programmable DMA controller

## Function

Four-channel DMA controller: fixed or rotating priority, autoload on channel 2, TC and MARK outputs;
read, write and verify cycles.

## Pinout

`record.md`, DMA-36 (40-pin DIP).

## Model status

`rtl/intel_8257.v` was rewritten by the owner to the Intel 8257 data sheet (2026) from Dmitry
Tselikov's `k580vt57.v` of MiSTer-devel/Apogee_MiSTer at `4b37da2`; kept from that base: the
register write decoding by {F/L, A3-A0}; the module renamed (`k580vt57` to `intel_8257`, in
comments too). It stays under Tselikov's licence as a derived work. `tb/tb_vt57.v`,
`tb/tb_vt57_func.v` and `faults/` are the owner's. Manifest `component.toml`.

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| КР580ВТ57 | `kr580vt57` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

- `rtl/intel_8257.v`: LicenseRef-Tselikov-BSD (`LICENSES/LicenseRef-Tselikov-BSD.txt`), Dmitry
  Tselikov 2011 and the owner's rewrite 2026; Tselikov's notice kept in its header.
- TBs and `component.toml`: BSD-3-Clause, the owner. Faults: each under the licence of the file
  it patches.
- The docs of this folder (the Markdown files): CC BY 4.0, the owner (`NOTICE`).
- Data sheets: third-party documents with their own status (`datasheets/index.md`).
