# Review checklist

One line per lesson, from the decisions of the RK86 16 MHz models (the Karabas fork's
`src/rtl/rk86_16/README.md` at `d995355`) and from past reviews. A reviewer goes through every line
that applies to the change.

## Sources and records

- Each behaviour is checked against its own chip's data sheet and the board schematics; an emulator or another core is never the reason for a choice.
- Each quoted sentence is found on the cited page; a citation one page off is a finding (the 8257 DRQ sentence is on [C78] 12-105, not 12-100).
- State boundaries and edges are checked against the AC table formulas as well as the drawings; a reading that fits only the drawing is a finding.
- Each assumption of a plan is checked against the data sheet before coding and recorded as confirmed or differs, with the effect (the 8224 RESET flip-flop clocks at p3, not at Φ2↓).
- A data sheet section that is ambiguous gets two blind readers (source only, no model, no record), then a comparison with the model.
- Differences between editions of one data sheet are recorded as D-items with both sources ([D79] against [D84]; [C78] against [D8255]).

## SILENT decisions

- Each decision where the data sheet is silent is marked `// SILENT` with its record ID at the code line that decides it, or listed in the component's notes when it has no inline marker.
- The basis of a SILENT decision is the original board (aligned picture, timing), never an emulator; the record names what was searched.
- A SILENT choice is checked against the whole machine, not only the chip: the 8257 hands out its block in order, so a skipped row-0 fill of the 8275 would shift the picture one row for good.
- The rejected reading of a SILENT item is kept as a fault that the tests catch, so the tests prove the difference.
- A reading kept but not merged is stored as one patch with its base commit named; a patch on an old base may not apply as it is.
- An internal difference that never shows at the pins of the target machine is recorded with the condition under which it would show (8257 SI to S0 shows only when HLDA comes early).
- A point that only a real chip can settle goes on the record's hardware check list (board, chip markings, analyser capture); an FPGA run of the model cannot settle it.
- A hardware result that differs from the model changes the model, its tests and its record together.

## Model and glue

- Both clock edges are checked: a chip that acts on θ↑ and θ↓ modelled on one enable moves the other edge's events (the 8257 on `f2` alone moves θ↓ events 5 oscillator periods early).
- Chip select and strobes are checked per state (the 8257 model ignores CS only in S1-S4: its choice where the states are SILENT, DMA-14).
- Side effects of reads are checked: a status read clears flags (8275 IR; the 8257 TC bits, cleared at IOR↑ in the model: its choice where the clear moment is SILENT, DMA-8), and a read during a flag set may lose it (seen only in simulation; real-hardware check open).
- A command given in the middle of an operation states what stops and when it resumes (8275 Reset during a row fill).
- Firmware dependencies on status flags are checked: the monitor waits for 8275 IR before it programs the 8257, so a model without IR stops the boot.
- Chips without a reset pin and free-running dividers start in a random state; the TBs set power-up values explicitly and a scenario randomises them.
- During DMA the address decoder works on the DMA address, so a DMA read gets whatever device is at that address, not only RAM; the glue is checked at every clock and with a DMA read pass over the whole address space.
- The 8080 hold rules are checked against the cycle type: HOLD is sampled in T2, and a write cycle ends before the DMA's first read.

## Tests and faults

- Each tested record item has a fault that its test catches with the named error; a fault that passes means the test is too weak.
- Coincident events get their own check (an 8275 burst space that ends at the CCLK that finds the underrun).
- A golden output changes only with a reason and a record ID; a changed golden output is never accepted silently.
- A fault that fails at a different first error line after a move, or a fault that was dropped, is a finding.
- Hierarchical paths into a wrapped module are updated with the wrapper; Icarus stops at an unresolved name, so a TB that still uses the old path fails loudly.

## Files and imports

- An imported third-party file is byte-identical or lists every change in its header (the 8080 model: line endings only); its source, commit and licence are recorded.
- No local path, host, user name or email in any committed file, message or PDF metadata; `check_privacy.py --all` passes.
- Sources are never edited by text-replacement scripts; faults are `git diff` patches.
