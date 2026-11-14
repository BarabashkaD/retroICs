# Conventions

Naming, the IC folder contract, record IDs, ports, clock enables and interface stability. The agent
rules are in `docs/agents/global.md`.

## IC folder contract

```text
ics/intel/8255a/
  component.toml      (planned) manifest: identity, reproduces, equivalents, files, deps, tests,
                      negatives
  README.md           vendor, part, function, pinout, model status, equivalents table
  record.md           data sheet record: PPI-n statements, SILENT items (choice and basis)
  equivalents.md      Soviet ICs and second sources: compatibility level, sources, differences
  implementation.md   model notes PPI-Mn (what is modelled, ce mapping, limits); vendor errata PPI-En
  AGENTS.md           scope, files, commands, record prefix, checklist, pitfalls
  datasheets/
    index.md          per source: ID, title, vendor, document number, edition, pages used,
                      provenance, licence check result, SHA-256
    *.pdf
  rtl/intel_8255a.v   (planned) top module <vendor>_<part>; SPDX header
  tb/  faults/*.patch  golden/  interface.lock      (planned)
```

- Today an IC folder holds the markdown files and `datasheets/index.md`. `component.toml`, `rtl/`,
  `tb/`, `faults/`, `golden/` and `interface.lock` are planned: they come when the models are
  imported.
- Skeletons of the markdown files: `docs/templates/ic/`.
- `equivalents.md` says "No differences known as of <date> (<version>)" until a difference is found;
  before the first release the version reads "unreleased".
- A docs-only folder has no `rtl/`, `tb/` or `faults/`; its README names where the part is modelled.

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

- Every manifest (planned, `component.toml`) says which physical part the model reproduces (`reproduces`). The default is the
  vendor part.
- A model written by the owner may take a `VARIANT` parameter for a variant, when every value is tied
  to D-items and tests. A second source with a different design gets its own folder with
  `variant_of`.
- Compatibility levels in `equivalents.md`: `drop-in`, `function`, `partial` (the differences are
  D-items), `unverified`. A `drop-in` or `function` level cites a source. Each D-item names the test
  that shows the difference, when one exists.

### The 8080

- When the models are imported, `ics/intel/8080a` holds the die-derived КР580ВМ80А model,
  byte-identical in `rtl/upstream/`, and a thin wrapper `intel_8080a` that gives the family-wide
  name (planned).
- No `VARIANT`. The manifest says `reproduces = "k580vm80a"`, and the README header says so. The
  known differences from the Intel 8080A are CPU-D items, listed as model limits.
- The wrapper instantiates `k580vm80a core(...)`. Every hierarchical path into the CPU (TBs,
  power-up files) goes through `.core`. Icarus stops at an unresolved hierarchical name, so a TB that
  still uses an old path fails loudly.
- If an Intel-accurate model appears, it replaces the wrapper's contents; consumers keep the name.

### The 8224 and the SN7492

- `ics/intel/8224/` (КР580ГФ24) and `ics/ti/sn7492/` (К155ИЕ4) are docs only: record, data sheets,
  equivalents.
- Both are modelled inside the RK86 clock block `rk86_clocks16` (in the Karabas fork until the RTL
  is imported, then in `retroMachines`). Their README states it. Each gets its own RTL only when a second machine needs it.
- Their board-wiring items are listed one by one in `docs/record-ids.md` with their home in the RK86
  board record.

## Record IDs

- `docs/record-ids.md` maps every prefix to its home file, in whichever repo that is. Existing IDs
  keep their prefix and number forever. When the items of one prefix split across files, the
  registry lists those IDs one by one. New items take the prefix of their home file.
- Pattern: `[A-Z][A-Z0-9]{1,9}(?:-DEV)?-[DEM]?\d+`.
- Kinds of item in an IC record: `<P>-n` data sheet statement (SILENT marked), `<P>-Dn` difference,
  `<P>-En` vendor erratum, `<P>-Mn` model note.
- An item is defined by the first cell of a table row in its home file. Prose and lists only refer
  to it.
- Differences between two editions of one vendor's data sheet stay in that IC's `record.md` under
  "Edition differences", as table rows (`PPI-D1`..`PPI-D6`: [C78] against [D8255]).
- Board items of a machine use a machine prefix (`RK86-n`, `MIK-n`, `UT88-n`, `APG-n`); the RK86's
  existing board prefixes (VID, GLUE, MEM, TAPE, SND, ROMD) keep their names.
- A new IC registers a new prefix (for example PIT for the 8253).
- Project deviations use `<PROJECT>-DEV-n`: `RK86M-DEV-n` in `retroMachines`, `RKPOCKET-DEV-n` in
  the Pocket repo.
- Source IDs are in brackets (`[C78]`) and are listed in `docs/sources.md`; they are not record IDs.

## Ports, clocks and parameters

- One system clock `clk` per machine, at the original master oscillator frequency where possible
  (16 MHz for the RK86). The original clocks become one-cycle enables `ce_<pin>`.
- Models never generate or gate clocks.
- Ports carry the data sheet pin names in lower case, with `_n` for active-low pins.
- Bidirectional pins split into `_i`, `_o` and `_oe`. No tristates inside a model.
- Parameters are UPPER_CASE, with defaults equal to the reproduced part.

## Interface stability

- Planned, when the models are imported: the `interface` counter in `component.toml` goes up on any
  change of ports or parameters, `interface.lock` records it, and the lint will compare both (not
  built yet).
- A change of interface reaches the consumers in order: a `retroICs` release, then a `retroMachines`
  PR that bumps the pin and adapts the glue, then the platform PR.
- A fidelity fix is a minor release with a record ID, a CHANGELOG line and a test.
