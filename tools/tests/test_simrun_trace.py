# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""simrun trace: record ID -> tests -> the faults that kill it -> status."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))
import check_records as cr  # noqa: E402
from simrun import manifest, trace  # noqa: E402
from simrun.trace import TraceError, TraceRow  # noqa: E402

BOARD = "retroComputersDocs/computers/demo/board.md"
REGISTRY = """# Record IDs

| Prefix | Home | Status | IDs |
|---|---|---|---|
| PPI | retroICs/ics/intel/8255a/record.md | here | |
| CRT | retroICs/ics/intel/8275/record.md | here | |
| OSC | %s | external | OSC-11 |
| BRD | %s | pending | |
""" % (BOARD, BOARD)

PPI_RECORD = """# 8255A

## Items (PPI-n)

| ID | Function | Behaviour | Source |
|---|---|---|---|
| PPI-1 | Reset | x | [C78] |
| PPI-2 | Mode set | x | [C78] |
| PPI-3 | Drive levels | x | [C78] |
| PPI-4 | Port C | x | [C78] |
| PPI-5 | Mode 1 input | x | [C78] |

## SILENT (PPI)

- PPI-2: a repeated mode set,
  continued.
- PPI-1 / PPI-4: (the line names the ID; tests win over SILENT)

## Untestable (PPI)

- PPI-3: an electrical value; no logic model shows it.

## Assumptions checked

- PPI-5: not SILENT (another section).
"""

CRT_RECORD = """# 8275

| ID | Function |
|---|---|
| CRT-22 | DRQ at WR |
| CRT-23 | Byte at WR |

## SILENT (CRT)

- CRT-23: whether CS takes part.
"""


def write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def make(top: Path, machine_ids=("CRT-22",), negative_ids=("CRT-22",)):
    """retroICs (registry, 8255A, 8275) and consumer (demo) under top. Returns (ics, machines)."""
    ics = top / "retroICs"
    machines = top / "consumer"
    write(ics / "docs" / "record-ids.md", REGISTRY)
    write(ics / "ics/intel/8255a/record.md", PPI_RECORD)
    write(ics / "ics/intel/8275/record.md", CRT_RECORD)
    for f in ("rtl/ppi.v", "tb/tb_vv55.v", "faults/vv55_ibf.patch", "faults/vv55_bsr.patch"):
        write(ics / "ics/intel/8255a" / f)
    for f in ("rtl/crt.v", "faults/vg75_drq_held.patch"):
        write(ics / "ics/intel/8275" / f)
    write(ics / "ics/intel/8255a/component.toml", """[component]
name = "intel/8255a"
kind = "ic"
title = "Intel 8255A"
reproduces = "k580vv55a"
fidelity = "datasheet"
interface = 1
record_prefix = "PPI"

[rtl]
top = "k580vv55"
files = ["rtl/ppi.v"]

[[test]]
name = "vv55"
tier = "quick"
top = "tb_vv55"
files = ["tb/tb_vv55.v"]
ids = ["PPI-4"]

[[negative]]
test = "vv55"
fault = "faults/vv55_ibf.patch"
expect = "ERROR: vv55: mode 1 input"
ids = ["PPI-1", "PPI-4"]

[[negative]]
test = "vv55"
fault = "faults/vv55_bsr.patch"
expect = "ERROR: vv55: bsr set"
""")
    write(ics / "ics/intel/8275/component.toml", """[component]
name = "intel/8275"
kind = "ic"
title = "Intel 8275"
reproduces = "k580vg75"
fidelity = "datasheet"
interface = 1
record_prefix = "CRT"

[rtl]
top = "k580vg75"
files = ["rtl/crt.v"]
""")
    for f in ("rtl/m.v", "tb/tb_m.v"):
        write(machines / "machines/demo" / f)
    write(machines / "machines/demo/component.toml", """[component]
name = "machines/demo"
kind = "machine"
title = "Demo machine"
reproduces = "demo"
fidelity = "board"
interface = 1

[rtl]
top = "demo_top"
files = ["rtl/m.v"]
depends = ["intel/8255a", "intel/8275"]

[[test]]
name = "run1"
tier = "standard"
top = "tb_m"
files = ["tb/tb_m.v"]
ids = %s

[[negative]]
test = "run1"
fault = "intel/8275:vg75_drq_held"
expect = "ERROR: hold periods"
ids = %s
""" % (list_toml(machine_ids), list_toml(negative_ids)))
    return ics, machines


def list_toml(ids) -> str:
    return "[%s]" % ", ".join('"%s"' % i for i in ids)


def load_all(ics, machines):
    return [manifest.resolve(n, [machines, ics])
            for n in ("intel/8255a", "intel/8275", "machines/demo")]


class Trace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.top = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def matrix(self, comps, ics, external=None):
        rows = trace.matrix(comps, external, registry=ics / "docs" / "record-ids.md")
        self.assertIsInstance(rows, list)
        return {r.id: r for r in rows}, [r.id for r in rows], rows.notes

    def test_trace_status(self):
        ics, machines = make(self.top)
        rows, order, notes = self.matrix(load_all(ics, machines), ics)
        ppi = "retroICs/ics/intel/8255a/record.md"
        crt = "retroICs/ics/intel/8275/record.md"
        self.assertEqual(order, ["CRT-22", "CRT-23", "PPI-1", "PPI-2", "PPI-3", "PPI-4", "PPI-5"])
        self.assertEqual(rows["PPI-1"], TraceRow("PPI-1", ppi, ["intel/8255a:vv55"],
                                                 ["intel/8255a:vv55_ibf"], "tested"))
        self.assertEqual(rows["PPI-2"], TraceRow("PPI-2", ppi, [], [], "SILENT"))
        self.assertEqual(rows["PPI-3"], TraceRow("PPI-3", ppi, [], [], "untestable"))
        self.assertEqual(rows["PPI-4"], TraceRow("PPI-4", ppi, ["intel/8255a:vv55"],
                                                 ["intel/8255a:vv55_ibf"], "tested"))
        self.assertEqual(rows["PPI-5"], TraceRow("PPI-5", ppi, [], [], "open"))
        # a dependency fault of the machine kills an 8275 item: named by its owner
        self.assertEqual(rows["CRT-22"], TraceRow("CRT-22", crt, ["machines/demo:run1"],
                                                  ["intel/8275:vg75_drq_held"], "tested"))
        self.assertEqual(rows["CRT-23"].status, "SILENT")
        self.assertEqual(notes, [])

    def test_cited_ids_of_a_record_not_given(self):
        # only the machine: its CRT ID is looked up in the 8275 record of the registry's repo
        ics, machines = make(self.top)
        rows, order, _ = self.matrix([manifest.resolve("machines/demo", [machines, ics])], ics)
        self.assertEqual(order, ["CRT-22"])
        self.assertEqual(rows["CRT-22"].status, "tested")

    def test_undefined_ids_fail(self):
        for ids, word in ((["CRT-99"], "CRT-99"), (["ZZZ-1"], "ZZZ-1")):
            with self.subTest(word):
                top = self.top / word
                ics, machines = make(top, machine_ids=ids)
                with self.assertRaises(TraceError) as cm:
                    self.matrix(load_all(ics, machines), ics)
                self.assertTrue(any(word in p for p in cm.exception.problems), cm.exception.problems)

    def test_trace_without_external_root(self):
        ics, machines = make(self.top, machine_ids=("OSC-11", "BRD-3"))
        rows, _, notes = self.matrix(load_all(ics, machines), ics)
        self.assertEqual(rows["OSC-11"], TraceRow("OSC-11", BOARD, ["machines/demo:run1"], [],
                                                  "tested"))
        self.assertEqual(rows["BRD-3"].home, BOARD)
        self.assertEqual(len(notes), 1)
        self.assertIn("IDs of retroComputersDocs not checked", notes[0])
        # with its root: an undefined board ID fails, a defined one passes without the note
        docs = self.top / "retroComputersDocs"
        write(docs / "computers/demo/board.md", "| OSC-12 | x |\n")
        with self.assertRaises(TraceError) as cm:
            self.matrix(load_all(ics, machines), ics, external={"retroComputersDocs": docs})
        self.assertTrue(any("OSC-11" in p for p in cm.exception.problems))
        write(docs / "computers/demo/board.md", "| OSC-11 | x |\n")
        _, _, notes = self.matrix(load_all(ics, machines), ics, external={"retroComputersDocs": docs})
        self.assertEqual(notes, [])
        with self.assertRaises(TraceError) as cm:
            self.matrix(load_all(ics, machines), ics,
                        external={"retroComputersDocs": self.top / "nope"})
        self.assertTrue(any("external root" in p for p in cm.exception.problems))

    def test_note_with_two_arguments(self):
        # matrix(components, external) as the interface names it: the note is on the result
        ics, machines = make(self.top, machine_ids=("OSC-11",))
        comps = load_all(ics, machines)
        with mock.patch.object(trace, "REGISTRY", ics / "docs" / "record-ids.md"):
            rows = trace.matrix(comps, None)
        self.assertEqual(rows.notes, [cr.not_checked_note("retroComputersDocs")])
        self.assertEqual([r.id for r in rows if r.id.startswith("OSC")], ["OSC-11"])

    def test_docs_only_ic(self):
        # an ic without [rtl] (a chip documented without a model): found by trace without names, its record traced
        ics, machines = make(self.top)
        write(ics / "ics/acme/clock/record.md",
              "| ID | Function |\n|---|---|\n| OSC-1 | Clock |\n| OSC-2 | Phases |\n\n"
              "## SILENT (OSC)\n\n- OSC-1: the oscillator edge.\n")
        write(ics / "ics/acme/clock/component.toml",
              '[component]\nname = "acme/clock"\nkind = "ic"\ntitle = "Acme clock"\n'
              'reproduces = "aclock"\nfidelity = "datasheet"\ninterface = 1\nrecord_prefix = "OSC"\n')
        write(ics / "docs" / "record-ids.md",
              REGISTRY.replace("| OSC | %s |" % BOARD,
                               "| OSC | retroICs/ics/acme/clock/record.md | here | |\n| OSC | %s |"
                               % BOARD))
        env = dict(os.environ, PYTHONPATH=str(TOOLS))
        cmd = [sys.executable, "-B", "-m", "simrun", "trace", "--search", str(machines),
               "--search", str(ics), "--registry", str(ics / "docs" / "record-ids.md")]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=self.top, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = r.stdout.splitlines()
        self.assertIn("| OSC-1 | retroICs/ics/acme/clock/record.md | | | SILENT |", lines)
        self.assertIn("| OSC-2 | retroICs/ics/acme/clock/record.md | | | open |", lines)
        self.assertIn("| PPI-5 | retroICs/ics/intel/8255a/record.md | | | open |", lines)

    def test_cli(self):
        ics, machines = make(self.top)
        env = dict(os.environ, PYTHONPATH=str(TOOLS))
        cmd = [sys.executable, "-B", "-m", "simrun", "trace", "--search", str(machines),
               "--search", str(ics), "--registry", str(ics / "docs" / "record-ids.md")]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=self.top, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], "| ID | Home | Tests | Killing faults | Status |")
        self.assertIn("| CRT-22 | retroICs/ics/intel/8275/record.md | machines/demo:run1 | "
                      "intel/8275:vg75_drq_held | tested |", lines)
        self.assertIn("| PPI-5 | retroICs/ics/intel/8255a/record.md | | | open |", lines)


if __name__ == "__main__":
    unittest.main()
