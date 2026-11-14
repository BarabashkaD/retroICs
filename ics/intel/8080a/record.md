# Intel 8080A microprocessor: data sheet record

Items of the 8080A (КР580ВМ80А) as the RK86 boards use it, split from the RK86 record with their IDs.

## Sources

Sources: [C78] 11-12..11-15 (PDF 428-431); [D8080N] `INS8080A.pdf` p. 5 (pin definitions, identical in content); [ВМ80] `kr580vm80a.pdf` (pins, electrical values). Vslav's model is not changed; only the board connections are recorded.

Not sources of behaviour: MAME, Emu80, Apogee, the Karabas core.

The documents cited here and their provenance: `datasheets/index.md` of this folder; the other source IDs: `docs/sources.md`.

## Notation

The original IDs are kept; new functions are numbered after them. What the section "Timing reference for 0.8.0 (Task 1 record)" establishes is cited as "Task 1 record, section a-d", not repeated: a in `ics/intel/8224/record.md`, b in `ics/intel/8257/record.md`, d in `ics/intel/8275/record.md`; c (the 8275 pins on the boards) is board wiring: `retroComputersDocs/computers/rk86/board.md` (pending). Renders cited by name are page crops of the cited documents, kept with the maintainer's source collection, not in this repository (`<document>_pNN` = PDF page NN; `_cA_B_C_D` = a crop in percent of the page: left, top, right, bottom; `...` stands for `Radio_Magazine-1986-05-page-32-33-Schematic_p01`). Researched 2026-11-10.

## Items (CPU-n)

| ID | Function | Data sheet behaviour (pins, edges, values) | Source (document, page / figure) |
|---|---|---|---|
| CPU-1 | READY (23) | From the 8224 READY; RDYIN tied high on both boards, so no wait states; the 8080 needs READY tRS ≥ 120 ns before Φ2↓ of T2 / TW ("must be externally synchronized", note 11). WAIT (24) not used ([K14] U1.24 no net) | [C78] 11-12, 11-15; [D8080N] p. 5; [R86], [K14] (CLK-11) |
| CPU-2 | RESET (12) | From the 8224 RESET. "When activated (high) for a minimum of three clock periods, the content of the Program Counter is cleared and the Interrupt Enable and Hold Acknowledge Flip-flops are reset"; flags, A, SP and registers are not cleared; execution starts at 0000 | [D8080N] p. 5; [C78] 11-12 |
| CPU-3 | HOLD (13) / HLDA (21) | HOLD ← 8257 HRQ (pin 10), HLDA → 8257 HLDA (pin 7), directly on both boards; timing and the HLDA rule: Task 1 record b (HOLD overhead) in `ics/intel/8257/record.md` | [C78] 11-12, 11-15; Task 1 record (`ics/intel/8257/record.md`) |
| CPU-4 | INT (14), INTE (16) | INT tied to ground on both boards ([R86] symbol at pin 14; [K14] U1.14 GND), so interrupts never occur; INTE drives the sound (SND-1) | [R86] crop `..._c34_13_55_50.png`; [K14] netlist; [C78] 11-12 |
| CPU-5 | SYNC (19) | → 8224 SYNC (pin 5) (STSTB unused) | [K14] netlist; [R86] crop `..._c34_13_55_50.png` |
| CPU-6 | DBIN (17) | → ЧТЕНИЕ XOR (GLUE-3); on [K14] also the start-up NAND (GLUE-12). tDF (DBIN from Φ2) 25..140 ns | [C78] 11-14; [K14] U16.2, U20.1 |
| CPU-7 | WR (18) | ЗАПИСЬ: memory write (DRAM / SRAM WE), PPI WR, 8257 IOW (pin 2), the 8275 WR gate (GLUE-6), [R86] the DRAM sequencer start (D4.4). Memory write strobe = the CPU WR alone | [R86-4] p. 26; [R86] p. 34 text; [K14] ~WR net |
| CPU-8 | Read data window | Address valid ≤ tAD 200 ns after Φ2↑ of T1; data in must meet tDS1 ≥ 30 ns (during Φ1 and DBIN) and tDS2 ≥ 150 ns (to Φ2 during DBIN) in T3 (note 10). At 1.778 MHz: about 800 ns from a valid address to the T3 sample, against the ROM's tACC 450 ns (MEM-4): no wait states needed | [C78] 11-14, 11-15 |

## Edition differences (CPU-Dn)

None recorded.

## SILENT (CPU)

None recorded.

## Assumptions checked

None recorded.

## Hardware checks

None planned.
