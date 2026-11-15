# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""The repo stays generic: no computer, platform or project it was built for or that uses it is
named, no fork or commit of another repo is named as the origin of a file, and no record ID of
another repo is cited, outside the allowed exceptions.

The exceptions (GENERIC_EXEMPT, keyed by file, word and a fragment of the line, so a new mention on
another line still fails): credits of the origin of a third-party base (where the third-party
models and their licence text were taken from), third-party notices kept as they are, quoted
vendor text, data sheet provenance (where a stored copy came from), a real system cited as
evidence by its source ID, a comparison-only source named in a source list, the test fixtures of
the -DEV-n ID pattern, and a language keyword spelt like a word of the list (the Verilog fork).
CHANGELOG.md (history) and this file are not read; binary files and LICENSES/*.txt are skipped.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wordscan import ROOT, wording_files  # noqa: E402

GENERIC_WORDS = [r"radio-?86", r"\brk-?86", r"rk86_", r"pocket", r"karabas", r"retroMachines",
                 r"apogee", r"mister", r"openfpga", r"analogue", r"микроша", r"ют-88", r"апогей",
                 r"\b8224\b", r"sn7492", r"ие4", r"clocks16", r"machine16", r"run_sim\.py",
                 r"\b(?:CLK|IE4|VID|GLUE|MEM|TAPE|SND|ROMD)-\d+\b", r"-DEV-\d+", r"\bfork\b",
                 r"35e86e7|d995355|dbb92cb"]
WORDS = [re.compile(w, re.I) for w in GENERIC_WORDS]
NOT_READ = {"CHANGELOG.md", "tools/tests/test_generic.py"}

CREDIT = "credit: origin of a third-party base"
NOTICE3 = "third-party notice kept as it is"
QUOTE = "quoted vendor text"
PROVENANCE = "data sheet provenance: where the stored copy came from"
EVIDENCE = "a real system cited as evidence by its source ID"
COMPARISON = "a comparison-only source named in a source list"
FIXTURE = "a test fixture of the ID pattern"
KEYWORD = "a language keyword spelt like a word of the list"
REASONS = (CREDIT, NOTICE3, QUOTE, PROVENANCE, EVIDENCE, COMPARISON, FIXTURE, KEYWORD)


def _entries(rel, frag, words, reason):
    return {(rel, w, frag): reason for w in words}


APOGEE = ("apogee", "mister")
GENERIC_EXEMPT = {
    # credits: the origin of a third-party base (the 8080 model, Tselikov's 8257 and 8275 and his
    # licence text); a fork or a project that uses this repo is named nowhere
    **_entries("LICENSES/README.md",
               "| `LICENSE.TXT` of MiSTer-devel/Apogee_MiSTer at `4b37da2` (the base", APOGEE,
               CREDIT),
    **_entries("NOTICE", "Apogee_MiSTer rtl/k580vm80a.v at 4b37da2, line endings", APOGEE, CREDIT),
    **_entries("NOTICE", "MiSTer-devel/Apogee_MiSTer at 4b37da2. The owner rewrote", APOGEE, CREDIT),
    **_entries("ics/intel/8080a/AGENTS.md",
               "(taken from MiSTer-devel/Apogee_MiSTer `rtl/k580vm80a.v` at `4b37da2`, line endings",
               APOGEE, CREDIT),
    **_entries("ics/intel/8080a/README.md",
               "MiSTer-devel/Apogee_MiSTer `rtl/k580vm80a.v` at `4b37da2`, line endings changed",
               APOGEE, CREDIT),
    **_entries("ics/intel/8257/AGENTS.md",
               "from Tselikov's `k580vt57.v` (MiSTer-devel/Apogee_MiSTer `4b37da2`", APOGEE, CREDIT),
    **_entries("ics/intel/8257/README.md", "`k580vt57.v` of MiSTer-devel/Apogee_MiSTer at", APOGEE,
               CREDIT),
    **_entries("ics/intel/8257/rtl/intel_8257.v", "// Base: MiSTer-devel/Apogee_MiSTer", APOGEE,
               CREDIT),
    **_entries("ics/intel/8275/AGENTS.md",
               "with Sorgelig's modifications (MiSTer-devel/Apogee_MiSTer `4b37da2`", APOGEE, CREDIT),
    **_entries("ics/intel/8275/README.md", "Sorgelig's modifications, of MiSTer-devel/Apogee_MiSTer",
               APOGEE, CREDIT),
    **_entries("ics/intel/8275/rtl/intel_8275.v", "// Modifications: Sorgelig (MiSTer-devel/Apogee_MiSTer",
               APOGEE, CREDIT),
    **_entries("tools/tests/test_docs.py", "# LICENSE.TXT of MiSTer-devel/Apogee_MiSTer at 4b37da2",
               APOGEE, CREDIT),
    **_entries("tools/tests/test_docs.py",
               '"Taken from MiSTer-devel/Apogee_MiSTer rtl/k580vm80a.v at 4b37da2"', APOGEE, CREDIT),
    # the Verilog keyword fork (fork ... join)
    **_entries("ics/intel/8257/tb/tb_vt57_func.v", "fork : lbl", ("fork",), KEYWORD),
    # Tselikov's notice, kept as it is
    **_entries("ics/intel/8257/rtl/intel_8257.v", "Radio-86RK FPGA REPLICA", ("radio-86",), NOTICE3),
    **_entries("ics/intel/8275/rtl/intel_8275.v", "Radio-86RK FPGA REPLICA", ("radio-86",), NOTICE3),
    **_entries("tools/tests/test_headers.py", "Radio-86RK FPGA REPLICA", ("radio-86",), NOTICE3),
    # quoted vendor text
    **_entries("ics/intel/8257/record.md", "\"An asynchronous input (generally from an 8224 device)",
               ("8224",), QUOTE),
    # data sheet provenance: where a stored or listed copy came from
    **_entries("ics/intel/8080a/datasheets/index.md",
               "| Copied from | skiselev/radio-86rk at c5e9cb7, `Documentation/INS8080A.pdf`",
               ("radio-86",), PROVENANCE),
    **_entries("ics/intel/8080a/datasheets/index.md",
               "skiselev/radio-86rk/raw/c5e9cb7/Documentation/INS8080A.pdf", ("radio-86",),
               PROVENANCE),
    **_entries("ics/intel/8080a/datasheets/index.md",
               "| Copied from | skiselev/radio-86rk at c5e9cb7, `Documentation/kr580vm80a.pdf`",
               ("radio-86",), PROVENANCE),
    **_entries("ics/intel/8080a/datasheets/index.md",
               "skiselev/radio-86rk/raw/c5e9cb7/Documentation/kr580vm80a.pdf", ("radio-86",),
               PROVENANCE),
    **_entries("ics/intel/8255a/datasheets/index.md",
               "| Copied from | skiselev/radio-86rk at c5e9cb7, `Documentation/Intel - 8255.pdf`",
               ("radio-86",), PROVENANCE),
    **_entries("ics/intel/8255a/datasheets/index.md",
               "skiselev/radio-86rk/raw/c5e9cb7/Documentation/Intel%20-%208255.pdf", ("radio-86",),
               PROVENANCE),
    **_entries("ics/intel/8275/datasheets/index.md",
               "| Copied from | skiselev/radio-86rk at c5e9cb7, `Documentation/Intel - 8275.pdf`",
               ("radio-86",), PROVENANCE),
    **_entries("ics/intel/8275/datasheets/index.md",
               "skiselev/radio-86rk/raw/c5e9cb7/Documentation/Intel%20-%208275.pdf", ("radio-86",),
               PROVENANCE),
    # a real system cited as evidence by its source ID: the source rows and source lists
    **_entries("docs/sources.md", "| [R86] | retroComputersDocs/computers/rk86/index.md |",
               ("rk86",), EVIDENCE),
    **_entries("docs/sources.md", "| [K14] | retroComputersDocs/computers/rk86/index.md |",
               ("rk86", "radio-86"), EVIDENCE),
    **_entries("docs/sources.md", "| [MON] | retroComputersDocs/computers/rk86/index.md |",
               ("rk86",), EVIDENCE),
    **_entries("ics/intel/8080a/datasheets/index.md",
               "| [R86] | retroComputersDocs/computers/rk86/index.md | see home", ("rk86",), EVIDENCE),
    **{("ics/intel/8275/datasheets/index.md", "rk86",
        "| %s | retroComputersDocs/computers/rk86/index.md | see home" % sid): EVIDENCE
       for sid in ("[R86]", "[K14]", "[MON]")},
    **_entries("ics/intel/8275/record.md", "- [R86] Радио 1986 No. 5, pp. 32-33, Fig. 3",
               ("radio-86",), EVIDENCE),
    **_entries("ics/intel/8275/record.md", "- [K14] Kiselev rev. 1.4: skiselev/radio-86rk",
               ("radio-86",), EVIDENCE),
    # comparison-only sources (emulators, other cores) named in a source list or source row
    **_entries("docs/sources.md", "| [APG] | retroComputersDocs/computers/rk86/index.md |",
               ("rk86",) + APOGEE, COMPARISON),
    **_entries("docs/sources.md", "| [MAME] | retroComputersDocs/computers/rk86/index.md |",
               ("rk86", "radio86"), COMPARISON),
    **_entries("docs/sources.md", "| [EMU] | retroComputersDocs/computers/rk86/index.md |",
               ("rk86",), COMPARISON),
    **_entries("ics/intel/8257/datasheets/index.md",
               "| [APG] | retroComputersDocs/computers/rk86/index.md | see home", ("rk86",),
               COMPARISON),
    **{("ics/intel/8275/datasheets/index.md", "rk86",
        "| %s | retroComputersDocs/computers/rk86/index.md | see home" % sid): COMPARISON
       for sid in ("[APG]", "[MAME]", "[EMU]")},
    **_entries("ics/intel/8257/record.md", "- [APG] MiSTer-devel/Apogee_MiSTer `4b37da2`", APOGEE,
               COMPARISON),
    **_entries("ics/intel/8275/record.md", "- [MAME] mamedev/mame master at `d077ea2`",
               ("radio86",), COMPARISON),
    **_entries("ics/intel/8275/record.md", "- [APG] MiSTer-devel/Apogee_MiSTer `4b37da2`", APOGEE,
               COMPARISON),
    # fixtures of the -DEV-n ID pattern
    **_entries("tools/tests/test_check_records.py", 'text = "| DEMO-DEV-1', ("-dev-1", "-dev-2"),
               FIXTURE),
    **_entries("tools/tests/test_check_records.py", 'cr.defined_ids(text), {"DEMO-DEV-1"',
               ("-dev-1", "-dev-2"), FIXTURE),
    **_entries("tools/tests/test_check_records.py", "See QQ-DEV-1.", ("-dev-1",), FIXTURE),
    **_entries("tools/tests/test_check_records.py", 'any("QQ-DEV-1" in l', ("-dev-1",), FIXTURE),
    **_entries("tools/tests/test_check_records.py", "OSC-20 and DEMO-DEV-1.", ("-dev-1",), FIXTURE),
}


def hits(text, rel, exempt):
    """[(line number, word)] of the words in text that no exemption of rel covers."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for w in WORDS:
            for m in w.finditer(line):
                key = m.group(0).lower()
                if any(p == rel and kw == key and frag in line for (p, kw, frag) in exempt):
                    continue
                out.append((n, m.group(0)))
    return out


def scan(repo=ROOT, exempt=None):
    exempt = GENERIC_EXEMPT if exempt is None else exempt
    out = {}
    for rel, data in wording_files(repo):
        if rel in NOT_READ:
            continue
        found = hits(data.decode("utf-8", errors="replace"), rel, exempt)
        if found:
            out[rel] = found
    return out


class Generic(unittest.TestCase):
    def test_no_project_words(self):
        self.assertEqual(scan(), {})

    def test_exempt_entries_not_stale(self):
        stale = []
        for (rel, word, frag), reason in sorted(GENERIC_EXEMPT.items()):
            self.assertIn(reason, REASONS, (rel, word))
            p = ROOT / rel
            lines = p.read_text(encoding="utf-8").splitlines() if p.is_file() else []
            if not any(frag in l and word in l.lower() for l in lines):
                stale.append((rel, word, frag))
        self.assertEqual(stale, [])

    def test_exemption_is_per_line(self):
        text = "credit: the Karabas core\nthe Karabas machine\n"
        exempt = {("a.md", "karabas", "credit:"): CREDIT}
        self.assertEqual(hits(text, "a.md", exempt), [(2, "Karabas")])
        self.assertEqual(hits("see CLK-11 and GLUE-3\n", "a.md", {}), [(1, "CLK-11"), (1, "GLUE-3")])

    def test_words(self):
        # a name joined by an underscore (a word character) is still caught
        self.assertEqual(hits("pocket_memory.v\n", "a.md", {}), [(1, "pocket")])
        self.assertEqual(hits("radio86rk_pocket\n", "a.md", {}), [(1, "radio86"), (1, "pocket")])


if __name__ == "__main__":
    unittest.main()
