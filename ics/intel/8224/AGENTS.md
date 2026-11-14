# AGENTS.md: intel/8224

## Scope

The Intel 8224 (КР580ГФ24): its data sheet record, equivalents and data sheet index. Docs only: modelled inside `rk86_clocks16` (the RK86 clock block, in the fork's `rk86_16` of https://github.com/BarabashkaD/karabas-go-core-rk86 until the RTL is imported).

## Files

`README.md`, `record.md` (CLK-n items, SILENT, assumptions checked), `equivalents.md`, `implementation.md`, `datasheets/index.md`.

## Commands

From the repo root, in PowerShell 7:

```text
python -B tools/check_records.py
python -B tools/check_privacy.py
python -B -m unittest discover -s tools/tests -v
```

## Record prefix

`CLK` (`docs/record-ids.md`). IDs are never renumbered; a new item takes the next free number.

CLK-11 (board use) is a board item, defined in the RK86 board record (planned, retroComputersDocs).

## Review checklist

`docs/agents/review-checklist.md`; each item cites its source ID, page and figure; SILENT items say what was searched.

## Pitfalls

- Emulators ([MAME], [EMU], [APG]) are comparison-only, never a source of behaviour.
- "Task 1 record" names the section "Timing reference for 0.8.0 (Task 1 record)": a in the 8224 record, b in the 8257 record, d in the 8275 record; c (the 8275 pins on the boards) is board wiring, in the RK86 board record (planned, retroComputersDocs).
- No RTL here: the behaviour is modelled inside `rk86_clocks16`; a change of it is a change of that block.
