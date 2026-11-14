# TI SN7492 divide-by-twelve counter

## Function

Ripple counter: a ÷2 stage (QA) and a ÷6 stage (QB, QC, QD); with QA connected to CKB it counts
0..11 (÷12).

## Pinout

The pins with their data sheet behaviour: `record.md`, IE4-1..IE4-3 ([7490] pp. 1-3).

## Model status

Docs only. Modelled inside `rk86_clocks16` (the RK86 clock block, in the fork's `rk86_16` of
https://github.com/BarabashkaD/karabas-go-core-rk86 until the RTL is imported, then in
`retroMachines`). It gets its own RTL only when a second machine needs it
(`docs/conventions.md`, "The 8224 and the SN7492").

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| К155ИЕ4 | `k155ie4` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

The docs of this folder: CC BY 4.0 (`NOTICE`). Data sheets keep their own status
(`datasheets/index.md`).
