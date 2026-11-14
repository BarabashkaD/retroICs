# retroICs

Models of the integrated circuits of 8080-based home computers (Radio-86RK first, then Микроша,
ЮТ-88, Апогей БК-01), each with its data sheets, its data sheet record, its equivalents and its
model notes. Each model follows its vendor data sheets; where they are silent, the original boards
decide. Emulators and other cores are never sources of behaviour.

This repository is the base layer. `retroMachines` builds the machines from these ICs, and one
platform repo per computer builds the cores (the Analogue Pocket first). `retroComputersDocs` holds
the board records, schematics and magazine scans.

## Status

Docs, checkers and the six IC folders with their records. The RTL and its tests come next.

| IC | Folder | Record prefix | Model |
|---|---|---|---|
| Intel 8080A (КР580ВМ80А) | `ics/intel/8080a/` | CPU | planned (the die-derived КР580ВМ80А model) |
| Intel 8224 (КР580ГФ24) | `ics/intel/8224/` | CLK | docs only; modelled inside the RK86 clock block |
| Intel 8255A (КР580ВВ55А) | `ics/intel/8255a/` | PPI | planned |
| Intel 8257 (КР580ВТ57) | `ics/intel/8257/` | DMA | planned |
| Intel 8275 (КР580ВГ75) | `ics/intel/8275/` | CRT | planned |
| TI SN7492 (К155ИЕ4) | `ics/ti/sn7492/` | IE4 | docs only; modelled inside the RK86 clock block |

## Layout

| Path | Content |
|---|---|
| `AGENTS.md` | rules for coding agents in this repo |
| `docs/agents/` | global agent rules (L0) and the review checklist |
| `docs/conventions.md` | naming, ports, clock enables, record IDs, interfaces |
| `docs/vendors.md` | vendor folder names |
| `docs/record-ids.md` | the record ID registry |
| `docs/sources.md`, `docs/sources-policy.md` | source IDs; how a source document gets in |
| `docs/quickstart.md` | the first commands |
| `docs/templates/ic/` | skeletons of a new IC folder |
| `ics/<vendor>/<part>/` | one IC folder per part |
| `tools/` | `check_records.py`, `check_privacy.py` and their tests |

## Licences

- The owner's code: BSD-3-Clause (`LICENSE`).
- The owner's docs (records, equivalents, implementation notes, AGENTS files, `docs/`): CC BY 4.0.
- Third-party files keep their own licence, named in each file header. All texts are in `LICENSES/`.
- Credit to Dmitry Veremeev (BarabashkaD) must be kept in copies and derived works (`NOTICE`).
