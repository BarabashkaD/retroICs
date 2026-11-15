# AGENTS.md: intel/8255a

## Scope

The Intel 8255A (КР580ВВ55А): its data sheet record, equivalents and data sheet index. RTL, TB and faults: the owner's, written to the Intel data sheet (`README.md`, Model status).

## Files

`README.md`, `record.md` (PPI-n items, SILENT, assumptions checked), `equivalents.md`, `implementation.md`, `datasheets/index.md` and the stored data sheets `datasheets/*.pdf`, `component.toml`, `rtl/intel_8255a.v`, `tb/tb_vv55.v`, `faults/*.patch`.

## Commands

From the repo root, in PowerShell 7:

```text
python -B tools/check_records.py
python -B tools/check_privacy.py
python -B -m unittest discover -s tools/tests -v
```

## Record prefix

`PPI` (`docs/record-ids.md`). IDs are never renumbered; a new item takes the next free number.

## Review checklist

`docs/agents/review-checklist.md`; each item cites its source ID, page and figure; SILENT items say what was searched.

## Pitfalls

- Emulators ([MAME], [EMU], [APG]) are comparison-only, never a source of behaviour.
