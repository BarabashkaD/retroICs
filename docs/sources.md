# Sources

Each bracket source ID used in the records, once. Checked by `tools/check_records.py`: every bracket
ID (Latin or Cyrillic capital first, or four digits first) in any markdown file under `ics/` must be
listed here. Rules for adding a source: `docs/sources-policy.md`.

- Home: the index that describes the document (provenance, licence check, SHA-256). A data sheet
  lives in the `datasheets/index.md` of its IC folder; a data book that covers several ICs lives with
  the first IC that uses it, and the other IC indexes point to it. Schematics, magazine articles and
  ROM listings of a real system live in the repo that documents that system; their rows here name
  that home. They are cited only as evidence where the data sheets are silent.
- Kind: `vendor` (a data sheet, data book, user's manual or application note of the maker, Soviet
  reference sheets included), `board` (a schematic, PCB or magazine article of a board), `listing`
  (a ROM image or its listing, read as code), `comparison-only` (an emulator or another core: shows
  how others read a point, never a source of behaviour).

| ID | Home | Kind | Document |
|---|---|---|---|
| [C78] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | Intel Component Data Catalog 1978: the 8080A, 8255A and 8257 data sheets |
| [UM83] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | Intel MCS-80/85 Family User's Manual, January 1983 |
| [D8080N] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | National INS8080A data sheet |
| [ВМ80] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | КР580ВМ80А reference sheet |
| [D8255] | retroICs/ics/intel/8255a/datasheets/index.md | vendor | Intel 8255A data sheet |
| [D79] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel 8275 data sheet 1979, 00224A, preliminary |
| [D84] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel 8275 data sheet 1984, AFN-00224B/C |
| [D8275K] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel 8275 data sheet, AFN-00224B, data book pages 8-223..8-246, no date |
| [AP-62] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel application note AP-62 "A Low Cost CRT Terminal Using the 8275" (AFN-01304A, November 1979), the reprint in a 1984 handbook, pp. 8-1 ff.; the same note as [DG81] |
| [DG81] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel application note AP-62 "A Low Cost CRT Terminal Using the 8275" (AFN-01304A, November 1979), the reprint in a 1981 handbook, pp. 2-439..2-478; the same note as [AP-62] |
| [R86] | retroComputersDocs/computers/rk86/index.md | board | Радио 1986 No. 5, pp. 31-34: text and the main board schematic, Fig. 3 |
| [K14] | retroComputersDocs/computers/rk86/index.md | board | S. Kiselev, Radio-86RK re-make rev. 1.4: schematic and KiCad nets |
| [MON] | retroComputersDocs/computers/rk86/index.md | listing | The RK86 monitor ROM `BIOS.BIN` (F800-FFFF) |
| [APG] | retroComputersDocs/computers/rk86/index.md | comparison-only | MiSTer-devel/Apogee_MiSTer at `4b37da2`: `k580vt57.v`, `k580vg75.sv`; comparison-only as a source of behaviour, and the code base of the third-party models (`NOTICE`) |
| [MAME] | retroComputersDocs/computers/rk86/index.md | comparison-only | mamedev/mame at `d077ea2`: `i8275.cpp`, `i8257.cpp`, `radio86.cpp` |
| [EMU] | retroComputersDocs/computers/rk86/index.md | comparison-only | vpyk/emu80v4 at `a243b8e`: `Crt8275.cpp`, `Dma8257.cpp` |
