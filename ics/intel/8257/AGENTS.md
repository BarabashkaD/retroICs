# AGENTS.md: intel/8257

## Scope

The Intel 8257 (КР580ВТ57): its data sheet record, equivalents and data sheet index. RTL rewritten by the owner to the Intel data sheet from Tselikov's `k580vt57.v` (MiSTer-devel/Apogee_MiSTer `4b37da2`; kept: the register write decoding; Tselikov's licence); TBs and faults the owner's (`README.md`, Model status).

## Files

`README.md`, `record.md` (DMA-n items, SILENT, assumptions checked), `equivalents.md`, `implementation.md`, `datasheets/index.md`, `component.toml`, `rtl/intel_8257.v`, `tb/tb_vt57.v`, `tb/tb_vt57_func.v`, `faults/*.patch`.

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
- The timing sections of `record.md` ("Transfer states", "HOLD overhead with an 8080A") are cited by their names.
