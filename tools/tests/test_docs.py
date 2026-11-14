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
BOARD = "retroComputersDocs/computers/rk86/board.md"

# the record ID prefixes of the legacy RK86 record
RECORD_PREFIXES = {"CPU", "PPI", "DMA", "CRT", "CLK", "IE4",
                   "VID", "GLUE", "MEM", "TAPE", "SND", "ROMD"}
HERE = {
    "CPU": "retroICs/ics/intel/8080a/record.md",
    "PPI": "retroICs/ics/intel/8255a/record.md",
    "DMA": "retroICs/ics/intel/8257/record.md",
    "CRT": "retroICs/ics/intel/8275/record.md",
    "CLK": "retroICs/ics/intel/8224/record.md",
    "IE4": "retroICs/ics/ti/sn7492/record.md",
}
PENDING = {
    "VID": BOARD, "GLUE": BOARD, "MEM": BOARD, "TAPE": BOARD, "SND": BOARD,
    "ROMD": "retroComputersDocs/computers/rk86/romdisk-module.md",
}
# bracket source IDs that docs/sources.md must list
REQUIRED_SOURCES = {"C78", "D79", "D84", "D8224", "D8255", "D8080N", "D8275K", "DG81", "AP-62",
                  "UM83", "K14", "R86", "R86-4", "R86-6", "R87-…", "MON", "APG", "EMU", "MAME"}
LICENCE_TEXTS = {
    "BSD-3-Clause.txt": "Neither the name of the copyright holder nor the names of its",
    "CC-BY-4.0.txt": "Attribution 4.0 International",
    "CC-BY-3.0.txt": "Attribution 3.0 Unported",
    "LicenseRef-Tselikov-BSD.txt": "Copyright (c) 2011 Dmitry Tselikov",
}
# the fork's src/LICENSE.TXT at d995355, CR LF changed to LF
TSELIKOV_SHA256 = "b0cf254cf4fc01b63480dda8927276ff26ac67951bc19f93a187a878aa9cc9d1"
# spdx/license-list-data, text/<id>.txt (main, 2026-11-14), bytes as downloaded (already LF)
SPDX_SHA256 = {
    "BSD-3-Clause.txt": "5a93d5831e1297ab10fe643e1a631e83be392896da14ee2951285a79012df69d",
    "CC-BY-4.0.txt": "d557539df68e771cc1eedcc91d13f70fca930e508d11eedcafa4b15db49e3744",
    "CC-BY-3.0.txt": "e6bc9e9c474700b708f568bac9e5a8a9bcb2b1dad53442f5ba449fcb848b8e76",
}
ATTRIBUTION = ("Contains retroICs / retroMachines by Dmitry Veremeev (BarabashkaD), "
               "https://github.com/BarabashkaD, BSD-3-Clause and CC BY 4.0. Credit to Dmitry "
               "Veremeev (BarabashkaD) must be kept in copies and derived works.")
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
        self.assertEqual({p for p in prefixes if p.endswith("-DEV")}, {"RK86M-DEV", "RKPOCKET-DEV"})

    def test_registry_homes_and_statuses(self):
        whole = {r.prefix: r for r in self.reg.values() if r.ids is None}
        for p, home in HERE.items():
            self.assertEqual((whole[p].home, whole[p].status), (home, "here"), p)
        for p, home in PENDING.items():
            self.assertEqual((whole[p].home, whole[p].status), (home, "pending"), p)
        for p in ("CLK", "IE4"):
            listed = [r for r in self.reg.values() if r.prefix == p and r.ids]
            self.assertEqual(len(listed), 1, p)
            self.assertEqual((listed[0].home, listed[0].status), (BOARD, "external"), p)
            self.assertTrue(all(cr.prefix_of(i) == p and cr.ID_FULL.fullmatch(i)
                                for i in listed[0].ids), listed[0].ids)

    def test_check_records_passes(self):
        out = [l for l in cr.check(ROOT, None, None) if not l.startswith("NOTE")]
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

    def test_sources_cover_legacy(self):
        legacy = os.environ.get("RETRO_LEGACY_RECORD")
        if not legacy:
            reason = ("RETRO_LEGACY_RECORD is not set: the legacy record is private; the "
                      "maintainer sets it before changing a record")
            print("SKIP test_sources_cover_legacy: " + reason, file=sys.stderr)
            self.skipTest(reason)
        text = Path(legacy).read_text(encoding="utf-8")
        found = {s for s in cr.BRACKET.findall(text) if len(s) > 1}
        self.assertTrue(found)
        known = set(sources_table())
        missing = sorted(s for s in found if not cr._source_known(s, known))
        self.assertEqual(missing, [])
        # and every record ID prefix of the legacy record is registered
        reg = cr.load_registry(ROOT / "docs" / "record-ids.md")
        unknown = sorted(i for i in cr.legacy_ids(text) if cr.resolve(reg, i) is None)
        self.assertEqual(unknown, [])


class Licences(unittest.TestCase):
    def test_notice_attribution(self):
        text = (ROOT / "NOTICE").read_text(encoding="utf-8")
        self.assertIn(ATTRIBUTION, text.splitlines())  # the attribution line, one line as it is
        self.assertIn("Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD", text)
        self.assertNotIn("@", text)
        lic = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(lic.startswith("Copyright (c) 2026, Dmitry Veremeev (BarabashkaD), "
                                       "https://github.com/BarabashkaD\n"), lic[:120])
        self.assertIn("Neither the name of the copyright holder", lic)
        self.assertNotIn("@", lic)

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
        files.append(ROOT / ".github" / "workflows" / "checks.yml")
        self.assertGreaterEqual(len(files), 7)
        for p in files:
            head = p.read_text(encoding="utf-8").splitlines()[:2]
            self.assertEqual(head, ["# " + SPDX_ID, "# " + SPDX_COPYRIGHT],
                             p.relative_to(ROOT).as_posix())

    def test_agents_names_the_legacy_gate(self):
        text = one_line((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("Before changing a record: set RETRO_LEGACY_RECORD to the private legacy record "
                      "and run the suite; the legacy tests must run, not skip.", text)

    def test_review_checklist_lines(self):
        lines = (ROOT / "docs" / "agents" / "review-checklist.md").read_text(
            encoding="utf-8").splitlines()
        items = [l for l in lines if l.startswith("- ")]
        self.assertGreaterEqual(len(items), 10)


if __name__ == "__main__":
    unittest.main()
