# Global agent rules (L0)

These rules apply to every repo that reads this file. A repo's `AGENTS.md` (L1) and a component's
`AGENTS.md` (L2) add to them; they never relax them. Rules for one machine or one platform live in
that repo's `AGENTS.md`. Read `review-checklist.md` next to this file as well.

## Source priority

1. Vendor data sheets: Intel and the other makers first, then the second-source and licensed-copy
   sheets (the Soviet reference sheets among them).
2. Schematics and publications of the real systems that use the part (magazine articles, the makers'
   documents), cited as evidence where the data sheets are silent.
3. Listings of original ROMs, read as code.

Emulators (MAME, Emu80 and others) and other FPGA cores are never sources of behaviour. They may be
cited as `comparison-only`, to show how others read a point; a decision never rests on them.

- Every modelled behaviour points to a record ID, and every record item cites its source: the
  bracket source ID, the page and the figure or table.
- Read the markdown records first. Open a PDF only to check a statement against its source.
- Quote the source where the wording matters. Mark a derived value as derived, with its steps.

## SILENT handling

- When the sources do not decide a behaviour, the item is SILENT. Record what was searched (document
  and pages), the behaviour chosen and its basis.
- The basis is the behaviour of a real system that uses the part (its picture, its timing), cited
  by its source IDs, then the simplest reading of the data sheet. Never an emulator.
- Mark the deciding code line with `// SILENT` and the record ID.
- A SILENT item that only real hardware can settle goes on the hardware check list of its record.
  Simulation never settles it.
- Where the data sheet itself is ambiguous, ask two blind readers (they read the source without the
  model or the record), then compare.

## Fidelity

- No unrequested behaviour change. A task changes what it names and nothing else.
- Report every side effect: a changed timing, a changed port, a test that now passes for a different
  reason, a golden output that moved.
- A fidelity fix carries its record ID, a test that fails without it, a fault that the test catches
  and a CHANGELOG line.
- Simulation and build results are not hardware results. Never report hardware behaviour from
  simulation; hardware runs are the maintainer's.

## Vendor-first naming

- Folder `ics/<vendor>/<part>/`; module and file `<vendor>_<part>`; vendor names from
  `docs/vendors.md`.
- `<part>` is the vendor's base part number in lower case, without package, speed or temperature
  marks: `intel/8255a`, `intel/8080a`.
- Docs titles use the vendor name ("Intel 8255A programmable peripheral interface"). Soviet names
  appear in Cyrillic with a transliteration, in `equivalents.md` and the README table.
- Details: `docs/conventions.md`.

## Pre-push source checklist

Before a source file (PDF, scan, netlist) is first pushed: provenance recorded (origin, copied from,
download link), licence status checked and written in the index, SHA-256 recorded, metadata
stripped. Steps: `docs/sources-policy.md`. History is public for good; a file pushed by mistake
cannot be taken back.

## Privacy and portability

- No absolute local paths, host names, user names, IP addresses or emails in committed files,
  commit messages or PDF metadata.
- Paths are relative to the repo, sibling repos are `../<repo>` or come from an environment
  variable. Values that differ per machine come from parameters, env vars or config files.
- `tools/check_privacy.py --all` passes before every push. Its only exceptions are the lines of
  `privacy-allow.txt`: one line each, with a reason, reviewed like code. Add a line only for a
  third-party header kept as it is or a commit trailer; never to hide a local path.
- Commits use the GitHub noreply address as author.

## SPDX and attribution

- The owner's code: `SPDX-License-Identifier: BSD-3-Clause` and
  `SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD`.
- The owner's files: every Markdown file CC BY 4.0, every other file BSD-3-Clause, stated in
  `NOTICE`. Exceptions: third-party files and source documents (below).
- Third-party files keep their licence and their header as they are; their licence text is in
  `LICENSES/` (a `LicenseRef-...` name when SPDX has none). Never relicense a third-party file.
- Every `.v`, `.vh`, `.py` and `.toml` file has its SPDX lines in its header, and every licence
  pointer of a header names a file under `LICENSES/` (`tools/tests/test_headers.py`; byte-identical
  copies kept without a header are listed there). A commit that sets headers changes header
  comment lines only: `tools/check_comment_only.py <base> <head>` passes on it.
- Each repo's `NOTICE` names that repo only, with its attribution line, and credits the origins of
  the files whose history began elsewhere. A package that combines repos carries the `NOTICE` of
  each.
- Source documents keep their own status in their index; they are not relicensed.

## Faults and patches

- A fault (negative test) is a unified-diff `.patch` made with `git diff`, paths relative to its
  repo root, applied to a copy with `git apply`. It must make its test fail with its named error.
- A fault that no longer applies is stale: regenerate it from a `git diff` of the changed file.
- Never edit sources with text-replacement scripts (sed-like rewrites, regex patches). Use an editor
  on the file or `git apply` of a reviewed diff.

## Tiers

| Tier | When | Content |
|---|---|---|
| quick | every commit; required PR check | lint, the tools' tests, the TBs without faults |
| standard | every RTL or TB change | the unit TBs of the changed components with their faults; the system scenarios that use them |
| full | before merging an RTL PR | everything with every fault; at most two long system scenarios at once |
| release | before a package | full on the pinned tags, the consumers' tests, the vendor build, the hardware check list |

- Choose the tests by the files changed. Docs only: lint and the tools' tests.
- Stop at the first failure. Never run the same long scenario twice at once.
- Remote runs start from a clean worktree at a commit, never from a tree that agents are editing.

## Mutation review

- Every component gets its own review with mutation testing: each record item that is tested has a
  fault that its test catches.
- A reviewer writes or reads the faults, runs them and checks that each fails with its named error.
  A fault that passes means the test is too weak; strengthen the test, not the fault.
- A review reads the code without the author's conclusions; findings name the record ID, the file
  and line, and the source page.

## Commands and git

- PowerShell only (`pwsh` 7; Windows PowerShell where noted). Never `bash`, `sh`, `zsh` or Linux
  utilities. Hosted CI on Ubuntu runs its steps in `pwsh`. Repeat this rule in every subagent brief.
- Python 3, standard library only, in committed tools. `git filter-repo` and `qpdf` are maintainer
  tools, never called by committed code.
- Files: LF, final newline; `.gitattributes` is `* -text`. Byte-identical imports keep their bytes.
- Commit or push only when the maintainer asks. Changes reach `main` by PR ("Rebase and merge"),
  merged by the maintainer. Never amend or rewrite published history. Never create a tag or a release.
