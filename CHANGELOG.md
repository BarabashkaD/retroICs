# Changelog

Features, changes, fixes and known issues of each release. Versions follow semver.

## Unreleased

- Record and privacy checkers (`tools/check_records.py`, `tools/check_privacy.py`), lint workflow.
- `simrun`: the `component.toml` schema and loader, `filelist` (Icarus, Quartus, ISE formats) and
  `trace` (record ID, tests, killing faults, status).
- Agent rules (L0), review checklist, conventions, vendor names, record ID registry, source IDs,
  sources policy, quick start, IC folder templates.
- Licences: CC BY 4.0 for the owner's Markdown files, BSD-3-Clause for the owner's other files;
  `NOTICE`; licence texts in `LICENSES/`.
- IC folders of the Intel 8080A, 8255A, 8257 and 8275: data sheet records, equivalents, data
  sheet indexes.
- Data sheets: seven PDFs stored with their IC folders (metadata stripped); every index entry with
  provenance, licence check and SHA-256; documents that cannot be stored listed by hash and link.
- A generic IC library: the docs, headers, tools and tests name no computer, platform or project
  the models were built for or that uses them, and no fork as the origin of a file, except the
  source of the third-party bases (MiSTer-devel/Apogee_MiSTer at 4b37da2), third-party notices,
  quoted vendor text, data sheet provenance and a real system cited as evidence by its source ID;
  a test guards the wording.
- The 8224 clock generator and the SN7492 counter left the library (no model here); their record
  IDs (CLK, IE4) are retired in the registry.
- The IC records hold data sheet content only; a board's use of a chip left them. Timing is written
  in the data sheets' own units (clock cycles, ns, states).
- `check_records.py` checks the records of any repo against that repo's own registry.
- `NOTICE` names only this repo and its files: the original authors of the third-party models
  (Vslav, Dmitry Tselikov, Sorgelig) and the source they were taken from, the 8257 and 8275
  rewrites, the one licence rule for the owner's files, what a build that contains the
  third-party models must carry, and the status of the stored data sheets.
- `check_comment_only.py`: `--paths` (only the matching files) and `--anywhere` (comment lines
  anywhere in a file, and the line comment of an unchanged code line).
