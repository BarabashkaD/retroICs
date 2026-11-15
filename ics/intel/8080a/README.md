# Intel 8080A microprocessor

## Function

8-bit microprocessor, the CPU of the 8080 family.

## Pinout

The pins with their data sheet behaviour and timings: `record.md` (CPU-n). Pin descriptions:
[C78] 11-12, [D8080N] p. 5.

## Model status

`rtl/upstream/k580vm80a.v` is the die-derived КР580ВМ80А model by Vslav (1801BM1), 2014
(`reproduces = "k580vm80a"`; `docs/conventions.md`, "The 8080"). Taken from
MiSTer-devel/Apogee_MiSTer `rtl/k580vm80a.v` at `4b37da2`, line endings changed from CR LF to LF,
otherwise unchanged; its SHA-256 here is
`75919c8cf5fddace79725e11e26aab710ca5eaf3f2575ebd8282d81f15a38bac` (`tools/tests/test_headers.py`
checks it). A later version by the author: https://github.com/1801BM1/vm80a.

`rtl/intel_8080a.v` is the owner's wrapper, written here (module `intel_8080a`, the same ports,
the model as instance `core`); manifest `component.toml`; no TB of its own yet.

## Equivalents

| Part | Transliteration | Level |
|---|---|---|
| КР580ВМ80А | `kr580vm80a` | unverified |

Details: `equivalents.md`.

## Sources

`record.md` (items), `datasheets/index.md` (documents), `docs/sources.md` (source IDs).

## Licence

- `rtl/upstream/k580vm80a.v`: CC BY 3.0 (`LICENSES/CC-BY-3.0.txt`), Vslav (1801BM1); the
  author's notice in its header kept as it is.
- `rtl/intel_8080a.v` and `component.toml`: BSD-3-Clause, the owner.
- The docs of this folder (the Markdown files): CC BY 4.0, the owner (`NOTICE`).
- Data sheets: third-party documents with their own status (`datasheets/index.md`).
