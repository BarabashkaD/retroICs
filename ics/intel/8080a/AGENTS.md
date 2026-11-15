# AGENTS.md: intel/8080a

## Scope

The Intel 8080A (КР580ВМ80А): its data sheet record, equivalents and data sheet index. RTL: `rtl/upstream/k580vm80a.v`, Vslav's die-derived КР580ВМ80А model (taken from MiSTer-devel/Apogee_MiSTer `rtl/k580vm80a.v` at `4b37da2`, line endings CR LF to LF, otherwise unchanged), under the owner's wrapper `rtl/intel_8080a.v` (module `intel_8080a`, instance `core`; `README.md`, Model status).

## Files

`README.md`, `record.md` (CPU-n items, SILENT, assumptions checked), `equivalents.md`, `implementation.md`, `datasheets/index.md` and the stored data sheets `datasheets/*.pdf`, `component.toml`, `rtl/intel_8080a.v`, `rtl/upstream/k580vm80a.v`. No TB or faults of its own yet.

## Commands

From the repo root, in PowerShell 7:

```text
python -B tools/check_records.py
python -B tools/check_privacy.py
python -B -m unittest discover -s tools/tests -v
```

## Record prefix

`CPU` (`docs/record-ids.md`). IDs are never renumbered; a new item takes the next free number.

## Review checklist

`docs/agents/review-checklist.md`; each item cites its source ID, page and figure; SILENT items say what was searched.

## Pitfalls

- `rtl/upstream/k580vm80a.v` stays byte-identical as it came in (`tools/tests/test_headers.py` checks it). Hierarchical paths into the CPU (TBs, power-up files) go through the wrapper's instance: `<inst>.core.<name>`; the pins also resolve on the wrapper.
- Emulators ([MAME], [EMU], [APG]) are comparison-only, never a source of behaviour.
