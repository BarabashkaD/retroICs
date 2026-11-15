# retroICs

IC implementations for building 8080-family and later computers, with the main focus on Intel
chips. Each model follows its vendor data sheets; where they are silent, the decision and its
evidence are recorded in the chip's `record.md`. Emulators and other cores are never sources of
behaviour.

The repository holds the implementations (RTL, testbenches, faults), their docs (data sheet
records, equivalents, implementation notes, data sheet indexes) and the instructions for coding
agents.

## Status

Four Intel chips, each with its model, its data sheet record and its manifest (`component.toml`).

| IC | Type | Soviet analog |
|---|---|---|
| [Intel 8080A](ics/intel/8080a/) | CPU | КР580ВМ80А |
| [Intel 8255A](ics/intel/8255a/) | PPI | КР580ВВ55А |
| [Intel 8257](ics/intel/8257/) | DMA | КР580ВТ57 |
| [Intel 8275](ics/intel/8275/) | CRT | КР580ВГ75 |

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
| `tools/` | `check_records.py`, `check_privacy.py`, `check_comment_only.py`, the `simrun` package (`component.toml`, file lists, trace) and their tests |

## Licences

- The owner's files: every Markdown file CC BY 4.0, every other file BSD-3-Clause (`LICENSE`).
  The exceptions are the third-party files and the data sheets.
- Third-party files keep their own licence, named in each file header:
  `ics/intel/8080a/rtl/upstream/k580vm80a.v` CC BY 3.0 (Vslav, 1801BM1);
  `ics/intel/8257/rtl/intel_8257.v` and `ics/intel/8275/rtl/intel_8275.v` LicenseRef-Tselikov-BSD
  (Dmitry Tselikov; the 8275 with Sorgelig's modifications; both rewritten by the owner).
- Data sheets: third-party documents with their own status (each `datasheets/index.md`), kept as
  archival copies and removed on request.
- All licence texts are in `LICENSES/`. The licences require keeping the copyright notices
  (BSD-3-Clause, the Tselikov licence) and the attribution (CC BY 4.0, CC BY 3.0) in copies and
  derived works; `NOTICE` says what that means for each part and for builds.
