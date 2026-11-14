# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_records as cr  # noqa: E402

REGISTRY = """# Record IDs

| Prefix | Home | Status | IDs |
|---|---|---|---|
| PPI | retroICs/ics/intel/8255a/record.md | here | |
| CLK | retroICs/ics/intel/8224/record.md | here | |
| CLK | retroComputersDocs/computers/rk86/board.md | external | CLK-20, CLK-21 |
| VID | retroComputersDocs/computers/rk86/board.md | pending | |
| RK86M-DEV | retroMachines/machines/rk86/implementation.md | external | |
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
        text = "| RK86M-DEV-1 | a |\n| RKPOCKET-DEV-2 | b |\n"
        self.assertEqual(cr.defined_ids(text), {"RK86M-DEV-1", "RKPOCKET-DEV-2"})

    def test_legacy_list_items(self):
        text = "| PPI-1 | a |\n- PPI-D1 (RESET text): x\n- CLK-5/6: y\nprose PPI-9\n"
        self.assertEqual(cr.legacy_ids(text), {"PPI-1", "PPI-D1", "CLK-5"})

    def test_silent_bullet_without_id_kept(self):
        text = ("#### SILENT (CLK)\n\n- CLK-1: phase open,\n  continued line\n"
                "- The power-up count (no reset).\n\n#### SILENT (IE4)\n- IE4-9: other\n")
        self.assertEqual(
            cr.silent_bullets(text, "CLK"),
            ["CLK-1: phase open, continued line", "The power-up count (no reset)."])
        self.assertEqual(cr.silent_bullets(text, "IE4"), ["IE4-9: other"])
        self.assertEqual(cr.silent_bullets(text, "PPI"), [])


class Brackets(unittest.TestCase):
    def test_source_ids(self):
        text = ("[ГФ24] [ВМ80] [ИЕ4] [7490] [2716] [74198] [C78] [AP-62] [R87-…] [R87-3] [D8275K] "
                "[ИР13] [ТМ2]")
        self.assertEqual(cr.BRACKET.findall(text),
                         ["ГФ24", "ВМ80", "ИЕ4", "7490", "2716", "74198", "C78", "AP-62", "R87-…",
                          "R87-3", "D8275K", "ИР13", "ТМ2"])

    def test_not_source_ids(self):
        text = ("bits [5:3] and [15:8], a [Link](x.md), [ГФ24](x.md), [7490](y.md), [12], [7], "
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
        self.assertEqual(listed[0].ids, frozenset({"CLK-20", "CLK-21"}))
        self.assertEqual(reg["RK86M-DEV"].status, "external")

    def test_bad_status_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text("| Prefix | Home | Status | IDs |\n|---|---|---|---|\n"
                         "| PPI | x | bogus | |\n", encoding="utf-8", newline="\n")
            with self.assertRaises(ValueError):
                cr.load_registry(p)


class Check(unittest.TestCase):
    def run_check(self, records, legacy_text=None, docs=None, **kw):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(Path(d) / "repo", records, **kw)
            legacy = None
            if legacy_text is not None:
                legacy = Path(d) / "legacy.md"
                legacy.write_text(legacy_text, encoding="utf-8", newline="\n")
            docs_root = None
            if docs is not None:
                docs_root = Path(d) / "docs-repo"
                for rel, text in docs.items():
                    p = docs_root / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(text, encoding="utf-8", newline="\n")
            return cr.check(root, legacy, docs_root)

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
        rec = PPI_RECORD + "\nBoard item VID-3 is pending.\n"
        out = self.run_check({"ics/intel/8255a/record.md": rec})
        self.assertEqual(self.errors(out), [])

    def test_split_prefix_listed_ids(self):
        recs = {
            "ics/intel/8224/record.md": "| CLK-1 | a |\n\nand CLK-20 lives on the board.\n",
            "ics/intel/8255a/record.md": PPI_RECORD,
        }
        out = self.run_check(recs)
        self.assertEqual(self.errors(out), [])
        # CLK-20 may not be defined here
        recs["ics/intel/8224/record.md"] += "| CLK-21 | wrong place |\n"
        out = self.errors(self.run_check(recs))
        self.assertTrue(any("CLK-21" in l for l in out))
        # CLK-22 is neither listed nor defined
        recs["ics/intel/8224/record.md"] = "| CLK-1 | a |\n\nCLK-22\n"
        out = self.errors(self.run_check(recs))
        self.assertTrue(any("CLK-22" in l for l in out))

    def test_duplicate_definition_fails(self):
        recs = {
            "ics/intel/8255a/record.md": PPI_RECORD,
            "ics/intel/8257/record.md": "| PPI-1 | again |\n",
        }
        out = self.errors(self.run_check(recs))
        self.assertTrue(any("PPI-1" in l and "twice" in l for l in out))

    def test_legacy_gate(self):
        legacy = "| PPI-1 | a |\n| PPI-2 | b |\n- PPI-D1 (x): y\n| VID-1 | pending |\n"
        recs = {"ics/intel/8255a/record.md": PPI_RECORD}
        out = self.errors(self.run_check(recs, legacy_text=legacy))
        self.assertEqual(len(out), 1)
        self.assertIn("PPI-2", out[0])
        recs["ics/intel/8255a/record.md"] += "| PPI-2 | now defined |\n"
        out = self.errors(self.run_check(recs, legacy_text=legacy))
        self.assertEqual(out, [])

    def test_docs_root_absent_reports_not_checked(self):
        legacy = "| CLK-20 | board |\n| RK86M-DEV-1 | dev |\n"
        recs = {"ics/intel/8255a/record.md": PPI_RECORD}
        out = self.run_check(recs, legacy_text=legacy)
        self.assertEqual(self.errors(out), [])
        self.assertTrue(any("board IDs not checked" in l for l in out))

    def test_docs_root_present_checks_external(self):
        legacy = "| CLK-20 | board |\n"
        recs = {"ics/intel/8255a/record.md": PPI_RECORD}
        out = self.errors(self.run_check(recs, legacy_text=legacy, docs={"b.md": "| CLK-99 | x |\n"}))
        self.assertTrue(any("CLK-20" in l for l in out))
        out = self.run_check(recs, legacy_text=legacy, docs={"b.md": "| CLK-20 | x |\n"})
        self.assertEqual(out, [])

    def test_missing_docs_root_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(Path(d) / "repo", {"ics/intel/8255a/record.md": PPI_RECORD})
            out = cr.check(root, None, Path(d) / "nope")
        self.assertTrue(any("docs root" in l for l in out))

    def test_missing_docs_root_only_the_error(self):
        # an external ID is referenced, but the "not checked" note would contradict --docs
        with tempfile.TemporaryDirectory() as d:
            recs = {"ics/intel/8224/record.md": "| CLK-1 | a |\n\nCLK-20 is on the board.\n"}
            root = make_repo(Path(d) / "repo", recs)
            out = cr.check(root, None, Path(d) / "nope")
        self.assertEqual(out, ["docs root nope not found"])

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
