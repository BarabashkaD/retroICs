# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Repository docs: record-ID registry, sources, NOTICE and licence texts, L0 files."""
import hashlib
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_records as cr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
# the record ID prefixes of the registry: this repo's own, and the retired ones
RECORD_PREFIXES = {"CPU", "PPI", "DMA", "CRT", "CLK", "IE4"}
HERE = {
    "CPU": "retroICs/ics/intel/8080a/record.md",
    "PPI": "retroICs/ics/intel/8255a/record.md",
    "DMA": "retroICs/ics/intel/8257/record.md",
    "CRT": "retroICs/ics/intel/8275/record.md",
}
# bracket source IDs that docs/sources.md must list
REQUIRED_SOURCES = {"C78", "D79", "D84", "D8255", "D8080N", "D8275K", "DG81", "AP-62", "ВМ80",
                    "UM83", "K14", "R86", "MON", "APG", "EMU", "MAME"}
LICENCE_TEXTS = {
    "BSD-3-Clause.txt": "Neither the name of the copyright holder nor the names of its",
    "CC-BY-4.0.txt": "Attribution 4.0 International",
    "CC-BY-3.0.txt": "Attribution 3.0 Unported",
    "LicenseRef-Tselikov-BSD.txt": "Copyright (c) 2011 Dmitry Tselikov",
}
# LICENSE.TXT of MiSTer-devel/Apogee_MiSTer at 4b37da2, CR LF changed to LF
TSELIKOV_SHA256 = "b0cf254cf4fc01b63480dda8927276ff26ac67951bc19f93a187a878aa9cc9d1"
# spdx/license-list-data, text/<id>.txt (main, 2026-11-14), bytes as downloaded (already LF)
SPDX_SHA256 = {
    "BSD-3-Clause.txt": "5a93d5831e1297ab10fe643e1a631e83be392896da14ee2951285a79012df69d",
    "CC-BY-4.0.txt": "d557539df68e771cc1eedcc91d13f70fca930e508d11eedcafa4b15db49e3744",
    "CC-BY-3.0.txt": "e6bc9e9c474700b708f568bac9e5a8a9bcb2b1dad53442f5ba449fcb848b8e76",
}
ATTRIBUTION = ("Contains retroICs by Dmitry Veremeev (BarabashkaD), "
               "https://github.com/BarabashkaD, BSD-3-Clause and CC BY 4.0.")
SPDX_ID = "SPDX-License-Identifier: BSD-3-Clause"
SPDX_COPYRIGHT = ("SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), "
                  "https://github.com/BarabashkaD")
DOCS = ["README.md", "AGENTS.md", "NOTICE", "CHANGELOG.md", "LICENSE", "LICENSES/README.md",
        "docs/agents/global.md", "docs/agents/review-checklist.md", "docs/conventions.md",
        "docs/vendors.md", "docs/record-ids.md", "docs/sources.md", "docs/sources-policy.md",
        "docs/quickstart.md"]
TEMPLATES = ["README.md", "record.md", "equivalents.md", "implementation.md", "AGENTS.md"]


def sources_table():
    out = {}
    for cells in cr.table_rows((ROOT / "docs" / "sources.md").read_text(encoding="utf-8")):
        first = cr._clean(cells[0])
        if len(cells) < 3 or first == "ID" or set(first) <= set("-: "):
            continue
        out[first.strip("[]")] = (cr._clean(cells[1]), cr._clean(cells[2]))
    return out


def one_line(text):
    return " ".join(text.split())


class Registry(unittest.TestCase):
    def setUp(self):
        self.reg = cr.load_registry(ROOT / "docs" / "record-ids.md")

    def test_registry_prefixes(self):
        prefixes = {r.prefix for r in self.reg.values()}
        self.assertEqual({p for p in prefixes if not p.endswith("-DEV")}, RECORD_PREFIXES)
        self.assertEqual({p for p in prefixes if p.endswith("-DEV")}, set())

    def test_registry_homes_and_statuses(self):
        whole = {r.prefix: r for r in self.reg.values() if r.ids is None}
        for p, home in HERE.items():
            self.assertEqual((whole[p].home, whole[p].status), (home, "here"), p)
        # no row of another repo's prefixes, none waiting for a home
        self.assertEqual([r.prefix for r in self.reg.values()
                          if r.status in ("external", "pending")], [])
        # the clock chips left with their docs to where they are implemented
        for p in ("CLK", "IE4"):
            self.assertEqual((whole[p].home, whole[p].status), ("-", "retired"), p)

    def test_check_records_passes(self):
        out = [l for l in cr.check(ROOT) if not l.startswith("NOTE")]
        self.assertEqual(out, [])


class Sources(unittest.TestCase):
    def test_sources_required(self):
        table = sources_table()
        self.assertLessEqual(REQUIRED_SOURCES, set(table))
        for sid in ("EMU", "MAME", "APG"):
            self.assertEqual(table[sid][1], "comparison-only", sid)
        for sid, (home, kind) in table.items():
            self.assertIn(kind, cr.KINDS, sid)
            self.assertTrue(home.startswith(("retroICs/ics/", "retroComputersDocs/computers/")),
                            (sid, home))
            if kind == "vendor" and home.startswith("retroICs/"):
                self.assertTrue(home.endswith("/datasheets/index.md"), (sid, home))


class Licences(unittest.TestCase):
    def test_notice_attribution(self):
        text = (ROOT / "NOTICE").read_text(encoding="utf-8")
        self.assertEqual(text.splitlines()[3], ATTRIBUTION)  # line 4, one line as it is
        self.assertIn("Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD", text)
        self.assertNotIn("@", text)
        lic = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(lic.startswith("Copyright (c) 2026, Dmitry Veremeev (BarabashkaD), "
                                       "https://github.com/BarabashkaD\n"), lic[:120])
        self.assertIn("Neither the name of the copyright holder", lic)
        self.assertNotIn("@", lic)

    def test_notice_imported_files(self):
        # the third-party models are in the repository: NOTICE names their licences, their original
        # authors and the source they were taken from, what a build must carry and the data sheets'
        # status; this repo only
        text = one_line((ROOT / "NOTICE").read_text(encoding="utf-8"))
        for phrase in ("k580vm80a.v", "LICENSES/CC-BY-3.0.txt", "at 4b37da2",
                       "die-derived 8080 model by Vslav (1801BM1), 2014",
                       "Taken from MiSTer-devel/Apogee_MiSTer rtl/k580vm80a.v at 4b37da2",
                       "from CRLF to LF", "https://github.com/1801BM1/vm80a",
                       "intel_8257.v and ics/intel/8275/rtl/intel_8275.v",
                       "derived from Dmitry Tselikov's k580vt57.v and k580vg75.sv",
                       "The owner rewrote both",
                       "kept from the base", "LicenseRef-Tselikov-BSD",
                       "LICENSES/LicenseRef-Tselikov-BSD.txt", "(trailing whitespace removed)",
                       "Sorgelig", "every Markdown file is under CC BY 4.0",
                       "under BSD-3-Clause (LICENSE, LICENSES/BSD-3-Clause.txt)",
                       "faults/*.patch", "Builds: a bitstream or netlist",
                       "https://creativecommons.org/licenses/by/3.0/",
                       "not licensed by this repo", "removed on request (open an issue)"):
            self.assertIn(phrase, text)
        # no text of another repo, and no other project the files passed through (the names
        # written in two parts, so this file holds none of them)
        for gone in ("roms/PROVENANCE.md", "retro" + "Machines", "keep their bytes",
                     "until their SPDX lines are set", "None is in", "must be kept in copies",
                     "first written", "import", " fo" + "rk", "Kara" + "bas"):
            self.assertNotIn(gone, text)

    def test_notice_ascii_lf(self):
        data = (ROOT / "NOTICE").read_bytes()
        self.assertEqual([b for b in data if b >= 0x80], [])
        self.assertNotIn(b"\r", data)
        self.assertTrue(data.endswith(b"\n") and not data.endswith(b"\n\n"))

    def test_spdx_texts_present(self):
        for name, phrase in LICENCE_TEXTS.items():
            p = ROOT / "LICENSES" / name
            self.assertTrue(p.is_file(), name)
            data = p.read_bytes()
            self.assertNotIn(b"\r", data, name)
            self.assertTrue(data.endswith(b"\n"), name)
            self.assertIn(phrase, one_line(data.decode("utf-8")), name)
        tselikov = (ROOT / "LICENSES" / "LicenseRef-Tselikov-BSD.txt").read_bytes()
        self.assertEqual(hashlib.sha256(tselikov).hexdigest(), TSELIKOV_SHA256)
        for name, digest in SPDX_SHA256.items():
            data = (ROOT / "LICENSES" / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, name)
        readme = (ROOT / "LICENSES" / "README.md").read_text(encoding="utf-8")
        self.assertIn("spdx/license-list-data", readme)
        for name in list(SPDX_SHA256) + ["LicenseRef-Tselikov-BSD.txt"]:
            self.assertIn(name, readme)


class Files(unittest.TestCase):
    def test_docs_present_lf(self):
        for rel in DOCS + ["docs/templates/ic/" + t for t in TEMPLATES]:
            p = ROOT / rel
            self.assertTrue(p.is_file(), rel)
            data = p.read_bytes()
            self.assertNotIn(b"\r", data, rel)
            self.assertTrue(data.endswith(b"\n") and not data.endswith(b"\n\n"), rel)

    def test_templates_headings_only(self):
        for t in TEMPLATES:
            lines = (ROOT / "docs" / "templates" / "ic" / t).read_text(encoding="utf-8").splitlines()
            body = [l for l in lines if l.strip() and not l.startswith("#")]
            self.assertEqual(body, [], t)
            self.assertTrue(any(l.startswith("# ") for l in lines), t)

    def test_global_rules_cover_l0(self):
        text = (ROOT / "docs" / "agents" / "global.md").read_text(encoding="utf-8").lower()
        for topic in ("source priority", "silent", "fidelity", "vendor-first", "pre-push",
                      "privacy-allow.txt", "spdx", "git diff", "tier", "mutation", "powershell"):
            self.assertIn(topic, text, topic)

    def test_spdx_headers_on_the_owners_code(self):
        files = sorted((ROOT / "tools").glob("*.py")) + sorted((ROOT / "tools" / "tests").glob("*.py"))
        files += sorted((ROOT / "tools" / "simrun").glob("*.py"))
        files.append(ROOT / ".github" / "workflows" / "checks.yml")
        files.append(ROOT / ".github" / "actions" / "setup-iverilog" / "action.yml")
        self.assertGreaterEqual(len(files), 14)
        for p in files:
            head = p.read_text(encoding="utf-8").splitlines()[:2]
            self.assertEqual(head, ["# " + SPDX_ID, "# " + SPDX_COPYRIGHT],
                             p.relative_to(ROOT).as_posix())

    def test_review_checklist_lines(self):
        lines = (ROOT / "docs" / "agents" / "review-checklist.md").read_text(
            encoding="utf-8").splitlines()
        items = [l for l in lines if l.startswith("- ")]
        self.assertGreaterEqual(len(items), 10)


if __name__ == "__main__":
    unittest.main()
