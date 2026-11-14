# Intel 8275 programmable CRT controller

## Function

CRT controller: two row buffers filled by DMA, character, line and row counters, HRTC and VRTC,
cursor, light pen, character and field attributes.

## Pinout

`record.md`, CRT-40 (40-pin DIP).

## Model status

RTL in the fork's `rk86_16` until the RTL is imported: `k580vg75.v` of karabas-go-core-rk86
(https://github.com/BarabashkaD/karabas-go-core-rk86, branch `rk86-16mhz`, `src/rtl/rk86_16/`).

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| КР580ВГ75 | `kr580vg75` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

The docs of this folder: CC BY 4.0 (`NOTICE`). Data sheets keep their own status
(`datasheets/index.md`).
