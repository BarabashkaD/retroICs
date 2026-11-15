# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Data sheet indexes (ics/*/*/datasheets/index.md) and the PDFs next to them.

Each source whose home is an index has a section "## [ID]" with the fields of
docs/sources-policy.md. Every field is filled, except Download (no direct link) and File (the
document is listed without the file; the reason is in Licence). The SHA-256 field starts with the
hash of the stored file, or of the file as copied when it is not stored. Every PDF is indexed and
passed the rewrite of docs/sources-policy.md (no metadata, one revision, no object streams).
"""
import hashlib
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_privacy as cp  # noqa: E402
import check_records as cr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
FIELDS = ("Title", "Vendor", "Document", "Edition", "Pages used", "Origin", "Copied from",
          "Download", "Licence", "SHA-256", "File")
MAY_BE_EMPTY = {"Download", "File"}
SUMMARY_HEAD = ["ID", "Home", "File", "SHA-256"]
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
SECTION = re.compile(r"^## (\[[^\]]+\])\s*$")
# keys of a document information dictionary that the rewrite clears
INFO_KEYS = re.compile(rb"/(Author|Creator|Producer|Title|Subject|Keywords|CreationDate|ModDate)\b")


def indexes(root=ROOT):
    return sorted((root / "ics").glob("*/*/datasheets/index.md"))


def summary_rows(text):
    """{ID: {column: value}} of the first table of an index (ID | Home | File | SHA-256)."""
    rows = list(cr.table_rows(text.split("\n## ", 1)[0]))
    if not rows or [cr._clean(c) for c in rows[0]] != SUMMARY_HEAD:
        return None
    out = {}
    for cells in rows[1:]:
        if set("".join(cells)) <= set("-: "):
            continue
        out[cr._clean(cells[0])] = dict(zip(SUMMARY_HEAD, (c.strip() for c in cells)))
    return out


def sections(text):
    """{ID: {field: value}} of every "## [ID]" section with a Field | Value table."""
    out = {}
    current = None
    for line in text.splitlines():
        m = SECTION.match(line)
        if m:
            current = m.group(1)
            out[current] = {}
            continue
        if line.startswith("#"):
            current = None
            continue
        cells = cr._cells(line)
        if current and cells and len(cells) == 2:
            key = cr._clean(cells[0])
            if key in ("Field",) or set(key) <= set("-: "):
                continue
            out[current][key] = cells[1].strip()
    return out


def file_cell(value):
    """The file name of a File cell (backticks dropped), or "" when the cell is empty."""
    return value.strip().strip("`").strip()


class DatasheetIndexes(unittest.TestCase):
    def setUp(self):
        self.indexes = indexes()
        self.assertEqual(len(self.indexes), 4)

    def test_index_fields_complete(self):
        for idx in self.indexes:
            rel = idx.relative_to(ROOT).as_posix()
            text = idx.read_text(encoding="utf-8")
            summary = summary_rows(text)
            self.assertIsNotNone(summary, rel)
            secs = sections(text)
            own = [i for i, row in summary.items() if row["Home"] == "this index"]
            self.assertEqual(sorted(own), sorted(secs), rel)
            for sid, row in summary.items():
                for col in ("ID", "Home", "SHA-256"):
                    self.assertTrue(row[col].strip(), (rel, sid, col))
                if row["Home"] != "this index":
                    self.assertEqual((row["File"], row["SHA-256"]), ("see home", "see home"),
                                     (rel, sid))
            for sid, fields in secs.items():
                self.assertEqual(sorted(fields), sorted(FIELDS), (rel, sid))
                for name in FIELDS:
                    if name not in MAY_BE_EMPTY:
                        self.assertTrue(fields[name].strip(), (rel, sid, name))
                self.assertNotIn("not checked yet", fields["Licence"], (rel, sid))
                self.assertTrue(HEX64.search(fields["SHA-256"]), (rel, sid))
                # the summary row repeats the section's file and first hash
                self.assertEqual(file_cell(summary[sid]["File"]), file_cell(fields["File"]),
                                 (rel, sid))
                self.assertEqual(HEX64.findall(summary[sid]["SHA-256"])[:1],
                                 HEX64.findall(fields["SHA-256"])[:1], (rel, sid))

    def test_sha256_matches(self):
        seen = 0
        for idx in self.indexes:
            for sid, fields in sections(idx.read_text(encoding="utf-8")).items():
                name = file_cell(fields.get("File", ""))
                if not name:
                    continue
                path = idx.parent / name
                self.assertTrue(path.is_file(), (idx, name))
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(HEX64.findall(fields["SHA-256"])[0], digest, (sid, name))
                seen += 1
        self.assertGreater(seen, 0)

    def test_every_pdf_indexed(self):
        for idx in self.indexes:
            named = {file_cell(f.get("File", ""))
                     for f in sections(idx.read_text(encoding="utf-8")).values()}
            named.discard("")
            stored = {p.name for p in idx.parent.iterdir() if p.name != "index.md"}
            self.assertEqual(sorted(stored), sorted(named), idx.relative_to(ROOT).as_posix())

    def test_pdfs_clean(self):
        allow = cp.load_allow(ROOT / "privacy-allow.txt")
        pdfs = sorted((ROOT / "ics").glob("*/*/datasheets/*.pdf"))
        self.assertTrue(pdfs)
        for p in pdfs:
            rel = p.relative_to(ROOT).as_posix()
            data = p.read_bytes()
            self.assertEqual(cp.scan_bytes(rel, data, allow), [], rel)
            # one revision, no object streams, no XMP, an empty or absent /Info
            self.assertEqual(data.count(b"startxref"), 1, rel)
            self.assertEqual(data.count(b"%%EOF"), 1, rel)
            self.assertNotIn(b"/ObjStm", data, rel)
            self.assertNotIn(b"/Metadata", data, rel)
            self.assertNotIn(b"/Encrypt", data, rel)
            self.assertIsNone(INFO_KEYS.search(data), rel)


class Parsers(unittest.TestCase):
    def test_sections_and_summary(self):
        text = ("# T\n\n| ID | Home | File | SHA-256 |\n|---|---|---|---|\n"
                "| [A1] | this index | `a.pdf` | " + "0" * 64 + " |\n"
                "| [B2] | elsewhere | see home | see home |\n\n"
                "## [A1]\n\n| Field | Value |\n|---|---|\n| Title | x |\n| File | `a.pdf` |\n")
        self.assertEqual(sorted(summary_rows(text)), ["[A1]", "[B2]"])
        self.assertEqual(sections(text), {"[A1]": {"Title": "x", "File": "`a.pdf`"}})
        self.assertEqual(file_cell("`a b.pdf`"), "a b.pdf")
        self.assertEqual(file_cell(""), "")


if __name__ == "__main__":
    unittest.main()
