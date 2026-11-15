# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""simrun: the component.toml loader, resolve, filelist and its command line."""
import hashlib
import io
import os
import re
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
from simrun import filelist, manifest  # noqa: E402
from simrun.manifest import ManifestError  # noqa: E402

ROOT = TOOLS.parent
# the file order of the demo machine of machine_fixture: its ICs and blocks, dependencies first
PRJ_LINES = [
    'verilog work "rtl/demo/cpu.v"',
    'verilog work "rtl/demo/clocks.v"',
    'verilog work "rtl/demo/ppi.v"',
    'verilog work "rtl/demo/dma.v"',
    'verilog work "rtl/demo/crt.v"',
    'verilog work "rtl/demo/video.v"',
    'verilog work "rtl/demo/machine.v"',
]


def write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def component(repo: Path, folder: str, toml: str, files=()) -> Path:
    """Writes <repo>/<folder>/component.toml and empty files at the given folder-relative paths."""
    d = repo / folder
    for f in files:
        write(d / f, "// %s\n" % f)
    return write(d / "component.toml", toml)


def ic(name: str, rtl: list[str], depends=(), extra: str = "") -> str:
    return ('[component]\nname = "%s"\nkind = "ic"\ntitle = "t"\nreproduces = "r"\n'
            'fidelity = "datasheet"\ninterface = 1\n\n[rtl]\ntop = "top"\nfiles = [%s]\n'
            'depends = [%s]\n%s' % (name, ", ".join('"%s"' % f for f in rtl),
                                    ", ".join('"%s"' % d for d in depends), extra))


def block(name: str, kind: str, rtl: list[str], depends=(), extra: str = "") -> str:
    return ic(name, rtl, depends, extra).replace('kind = "ic"', 'kind = "%s"' % kind)


# the manifest example of the repository layout design (section 4.1), copied as written there
EXAMPLE = TOOLS / "tests" / "fixtures" / "component-example.toml"
EXAMPLE_SHA256 = "55ce20d1e2499edc66d6e57d87102898afbdb5a4892666e7b1213f5c9a5358ba"
# the only two changes the loader needs: the negative's key and plusargs as a table
EXAMPLE_CHANGES = [('patch = "faults/', 'fault = "faults/'), ("plusargs = []", "plusargs = {}")]


def spec_example() -> str:
    """The layout design's manifest example with EXAMPLE_CHANGES applied (each exactly once)."""
    text = EXAMPLE.read_text(encoding="utf-8")
    for old, new in EXAMPLE_CHANGES:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def conventions_example() -> str:
    """The component.toml example of docs/conventions.md."""
    text = (ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
    section = text.split("\n## component.toml\n", 1)[1].split("\n## ", 1)[0]
    m = re.search(r"```toml\n(.*?)```", section, re.S)
    assert m, "no toml block in the component.toml section"
    return m.group(1)


class Load(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"

    def tearDown(self):
        self.tmp.cleanup()

    def spec_files(self):
        return ["rtl/intel_8255a.v", "tb/tb_intel_8255a.v", "golden/modes.txt",
                "faults/mode1_ibf_stuck.patch"]

    def test_example_fixture_as_written(self):
        data = EXAMPLE.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), EXAMPLE_SHA256)
        self.assertNotIn(b"\r", data)

    def test_load_spec_example(self):
        p = component(self.repo, "ics/intel/8255a", spec_example(), self.spec_files())
        c = manifest.load(p)
        d = p.parent.resolve()
        self.assertEqual((c.name, c.kind, c.title, c.reproduces, c.fidelity, c.interface,
                          c.record_prefix),
                         ("intel/8255a", "ic", "Intel 8255A programmable peripheral interface",
                          "i8255a", "datasheet", 1, "PPI"))
        self.assertEqual(c.equivalents, [manifest.Equivalent("К580ВВ55А", "k580vv55a",
                                                             "unverified")])
        self.assertEqual((c.variant_of, c.board_record), (None, None))
        self.assertEqual(c.root, d)
        self.assertEqual(c.repo_root, self.repo.resolve())
        self.assertEqual(c.rtl_top, "intel_8255a")
        self.assertEqual(c.rtl_files, [d / "rtl" / "intel_8255a.v"])
        self.assertEqual((c.depends, c.incdirs, c.iverilog_flags), ([], [], []))
        self.assertEqual(len(c.tests), 1)
        t = c.tests[0]
        self.assertEqual((t.name, t.tier, t.top, t.files, t.incdirs, t.params, t.plusargs, t.data,
                          t.timeout_s, t.ids),
                         ("modes", "quick", "tb_intel_8255a", [d / "tb" / "tb_intel_8255a.v"], [],
                          {}, {}, {}, 120, []))
        self.assertEqual((t.golden.path, t.golden.compare), (d / "golden" / "modes.txt", "exact"))
        self.assertEqual(len(c.negatives), 1)
        n = c.negatives[0]
        self.assertEqual((n.test, n.fault, n.expect, n.match, n.ids),
                         ("modes", "faults/mode1_ibf_stuck.patch", "FAIL PPI-14", "first", []))
        self.assertEqual(manifest.fault_path(c, n, [self.repo]),
                         d / "faults" / "mode1_ibf_stuck.patch")
        # unchanged, the example fails on exactly the two keys
        for old, new in EXAMPLE_CHANGES:
            with self.subTest(old):
                p = component(self.repo, "ics/intel/8255a", spec_example().replace(new, old),
                              self.spec_files())
                with self.assertRaises(ManifestError):
                    manifest.load(p)

    def test_conventions_example_loads(self):
        p = component(self.repo, "ics/intel/8255a", conventions_example(), self.spec_files())
        c = manifest.load(p)
        self.assertEqual([e.level for e in c.equivalents], ["unverified"])
        self.assertEqual(c.tests[0].ids, ["PPI-5"])
        self.assertEqual(c.negatives[0].match, "first")

    def test_equivalents(self):
        base = spec_example()
        two = base.replace('[rtl]', '[[equivalent]]\npart = "AMD P8255A"\nlevel = "function"\n\n[rtl]')
        p = component(self.repo, "ics/intel/8255a", two, self.spec_files())
        c = manifest.load(p)
        self.assertEqual(c.equivalents[1], manifest.Equivalent("AMD P8255A", None, "function"))
        bad = {
            "level": base.replace('level = "unverified"', 'level = "same"'),
            "translit": base.replace('translit = "k580vv55a"', 'translit = "K580VV55A"'),
            "no part": base.replace('part = "К580ВВ55А"\n', ''),
            "twice": base.replace('[rtl]', '[[equivalent]]\npart = "К580ВВ55А"\nlevel = "partial"'
                                  '\n\n[rtl]'),
            "unknown key": base.replace('translit = "k580vv55a"', 'translit = "k580vv55a"\nnote = "x"'),
        }
        for where, text in bad.items():
            with self.subTest(where):
                p = component(self.repo, "ics/intel/8255a", text, self.spec_files())
                with self.assertRaises(ManifestError):
                    manifest.load(p)

    def test_variant_of_and_board_record(self):
        extra = ('variant_of = "machines/demo"\nboard_record = { repo = "retroComputersDocs", '
                 'tag = "v2026.11.14", file = "computers/demo/board.md" }\n')
        text = block("machines/demo_plus", "machine", ["rtl/m.v"]).replace(
            'interface = 1\n', 'interface = 1\n' + extra)
        p = component(self.repo, "machines/demo_plus", text, ["rtl/m.v"])
        c = manifest.load(p)
        self.assertEqual(c.variant_of, "machines/demo")
        self.assertEqual(c.board_record, manifest.BoardRecord("retroComputersDocs", "v2026.11.14",
                                                              "computers/demo/board.md"))
        bad = {
            "variant name": text.replace('"machines/demo"', '"Machines Demo"'),
            "variant self": text.replace('variant_of = "machines/demo"',
                                         'variant_of = "machines/demo_plus"'),
            "record key": text.replace('file = "computers', 'branch = "main", file = "computers'),
            "record missing tag": text.replace('tag = "v2026.11.14", ', ''),
            "record path up": text.replace('"computers/demo/board.md"', '"../x/board.md"'),
            "record path absolute": text.replace('"computers/demo/board.md"', '"/x/board.md"'),
            "record not a table": text.replace(
                'board_record = { repo = "retroComputersDocs", tag = "v2026.11.14", '
                'file = "computers/demo/board.md" }', 'board_record = "board.md"'),
        }
        for where, t in bad.items():
            with self.subTest(where):
                p = component(self.repo, "machines/demo_plus", t, ["rtl/m.v"])
                with self.assertRaises(ManifestError):
                    manifest.load(p)

    def test_docs_only_ic(self):
        text = ('[component]\nname = "acme/clock"\nkind = "ic"\ntitle = "Acme clock"\n'
                'reproduces = "aclock"\nfidelity = "datasheet"\ninterface = 1\n'
                'record_prefix = "OSC"\n\n[[equivalent]]\npart = "АБ123"\n'
                'translit = "ab123"\nlevel = "unverified"\n')
        p = component(self.repo, "ics/acme/clock", text)
        c = manifest.load(p)
        self.assertEqual((c.rtl_top, c.rtl_files, c.depends, c.tests, c.negatives),
                         (None, [], [], [], []))
        self.assertEqual(filelist.render(c, [self.repo], "f"), [])
        # only an ic may have no [rtl], and then no tests
        for where, t in {"machine": text.replace('kind = "ic"', 'kind = "machine"'),
                         "tests": text + '\n[[test]]\nname = "t"\ntier = "quick"\ntop = "tb"\n'
                                         'files = ["component.toml"]\n'}.items():
            with self.subTest(where):
                folder = "ics/acme/clock" if where == "tests" else "acme/clock"
                p = component(self.repo, folder, t)
                with self.assertRaises(ManifestError) as cm:
                    manifest.load(p)
                self.assertIn("[rtl]", str(cm.exception))

    def test_full_test_fields(self):
        extra = ('incdirs = ["inc"]\niverilog_flags = ["-g2005"]\n\n'
                 '[[test]]\nname = "run1"\ntier = "standard"\ntop = "tb_m"\n'
                 'files = ["tb/tb_m.v"]\nincdirs = ["tb"]\nids = ["CRT-22"]\n'
                 'params = { FRAMES = 3 }\nplusargs = { seed = 7, mode = "x" }\n'
                 '[test.data.bios]\npath = "roms/monitor.bin"\nsizes = [2048]\n'
                 '[test.data.font]\npath = "roms/font.bin"\nsizes = [1024]\npad_to = 2048\n\n'
                 '[[negative]]\ntest = "run1"\nfault = "faults/f.patch"\n'
                 'expect = "ERROR: dma byte: frame *: x"\nmatch = "anywhere"\n')
        p = component(self.repo, "machines/demo", block("machines/demo", "machine", ["rtl/m.v"],
                                                        extra=extra),
                      ["rtl/m.v", "tb/tb_m.v", "roms/monitor.bin", "roms/font.bin",
                       "faults/f.patch", "inc/x.vh"])
        c = manifest.load(p)
        d = p.parent.resolve()
        self.assertEqual(c.repo_root, self.repo.resolve())
        self.assertEqual((c.incdirs, c.iverilog_flags), ([d / "inc"], ["-g2005"]))
        t = c.tests[0]
        self.assertEqual((t.tier, t.incdirs, t.params, t.plusargs, t.timeout_s),
                         ("standard", [d / "tb"], {"FRAMES": 3}, {"seed": 7, "mode": "x"}, None))
        self.assertEqual(t.data["bios"], manifest.DataFile(d / "roms" / "monitor.bin", (2048,), 0))
        self.assertEqual(t.data["font"], manifest.DataFile(d / "roms" / "font.bin", (1024,), 2048))
        self.assertIsNone(t.golden)
        self.assertEqual(c.negatives[0].match, "anywhere")

    def test_unknown_key_fails(self):
        base = spec_example()
        cases = {
            "component": base.replace('record_prefix = "PPI"', 'record_prefix = "PPI"\ncolour = "red"'),
            "rtl": base.replace('depends = []', 'depends = []\nsources = []'),
            "test": base.replace('timeout_s = 120', 'timeout_s = 120\nretries = 2'),
            "negative": base.replace('expect = "FAIL PPI-14"',
                                     'expect = "FAIL PPI-14"\npatch = "x.patch"'),
            "equivalent": base.replace('translit = "k580vv55a"', 'translit = "k580vv55a"\npin = 1'),
            "top level": base + '\n[[alias]]\npart = "К580ВВ55А"\n',
            "golden": base.replace('compare = "exact"', 'compare = "exact", tolerance = 1'),
            "data": base.replace('timeout_s = 120',
                                 'timeout_s = 120\ndata = { bios = { path = "golden/modes.txt", '
                                 'crc = 1 } }'),
        }
        for where, text in cases.items():
            with self.subTest(where):
                p = component(self.repo, "ics/intel/8255a", text, self.spec_files())
                with self.assertRaises(ManifestError) as cm:
                    manifest.load(p)
                self.assertIn("unknown key", str(cm.exception))

    def test_bad_values_fail(self):
        base = spec_example()
        cases = {
            "kind": base.replace('kind = "ic"', 'kind = "chip"'),
            "tier": base.replace('tier = "quick"', 'tier = "nightly"'),
            "match": base.replace('expect = "FAIL PPI-14"', 'expect = "FAIL PPI-14"\nmatch = "last"'),
            "interface": base.replace('interface = 1', 'interface = "1"'),
            "missing title": base.replace('title = "Intel 8255A programmable peripheral interface"\n',
                                          ''),
            "id pattern": base.replace('timeout_s = 120', 'timeout_s = 120\nids = ["ppi5"]'),
            "negative test": base.replace('test = "modes"', 'test = "other"'),
            "fault form": base.replace('fault = "faults/mode1_ibf_stuck.patch"',
                                       'fault = "mode1_ibf_stuck"'),
            "name vs folder": base.replace('name = "intel/8255a"', 'name = "intel/8257"'),
            "plusargs list": base.replace('plusargs = {}', 'plusargs = []'),
        }
        for where, text in cases.items():
            with self.subTest(where):
                p = component(self.repo, "ics/intel/8255a", text, self.spec_files())
                with self.assertRaises(ManifestError):
                    manifest.load(p)

    def test_missing_file_fails(self):
        base = spec_example()
        files = self.spec_files()
        for missing in files:
            with self.subTest(missing):
                d = self.repo / missing.replace("/", "_")
                p = component(d, "ics/intel/8255a", base, [f for f in files if f != missing])
                with self.assertRaises(ManifestError) as cm:
                    manifest.load(p)
                self.assertIn(missing, str(cm.exception))
                self.assertIn("not found", str(cm.exception))

    def test_dependency_fault_reference(self):
        ics = Path(self.tmp.name) / "retroICs"
        machines = Path(self.tmp.name) / "consumer"
        component(ics, "ics/intel/8275", ic("intel/8275", ["rtl/crt.v"]),
                  ["rtl/crt.v", "faults/vg75_drq_held.patch"])
        neg = ('\n[[test]]\nname = "run1"\ntier = "standard"\ntop = "tb"\n'
               'files = ["tb/tb.v"]\n\n[[negative]]\ntest = "run1"\n'
               'fault = "intel/8275:vg75_drq_held"\n'
               'expect = "ERROR: hold periods: HRQ high after theta-up of S4"\n')
        p = component(machines, "machines/demo",
                      block("machines/demo", "machine", ["rtl/m.v"], ["intel/8275"], neg),
                      ["rtl/m.v", "tb/tb.v"])
        c = manifest.load(p)
        n = c.negatives[0]
        self.assertEqual(n.fault, "intel/8275:vg75_drq_held")
        self.assertEqual(manifest.fault_path(c, n, [machines, ics]),
                         (ics / "ics/intel/8275/faults/vg75_drq_held.patch").resolve())
        # the dependency without that patch
        n2 = manifest.Negative("run1", "intel/8275:vg75_nope", "x", "first", [])
        with self.assertRaises(ManifestError) as cm:
            manifest.fault_path(c, n2, [machines, ics])
        self.assertIn("faults/vg75_nope.patch", str(cm.exception))
        # a component that is not a dependency
        bad = p.read_text(encoding="utf-8").replace("intel/8275:", "intel/8257:")
        write(p, bad)
        with self.assertRaises(ManifestError) as cm:
            manifest.load(p)
        self.assertIn("intel/8257", str(cm.exception))

    def test_resolve(self):
        a = Path(self.tmp.name) / "a"
        b = Path(self.tmp.name) / "b"
        component(a, "ics/intel/8255a", ic("intel/8255a", ["rtl/x.v"]), ["rtl/x.v"])
        component(b, "machines/demo", block("machines/demo", "machine", ["rtl/m.v"]), ["rtl/m.v"])
        self.assertEqual(manifest.resolve("intel/8255a", [b, a]).name, "intel/8255a")
        self.assertEqual(manifest.resolve("machines/demo", [b, a]).root,
                         (b / "machines/demo").resolve())
        with self.assertRaises(ManifestError):
            manifest.resolve("intel/8257", [a, b])
        component(b, "ics/intel/8255a", ic("intel/8255a", ["rtl/x.v"]), ["rtl/x.v"])
        with self.assertRaises(ManifestError) as cm:
            manifest.resolve("intel/8255a", [a, b])
        self.assertIn("twice", str(cm.exception))
        # the same root twice is one place
        self.assertEqual(manifest.resolve("machines/demo", [b, b]).name, "machines/demo")

    def test_paths_relative(self):
        base = spec_example()
        cases = {
            "absolute": base.replace('"rtl/intel_8255a.v"',
                                     '"%s"' % (self.repo / "x.v").resolve().as_posix()),
            "backslash": base.replace('"rtl/intel_8255a.v"', '"rtl\\\\intel_8255a.v"'),
            "outside the repo": base.replace('"rtl/intel_8255a.v"', '"../../../../x.v"'),
        }
        write(Path(self.tmp.name) / "x.v")
        for where, text in cases.items():
            with self.subTest(where):
                p = component(self.repo, "ics/intel/8255a", text, self.spec_files())
                with self.assertRaises(ManifestError):
                    manifest.load(p)
        # ".." inside the repo is allowed (an old layout during the import)
        write(self.repo / "rtl" / "old.v")
        p = component(self.repo, "ics/intel/8255a",
                      base.replace('"rtl/intel_8255a.v"', '"../../../rtl/old.v"'), self.spec_files())
        self.assertEqual(manifest.load(p).rtl_files, [(self.repo / "rtl" / "old.v").resolve()])


class RealManifests(unittest.TestCase):
    """This repo's component.toml files: each IC folder has one that loads, and it names the
    equivalents of the README's table, with the same transliterations and levels."""

    def test_every_ic_folder(self):
        folders = sorted(p.parent for p in (ROOT / "ics").glob("*/*/README.md"))
        self.assertTrue(folders)
        for d in folders:
            with self.subTest(d.name):
                c = manifest.load(d / manifest.MANIFEST)
                readme = (d / "README.md").read_text(encoding="utf-8")
                section = readme.split("\n## Equivalents\n", 1)[1].split("\n## ", 1)[0]
                rows = [tuple(x.strip() for x in line.strip().strip("|").split("|"))
                        for line in section.splitlines()
                        if line.startswith("| ") and not line.startswith("| Part ")]
                self.assertEqual([(e.part, "`%s`" % e.translit, e.level) for e in c.equivalents],
                                 rows)


def machine_fixture(src: Path) -> None:
    """An older layout's flat RTL folder under <src>/rtl/demo/ (the old names), split into the
    components of the new layout, with <src> as the repo root."""
    rtl = "rtl/demo/"
    for f in ("cpu.v", "clocks.v", "ppi.v", "dma.v", "crt.v",
              "video.v", "machine.v"):
        write(src / rtl / f, "// %s\n" % f)
    for name, f in (("intel/8080a", "cpu.v"), ("intel/8255a", "ppi.v"),
                    ("intel/8257", "dma.v"), ("intel/8275", "crt.v")):
        component(src, "ics/" + name, ic(name, ["../../../" + rtl + f]))
    for name, f in (("blocks/demo_clocks", "clocks.v"),
                    ("blocks/demo_video", "video.v")):
        component(src, name, block(name, "block", ["../../" + rtl + f]))
    component(src, "machines/demo",
              block("machines/demo", "machine", ["../../" + rtl + "machine.v"],
                    ["intel/8080a", "blocks/demo_clocks", "intel/8255a", "intel/8257",
                     "intel/8275", "blocks/demo_video"]))


class FileList(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.top = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_filelist_order_and_dedup(self):
        r = self.top / "r"
        component(r, "ics/v/base", ic("v/base", ["rtl/base.v"]), ["rtl/base.v"])
        component(r, "ics/v/left", ic("v/left", ["rtl/left.v", "rtl/shared.v"], ["v/base"]),
                  ["rtl/left.v", "rtl/shared.v"])
        component(r, "ics/v/right", ic("v/right", ["rtl/right.v", "../left/rtl/shared.v"],
                                       ["v/base"]), ["rtl/right.v"])
        p = component(r, "machines/m", block("machines/m", "machine", ["rtl/m.v"],
                                              ["v/left", "v/right"]), ["rtl/m.v"])
        c = manifest.load(p)
        got = [f.relative_to(r.resolve()).as_posix() for f in filelist.files(c, [r])]
        self.assertEqual(got, ["ics/v/base/rtl/base.v", "ics/v/left/rtl/left.v",
                               "ics/v/left/rtl/shared.v", "ics/v/right/rtl/right.v",
                               "machines/m/rtl/m.v"])
        self.assertEqual([x.name for x in filelist.components(c, [r])],
                         ["v/base", "v/left", "v/right", "machines/m"])

    def test_dependency_cycle_fails(self):
        r = self.top / "r"
        component(r, "ics/v/a", ic("v/a", ["rtl/a.v"], ["v/b"]), ["rtl/a.v"])
        p = component(r, "ics/v/b", ic("v/b", ["rtl/b.v"], ["v/a"]), ["rtl/b.v"])
        with self.assertRaises(ManifestError) as cm:
            filelist.files(manifest.load(p), [r])
        self.assertIn("cycle", str(cm.exception))

    def test_formats(self):
        src = self.top / "src"
        machine_fixture(src)
        c = manifest.resolve("machines/demo", [src])
        paths = filelist.files(c, [src])
        self.assertEqual(filelist.render(c, [src], "prj", relative_to=src), PRJ_LINES)
        rel = [l.split('"')[1] for l in PRJ_LINES]
        self.assertEqual(filelist.render(c, [src], "f", relative_to=src), rel)
        self.assertEqual(filelist.render(c, [src], "qsf", relative_to=src),
                         ["set_global_assignment -name VERILOG_FILE " + f for f in rel])
        self.assertEqual(filelist.render(c, [src], "f"), [p.as_posix() for p in paths])
        with self.assertRaises(ValueError):
            filelist.render(c, [src], "mk")

    def test_incdirs_in_formats(self):
        r = self.top / "r"
        p = component(r, "ics/v/a", ic("v/a", ["rtl/a.v", "rtl/b.sv"], extra='incdirs = ["inc"]\n'),
                      ["rtl/a.v", "rtl/b.sv", "inc/x.vh"])
        c = manifest.load(p)
        d = "ics/v/a/"
        self.assertEqual(filelist.render(c, [r], "f", relative_to=r),
                         ["+incdir+" + d + "inc", d + "rtl/a.v", d + "rtl/b.sv"])
        self.assertEqual(filelist.render(c, [r], "qsf", relative_to=r),
                         ["set_global_assignment -name SEARCH_PATH " + d + "inc",
                          "set_global_assignment -name VERILOG_FILE " + d + "rtl/a.v",
                          "set_global_assignment -name SYSTEMVERILOG_FILE " + d + "rtl/b.sv"])
        self.assertEqual(filelist.render(c, [r], "prj", relative_to=r),
                         ['verilog work "%srtl/a.v"' % d, 'verilog work "%srtl/b.sv"' % d])

    def test_cli(self):
        src = self.top / "src"
        machine_fixture(src)
        env = dict(os.environ, PYTHONPATH=str(TOOLS))
        cmd = [sys.executable, "-B", "-m", "simrun", "filelist", "machines/demo", "--format", "prj",
               "--relative-to", str(src), "--search", str(src)]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=self.top, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), PRJ_LINES)
        # a component folder instead of a name; paths relative to the current directory
        cmd = [sys.executable, "-B", "-m", "simrun", "filelist", str(src / "ics" / "intel" / "8257"),
               "--format", "f", "--relative-to", "."]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=src, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), ["rtl/demo/dma.v"])
        # an unknown component: exit 2 and one error line
        cmd = [sys.executable, "-B", "-m", "simrun", "filelist", "intel/9999", "--format", "f",
               "--search", str(src)]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=self.top, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("ERROR: "), r.stdout)

    def test_relative_to_another_drive(self):
        # Windows: os.path.relpath raises ValueError for a path on another drive
        src = self.top / "src"
        machine_fixture(src)
        out = io.StringIO()
        with mock.patch.object(filelist.os.path, "relpath",
                               side_effect=ValueError("path is on mount 'D:', start on mount 'E:'")), \
                redirect_stdout(out):
            code = simrun_main.main(["filelist", "machines/demo", "--format", "f",
                                     "--relative-to", str(src), "--search", str(src)])
        self.assertEqual(code, 2)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("ERROR: "), lines)
        self.assertIn("cannot be written relative to", lines[0])


if __name__ == "__main__":
    unittest.main()
