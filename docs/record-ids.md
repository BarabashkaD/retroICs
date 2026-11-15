# Record ID registry

Every record ID prefix this repo defines, and where its items are. Checked by
`tools/check_records.py`. Each repo that keeps records has a registry like this one.

- Status `here`: defined in this repo (a `record.md`, or the Home file of the row). `pending`: the
  home does not exist yet; nothing is checked. `external`: a prefix of another repo that the records
  here cite; checked only with `--external <repo>=<checkout>`. `retired` (Home `-`): defined nowhere
  here any more; never defined again, references allowed.
- IDs: empty for a whole prefix. A list when the items of one prefix are split over several homes;
  that row then covers only the listed IDs.
- Existing IDs keep their prefix and number forever. New items take the prefix of their home file.
- ID pattern: `[A-Z][A-Z0-9]{1,9}(?:-DEV)?-[DEM]?\d+`. Kinds in an IC record: `<P>-n` data sheet
  statement, `<P>-Dn` difference, `<P>-En` vendor erratum, `<P>-Mn` model note. A project's
  deviations use `<PROJECT>-DEV-n`.
- `PPI-D1`..`PPI-D6` are differences between two Intel editions ([C78] and [D8255]). They stay in the
  8255A `record.md` under "Edition differences", as table rows.
- A new IC registers a new prefix (for example PIT for the 8253). The items of a board, a machine or
  a project are registered in the repo that defines them.
- The retired rows: items that left this repo with their IDs (a board's use of a chip, or a chip
  that has no model here); they keep those IDs in their new home.

| Prefix | Home | Status | IDs |
|---|---|---|---|
| CPU | retroICs/ics/intel/8080a/record.md | here | |
| CPU | - | retired | CPU-5, CPU-7 |
| PPI | retroICs/ics/intel/8255a/record.md | here | |
| DMA | retroICs/ics/intel/8257/record.md | here | |
| CRT | retroICs/ics/intel/8275/record.md | here | |
| CLK | - | retired | |
| IE4 | - | retired | |
