# AGENTS.md

Instructions for coding agents in `retroICs`. Read `docs/agents/global.md` (the L0 rules) and
`docs/agents/review-checklist.md` first. They apply to every repo that reads them.

## Repository

- IC implementations for building 8080-family and later computers, main focus Intel: each IC with
  its model, data sheets, record, equivalents and implementation notes. Only an IC with a model here
  has a folder here.
- Depends on nothing. Consumers pin it as a git submodule.
- One IC folder per part: `ics/<vendor>/<part>/` (contract: `docs/conventions.md`). Work on one IC
  needs this repo and that folder only. The folder's own `AGENTS.md` gives its scope and commands.
- The records of other repos (a board record, a machine's notes) are checked only with a checkout of
  that repo (`--external <repo>=<checkout>`), never as a submodule.
- Docs: `README.md`, `docs/conventions.md`, `docs/vendors.md`, `docs/record-ids.md`,
  `docs/sources.md`, `docs/sources-policy.md`, `docs/quickstart.md`, `docs/templates/ic/`.

## Commands

From the repo root, in PowerShell 7 (`pwsh`). Python 3, standard library only, always with `-B`.

```text
python -B -m unittest discover -s tools/tests -v       the tools' tests
python -B tools/check_records.py                       registry, records, source IDs
python -B tools/check_records.py --external <repo>=<checkout>   also the IDs homed in <repo>
python -B tools/check_privacy.py                       working tree
python -B tools/check_privacy.py --all                 working tree and every commit
python -B tools/check_comment_only.py <base> <head>    a header-only commit: header comment lines only,
                                                       each fault on a changed file the same edit
python -B tools/check_comment_only.py <base> <head> --paths '<glob>' --anywhere
                                                       only the matching files; comment lines anywhere
                                                       and line comments of unchanged code lines
$env:PYTHONPATH = 'tools'                              then simrun (docs/conventions.md, component.toml):
python -B -m simrun filelist <component> --format f    file list, dependencies first
python -B -m simrun trace                              record ID -> tests -> faults -> status
python -B -m simrun run ics --tier quick [--negative]  the TBs (and faults); Icarus Verilog 13.0
```

`--anywhere` judges each line on its own: in a `.py` file a `#` line inside a multi-line string
counts as a comment, so a change there passes the check (a limit of the check; read such a diff).

The simulation tests of `tools/tests/test_simrun_run.py` need Icarus Verilog 13.0 (`IVERILOG`, else
`PATH`); without it they skip, unless `SIMRUN_REQUIRE_IVERILOG=1` (CI job `quick`).

The command passes on a clean clone. The wording test (`tools/tests/test_private_wording.py`, its
helpers in `tools/tests/wordscan.py`) reads every file of the working tree (binary files and the
official licence texts `LICENSES/*.txt` excepted) with generic patterns; when `RETRO_PRIVATE_WORDS`
names a file outside the repository (or ignored by git) of more words (one per line), it checks
those too, and without it it prints a NOTE. A word of that list in imported text that is already
public upstream is exempt only for its file: `WORD_EXEMPT` in `tools/tests/wordscan.py` (path, word,
reason; a stale entry fails). Exemptions live there, not in `privacy-allow.txt` (which is the
privacy checker's).

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
