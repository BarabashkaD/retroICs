# Sources

Each bracket source ID used in the records, once. Checked by `tools/check_records.py`: every bracket
ID (Latin or Cyrillic capital first, or four digits first) in any markdown file under `ics/` must be
listed here. Rules for adding a source: `docs/sources-policy.md`.

- Home: the index that describes the document (provenance, licence check, SHA-256). A data sheet
  lives in the `datasheets/index.md` of its IC folder; a data book that covers several ICs lives with
  the first IC that uses it, and the other IC indexes point to it. Board schematics, magazines and
  ROM listings live in `retroComputersDocs`.
- Kind: `vendor` (a data sheet, data book, user's manual or application note of the maker, Soviet
  reference sheets included), `board` (a schematic, PCB or magazine article of a board), `listing`
  (a ROM image or its listing, read as code), `comparison-only` (an emulator or another core: shows
  how others read a point, never a source of behaviour).
- `[R87-…]` covers every Радио 1987 issue (`[R87-3]`, `[R87-5]`, ...).

| ID | Home | Kind | Document |
|---|---|---|---|
| [C78] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | Intel Component Data Catalog 1978: 8080A, 8224, 8255A, 8257; for board parts 8212 (PDF 526), 2708 (4-40), 2716 (4-46), 2116 (3-109) |
| [UM83] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | Intel MCS-80/85 Family User's Manual, January 1983 |
| [D8080N] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | National INS8080A data sheet |
| [ВМ80] | retroICs/ics/intel/8080a/datasheets/index.md | vendor | КР580ВМ80А reference sheet |
| [D8224] | retroICs/ics/intel/8224/datasheets/index.md | vendor | Intel 8224 clock generator data sheet, order 231464-001, November 1992 |
| [ГФ24] | retroICs/ics/intel/8224/datasheets/index.md | vendor | КР580ГФ24 reference sheet |
| [D8255] | retroICs/ics/intel/8255a/datasheets/index.md | vendor | Intel 8255A data sheet |
| [D79] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel 8275 data sheet 1979, 00224A, preliminary |
| [D84] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel 8275 data sheet 1984, AFN-00224B/C |
| [D8275K] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel 8275 data sheet, AFN-00224B, data book pages 8-223..8-246, no date |
| [AP-62] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel application note AP-62 (8275), 1984 |
| [DG81] | retroICs/ics/intel/8275/datasheets/index.md | vendor | Intel 8275 design guide, 1981 |
| [7490] | retroICs/ics/ti/sn7492/datasheets/index.md | vendor | TI SN7490A, SN7492A, SN7493A data sheet, SDLS940A |
| [ИЕ4] | retroICs/ics/ti/sn7492/datasheets/index.md | vendor | К155ИЕ4 reference sheet |
| [2716] | retroComputersDocs/computers/rk86/index.md | vendor | Intel 2716 EPROM data sheet |
| [7474] | retroComputersDocs/computers/rk86/index.md | vendor | TI SN7474 data sheet |
| [74198] | retroComputersDocs/computers/rk86/index.md | vendor | TI SN74198 data sheet |
| [ИР13] | retroComputersDocs/computers/rk86/index.md | vendor | К155ИР13 reference sheet |
| [ТМ2] | retroComputersDocs/computers/rk86/index.md | vendor | К155ТМ2 reference sheet |
| [R86] | retroComputersDocs/computers/rk86/index.md | board | Радио 1986 No. 5, pp. 31-34: text and the main board schematic, Fig. 3 |
| [R86-4] | retroComputersDocs/computers/rk86/index.md | board | Радио 1986 No. 4, pp. 24-26: architecture, memory map |
| [R86-6] | retroComputersDocs/computers/rk86/index.md | board | Радио 1986: the main board PCB insert |
| [R87-…] | retroComputersDocs/computers/rk86/index.md | board | Радио 1987 issues: No. 3 p. 32 (the ROM module), No. 5 (the КР580ВГ75 replacement, reference tables) |
| [K14] | retroComputersDocs/computers/rk86/index.md | board | S. Kiselev, Radio-86RK re-make rev. 1.4: schematic and KiCad nets |
| [MON] | retroComputersDocs/computers/rk86/index.md | listing | The RK86 monitor ROM `BIOS.BIN` (F800-FFFF) |
| [APG] | retroComputersDocs/computers/rk86/index.md | comparison-only | MiSTer-devel/Apogee_MiSTer at `4b37da2`: `k580vt57.v`, `k580vg75.sv` |
| [MAME] | retroComputersDocs/computers/rk86/index.md | comparison-only | mamedev/mame at `d077ea2`: `i8275.cpp`, `i8257.cpp`, `radio86.cpp` |
| [EMU] | retroComputersDocs/computers/rk86/index.md | comparison-only | vpyk/emu80v4 at `a243b8e`: `Crt8275.cpp`, `Dma8257.cpp` |
