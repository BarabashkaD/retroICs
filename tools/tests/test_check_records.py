# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
import io
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_records as cr  # noqa: E402

REGISTRY = """# Record IDs

| Prefix | Home | Status | IDs |
|---|---|---|---|
| PPI | retroICs/ics/intel/8255a/record.md | here | |
| OSC | retroICs/ics/acme/clock/record.md | here | |
| OSC | retroComputersDocs/computers/demo/board.md | external | OSC-20, OSC-21 |
| BRD | retroComputersDocs/computers/demo/board.md | pending | |
| DEMO-DEV | consumer/machines/demo/implementation.md | external | |
"""

SOURCES = """# Sources

| ID | Home | Kind |
|---|---|---|
| [C78] | datasheets/c78.pdf | vendor |
| [EMU] | none | comparison-only |
"""

PPI_RECORD = """# 8255A

| ID | Item | Source |
|---|---|---|
| PPI-1 | Reset | [C78] 12-78 |
| PPI-D1 | Edition difference | [C78] |
| PPI-E2 | Edge case | [C78] |
| PPI-M3 | Measured | [C78] |

See PPI-1 and PPI-D1.
"""


def make_repo(root: Path, records: dict[str, str], registry: str = REGISTRY,
              sources: str = SOURCES) -> Path:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "record-ids.md").write_text(registry, encoding="utf-8", newline="\n")
    (root / "docs" / "sources.md").write_text(sources, encoding="utf-8", newline="\n")
    for rel, text in records.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    return root


class IdParsing(unittest.TestCase):
    def test_defined_ids_table_first_cell_only(self):
        text = "| PPI-1 | refers to PPI-2 | x |\n|---|---|---|\n- PPI-3 (list)\nPPI-4 prose\n"
        self.assertEqual(cr.defined_ids(text), {"PPI-1"})

    def test_kinds(self):
        text = "| PPI-D1 | a |\n| PPI-E2 | b |\n| PPI-M3 | c |\n| CCCC | not an id |\n| 0000 | no |\n"
        self.assertEqual(cr.defined_ids(text), {"PPI-D1", "PPI-E2", "PPI-M3"})

    def test_dev_ids(self):
        text = "| DEMO-DEV-1 | a |\n| PROJ-DEV-2 | b |\n"
        self.assertEqual(cr.defined_ids(text), {"DEMO-DEV-1", "PROJ-DEV-2"})

    def test_silent_bullet_without_id_kept(self):
        text = ("#### SILENT (OSC)\n\n- OSC-1: phase open,\n  continued line\n"
                "- The power-up count (no reset).\n\n#### SILENT (CNT)\n- CNT-9: other\n")
        self.assertEqual(
            cr.silent_bullets(text, "OSC"),
            ["OSC-1: phase open, continued line", "The power-up count (no reset)."])
        self.assertEqual(cr.silent_bullets(text, "CNT"), ["CNT-9: other"])
        self.assertEqual(cr.silent_bullets(text, "PPI"), [])


class Brackets(unittest.TestCase):
    def test_source_ids(self):
        text = ("[ВГ75] [ВМ80] [ВВ55] [8275] [2716] [74198] [C78] [AP-62] [R87-…] [R87-3] [D8275K] "
                "[ИР13] [ТМ2]")
        self.assertEqual(cr.BRACKET.findall(text),
                         ["ВГ75", "ВМ80", "ВВ55", "8275", "2716", "74198", "C78", "AP-62", "R87-…",
                          "R87-3", "D8275K", "ИР13", "ТМ2"])

    def test_not_source_ids(self):
        text = ("bits [5:3] and [15:8], a [Link](x.md), [ВГ75](x.md), [8275](y.md), [12], [7], "
                "[x], [ ], [a-b], [0..7], [read me]")
        self.assertEqual(cr.BRACKET.findall(text), [])

    def test_sources_md_ids_match(self):
        # every ID of the repo's own source table is a bracket ID the checker sees
        text = (Path(__file__).resolve().parent.parent.parent / "docs" / "sources.md").read_text(
            encoding="utf-8")
        ids = [cr._clean(c[0]) for c in cr.table_rows(text)
               if cr._clean(c[0]).startswith("[")]
        self.assertTrue(ids)
        for i in ids:
            self.assertEqual(cr.BRACKET.findall(i), [i.strip("[]")], i)


class Registry(unittest.TestCase):
    def test_load_registry(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text(REGISTRY, encoding="utf-8", newline="\n")
            reg = cr.load_registry(p)
        self.assertEqual(reg["PPI"].status, "here")
        self.assertIsNone(reg["PPI"].ids)
        listed = [r for r in reg.values() if r.ids]
        self.assertEqual(listed[0].ids, frozenset({"OSC-20", "OSC-21"}))
        self.assertEqual(reg["DEMO-DEV"].status, "external")

    def test_bad_status_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text("| Prefix | Home | Status | IDs |\n|---|---|---|---|\n"
                         "| PPI | x | bogus | |\n", encoding="utf-8", newline="\n")
            with self.assertRaises(ValueError):
                cr.load_registry(p)


class Check(unittest.TestCase):
    def run_check(self, records, docs=None, record_dirs=("ics",), **kw):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(Path(d) / "repo", records, **kw)
            external = {}
            for repo, files in (docs or {}).items():
                external[repo] = Path(d) / repo
                for rel, text in files.items():
                    p = external[repo] / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(text, encoding="utf-8", newline="\n")
            return cr.check(root, external, record_dirs)

    @staticmethod
    def errors(lines):
        return [l for l in lines if not l.startswith("NOTE")]

    def test_clean_passes(self):
        out = self.run_check({"ics/intel/8255a/record.md": PPI_RECORD})
        self.assertEqual(self.errors(out), [])

    def test_undefined_reference_fails(self):
        rec = PPI_RECORD + "\nAlso PPI-99 applies.\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}))
        self.assertEqual(len(out), 1)
        self.assertIn("PPI-99", out[0])

    def test_unregistered_prefix_fails_in_definition(self):
        rec = PPI_RECORD + "| ZZZ-1 | stray |\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}))
        self.assertTrue(any("ZZZ-1" in l for l in out))

    def test_signal_names_in_prose_are_not_references(self):
        rec = PPI_RECORD + ("\nD7 is set, A1-A0 select, PC2-PC0 and LC0-3 are lines; SHA-256 "
                            "and ZZZ-1 are not records. The ва D22 pin.\n")
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}))
        self.assertEqual(out, [])

    def test_dev_prefix_reference_must_be_registered(self):
        rec = PPI_RECORD + "\nSee QQ-DEV-1.\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}))
        self.assertTrue(any("QQ-DEV-1" in l for l in out))

    def test_source_ids_in_brackets_are_not_record_ids(self):
        rec = PPI_RECORD + "\nSource [C78] and [EMU] and [AP-62].\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}))
        self.assertEqual(len(out), 1)
        self.assertIn("AP-62", out[0])
        self.assertIn("source", out[0])

    def test_pending_prefix_passes(self):
        rec = PPI_RECORD + "\nBoard item BRD-3 is pending.\n"
        out = self.run_check({"ics/intel/8255a/record.md": rec})
        self.assertEqual(self.errors(out), [])

    def test_split_prefix_listed_ids(self):
        recs = {
            "ics/acme/clock/record.md": "| OSC-1 | a |\n\nand OSC-20 lives on the board.\n",
            "ics/intel/8255a/record.md": PPI_RECORD,
        }
        out = self.run_check(recs)
        self.assertEqual(self.errors(out), [])
        # OSC-20 may not be defined here
        recs["ics/acme/clock/record.md"] += "| OSC-21 | wrong place |\n"
        out = self.errors(self.run_check(recs))
        self.assertTrue(any("OSC-21" in l for l in out))
        # OSC-22 is neither listed nor defined
        recs["ics/acme/clock/record.md"] = "| OSC-1 | a |\n\nOSC-22\n"
        out = self.errors(self.run_check(recs))
        self.assertTrue(any("OSC-22" in l for l in out))

    def test_duplicate_definition_fails(self):
        recs = {
            "ics/intel/8255a/record.md": PPI_RECORD,
            "ics/intel/8257/record.md": "| PPI-1 | again |\n",
        }
        out = self.errors(self.run_check(recs))
        self.assertTrue(any("PPI-1" in l and "twice" in l for l in out))

    def test_external_root_absent_reports_not_checked(self):
        recs = {"ics/intel/8255a/record.md": PPI_RECORD + "\nThe board item OSC-20.\n"}
        out = self.run_check(recs)
        self.assertEqual(self.errors(out), [])
        self.assertTrue(any("retroComputersDocs" in l and "not checked" in l for l in out), out)

    def test_external_root_present_checks_external(self):
        recs = {"ics/intel/8255a/record.md": PPI_RECORD + "\nThe board item OSC-20.\n"}
        bad = {"retroComputersDocs": {"b.md": "| OSC-99 | x |\n"}}
        out = self.errors(self.run_check(recs, docs=bad))
        self.assertTrue(any("OSC-20" in l for l in out))
        out = self.run_check(recs, docs={"retroComputersDocs": {"b.md": "| OSC-20 | x |\n"}})
        self.assertEqual(out, [])

    def test_external_keyed_by_repo(self):
        # two repos named by external rows; only one root given: the other gives one NOTE
        recs = {"ics/intel/8255a/record.md": PPI_RECORD + "\nOSC-20 and DEMO-DEV-1.\n"}
        docs = {"retroComputersDocs": {"b.md": "| OSC-20 | x |\n"}}
        out = self.run_check(recs, docs=docs)
        self.assertEqual(self.errors(out), [])
        notes = [l for l in out if l.startswith("NOTE")]
        self.assertEqual(len(notes), 1, out)
        self.assertIn("consumer", notes[0])
        # an ID of the given repo that its root does not define is a problem
        recs["ics/intel/8255a/record.md"] += "And OSC-21.\n"
        out = self.errors(self.run_check(recs, docs=docs))
        self.assertTrue(any("OSC-21" in l for l in out), out)

    def test_missing_external_root_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(Path(d) / "repo", {"ics/intel/8255a/record.md": PPI_RECORD})
            out = cr.check(root, {"retroComputersDocs": Path(d) / "nope"})
        self.assertTrue(any("external root" in l and "nope" in l for l in out), out)

    def test_missing_external_root_only_the_error(self):
        # an external ID is referenced, but a "not checked" note would contradict the given root
        with tempfile.TemporaryDirectory() as d:
            recs = {"ics/acme/clock/record.md": "| OSC-1 | a |\n\nOSC-20 is on the board.\n"}
            root = make_repo(Path(d) / "repo", recs)
            out = cr.check(root, {"retroComputersDocs": Path(d) / "nope"})
        self.assertEqual(out, ["external root retroComputersDocs (nope) not found"])

    def test_records_dir_option(self):
        registry = ("| Prefix | Home | Status | IDs |\n|---|---|---|---|\n"
                    "| ABC | demo/machines/x/record.md | here | |\n")
        recs = {"machines/x/record.md": "| ABC-1 | a [C78] |\n",
                "machines/x/README.md": "See ABC-1 and ABC-2.\n"}
        out = self.errors(self.run_check(recs, registry=registry, record_dirs=("machines",)))
        self.assertEqual(len(out), 1, out)
        self.assertIn("ABC-2", out[0])
        # without --records machines the README is not read
        self.assertEqual(self.errors(self.run_check(recs, registry=registry)), [])

    def test_definitions_from_home_file(self):
        registry = ("| Prefix | Home | Status | IDs |\n|---|---|---|---|\n"
                    "| BRD | demo/computers/x/board.md | here | |\n"
                    "| WIRE | demo/computers/x/wire.md | here | |\n")
        board = ("| BRD-1 | the video path |\n| RS-232 receiver | not an ID |\n"
                 "| WIRE-3 | not this file's prefix |\n\nSee BRD-1.\n")
        recs = {"computers/x/board.md": board, "computers/x/wire.md": "| WIRE-1 | a |\n"}
        out = self.errors(self.run_check(recs, registry=registry, record_dirs=("computers",)))
        self.assertEqual(len(out), 1, out)
        self.assertIn("WIRE-3", out[0])
        self.assertIn("not defined", out[0])

    def test_here_rows_name_one_repo(self):
        registry = ("| Prefix | Home | Status | IDs |\n|---|---|---|---|\n"
                    "| PPI | a/ics/x/record.md | here | |\n| CPU | b/ics/y/record.md | here | |\n")
        out = self.run_check({"ics/x/record.md": "| PPI-1 | a |\n"}, registry=registry)
        self.assertTrue(any("more than one repo" in l for l in out), out)

    def test_retired_id_defined_is_a_problem(self):
        registry = REGISTRY + "| PPI | - | retired | PPI-10 |\n"
        rec = PPI_RECORD + "| PPI-10 | moved out |\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}, registry=registry))
        self.assertTrue(any("PPI-10" in l and "retired" in l for l in out), out)

    def test_retired_id_referenced_is_fine(self):
        registry = REGISTRY + "| PPI | - | retired | PPI-10 |\n"
        rec = PPI_RECORD + "\nPPI-10 left this record.\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}, registry=registry))
        self.assertEqual(out, [])

    def test_retired_whole_prefix(self):
        registry = REGISTRY.replace("| OSC | retroICs/ics/acme/clock/record.md | here | |\n",
                                    "| OSC | - | retired | |\n")
        rec = PPI_RECORD + "\nOSC-3 is gone.\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}, registry=registry))
        self.assertEqual(out, [])
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec + "| OSC-3 | x |\n"},
                                         registry=registry))
        self.assertTrue(any("OSC-3" in l and "retired" in l for l in out), out)

    def test_cli_external_needs_name(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(Path(d) / "repo", {"ics/intel/8255a/record.md": PPI_RECORD})
            with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
                cr.main(["--repo", str(root), "--external", str(d)])
            self.assertEqual(cm.exception.code, 2)
            with redirect_stdout(io.StringIO()) as out:
                code = cr.main(["--repo", str(root), "--external", "retroComputersDocs=" + d,
                                "--records", "ics"])
            self.assertEqual(code, 0, out.getvalue())

    def test_cyrillic_and_digit_first_sources_checked(self):
        rec = PPI_RECORD + "\nAlso [ЖЖ1], [7400] and [C78].\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}))
        self.assertEqual(len(out), 2, out)
        self.assertTrue(any("[ЖЖ1]" in l for l in out))
        self.assertTrue(any("[7400]" in l for l in out))
        sources = SOURCES + "| [ЖЖ1] | x | vendor |\n| [7400] | x | vendor |\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": rec}, sources=sources))
        self.assertEqual(out, [])

    def test_every_markdown_file_under_ics_checked(self):
        recs = {
            "ics/intel/8255a/record.md": PPI_RECORD,
            "ics/intel/8255a/README.md": "# 8255A\n\nItems PPI-1 and PPI-99; source [ЖЖ1].\n",
            "ics/intel/8255a/datasheets/index.md": "| ID | Home |\n|---|---|\n| [Q99] | x |\n",
            "ics/intel/8255a/AGENTS.md": "See PPI-D1 and [C78].\n",
        }
        out = self.errors(self.run_check(recs))
        self.assertEqual(len(out), 3, out)
        self.assertTrue(any(l.startswith("ics/intel/8255a/README.md") and "PPI-99" in l for l in out))
        self.assertTrue(any(l.startswith("ics/intel/8255a/README.md") and "[ЖЖ1]" in l for l in out))
        self.assertTrue(any(l.startswith("ics/intel/8255a/datasheets/index.md") and "[Q99]" in l
                            for l in out))

    def test_definitions_only_in_record_md(self):
        recs = {"ics/intel/8255a/record.md": PPI_RECORD,
                "ics/intel/8255a/README.md": "| PPI-7 | a table row elsewhere |\n\nPPI-7\n"}
        out = self.errors(self.run_check(recs))
        self.assertTrue(any("PPI-7" in l and "not defined" in l for l in out))

    def test_sources_table(self):
        bad = SOURCES + "| [C78] | again | vendor |\n| [X1] | y | nonsense |\n"
        out = self.errors(self.run_check({"ics/intel/8255a/record.md": PPI_RECORD}, sources=bad))
        self.assertTrue(any("C78" in l and "twice" in l for l in out))
        self.assertTrue(any("X1" in l and "nonsense" in l for l in out))


if __name__ == "__main__":
    unittest.main()
