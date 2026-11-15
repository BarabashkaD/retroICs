# Intel 8080A microprocessor: data sheet record

Data sheet items of the Intel 8080A (КР580ВМ80А): the pins and timings a board around it has to meet.

## Sources

Sources: [C78] 11-12..11-15 (PDF 428-431); [D8080N] `INS8080A.pdf` p. 5 (pin definitions, identical in content); [ВМ80] `kr580vm80a.pdf` (pins, electrical values). Vslav's model is not changed.

Not sources of behaviour: emulators and other cores.

The documents cited here and their provenance: `datasheets/index.md` of this folder; the other source IDs: `docs/sources.md`.

## Notation

The original IDs are kept; new functions are numbered after them. A board's use of these pins (what drives them, what they drive) is recorded with the board, not here. Researched 2026-11-10.

## Items (CPU-n)

| ID | Function | Data sheet behaviour (pins, edges, values) | Source (document, page / figure) |
|---|---|---|---|
| CPU-1 | READY (23) | The 8080 needs READY tRS ≥ 120 ns before Φ2↓ of T2 / TW ("must be externally synchronized", note 11); while READY is low the CPU enters wait states and WAIT (24) is high | [C78] 11-12, 11-15; [D8080N] p. 5 |
| CPU-2 | RESET (12) | "When activated (high) for a minimum of three clock periods, the content of the Program Counter is cleared and the Interrupt Enable and Hold Acknowledge Flip-flops are reset"; flags, A, SP and registers are not cleared; execution starts at 0000 | [D8080N] p. 5; [C78] 11-12 |
| CPU-3 | HOLD (13) / HLDA (21) | HOLD requests the bus; HLDA acknowledges it and the CPU floats its address and data buses. Timing and the HLDA rule with an 8257: `ics/intel/8257/record.md`, "HOLD overhead with an 8080A" | [C78] 11-12, 11-15; `ics/intel/8257/record.md` |
| CPU-4 | INT (14), INTE (16) | INT: the interrupt request input; INTE: the interrupt enable output, the state of the internal interrupt enable flip-flop (set by EI, reset by DI and by RESET) | [C78] 11-12 |
| CPU-6 | DBIN (17) | Data bus in: high while the CPU reads the data bus. tDF (DBIN from Φ2) 25..140 ns | [C78] 11-14 |
| CPU-8 | Read data window | Address valid ≤ tAD 200 ns after Φ2↑ of T1; data in must meet tDS1 ≥ 30 ns (during Φ1 and DBIN) and tDS2 ≥ 150 ns (to Φ2 during DBIN) in T3 (note 10) | [C78] 11-14, 11-15 |

## Edition differences (CPU-Dn)

None recorded.

## SILENT (CPU)

None recorded.

## Assumptions checked

None recorded.

## Hardware checks

None planned.
