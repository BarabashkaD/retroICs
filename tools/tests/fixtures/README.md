# Test fixtures

Test inputs only: the tests read these files (and simulate the Verilog of `simrun/` with Icarus
Verilog); no Python file here is imported or run.

| File | What | Licence |
|---|---|---|
| `component-example.toml` | The `component.toml` example of the owner's repository layout design note (not published), as written there (SHA-256 `55ce20d1e2499edc66d6e57d87102898afbdb5a4892666e7b1213f5c9a5358ba`). The tests apply two changes before loading it: `patch` becomes `fault`, `plusargs = []` becomes `plusargs = {}`. | BSD-3-Clause (`LICENSE`) |
| `simrun/` | Two small repos for `test_simrun_run.py`, written for the tests: `retroICs/ics/acme/counter` (a counter IC, its TB, three faults made with `git diff` against `simrun/retroICs`) and `consumer/demo/ticker` (a block that depends on `acme/counter`, with a fault of that dependency). The tests copy them into a temporary folder. | BSD-3-Clause (`LICENSE`); SPDX lines in the `.v` and `.toml` files, none in the `.patch` files (`git diff` output as it is) |

`component-example.toml` has no SPDX line: it is kept byte for byte as its source has it, and a
header would change the bytes the test pins (`test_example_fixture_as_written`). Its licence is
recorded here instead, and `tools/tests/test_headers.py` lists it as exempt from the header rule.
