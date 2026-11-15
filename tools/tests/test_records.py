# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""The IC records and their folders: files, IDs, sections, model line citations, links."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_records as cr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
RECORDS = {
    "CPU": "ics/intel/8080a",
    "PPI": "ics/intel/8255a",
    "DMA": "ics/intel/8257",
    "CRT": "ics/intel/8275",
}
FOLDER_FILES = ("README.md", "record.md", "equivalents.md", "implementation.md", "AGENTS.md",
                "datasheets/index.md")
# a citation of model lines in a record: `<file>.v:<line>[-<line>][, <line>...]`
LINE_CITATION = re.compile(r"`([A-Za-z0-9_]+\.v):(\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*)`")
# the decisions of the 8275 record where the data sheets are silent, in this order
CRT_DECISIONS = ["S11 / S12 order", "S11 / CRT-25 underrun restart",
                 "CRT-21 burst space reference point", "CRT-25 DU set moment",
                 "CRT-33 / CRT-34 cursor and VSP"]
NOT_SOURCES = "Not sources of behaviour: emulators and other cores."
# a markdown link: [text](target)
LINK = re.compile(r"\]\(([^)\s]+)\)")
# a bracket token that may be a source ID, Latin or Cyrillic
ANY_BRACKET = re.compile(r"\[([^\]\s]+)\]")


def section(md_text, heading):
    """The body of the level-2 section `## <heading>`, up to the next level-2 heading."""
    out, inside = [], False
    for line in md_text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == heading
            continue
        if inside:
            out.append(line)
    return "\n".join(out) if out or inside else None


def ics_markdown():
    return sorted((ROOT / "ics").rglob("*.md")) if (ROOT / "ics").is_dir() else []


class Records(unittest.TestCase):

    def test_folders_complete(self):
        for prefix, folder in RECORDS.items():
            for name in FOLDER_FILES:
                p = ROOT / folder / name
                self.assertTrue(p.is_file(), "%s/%s" % (folder, name))
                data = p.read_bytes()
                self.assertNotIn(b"\r", data, p.name)
                self.assertTrue(data.endswith(b"\n") and not data.endswith(b"\n\n"),
                                "%s/%s" % (folder, name))

    def test_ids_per_record(self):
        defined = set()
        for prefix, folder in RECORDS.items():
            ids = cr.defined_ids((ROOT / folder / "record.md").read_text(encoding="utf-8"))
            self.assertTrue(ids, folder)
            self.assertTrue(all(cr.prefix_of(i) == prefix for i in ids), (folder, sorted(ids)))
            self.assertTrue(defined.isdisjoint(ids))
            defined |= ids

    def test_ppi_edition_differences_rows(self):
        text = (ROOT / RECORDS["PPI"] / "record.md").read_text(encoding="utf-8")
        body = section(text, "Edition differences (PPI-Dn)")
        self.assertIsNotNone(body)
        self.assertEqual(cr.defined_ids(body), {"PPI-D%d" % n for n in range(1, 7)})

    def test_silent_sections(self):
        for prefix, folder in RECORDS.items():
            text = (ROOT / folder / "record.md").read_text(encoding="utf-8")
            body = section(text, "SILENT (%s)" % prefix)
            self.assertIsNotNone(body, "%s: no '## SILENT (%s)'" % (folder, prefix))

    def test_notation_section(self):
        for prefix, folder in RECORDS.items():
            body = section((ROOT / folder / "record.md").read_text(encoding="utf-8"), "Notation")
            self.assertIsNotNone(body, folder)
            self.assertNotIn("testbenches", body, folder)
            # D-numbers of a design document only where the record defines them
            for d in re.findall(r"\bD1[1-3]\b", body):
                self.assertIn(d + " = ", body, (folder, d))

    def test_crt_decisions(self):
        text = (ROOT / RECORDS["CRT"] / "record.md").read_text(encoding="utf-8")
        body = section(text, "SILENT (CRT)")
        self.assertIn("\n### Decisions\n", "\n" + body + "\n")
        decisions = body.split("### Decisions", 1)[1]
        heads = [l[2:] for l in decisions.splitlines() if l.startswith("- ")]
        self.assertEqual(len(heads), len(CRT_DECISIONS))
        for head, want in zip(heads, CRT_DECISIONS):
            self.assertTrue(head.startswith(want + " ("), head[:60])

    def test_model_line_citations(self):
        # a cited model line is a line of the IC's own rtl/ file under its current name
        seen = 0
        for folder in RECORDS.values():
            text = (ROOT / folder / "record.md").read_text(encoding="utf-8")
            for name, spans in LINE_CITATION.findall(text):
                path = ROOT / folder / "rtl" / name
                self.assertTrue(path.is_file(), (folder, name))
                count = len(path.read_text(encoding="utf-8").splitlines())
                for span in spans.split(", "):
                    lo, _, hi = span.partition("-")
                    self.assertTrue(1 <= int(lo) <= int(hi or lo) <= count, (name, span))
                    seen += 1
        self.assertGreaterEqual(seen, 12)

    def test_not_sources_sentence(self):
        for folder in RECORDS.values():
            text = (ROOT / folder / "record.md").read_text(encoding="utf-8")
            self.assertNotIn("- Not sources of behaviour:", text, folder)
            self.assertIn("\n" + NOT_SOURCES + "\n", text, folder)

    def test_no_private_links(self):
        files = ics_markdown()
        self.assertTrue(files)
        root = ROOT.resolve()
        for p in files:
            text = p.read_text(encoding="utf-8")
            rel = p.relative_to(ROOT).as_posix()
            for target in LINK.findall(text):
                if re.match(r"[a-z]+://", target):
                    continue
                path = target.split("#", 1)[0]
                if not path:
                    continue
                dest = (p.parent / path).resolve()
                self.assertTrue(dest == root or root in dest.parents, (rel, target))
                self.assertTrue(dest.exists(), (rel, target))

    def test_datasheet_index_rows(self):
        sources = {}
        for cells in cr.table_rows((ROOT / "docs" / "sources.md").read_text(encoding="utf-8")):
            first = cr._clean(cells[0])
            if len(cells) >= 3 and first.startswith("["):
                sources[first.strip("[]")] = cr._clean(cells[1])
        for prefix, folder in RECORDS.items():
            rec = (ROOT / folder / "record.md").read_text(encoding="utf-8")
            cited = {s for s in ANY_BRACKET.findall(rec) if cr._source_known(s, set(sources))}
            cited = {next((k for k in sources if k == s or
                           (k.endswith("…") and s.startswith(k[:-1]))), s) for s in cited}
            index = (ROOT / folder / "datasheets" / "index.md").read_text(encoding="utf-8")
            rows = {cr._clean(c[0]).strip("[]") for c in cr.table_rows(index)}
            self.assertEqual(sorted(cited - rows), [], folder)
            own = {s for s, home in sources.items()
                   if home == "retroICs/%s/datasheets/index.md" % folder}
            self.assertLessEqual(own, rows, folder)


if __name__ == "__main__":
    unittest.main()
