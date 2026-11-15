# AGENTS.md: intel/8275

## Scope

The Intel 8275 (КР580ВГ75): its data sheet record, equivalents and data sheet index. RTL rewritten by the owner to the Intel data sheets from Tselikov's `k580vg75.sv` with Sorgelig's modifications (MiSTer-devel/Apogee_MiSTer `4b37da2`; kept: the row buffers and FIFOs, the parameter state machine, the status byte layout; Tselikov's licence); TBs and faults the owner's (`README.md`, Model status).

## Files

`README.md`, `record.md` (CRT-n items, SILENT, assumptions checked), `equivalents.md`, `implementation.md`, `datasheets/index.md` and the stored data sheets `datasheets/*.pdf`, `component.toml`, `rtl/intel_8275.v`, `tb/tb_vg75.v`, `tb/tb_vg75_dma.v`, `tb/tb_vg75_attr.v`, `faults/*.patch`.

## Commands

From the repo root, in PowerShell 7:

```text
python -B tools/check_records.py
python -B tools/check_privacy.py
python -B -m unittest discover -s tools/tests -v
```

## Record prefix

`CRT` (`docs/record-ids.md`). IDs are never renumbered; a new item takes the next free number.

## Review checklist

`docs/agents/review-checklist.md`; each item cites its source ID, page and figure; SILENT items say what was searched.

## Pitfalls

- Emulators ([MAME], [EMU], [APG]) are comparison-only, never a source of behaviour.
- The timing section of `record.md` ("Timing (data sheet)") and the 8257 record's "Transfer states" are cited by their names.
