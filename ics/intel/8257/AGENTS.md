# AGENTS.md: intel/8257

## Scope

The Intel 8257 (КР580ВТ57): its data sheet record, equivalents and data sheet index. RTL in the fork's `rk86_16` (https://github.com/BarabashkaD/karabas-go-core-rk86, branch `rk86-16mhz`) until the RTL is imported (`k580vt57.v`).

## Files

`README.md`, `record.md` (DMA-n items, SILENT, assumptions checked), `equivalents.md`, `implementation.md`, `datasheets/index.md`. The RTL, TBs and faults come when the RTL is imported.

## Commands

From the repo root, in PowerShell 7:

```text
python -B tools/check_records.py
python -B tools/check_privacy.py
python -B -m unittest discover -s tools/tests -v
```

## Record prefix

`DMA` (`docs/record-ids.md`). IDs are never renumbered; a new item takes the next free number.

## Review checklist

`docs/agents/review-checklist.md`; each item cites its source ID, page and figure; SILENT items say what was searched.

## Pitfalls

- Emulators ([MAME], [EMU], [APG]) are comparison-only, never a source of behaviour.
- "Task 1 record" names the section "Timing reference for 0.8.0 (Task 1 record)": a in the 8224 record, b in the 8257 record, d in the 8275 record; c (the 8275 pins on the boards) is board wiring, in the RK86 board record (planned, retroComputersDocs).
