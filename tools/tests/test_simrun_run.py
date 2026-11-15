# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""simrun run: the pass rule, the fault rules, data files, the summary.

The simulation tests need Icarus Verilog 13.0 (IVERILOG, else iverilog on PATH); without it they
skip, unless SIMRUN_REQUIRE_IVERILOG=1 (CI job quick), which turns the missing tool into a failure.
They copy the fixture repos (tools/tests/fixtures/simrun/) into a temporary folder.
"""
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))
from simrun import __main__ as simrun_main  # noqa: E402
from simrun import hexdata, manifest, negative  # noqa: E402
from simrun import run as simrun_run  # noqa: E402
from simrun.manifest import DataFile  # noqa: E402

FIX = TOOLS / "tests" / "fixtures" / "simrun"
AT = "@"
NOREPLY = "12345+someone" + AT + "users.noreply.github.com"
COUNTER_RTL = "ics/acme/counter/rtl/acme_counter.v"
CE_GEN = "ics/acme/counter/tb/acme_ce_gen.v"


def find_iverilog():
    p = os.environ.get("IVERILOG") or "iverilog"
    return shutil.which(p)


IVERILOG = find_iverilog()
REQUIRE = os.environ.get("SIMRUN_REQUIRE_IVERILOG") == "1"
needs_iverilog = unittest.skipUnless(
    IVERILOG, "Icarus Verilog not found (IVERILOG or PATH); set SIMRUN_REQUIRE_IVERILOG=1 to fail")


def git(repo: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": NOREPLY,
                "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": NOREPLY})
    r = subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True, text=True,
                       check=True)
    return r.stdout.strip()


class Tree(unittest.TestCase):
    """The fixture repos in a temporary folder: <tmp>/retroICs, <tmp>/consumer."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.ics = self.tmp / "retroICs"
        self.machines = self.tmp / "consumer"
        shutil.copytree(FIX / "retroICs", self.ics)
        shutil.copytree(FIX / "consumer", self.machines)
        self.out = self.tmp / "build" / "simrun"
        self.search = [self.ics, self.machines]
        self.lines: list[str] = []

    def edit(self, path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, (path.name, old))
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

    def counter_toml(self) -> Path:
        return self.ics / "ics" / "acme" / "counter" / "component.toml"

    def counter(self):
        return manifest.load(self.counter_toml())

    def ticker(self):
        return manifest.load(self.machines / "demo" / "ticker" / "component.toml")

    def run_sim(self, comps, negative=False, tier="full", replace=None, params=None, out=None,
                jobs=1, **kw):
        return simrun_run.run(comps, tier, jobs, negative, out or self.out, replace or {},
                              params or {}, search=self.search, iverilog=IVERILOG,
                              log=self.lines.append, **kw)

    def one(self, results, fault=None):
        hits = [r for r in results if r.fault == fault] if fault else list(results)
        self.assertEqual(len(hits), 1, [(r.component, r.test, r.fault) for r in results])
        return hits[0]

    def fault(self, summary, name):
        return self.one(summary.faults, name)

    def log_text(self, summary, result) -> str:
        self.assertIsNotNone(result.log)
        return (summary.run_dir / result.log).read_text(encoding="utf-8")


class Rules(unittest.TestCase):
    """The runner's rules; no simulator needed."""

    def test_iverilog_present_when_required(self):
        if REQUIRE:
            self.assertIsNotNone(IVERILOG, "SIMRUN_REQUIRE_IVERILOG=1 but no Icarus Verilog")

    def test_pass_rule(self):
        ok = simrun_run.passes
        self.assertTrue(ok(0, "INFO: x\nPASS: t\n"))
        self.assertTrue(ok(0, "  PASS: indented\n"))
        self.assertFalse(ok(1, "PASS: t\n"))                       # vvp exit code
        self.assertFalse(ok(0, "INFO: no pass line\n"))
        self.assertFalse(ok(0, "PASS: t\n  ERROR: late\n"))        # an ERROR line, stripped
        self.assertFalse(ok(0, "PASS: t\nsome FATAL here\n"))     # FATAL anywhere on a line
        self.assertTrue(ok(0, "PASS: t\nINFO: no ERROR prefix\n"))  # ERROR not at the start

    def test_first_error(self):
        fe = simrun_run.first_error
        self.assertIsNone(fe("PASS\nINFO: x\n"))
        self.assertEqual(fe("INFO\n  ERROR: a\nERROR: b\n"), "ERROR: a")
        self.assertEqual(fe("x FATAL: y\nERROR: b\n"), "x FATAL: y")

    def test_contains(self):
        c = simrun_run.contains
        self.assertTrue(c("ERROR: a 12 b", "a * b"))
        self.assertTrue(c("ERROR: a.b", "a.b"))
        self.assertFalse(c("ERROR: axb", "a.b"))                  # '.' is literal
        self.assertTrue(c("ERROR: (x) [y]", "(x) [y]"))
        self.assertFalse(c("ERROR: b 12 a", "a * b"))

    def test_wildcard(self):
        """Expects with '*' (as a machine's faults of the 8275 use them) match their errors with
        any number in place of '*', and only those."""
        stars = [("burst_count", "ERROR: burst length: frame * fill: DRQ again after transfer 8 of "
                                 "burst 0, expected a burst of 8"),
                 ("burst_space", "ERROR: burst space: frame * fill: DRQ back * ce16 after the WR "
                                 "rise of transfer 8 of burst 0"),
                 ("restart_late", "ERROR: dma byte: frame *: its first DMA byte (the row 0 fill) "
                                  "is transfer")]
        for name, expect in stars:
            with self.subTest(name):
                line = expect.replace("*", "1234")
                self.assertTrue(simrun_run.contains(line, expect))
                self.assertTrue(simrun_run.contains("prefix " + line + " suffix", expect))
                self.assertFalse(simrun_run.contains(line[:-1] + "#", expect))  # the last part
                self.assertFalse(simrun_run.contains(line.replace("ERROR", "WARN", 1), expect))

    def test_version(self):
        v = simrun_run.version_of
        self.assertEqual(v("Icarus Verilog version 13.0 (stable) (v13_0)\n\nCopyright"), "13.0")
        self.assertEqual(v("Icarus Verilog version 12.0 (stable) ()\n"), "12.0")
        self.assertIsNone(v("command not found\n"))

    def test_parse_replace_and_param(self):
        r = simrun_run.parse_replace(["a/b.v=c.v,d/e.v", "x.v=y.v"])
        self.assertEqual(r, {"a/b.v": ["c.v", "d/e.v"], "x.v": ["y.v"]})
        self.assertEqual(simrun_run.parse_param(["N=4", "S=ab"]), {"N": "4", "S": "ab"})
        for bad in (["a.v"], ["a.v="], ["=b.v"]):
            with self.assertRaises(simrun_run.RunError):
                simrun_run.parse_replace(bad)
        for bad in (["N"], ["1N=2"], ["N="]):
            with self.assertRaises(simrun_run.RunError):
                simrun_run.parse_param(bad)


class NegativeApi(unittest.TestCase):
    """test_negative_api_compat: what the callers of negative.py rely on: copy the files, then apply
    at the repository root, with the ValueError message."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()

    def test_negative_api_compat(self):
        self.assertEqual(list(inspect.signature(negative.apply_patch).parameters),
                         ["root", "copy_root", "patch"])
        self.assertEqual(list(inspect.signature(negative.patched_files).parameters), ["patch"])
        patch = FIX / "retroICs" / "ics" / "acme" / "counter" / "faults" / "count_stuck.patch"
        self.assertEqual(negative.patched_files(str(patch)), [COUNTER_RTL])
        # the callers' layout: copies under <root>/build/.../copy, root a git work tree
        root = self.tmp / "repo"
        shutil.copytree(FIX / "retroICs", root)
        git(root, "init", "-q")
        copy_root = root / "build" / "sim" / "t" / "neg_count_stuck" / "copy"
        dst = copy_root / COUNTER_RTL
        dst.parent.mkdir(parents=True)
        shutil.copyfile(root / COUNTER_RTL, dst)
        negative.apply_patch(str(root), str(copy_root), str(patch))
        self.assertIn("q <= q;", dst.read_text(encoding="utf-8"))
        self.assertIn("q <= q + 1'b1;", (root / COUNTER_RTL).read_text(encoding="utf-8"))
        # applied twice: the copy no longer matches; ValueError names the patch
        with self.assertRaises(ValueError) as e:
            negative.apply_patch(str(root), str(copy_root), str(patch))
        self.assertIn("patch %s does not apply: " % patch, str(e.exception))
        # outside a git work tree, root = copy_root
        bare = self.tmp / "bare" / "copy"
        (bare / COUNTER_RTL).parent.mkdir(parents=True)
        shutil.copyfile(FIX / "retroICs" / COUNTER_RTL, bare / COUNTER_RTL)
        negative.apply_patch(str(bare), str(bare), str(patch))
        self.assertIn("q <= q;", (bare / COUNTER_RTL).read_text(encoding="utf-8"))


class HexData(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()

    def bin(self, name, data: bytes) -> Path:
        p = self.tmp / name
        p.write_bytes(data)
        return p

    def test_data_hex(self):
        src = self.bin("rom.bin", bytes([0x00, 0x12, 0xAB, 0xFF]))
        dst = self.tmp / "rom.hex"
        self.assertEqual(hexdata.write_hex(src, dst, sizes=(4,), pad_to=8), 8)
        self.assertEqual(dst.read_bytes(), b"00\n12\nab\nff\nff\nff\nff\nff\n")
        # no padding, any size
        self.assertEqual(hexdata.write_hex(src, dst), 4)
        self.assertEqual(dst.read_bytes(), b"00\n12\nab\nff\n")
        # a larger image than pad_to stays as it is
        self.assertEqual(hexdata.write_hex(src, dst, sizes=(2, 4), pad_to=2), 4)
        # size check
        short = self.bin("short.bin", b"\x01\x02\x03")
        with self.assertRaises(hexdata.HexError) as e:
            hexdata.write_hex(short, dst, sizes=(4, 8))
        self.assertEqual(str(e.exception), "short.bin is 3 bytes, expected 4 or 8")
        # write_hexfiles: <prefix><name>.hex in out_dir, {name: file name}
        made = hexdata.write_hexfiles({"bios": DataFile(src, (4,), 0)}, self.tmp, prefix="p_")
        self.assertEqual(made, {"bios": "p_bios.hex"})
        self.assertEqual((self.tmp / "p_bios.hex").read_bytes(), b"00\n12\nab\nff\n")


@needs_iverilog
class Simulate(Tree):
    def test_pass(self):
        s = self.run_sim([self.counter()])
        t = self.one(s.tests)
        self.assertEqual((t.component, t.test, t.status, t.first_error),
                         ("acme/counter", "count", "PASS", None))
        self.assertEqual(s.faults, [])
        self.assertEqual(s.exit_code, 0)
        self.assertEqual(t.log, "acme/counter/count/vvp.log")
        self.assertIn("PASS: counter", self.log_text(s, t))
        self.assertIn("acme/counter:count: PASS", self.lines)
        # without --keep the .vvp goes, the log stays
        self.assertEqual(list((s.run_dir / "acme" / "counter" / "count").glob("*.vvp")), [])
        k = self.run_sim([self.counter()], keep=True)
        self.assertEqual(len(list((k.run_dir / "acme" / "counter" / "count").glob("*.vvp"))), 1)
        self.assertNotEqual(k.run_dir, s.run_dir)

    def test_fail_on_error_line(self):
        self.edit(self.counter_toml(), "params = { N = 10 }",
                  "params = { N = 10 }\nplusargs = { inject_error = 1 }")
        s = self.run_sim([self.counter()])
        t = self.one(s.tests)
        self.assertEqual(t.status, "FAIL")
        self.assertEqual(t.first_error, "ERROR: counter: injected by +inject_error")
        self.assertIn("PASS: counter", self.log_text(s, t))   # PASS printed, still a failure
        self.assertEqual(s.exit_code, 1)

    def test_first_error_rule(self):
        # the expected text is on the second ERROR line: without "anywhere" the fault is MISSED
        self.edit(self.counter_toml(), 'expect = "ERROR: counter: changed without ce"\nmatch = "anywhere"\n',
                  'expect = "ERROR: counter: changed without ce"\n')
        s = self.run_sim([self.counter()], negative=True)
        f = self.fault(s, "acme/counter:ce_ignored")
        self.assertEqual(f.status, "MISSED")
        self.assertEqual(f.first_error, "ERROR: counter: count 23 after 10 ce, expected 10")
        self.assertEqual(f.match, "first")
        self.assertIn("ERROR: counter: changed without ce", self.log_text(s, f))
        self.assertEqual(s.exit_code, 1)
        self.assertTrue(any("ce_ignored MISSED" in l for l in self.lines), self.lines)

    def test_anywhere(self):
        s = self.run_sim([self.counter()], negative=True)
        self.assertEqual(self.one(s.tests).status, "PASS")
        st = {f.fault: (f.status, f.first_error) for f in s.faults}
        self.assertEqual(st, {
            "acme/counter:count_stuck": ("CAUGHT", "ERROR: counter: count 0 after 10 ce, expected 10"),
            "acme/counter:ce_ignored": ("CAUGHT", "ERROR: counter: count 23 after 10 ce, expected 10"),
            "acme/counter:ce_gen_never": ("CAUGHT", "FATAL: counter: timeout, 0 of 10 ce"),
        })
        self.assertEqual(self.fault(s, "acme/counter:ce_ignored").match, "anywhere")
        self.assertEqual(s.exit_code, 0)
        # the patched copy is in the fault's folder; the source is untouched
        copy = s.run_dir / "acme" / "counter" / "count" / "neg_count_stuck" / "copy" / COUNTER_RTL
        self.assertFalse(copy.exists())                     # removed without --keep
        self.assertIn("q <= q + 1'b1;", (self.ics / COUNTER_RTL).read_text(encoding="utf-8"))

    def test_jobs(self):
        s = self.run_sim([self.counter()], negative=True, jobs=4)
        self.assertEqual([f.status for f in s.faults], ["CAUGHT"] * 3)
        self.assertEqual([f.fault for f in s.faults], ["acme/counter:count_stuck",
                                                       "acme/counter:ce_ignored",
                                                       "acme/counter:ce_gen_never"])

    def test_dependency_fault(self):
        git(self.machines, "init", "-q")
        git(self.machines, "add", "-A")
        git(self.machines, "commit", "-q", "-m", "fixture")
        head = git(self.machines, "rev-parse", "HEAD")
        out = self.machines / "build" / "simrun"
        s = self.run_sim([self.ticker()], negative=True, out=out, keep=True)
        self.assertEqual(self.one(s.tests).status, "PASS")
        f = self.one(s.faults)
        self.assertEqual((f.component, f.test, f.fault, f.status),
                         ("demo/ticker", "tick", "acme/counter:count_stuck", "CAUGHT"))
        self.assertEqual(f.first_error, "ERROR: ticker: count 0 after 20 clocks, expected 10")
        # the dependency's file, copied by its path in its own repo, patched there
        copy = (s.run_dir / "demo" / "ticker" / "tick" / "neg_acme_counter_count_stuck" / "copy"
                / COUNTER_RTL)
        self.assertIn("q <= q;", copy.read_text(encoding="utf-8"))
        self.assertIn("q <= q + 1'b1;", (self.ics / COUNTER_RTL).read_text(encoding="utf-8"))
        self.assertEqual(s.commit, head)
        data = json.loads(s.path.read_text(encoding="utf-8"))
        self.assertEqual(data["commit"], head)
        # the repos the components come from, relative to the checkout that holds the output
        self.assertEqual(data["repos"], {"../retroICs": None, ".": head})
        self.assertEqual(s.repos, data["repos"])

    def test_flags_from_dependencies(self):
        # the ticker without its own -g2005 compiles with its dependency's
        self.edit(self.machines / "demo" / "ticker" / "component.toml",
                  'iverilog_flags = ["-g2005"]\n', "")
        self.assertEqual(self.ticker().iverilog_flags, [])
        calls = []
        real = subprocess.run

        def spy(cmd, *a, **k):
            calls.append(list(cmd))
            return real(cmd, *a, **k)
        with mock.patch.object(simrun_run.subprocess, "run", side_effect=spy):
            s = self.run_sim([self.ticker()])
        self.assertEqual(self.one(s.tests).status, "PASS")
        compiles = [c for c in calls if "-s" in c and "-o" in c]
        self.assertEqual(len(compiles), 1)
        self.assertEqual(compiles[0][1], "-g2005")
        self.assertEqual(compiles[0].count("-g2005"), 1)

    def test_stale(self):
        self.edit(self.ics / COUNTER_RTL, "q <= q + 1'b1;", "q <= q + {{(WIDTH-1){1'b0}}, 1'b1};")
        s = self.run_sim([self.counter()], negative=True)
        f = self.fault(s, "acme/counter:count_stuck")
        self.assertEqual(f.status, "STALE")
        self.assertTrue(f.first_error.startswith("ERROR: fault acme/counter:count_stuck: patch "),
                        f.first_error)
        self.assertIn("does not apply", f.first_error)
        self.assertEqual(s.exit_code, 1)
        # a patch of a file the test does not compile: "not compiled in this test"
        d = self.ics / "ics" / "acme" / "counter"
        (d / "notes.txt").write_text("a\n", encoding="utf-8", newline="\n")
        (d / "faults" / "notes.patch").write_text(
            "diff --git a/ics/acme/counter/notes.txt b/ics/acme/counter/notes.txt\n"
            "--- a/ics/acme/counter/notes.txt\n+++ b/ics/acme/counter/notes.txt\n"
            "@@ -1 +1 @@\n-a\n+b\n", encoding="utf-8", newline="\n")
        with open(self.counter_toml(), "a", encoding="utf-8", newline="\n") as fh:
            fh.write('\n[[negative]]\ntest = "count"\nfault = "faults/notes.patch"\n'
                     'expect = "ERROR"\n')
        s = self.run_sim([self.counter()], negative=True)
        f = self.fault(s, "acme/counter:notes")
        self.assertEqual(f.status, "STALE")
        self.assertEqual(f.first_error, "ERROR: fault acme/counter:notes: "
                         "ics/acme/counter/notes.txt is not compiled in this test")

    def test_replace(self):
        alt = self.tmp / "alt"
        alt.mkdir()
        (alt / "alt_ce_gen.v").write_text(
            "module acme_ce_gen (input clk, input en, output ce);\n"
            "    alt_toggle t (.clk(clk), .en(en), .q(ce));\n"
            "    initial $display(\"INFO: alt ce gen\");\nendmodule\n", encoding="utf-8")
        (alt / "alt_toggle.v").write_text(
            "module alt_toggle (input clk, input en, output reg q);\n"
            "    initial q = 1'b0;\n    always @(posedge clk) q <= en ? ~q : 1'b0;\nendmodule\n",
            encoding="utf-8")
        replace = {str(self.ics / CE_GEN): [str(alt / "alt_ce_gen.v"), str(alt / "alt_toggle.v")]}
        s = self.run_sim([self.counter()], negative=True, replace=replace)
        t = self.one(s.tests)
        self.assertEqual(t.status, "PASS")
        self.assertIn("INFO: alt ce gen", self.log_text(s, t))
        st = {f.fault: f.status for f in s.faults}
        # the --replace rule: a fault that patches only a replaced file is skipped
        self.assertEqual(st, {"acme/counter:count_stuck": "CAUGHT",
                              "acme/counter:ce_ignored": "CAUGHT",
                              "acme/counter:ce_gen_never": "SKIPPED"})
        self.assertEqual(s.exit_code, 0)
        with self.assertRaises(simrun_run.RunError) as e:
            self.run_sim([self.counter()], replace={str(self.tmp / "none.v"): [str(alt / "alt_toggle.v")]})
        self.assertIn("none.v", str(e.exception))

    def test_param(self):
        s = self.run_sim([self.counter()], negative=True, params={"N": "4"})
        t = self.one(s.tests)
        self.assertEqual(t.status, "PASS")
        self.assertIn("INFO: counter: N = 4", self.log_text(s, t))
        self.assertEqual(self.fault(s, "acme/counter:count_stuck").first_error,
                         "ERROR: counter: count 0 after 4 ce, expected 4")
        # a parameter that no selected test declares is an error (a typo would pass silently)
        with self.assertRaises(simrun_run.RunError) as e:
            self.run_sim([self.counter()], params={"FRAMES": "2"})
        self.assertIn("FRAMES", str(e.exception))

    def test_data_hex(self):
        d = self.ics / "ics" / "acme" / "counter"
        (d / "tb" / "rom.bin").write_bytes(b"\x01\x02\x03\x04")
        self.edit(self.counter_toml(), "timeout_s = 120",
                  'timeout_s = 120\ndata = { rom = { path = "tb/rom.bin", sizes = [4], pad_to = 8 } }')
        s = self.run_sim([self.counter()])
        self.assertEqual(self.one(s.tests).status, "PASS")
        hexfile = s.run_dir / "acme" / "counter" / "count" / "rom.hex"
        self.assertEqual(hexfile.read_bytes(), b"01\n02\n03\n04\nff\nff\nff\nff\n")
        (d / "tb" / "rom.bin").write_bytes(b"\x01\x02\x03")
        s = self.run_sim([self.counter()])
        t = self.one(s.tests)
        self.assertEqual(t.status, "FAIL")
        self.assertEqual(t.first_error, "ERROR: data rom: rom.bin is 3 bytes, expected 4")

    def test_golden(self):
        d = self.ics / "ics" / "acme" / "counter"
        (d / "golden").mkdir()
        (d / "golden" / "count.txt").write_bytes(b"10\n")
        self.edit(self.counter_toml(), "timeout_s = 120",
                  'timeout_s = 120\ngolden = { file = "golden/count.txt", compare = "exact" }')
        self.assertEqual(self.one(self.run_sim([self.counter()]).tests).status, "PASS")
        s = self.run_sim([self.counter()], params={"N": "4"})
        t = self.one(s.tests)
        self.assertEqual((t.status, t.first_error),
                         ("FAIL", "ERROR: golden: count.txt differs from the golden file"))
        # another compare kind: the consumer's hook, else a failure
        self.edit(self.counter_toml(), 'compare = "exact"', 'compare = "frames"')
        t = self.one(self.run_sim([self.counter()]).tests)
        self.assertEqual((t.status, t.first_error),
                         ("FAIL", "ERROR: golden: no comparer for compare = frames "
                                  "(the consumer passes one)"))
        seen = []
        hook = {"frames": lambda produced, golden: (seen.append((produced.name, golden.name))
                                                    or (True, "INFO: frames ok\n"))}
        s = self.run_sim([self.counter()], comparers=hook)
        self.assertEqual(self.one(s.tests).status, "PASS")
        self.assertEqual(seen, [("count.txt", "count.txt")])

    def test_summary_schema(self):
        s = self.run_sim([self.counter(), self.ticker()], negative=True, tier="standard")
        self.assertEqual(s.path, s.run_dir / "summary.json")
        self.assertEqual(s.run_dir.parent, self.out)
        data = json.loads(s.path.read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"run_id", "commit", "repos", "iverilog", "tier", "negative",
                                     "tests", "faults"})
        self.assertEqual(len(data["repos"]), 2)
        for name, commit in data["repos"].items():
            self.assertFalse(os.path.isabs(name) or ":" in name or "\\" in name, name)
            self.assertIsNone(commit)                     # the temporary repos are no git work trees
        self.assertEqual(data["run_id"], s.run_dir.name)
        self.assertEqual(data["iverilog"], "13.0")
        self.assertIsNone(data["commit"])                 # the temporary folder is no git work tree
        self.assertEqual((data["tier"], data["negative"]), ("standard", True))
        self.assertEqual([(t["component"], t["test"]) for t in data["tests"]],
                         [("acme/counter", "count"), ("demo/ticker", "tick")])
        for t in data["tests"]:
            self.assertEqual(set(t), {"component", "test", "status", "first_error", "log"})
            self.assertEqual(t["status"], "PASS")
        self.assertEqual(len(data["faults"]), 4)
        for f in data["faults"]:
            self.assertEqual(set(f), {"component", "test", "fault", "status", "expect", "match",
                                      "first_error", "log"})
            self.assertIn(f["status"], ("CAUGHT", "MISSED", "STALE", "SKIPPED"))
            self.assertTrue(f["first_error"])
            self.assertFalse(Path(f["log"]).is_absolute())
        # tier quick leaves out the ticker (tier standard)
        q = self.run_sim([self.counter(), self.ticker()], tier="quick")
        self.assertEqual([(t.component, t.test) for t in q.tests], [("acme/counter", "count")])

    def test_cli(self):
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(self.tmp)
        buf = io.StringIO()
        argv = ["run", str(self.ics / "ics"), "--tier", "quick", "--negative",
                "--search", str(self.ics), "--param", "N=6", "--out", str(self.out)]
        if IVERILOG:
            argv += ["--iverilog", IVERILOG]
        with redirect_stdout(buf):
            code = simrun_main.main(argv)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("acme/counter:count: PASS", buf.getvalue())
        self.assertIn("acme/counter:count: negative acme/counter:count_stuck CAUGHT", buf.getvalue())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = simrun_main.main(argv[:2] + ["--param", "NOPE=1", "--search", str(self.ics)]
                                    + (["--iverilog", IVERILOG] if IVERILOG else []))
        self.assertEqual(code, 2)
        self.assertIn("ERROR: ", buf.getvalue())


class Cli(Tree):
    """No simulator needed: the version check, no components."""

    def test_version_mismatch_stops(self):
        with mock.patch.object(simrun_run, "iverilog_version", return_value="12.0"), \
                mock.patch.object(simrun_run.shutil, "which", side_effect=lambda p, **k: p):
            with self.assertRaises(simrun_run.ToolError) as e:
                simrun_run.run([self.counter()], "full", 1, False, self.out, {}, {},
                               search=self.search, iverilog="iverilog", log=self.lines.append)
            self.assertIn("13.0", str(e.exception))
            self.assertIn("12.0", str(e.exception))
            self.assertFalse(self.out.exists())          # nothing compiled, no run folder
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = simrun_main.main(["run", str(self.counter_toml()), "--search", str(self.ics),
                                         "--iverilog", "iverilog", "--out", str(self.out)])
        self.assertEqual(code, 2)
        self.assertIn("ERROR: Icarus Verilog 13.0 required", buf.getvalue())
        self.assertFalse(self.out.exists())

    def ticker_toml(self) -> Path:
        return self.machines / "demo" / "ticker" / "component.toml"

    def test_flags_merged(self):
        roots = self.search
        self.assertEqual(simrun_run.compile_flags(self.ticker(), roots), ["-g2005"])  # once
        self.edit(self.ticker_toml(), 'iverilog_flags = ["-g2005"]', 'iverilog_flags = ["-Wall"]')
        self.assertEqual(simrun_run.compile_flags(self.ticker(), roots), ["-g2005", "-Wall"])
        self.edit(self.ticker_toml(), 'iverilog_flags = ["-Wall"]', 'iverilog_flags = ["-g2012"]')
        with self.assertRaises(simrun_run.RunError) as e:
            simrun_run.compile_flags(self.ticker(), roots)
        self.assertEqual(str(e.exception), "demo/ticker: iverilog generations differ: "
                                           "acme/counter -g2005, demo/ticker -g2012")
        with self.assertRaises(simrun_run.RunError):           # before any tool or folder
            self.run_sim([self.ticker()])
        self.assertFalse(self.out.exists())

    def test_fault_folder_collision(self):
        # a local fault named like the folder of the dependency fault acme/counter:count_stuck
        d = self.machines / "demo" / "ticker"
        (d / "faults").mkdir()
        shutil.copyfile(self.ics / "ics" / "acme" / "counter" / "faults" / "count_stuck.patch",
                        d / "faults" / "Acme_counter_count_stuck.patch")
        with open(self.ticker_toml(), "a", encoding="utf-8", newline="\n") as fh:
            fh.write('\n[[negative]]\ntest = "tick"\nfault = "faults/Acme_counter_count_stuck.patch"\n'
                     'expect = "ERROR"\n')
        with self.assertRaises(simrun_run.RunError) as e:
            self.run_sim([self.ticker()], negative=True)
        self.assertEqual(str(e.exception), "demo/ticker:tick: faults acme/counter:count_stuck and "
                         "demo/ticker:Acme_counter_count_stuck share the folder "
                         "neg_Acme_counter_count_stuck")
        self.assertFalse(self.out.exists())

    def test_unexpected_errors_one_line(self):
        # an unreadable patch (not UTF-8): one ERROR line, exit 2, no traceback
        patch = self.ics / "ics" / "acme" / "counter" / "faults" / "count_stuck.patch"
        patch.write_bytes(b"\xff\xfe not text\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = simrun_main.main(["run", str(self.counter_toml()), "--negative",
                                     "--search", str(self.ics), "--out", str(self.out)])
        self.assertEqual(code, 2)
        lines = buf.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("ERROR: fault acme/counter:count_stuck: cannot read "
                                            "the patch: "), lines)
        # any other exception: one line with its type
        buf = io.StringIO()
        with mock.patch.object(simrun_run, "select", side_effect=RuntimeError("boom\n  two")), \
                redirect_stdout(buf):
            code = simrun_main.main(["run", str(self.counter_toml()), "--search", str(self.ics),
                                     "--out", str(self.out)])
        self.assertEqual(code, 2)
        self.assertEqual(buf.getvalue(), "ERROR: RuntimeError: boom two\n")
        self.assertFalse(self.out.exists())

    def test_missing_iverilog(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = simrun_main.main(["run", str(self.counter_toml()), "--search", str(self.ics),
                                     "--iverilog", str(self.tmp / "no-iverilog"),
                                     "--out", str(self.out)])
        self.assertEqual(code, 2)
        self.assertIn("ERROR: iverilog not found", buf.getvalue())

    def test_no_components(self):
        empty = self.tmp / "ics"
        empty.mkdir()
        (empty / "README.md").write_text("x\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = simrun_main.main(["run", str(empty), "--tier", "quick", "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertTrue(buf.getvalue().startswith("no components"), buf.getvalue())
        self.assertFalse(self.out.exists())
        # components, but none with a test at the tier
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = simrun_main.main(["run", str(self.machines / "demo"), "--tier", "quick",
                                     "--search", str(self.ics), "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertTrue(buf.getvalue().startswith("no components"), buf.getvalue())

    def test_this_repo_components(self):
        """What CI's `run ics --tier quick` runs (found here, not run): the TBs of the IC models;
        the 8080 has none of its own."""
        root = TOOLS.parent
        comps = simrun_main.components_at([str(root / "ics")], [root])
        self.assertEqual(sorted(c.name for c in comps),
                         ["intel/8080a", "intel/8255a", "intel/8257", "intel/8275"])
        self.assertEqual(sorted(t.name for _, t in simrun_run.select(comps, "quick")),
                         ["vg75", "vg75_attr", "vg75_dma", "vt57", "vt57_func", "vv55"])
        self.assertEqual(simrun_run.select(comps, "full"), simrun_run.select(comps, "quick"))
        for c in comps:
            self.assertEqual(c.iverilog_flags, ["-g2005"] if c.rtl_top else [], c.name)


class Fixtures(unittest.TestCase):
    def test_fixture_manifests_load(self):
        c = manifest.load(FIX / "retroICs" / "ics" / "acme" / "counter" / "component.toml")
        self.assertEqual([n.fault for n in c.negatives], ["faults/count_stuck.patch",
                                                          "faults/ce_ignored.patch",
                                                          "faults/ce_gen_never.patch"])
        t = manifest.load(FIX / "consumer" / "demo" / "ticker" / "component.toml")
        self.assertEqual(t.depends, ["acme/counter"])
        p = manifest.fault_path(t, t.negatives[0], [FIX / "retroICs"])
        self.assertEqual(p.name, "count_stuck.patch")

    def test_prj_files_reads_what_filelist_writes(self):
        from simrun import filelist
        with tempfile.TemporaryDirectory() as d:
            d = Path(d).resolve()
            prj = d / "src" / "m.prj"
            prj.parent.mkdir()
            prj.write_text('verilog work "rtl/a.v"\nverilog work "../x/b.v"\n# comment\n',
                           encoding="utf-8", newline="\n")
            self.assertEqual(filelist.prj_files(prj), [d / "src" / "rtl" / "a.v", d / "x" / "b.v"])


if __name__ == "__main__":
    unittest.main()
