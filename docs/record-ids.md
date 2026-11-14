# Record ID registry

Every record ID prefix and where its items are defined. Checked by `tools/check_records.py`.

- Status `here`: defined in a `retroICs/ics/**/record.md`. `pending`: the home does not exist yet;
  nothing is checked. `external`: defined in another repo; checked only with `--docs`.
- IDs: empty for a whole prefix. A list when the items of one prefix are split over several homes;
  that row then covers only the listed IDs.
- Existing IDs keep their prefix and number forever. New items take the prefix of their home file.
- ID pattern: `[A-Z][A-Z0-9]{1,9}(?:-DEV)?-[DEM]?\d+`. Kinds in an IC record: `<P>-n` data sheet
  statement, `<P>-Dn` difference, `<P>-En` vendor erratum, `<P>-Mn` model note.
- `PPI-D1`..`PPI-D6` are differences between two Intel editions ([C78] and [D8255]). They stay in the
  8255A `record.md` under "Edition differences", as table rows.
- The 8224 (CLK) and the SN7492 (IE4) are docs only: both are modelled inside the RK86 clock block
  `rk86_clocks16` (in the Karabas fork until the RTL is imported, then in `retroMachines`). Their
  board-wiring items are to live in the RK86 board record (planned, retroComputersDocs):
  CLK-11 (board use), IE4-4 (board wiring) and IE4-5 (the load strobe states, derived from the
  board's gate QD·QC and the 8275 CCLK).
- Board items of a new machine use a machine prefix (`RK86-n`, `MIK-n`, `UT88-n`, `APG-n`). A new IC
  registers a new prefix (for example PIT for the 8253). Project deviations use `<PROJECT>-DEV-n`.

| Prefix | Home | Status | IDs |
|---|---|---|---|
| CPU | retroICs/ics/intel/8080a/record.md | here | |
| PPI | retroICs/ics/intel/8255a/record.md | here | |
| DMA | retroICs/ics/intel/8257/record.md | here | |
| CRT | retroICs/ics/intel/8275/record.md | here | |
| CLK | retroICs/ics/intel/8224/record.md | here | |
| CLK | retroComputersDocs/computers/rk86/board.md | external | CLK-11 |
| IE4 | retroICs/ics/ti/sn7492/record.md | here | |
| IE4 | retroComputersDocs/computers/rk86/board.md | external | IE4-4, IE4-5 |
| VID | retroComputersDocs/computers/rk86/board.md | pending | |
| GLUE | retroComputersDocs/computers/rk86/board.md | pending | |
| MEM | retroComputersDocs/computers/rk86/board.md | pending | |
| TAPE | retroComputersDocs/computers/rk86/board.md | pending | |
| SND | retroComputersDocs/computers/rk86/board.md | pending | |
| ROMD | retroComputersDocs/computers/rk86/romdisk-module.md | pending | |
| RK86M-DEV | retroMachines/machines/rk86/implementation.md | pending | |
| RKPOCKET-DEV | radio86-rk-pocket/fpga/implementation.md | pending | |
