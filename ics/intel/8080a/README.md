# Intel 8080A microprocessor

## Function

8-bit microprocessor of the Radio-86RK and the other 8080-based home computers of this family.

## Pinout

The pins the RK86 boards use, with their data sheet behaviour: `record.md`, CPU-1..CPU-8. Pin
descriptions: [C78] 11-12, [D8080N] p. 5.

## Model status

RTL in the fork's `rk86_16` until the RTL is imported: `k580vm80a.v` of karabas-go-core-rk86
(https://github.com/BarabashkaD/karabas-go-core-rk86, branch `rk86-16mhz`, `src/rtl/rk86_16/`). The model is the die-derived КР580ВМ80А model
(`reproduces = "k580vm80a"`); it moves here unchanged, with the wrapper `intel_8080a`
(`docs/conventions.md`, "The 8080").

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| КР580ВМ80А | `kr580vm80a` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

The docs of this folder: CC BY 4.0 (`NOTICE`). Data sheets keep their own status
(`datasheets/index.md`).
