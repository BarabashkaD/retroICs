# Conventions

Naming, the IC folder contract, record IDs, ports, clock enables and interface stability. The agent
rules are in `docs/agents/global.md`.

## IC folder contract

```text
ics/intel/8255a/
  component.toml      manifest: identity, reproduces, equivalents, files, deps, tests, negatives
                      (schema below)
  README.md           vendor, part, function, pinout, model status, equivalents table
  record.md           data sheet record: PPI-n statements, SILENT items (choice and basis)
  equivalents.md      second sources and copies (Soviet ones among them): level, sources, differences
  implementation.md   model notes PPI-Mn (what is modelled, ce mapping, limits); vendor errata PPI-En
  AGENTS.md           scope, files, commands, record prefix, checklist, pitfalls
  datasheets/
    index.md          per source: ID, title, vendor, document number, edition, pages used,
                      provenance, licence check result, SHA-256
    *.pdf
  rtl/intel_8255a.v   top module <vendor>_<part>; SPDX header
  tb/  faults/*.patch
  golden/  interface.lock                           (planned)
```

- Today an IC folder with a model holds the markdown files, `datasheets/index.md`, its
  `component.toml`, `rtl/`, `tb/` and `faults/` (imported; the models renamed to
  `<vendor>_<part>`, the TBs and faults under their old names); `golden/` and `interface.lock`
  come later. Only an IC with a model here has a folder here; a chip modelled inside a machine's
  block is documented where it is implemented.
- Skeletons of the markdown files: `docs/templates/ic/`.
- `equivalents.md` says "No differences known as of <date> (<version>)" until a difference is found;
  before the first release the version reads "unreleased".
- `component.toml` allows an `ic` without `[rtl]` (docs only, no tests), for a part documented in a
  repo before its model exists; this repo holds none.
  Its `component.toml` has no `[rtl]`, tests or negatives, so `simrun trace` still covers its
  record.

## component.toml

The manifest of a component (an IC, a board block, a machine, an adapter, a platform), read by
`tools/simrun/manifest.py` with Python's `tomllib`. Example:

```toml
[component]
name = "intel/8255a"
kind = "ic"                       # ic | block | machine | adapter | platform
title = "Intel 8255A programmable peripheral interface"
reproduces = "i8255a"
fidelity = "datasheet"            # datasheet | board | extended
interface = 1
record_prefix = "PPI"

[[equivalent]]
part = "К580ВВ55А"
translit = "k580vv55a"
level = "unverified"              # drop-in | function | partial | unverified

[rtl]
top = "intel_8255a"
files = ["rtl/intel_8255a.v"]
depends = []

[[test]]
name = "modes"
tier = "quick"                    # quick | standard | full
top = "tb_intel_8255a"
files = ["tb/tb_intel_8255a.v"]
plusargs = {}
timeout_s = 120
golden = { file = "golden/modes.txt", compare = "exact" }   # exact | frames | events
ids = ["PPI-5"]

[[negative]]
test = "modes"
fault = "faults/mode1_ibf_stuck.patch"
expect = "ERROR: vv55: mode 1 input: ibf"
match = "first"                   # first | anywhere
ids = ["PPI-5"]
```

| Table | Key | Value | Default |
|---|---|---|---|
| `[component]` | `name` | lower-case path segments; the folder: `<repo>/ics/<name>` for an `ic`, `<repo>/<name>` otherwise (`machines/<name>`) | required |
| | `kind`, `title`, `reproduces`, `fidelity`, `interface` | as in the example; `interface` an integer from 1 | required |
| | `record_prefix` | the prefix of the component's `record.md` items | none |
| | `variant_of` | the component this one is a second-source design of (its own folder) | none |
| | `board_record` | `{ repo = "<docs repo>", tag = "...", file = "<path>" }`: a machine's board record (a path in that repo, no `..`; not checked here) | none |
| `[[equivalent]]` | `part`, `level` | the part name (Cyrillic for a Soviet part); `drop-in`, `function`, `partial` or `unverified` | required |
| | `translit` | the transliteration, `[a-z0-9]+` (`k580vv55a`) | none |
| `[rtl]` | `top`, `files` | top module; the RTL files (at least one); the table is optional only for a docs-only `ic` (then no tests, no negatives) | required |
| | `depends` | names of the components compiled before this one, in this order | `[]` |
| | `incdirs`, `iverilog_flags` | include folders; Icarus options (`-g2005`) | `[]` |
| `[[test]]` | `name`, `tier`, `top`, `files` | a word; `quick`, `standard` or `full`; the TB top; the test's own files (TB, models) | required |
| | `incdirs` | include folders of the test | `[]` |
| | `params` | `{ NAME = value }`: Verilog parameters of the top (`-P<top>.<NAME>`) | `{}` |
| | `plusargs` | `{ name = value }`: `+name=value` on the vvp line | `{}` |
| | `data` | `{ name = { path = "...", sizes = [2048], pad_to = 0 } }`: a binary written as hex (one byte per line) and passed as `+name=<file>`; `sizes` the allowed sizes (empty: any), `pad_to` pads with FFh | `{}` |
| | `timeout_s` | seconds | none |
| | `golden` | `{ file = "...", compare = "exact" \| "frames" \| "events" }` | none |
| | `ids` | record IDs the test checks | `[]` |
| `[[negative]]` | `test`, `fault`, `expect` | a test of this component; `faults/<name>.patch` of this component or `<component>:<name>` of a dependency (its `faults/<name>.patch`; the component must be in `rtl.depends`); the expected text, `*` for any characters | required |
| | `match` | `first`: `expect` is in the first ERROR/FATAL line; `anywhere`: in any line | `first` |
| | `ids` | record IDs the fault kills | `[]` |

- Any other key, table or array (also inside `data` and `golden`) is an error.
- Paths are relative to the component folder, with `/`; they may use `..` but stay inside the
  repo; every file and folder named must exist. Values are strings or integers; no booleans.
- `ids` entries follow the record ID pattern. `simrun trace` checks that each one is defined.
- Equivalents (second sources and copies, Soviet ones among them) are in both places: the manifest gives each part and
  its level (for generated tables such as the README's), `equivalents.md` the text (the
  differences and their sources). Both name the same parts with the same levels.

Commands, from a repo root, with `tools` of `retroICs` on the module path:

```text
$env:PYTHONPATH = 'tools'
python -B -m simrun filelist intel/8255a --format f|qsf|prj [--relative-to DIR] [--search ROOT ...]
python -B -m simrun trace [<component> ...] [--external <repo>=<checkout> ...] [--search ROOT ...]
python -B -m simrun run <path> ... [--tier T] [--jobs N] [--negative] [--replace FILE=FILES ...]
    [--param NAME=V ...] [--keep] [--out DIR] [--iverilog PATH] [--search ROOT ...]
```

- `--search`: the repo roots to find components in (default: the current folder, then this
  checkout). A name found in two roots is an error.
- `filelist`: the dependencies first, in `depends` order, each once, then the component's own
  files. `f` (Icarus `-c` file: `+incdir+` lines, then files), `qsf` (`SEARCH_PATH`,
  `VERILOG_FILE`, `SYSTEMVERILOG_FILE` for `.sv`), `prj` (`verilog work "<path>"`, files only).
- `trace`: one row per record ID (the IDs of each component's `record.md` and every cited ID):
  home (from `docs/record-ids.md`), the tests that cite it, the faults that kill it, status.
  `tested`: a test or negative cites it; else `SILENT`: a bullet of the record's
  `## SILENT (<prefix>)` section names it before its first `: `; else `untestable`: the same in a
  `## Untestable (<prefix>)` section; else `open`. Board IDs (`external` in the registry) are
  checked only with `--external <repo>=<checkout>`; without it the output ends with one
  "NOTE: IDs of <repo> not checked" per repo (`trace.matrix(components, external)` returns the
  rows with those lines in `.notes`).
- `run` (`tools/simrun/run.py`): `<path>` is a component or a folder
  searched for `component.toml` files. It runs the tests of tier `--tier` and lower
  (`quick` < `standard` < `full`; default `full`), with `--negative` also their faults, `--jobs` at
  once. Compile: Icarus Verilog 13.0 (`--iverilog`, else `IVERILOG`, else `PATH`; `iverilog -V` is
  checked first), the `iverilog_flags` of the dependencies and the component (dependencies first,
  each flag once; two different generations such as `-g2005` and `-g2012` are an error, so a
  consumer without `-g2005` that depends on a component with it compiles with `-g2005`), `-I` for
  the include folders of the dependencies, the component and the test, `-P<top>.<NAME>` for `params`, then the test's files and
  the RTL files (dependencies first). Data files become `<name>.hex` (`sizes` checked, FFh padding
  to `pad_to`), passed as `+<name>=<name>.hex` after the `plusargs`.
- Pass rule: `vvp` exits 0, prints a line that starts with `PASS` and no line that starts with
  `ERROR` or contains `FATAL`; with `golden`, the compare passes: `exact` compares the file of the
  golden's name that the test writes into its run folder; other kinds need a comparer from the
  consumer (`run(comparers=...)`), else the test fails.
- A fault copies only the files its patch changes, from the repo that owns the patch (a
  dependency's fault patches a file of that repo), and applies the patch to the copies with
  `git apply`. `CAUGHT`: the run fails and its first `ERROR`/`FATAL` line (`match = "first"`) or any
  line (`"anywhere"`) contains `expect` (`*` any characters); else `MISSED`. A patch that does not
  apply, or that changes a file the test does not compile, is `STALE`; one that changes only files
  replaced by `--replace` is `SKIPPED`. Each fault runs in `neg_<name>/` (a dependency's fault:
  `neg_<component>_<name>`, `/` and `:` as `_`); two faults of one test with the same folder name
  (compared without case) are an error.
- `--replace FILE=FILES` compiles FILES (comma-separated) in place of FILE; `--param NAME=V` sets
  NAME in every test whose `params` has it. Either one that no selected test uses is an error.
- Outputs: `build/simrun/<run-id>/<component>/<test>/` (`vvp.log`, `iverilog.log`, the hex files;
  faults in `neg_<fault>/`) and `summary.json` (`run_id`, `commit` of the checkout that holds the
  output, `repos`: the HEAD of each repo root the run's components and dependencies come from,
  keyed by its path relative to that checkout (`"."`, `"lib/retroICs"`, `"../retroICs"`; null
  outside git), `iverilog`, `tier`, `negative`, per test and fault the status, the first error line
  and the log). Without `--keep` the `.vvp` files and patched copies of passing runs are removed.
- With no test at the tier, `run` prints `no components ...` and exits 0. Exit code 0 when every
  test passes and every fault is caught or skipped, 1 otherwise, 2 on an error below.
- Errors (a manifest problem, a path that cannot be written relative to `--relative-to`, such as
  another drive on Windows, a bad `run` option, Icarus missing or not 13.0, a patch that cannot be
  read, any other error of `run`) print one `ERROR:` line, no traceback, and exit with 2; trace
  problems exit with 1.

## Naming

- Folder `ics/<vendor>/<part>/`; module and file `<vendor>_<part>`. Vendor names: `docs/vendors.md`.
- `<part>` is the vendor's base part number in lower case, without package, speed or temperature
  marks.
- Docs titles use the vendor name ("Intel 8255A programmable peripheral interface").
- Soviet names appear in Cyrillic with a transliteration (КР580ВВ55А, `kr580vv55a`) in
  `equivalents.md` and the README table.
- TTL parts stay machine glue unless a machine needs a part's exact behaviour as an IC.
  `ti/<part>/` holds TTL parts; `ussr/<part>/` Soviet designs without a foreign prototype.

## Reproduced part and variants

- Every manifest (`component.toml`) says which physical part the model reproduces (`reproduces`).
  The default is the vendor part.
- A model written by the owner may take a `VARIANT` parameter for a variant, when every value is tied
  to D-items and tests. A second source with a different design gets its own folder with
  `variant_of`.
- Compatibility levels in `equivalents.md`: `drop-in`, `function`, `partial` (the differences are
  D-items), `unverified`. A `drop-in` or `function` level cites a source. Each D-item names the test
  that shows the difference, when one exists.

### The 8080

- `ics/intel/8080a` holds the die-derived КР580ВМ80А model, byte-identical in `rtl/upstream/`
  (imported), and the thin wrapper `rtl/intel_8080a.v` (module `intel_8080a`, the same ports) that
  gives the family-wide name.
- No `VARIANT`. The manifest says `reproduces = "k580vm80a"`, and the README header says so. The
  known differences from the Intel 8080A are CPU-D items, listed as model limits.
- The wrapper instantiates `k580vm80a core(...)`. Every hierarchical path into the CPU (TBs,
  power-up files) goes through `.core` (`dut.cpu.core.t3`, `` `CPU16_ZERO(dut.cpu.core) ``); the
  pins also resolve on the wrapper (`dut.cpu.pin_a`). Icarus stops at an unresolved hierarchical
  name, so a TB that still uses an old path fails loudly.
- If an Intel-accurate model appears, it replaces the wrapper's contents; consumers keep the name.

## Record IDs

- `docs/record-ids.md` maps every prefix this repo defines to its home file; a repo that keeps
  records of its own has its own registry. Existing IDs keep their prefix and number forever; an
  item that leaves a repo keeps its ID in its new home and is listed `retired` in the old one. When the items of one prefix split across files, the
  registry lists those IDs one by one. New items take the prefix of their home file.
- Pattern: `[A-Z][A-Z0-9]{1,9}(?:-DEV)?-[DEM]?\d+`.
- Kinds of item in an IC record: `<P>-n` data sheet statement (SILENT marked), `<P>-Dn` difference,
  `<P>-En` vendor erratum, `<P>-Mn` model note.
- An item is defined by the first cell of a table row in its home file. Prose and lists only refer
  to it.
- Differences between two editions of one vendor's data sheet stay in that IC's `record.md` under
  "Edition differences", as table rows (`PPI-D1`..`PPI-D6`: [C78] against [D8255]).
- A new IC registers a new prefix (for example PIT for the 8253). A board's use of a chip is not an
  IC item: it lives in that board's record, under the board's prefixes.
- Project deviations use `<PROJECT>-DEV-n`, registered in the project's repo.
- Source IDs are in brackets (`[C78]`) and are listed in `docs/sources.md`; they are not record IDs.

## Ports, clocks and parameters

- One system clock `clk` per machine, at the original master oscillator frequency where possible.
  The original clocks become one-cycle enables `ce_<pin>`.
- Models never generate or gate clocks.
- Ports carry the data sheet pin names in lower case, with `_n` for active-low pins.
- Bidirectional pins split into `_i`, `_o` and `_oe`. No tristates inside a model.
- Parameters are UPPER_CASE, with defaults equal to the reproduced part.

## Interface stability

- The `interface` counter in `component.toml` goes up on any change of ports or parameters.
  Planned: `interface.lock` records it, and the lint will compare both (not built yet).
- A change of interface reaches the consumers in order: a release of this repo, then each consumer's
  change that moves its pin and adapts its glue, down the chain of pins.
- A fidelity fix is a minor release with a record ID, a CHANGELOG line and a test.
