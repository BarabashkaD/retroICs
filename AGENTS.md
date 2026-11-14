# AGENTS.md

Instructions for coding agents in `retroICs`. Read `docs/agents/global.md` (the L0 rules) and
`docs/agents/review-checklist.md` first. They apply to every repo of the family.

## Repository

- IC models of 8080-based home computers, with data sheets, records, equivalents and model notes.
- Depends on nothing. `retroMachines` (planned) will pin this repo as a submodule; platform repos pin
  `retroMachines`.
- One IC folder per part: `ics/<vendor>/<part>/` (contract: `docs/conventions.md`). Work on one IC
  needs this repo and that folder only. The folder's own `AGENTS.md` gives its scope and commands.
- Board records (`board.md` of a computer) live in `retroComputersDocs`, a sibling checkout, found
  by the `RETRO_DOCS` environment variable (default `../retroComputersDocs`). It is never a submodule.
- Docs: `README.md`, `docs/conventions.md`, `docs/vendors.md`, `docs/record-ids.md`,
  `docs/sources.md`, `docs/sources-policy.md`, `docs/quickstart.md`, `docs/templates/ic/`.

## Commands

From the repo root, in PowerShell 7 (`pwsh`). Python 3, standard library only, always with `-B`.

```text
python -B -m unittest discover -s tools/tests -v       the tools' tests
python -B tools/check_records.py                       registry, records, source IDs
python -B tools/check_records.py --docs ../retroComputersDocs   also the board IDs (once it exists)
python -B tools/check_privacy.py                       working tree
python -B tools/check_privacy.py --all                 working tree and every commit
```

The command passes on a clean clone. The tests that compare the records with the private legacy
record (`tools/tests/test_records_split.py` `LegacySplit`, `tools/tests/test_docs.py`
`test_sources_cover_legacy`) read it from `RETRO_LEGACY_RECORD`; without it they skip with a printed
reason. CI has no legacy record and keeps `tools/check_records.py` as its gate. The wording test
(`test_no_private_wording`) reads every file of the working tree (binary files and the official
licence texts `LICENSES/*.txt` excepted) with generic patterns; when `RETRO_PRIVATE_WORDS` names an
a file outside the repository (or ignored by git) of more words (one per line), it checks those too, and without it it prints a NOTE.

Before changing a record: set RETRO_LEGACY_RECORD to the private legacy record and run the suite;
the legacy tests must run, not skip. In one command:
`$env:RETRO_LEGACY_RECORD = '<path>'; python -B -m unittest discover -s tools/tests -v`.

## Rules for this repo

- Every rule of `docs/agents/global.md`.
- A new record ID prefix goes into `docs/record-ids.md` in the same commit as its first item.
- A new bracket source ID goes into `docs/sources.md` in the same commit as its first citation, and
  its document passes `docs/sources-policy.md` before the first push.
- An IC folder changes only with its own record, tests and faults in the same PR.
- `docs/templates/ic/` keeps headings only.

## Releases

- Semver, immutable `vX.Y.Z` tags, PR-only `main` ("Rebase and merge"). The maintainer merges and
  tags by hand; an agent never creates a tag or a release.
- A fidelity fix is a minor release with a record ID, a CHANGELOG line and a test. A change of ports
  or parameters bumps the IC's `interface` counter.
- CHANGELOG and release notes list features, changes, fixes and known issues only; no test results,
  no hardware results.
