# Intel 8224 clock generator

## Function

Clock generator and driver for the 8080A: Φ1, Φ2 and Φ2 (TTL) from a crystal (÷9), the RESET and
READY synchronisers, STSTB.

## Pinout

The pins with their data sheet behaviour: `record.md`, CLK-1..CLK-10 ([D8224] 1-50 Fig. 1).

## Model status

Docs only. Modelled inside `rk86_clocks16` (the RK86 clock block, in the fork's `rk86_16` of
https://github.com/BarabashkaD/karabas-go-core-rk86 until the RTL is imported, then in
`retroMachines`). It gets its own RTL only when a second machine needs it
(`docs/conventions.md`, "The 8224 and the SN7492").

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| КР580ГФ24 | `kr580gf24` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

The docs of this folder: CC BY 4.0 (`NOTICE`). Data sheets keep their own status
(`datasheets/index.md`).
