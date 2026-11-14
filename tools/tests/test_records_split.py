# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""The six IC records split from the private legacy RK86 record: IDs and texts kept.

RecordsSplit checks the records alone and always runs. LegacySplit compares them with the legacy
record named by RETRO_LEGACY_RECORD (its path is never committed); without the variable it skips
with a printed reason. Before changing a record the maintainer sets the variable and runs the suite:
then the legacy tests must run, not skip.
"""
import io
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_privacy as cp  # noqa: E402
import check_records as cr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
LEGACY_COUNT = 171
RECORDS = {
    "CPU": "ics/intel/8080a",
    "CLK": "ics/intel/8224",
    "PPI": "ics/intel/8255a",
    "DMA": "ics/intel/8257",
    "CRT": "ics/intel/8275",
    "IE4": "ics/ti/sn7492",
}
FOLDER_FILES = ("README.md", "record.md", "equivalents.md", "implementation.md", "AGENTS.md",
                "datasheets/index.md")
# the only changes of SILENT bullet text (pattern on the legacy text, new text): a section
# reference that now points at another file, and a pointer to a private document in neutral words
SILENT_REWRITES = {
    "IE4": [(re.escape("(CLK SILENT)"), "(CLK SILENT, `ics/intel/8224/record.md`)")],
    "CLK": [(r"This is the \S+ \S+ \d+ SILENT item\.", "The model's checks list it as SILENT.")],
}
SKIP_REASON = ("RETRO_LEGACY_RECORD is not set: the legacy record is private; the maintainer sets "
               "it before changing a record")
# the decisions of the legacy list of SILENT points, in the 8275 record in this order
CRT_DECISIONS = ["S11 / S12 order", "S11 / CRT-25 underrun restart",
                 "CRT-21 burst space reference point", "CRT-25 DU set moment",
                 "CRT-33 / CRT-34 cursor and VSP"]
# Wording that points at private planning documents, generic patterns only. A task number followed
# by "record" is the name of the timing reference sections of the records and resolves here. The
# lines that define the patterns end with the marker below; in this file only, those lines are
# exempt from the generic patterns (never from the private word list).
PATTERN_MARK = "# wording-pattern"
PLAN_WORDING = re.compile(r"\bthe plan\b|\bplan's\b|\bTasks? \d+(?! record)|\bStep \d|\bspec \d"  # wording-pattern
                          r"|§|Assumptions of the plan|\bthe spec\b|\bthe brief\b|superpowers"  # wording-pattern
                          r"|\d+\.\d+ a-d of the 0\.8\.0 design", re.I)  # wording-pattern
# a controller as the one who decides; the chips' own controller words (the CRT controller and
# the Buffer Output Controller) are not matched
CONTROLLER_ACTOR = re.compile(r"\bcontroller(?:,| ruling| decision|\))|\bby the controller\b")  # wording-pattern
# more private words, one per line ('#' starts a comment), from an untracked file on the
# maintainer's PC named by this variable; without it only the generic patterns apply, and the
# test says so with this NOTE line
PRIVATE_WORDS_VAR = "RETRO_PRIVATE_WORDS"
GENERIC_ONLY_NOTE = "NOTE: private word list not set: generic patterns only"
# the one file whose marked lines are exempt from the generic patterns (never from the words)
OWN_FILE = "tools/tests/test_records_split.py"
BOARD_POINTER = "Board wiring of the pins: `retroComputersDocs/computers/rk86/board.md` (pending)."
# a markdown link: [text](target)
LINK = re.compile(r"\]\(([^)\s]+)\)")
# a bracket token that may be a source ID, Latin or Cyrillic
ANY_BRACKET = re.compile(r"\[([^\]\s]+)\]")


def private_words():
    """The extra words of RETRO_PRIVATE_WORDS, lower case; [] when the variable is not set."""
    path = os.environ.get(PRIVATE_WORDS_VAR)
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        raise AssertionError("%s does not name a file" % PRIVATE_WORDS_VAR)
    words = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            words.append(line.lower())
    return words


def words_for_scan():
    """private_words(), printing GENERIC_ONLY_NOTE to stderr when the variable is not set."""
    if not os.environ.get(PRIVATE_WORDS_VAR):
        print(GENERIC_ONLY_NOTE, file=sys.stderr)
    return private_words()


def wording_hits(text, words=(), skip_marked=False):
    """Every private wording in text: the generic patterns and the given words. With skip_marked,
    a line ending with PATTERN_MARK is exempt from the generic patterns only; the words are
    checked on every line."""
    found = set()
    for line in text.splitlines():
        if not (skip_marked and line.rstrip().endswith(PATTERN_MARK)):
            found |= {m.group(0) for m in PLAN_WORDING.finditer(line)}
            found |= {m.group(0) for m in CONTROLLER_ACTOR.finditer(line)}
        low = line.lower()
        found |= {w for w in words if w in low}
    return sorted(found)


def wording_files(repo=ROOT):
    """The files of the working tree as check_privacy sees them (tracked, and untracked but not
    ignored), as (repo-relative name, bytes). Skipped: binary files (a NUL byte in the first 8 KiB;
    no wording to read) and LICENSES/*.txt (the official licence texts, kept byte for byte)."""
    repo = Path(repo)
    out = []
    for f in cp.working_tree_files(repo):
        if not f.is_file():
            continue
        rel = f.relative_to(repo).as_posix()
        if rel.startswith("LICENSES/") and rel.endswith(".txt"):
            continue
        data = f.read_bytes()
        if b"\0" in data[:8192]:
            continue
        out.append((rel, data))
    return sorted(out)


def scan_repo(repo, words):
    """{name: hits} of every file of wording_files(repo) with a hit."""
    out = {}
    for rel, data in wording_files(repo):
        hits = wording_hits(data.decode("utf-8", errors="replace"), words,
                            skip_marked=(rel == OWN_FILE))
        if hits:
            out[rel] = hits
    return out


def legacy_text():
    path = os.environ.get("RETRO_LEGACY_RECORD")
    if not path:
        print("SKIP test_records_split legacy tests: " + SKIP_REASON, file=sys.stderr)
        raise unittest.SkipTest(SKIP_REASON)
    p = Path(path)
    if not p.is_file():
        raise AssertionError("RETRO_LEGACY_RECORD does not name a file")
    return p, p.read_text(encoding="utf-8")


def one_line(text):
    return " ".join(text.split())


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


class GateWithoutLegacy(unittest.TestCase):
    """legacy_text() and the legacy tests with the environment patched; stderr is captured."""

    def call(self, env):
        err = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), redirect_stderr(err):
            try:
                return legacy_text(), None, err.getvalue()
            except unittest.SkipTest as e:
                return None, str(e), err.getvalue()

    def test_skips_without_variable(self):
        got, skip, err = self.call({})
        self.assertIsNone(got)
        self.assertEqual(skip, SKIP_REASON)
        self.assertIn("SKIP", err)
        self.assertIn(SKIP_REASON, err)

    def test_github_actions_is_not_special(self):
        self.assertEqual(self.call({"GITHUB_ACTIONS": "true"}), self.call({}))

    def test_variable_set_runs_without_skip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "legacy.md"
            p.write_text("legacy\n", encoding="utf-8", newline="\n")
            got, skip, err = self.call({"RETRO_LEGACY_RECORD": str(p)})
        self.assertIsNone(skip)
        self.assertEqual(got[1], "legacy\n")
        self.assertNotIn("SKIP", err)

    def test_variable_naming_no_file_fails(self):
        with mock.patch.dict(os.environ, {"RETRO_LEGACY_RECORD": str(ROOT / "no-such-file.md")},
                             clear=True):
            with self.assertRaises(AssertionError) as cm:
                legacy_text()
        self.assertIn("does not name a file", str(cm.exception))

    def run_legacy_tests(self, env):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(LegacySplit)
        result = unittest.TestResult()
        with mock.patch.dict(os.environ, env, clear=True), redirect_stderr(io.StringIO()):
            suite.run(result)
        return suite, result

    def test_legacy_tests_run_when_variable_set(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "legacy.md"
            p.write_text("legacy\n", encoding="utf-8", newline="\n")
            suite, result = self.run_legacy_tests({"RETRO_LEGACY_RECORD": str(p)})
        self.assertEqual(result.skipped, [])
        self.assertEqual(result.testsRun, suite.countTestCases())
        self.assertGreater(result.testsRun, 0)

    def test_legacy_tests_skip_without_variable(self):
        _, result = self.run_legacy_tests({})
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(result.skipped[0][1], SKIP_REASON)


class PrivateWording(unittest.TestCase):
    """The wording scan itself."""

    def test_generic_patterns(self):
        text = "as the plan says\nsee Step 2 and spec 4\nthe brief\nsuperpowers/x\n"  # wording-pattern
        self.assertEqual(len(wording_hits(text)), 5)
        self.assertEqual(wording_hits("Timing reference (Task 1 record)\nthe planned model\n"), [])

    def test_marked_lines_skipped_only_on_request(self):
        text = "x = 'the spec'  " + PATTERN_MARK + "\n"  # wording-pattern
        self.assertEqual(wording_hits(text, skip_marked=True), [])
        self.assertEqual(wording_hits(text), ["the spec"])  # wording-pattern

    def test_controller_as_actor(self):
        hits = wording_hits("decided by the controller\n")  # wording-pattern
        self.assertEqual(hits, ["by the controller"])  # wording-pattern
        self.assertEqual(wording_hits("the CRT controller and the Buffer Output Controller\n"), [])

    def test_words_from_the_variable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "words.txt"
            p.write_text("# comment\nSecret-Name  # why\n\nother/folder/\n", encoding="utf-8",
                         newline="\n")
            with mock.patch.dict(os.environ, {PRIVATE_WORDS_VAR: str(p)}, clear=True):
                words = private_words()
        self.assertEqual(words, ["secret-name", "other/folder/"])
        self.assertEqual(wording_hits("see secret-NAME.md in other/folder/\n", words),
                         ["other/folder/", "secret-name"])

    @staticmethod
    def word_file(d, text="secret-name\n"):
        p = Path(d) / "words.txt"
        p.write_text(text, encoding="utf-8", newline="\n")
        return p

    def test_marked_line_still_checked_for_words(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.word_file(d)
            with mock.patch.dict(os.environ, {PRIVATE_WORDS_VAR: str(p)}, clear=True):
                words = private_words()
        line = "x = re.compile('secret-name|the spec')  " + PATTERN_MARK + "\n"  # wording-pattern
        self.assertEqual(wording_hits(line, words, skip_marked=True), ["secret-name"])

    def test_without_the_variable_only_generic_with_note(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stderr(err):
            self.assertEqual(words_for_scan(), [])
        self.assertEqual(err.getvalue(), GENERIC_ONLY_NOTE + "\n")

    def test_no_note_with_the_variable(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            p = self.word_file(d)
            with mock.patch.dict(os.environ, {PRIVATE_WORDS_VAR: str(p)}, clear=True), \
                    redirect_stderr(err):
                self.assertEqual(words_for_scan(), ["secret-name"])
        self.assertEqual(err.getvalue(), "")

    def test_variable_naming_no_file_fails(self):
        with mock.patch.dict(os.environ, {PRIVATE_WORDS_VAR: str(ROOT / "no-such-file.txt")},
                             clear=True):
            self.assertRaises(AssertionError, private_words)

    def test_scope_is_the_working_tree(self):
        names = {rel for rel, _ in wording_files()}
        for name in ("privacy-allow.txt", "README.md", "AGENTS.md", "NOTICE", ".gitignore",
                     "LICENSES/README.md", "docs/conventions.md", "tools/check_records.py",
                     OWN_FILE, ".github/workflows/checks.yml", "ics/intel/8257/record.md"):
            self.assertIn(name, names)
        self.assertFalse(any(n.startswith("LICENSES/") and n.endswith(".txt") for n in names))

    def test_new_top_level_file_reported(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir()
            cp._git(repo, "init", "-q")
            (repo / "NEWFILE.md").write_bytes(b"as the brief says\n")  # wording-pattern
            (repo / "data.bin").write_bytes(b"\0the brief\n")  # wording-pattern
            (repo / "LICENSES").mkdir()
            (repo / "LICENSES" / "X.txt").write_bytes(b"the spec\n")  # wording-pattern
            (repo / "own.py").write_bytes(b"'the spec'  " + PATTERN_MARK.encode() + b"\n")  # wording-pattern
            cp._git(repo, "add", "-A")
            self.assertEqual(scan_repo(repo, []),
                             {"NEWFILE.md": ["the brief"], "own.py": ["the spec"]})  # wording-pattern


class RecordsSplit(unittest.TestCase):
    """Checks of the records alone; they need no legacy record and always run."""

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
        timing = '"Timing reference for 0.8.0 (Task 1 record)"'
        for prefix, folder in RECORDS.items():
            body = section((ROOT / folder / "record.md").read_text(encoding="utf-8"), "Notation")
            self.assertIsNotNone(body, folder)
            paragraphs = [p for p in body.split("\n\n") if p.strip()]
            labelled = [p for p in paragraphs if p.startswith("Notation:")]
            self.assertEqual(len(paragraphs) - len(labelled), 1, folder)
            self.assertEqual(len(labelled), 1 if prefix in ("CLK", "DMA") else 0, folder)
            self.assertNotIn("testbenches", body, folder)
            self.assertIn(timing, body, folder)
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

    def test_board_wiring_out_of_8275(self):
        text = (ROOT / RECORDS["CRT"] / "record.md").read_text(encoding="utf-8")
        self.assertNotIn("| 8275 pin |", text)
        self.assertNotIn("Video path [R86]", text)
        self.assertNotIn("Correction to the ", text)
        self.assertEqual(text.count(BOARD_POINTER), 1)

    def test_no_private_wording(self):
        self.assertEqual(scan_repo(ROOT, words_for_scan()), {})

    def test_not_sources_sentence(self):
        for folder in RECORDS.values():
            text = (ROOT / folder / "record.md").read_text(encoding="utf-8")
            self.assertNotIn("- Not sources of behaviour:", text, folder)
            self.assertIn("\nNot sources of behaviour: MAME, Emu80, Apogee, the Karabas core.\n",
                          text, folder)

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


class LegacySplit(unittest.TestCase):
    """The records against the legacy record; skipped with a printed reason without it."""

    @classmethod
    def setUpClass(cls):
        cls.legacy_path, cls.legacy = legacy_text()
        cls.reg = cr.load_registry(ROOT / "docs" / "record-ids.md")

    def test_legacy_gate(self):
        out = cr.check(ROOT, self.legacy_path, None)
        self.assertEqual([l for l in out if not l.startswith("NOTE")], [])

    def test_id_count(self):
        legacy = cr.legacy_ids(self.legacy)
        self.assertEqual(len(legacy), LEGACY_COUNT)
        defined = set()
        for folder in RECORDS.values():
            defined |= cr.defined_ids((ROOT / folder / "record.md").read_text(encoding="utf-8"))
        elsewhere = set()
        for i in legacy:
            row = cr.resolve(self.reg, i)
            self.assertIsNotNone(row, i)
            if row.status in ("pending", "external"):
                elsewhere.add(i)
        listed = set().union(*(r.ids for r in self.reg.values()
                               if r.ids is not None and r.status == "external"))
        self.assertLessEqual(listed, legacy)
        self.assertEqual(defined & elsewhere, set())
        self.assertEqual(defined | elsewhere, legacy)
        self.assertEqual(len(defined) + len(elsewhere), LEGACY_COUNT)

    def test_silent_kept(self):
        for prefix, folder in RECORDS.items():
            text = (ROOT / folder / "record.md").read_text(encoding="utf-8")
            new = one_line(section(text, "SILENT (%s)" % prefix) or "")
            bullets = cr.silent_bullets(self.legacy, prefix)
            if prefix != "CPU":
                self.assertTrue(bullets, prefix)
            for b in bullets:
                for old, repl in SILENT_REWRITES.get(prefix, []):
                    b = re.sub(old, lambda _m, r=repl: r, b)
                self.assertIn(one_line(b), new, "%s SILENT: %s" % (prefix, b[:60]))

    def test_crt_decisions_in_legacy(self):
        # every decision of the 8275 record is in the legacy list of SILENT points
        for want in CRT_DECISIONS:
            self.assertIn("\n- " + want + " (", self.legacy)


if __name__ == "__main__":
    unittest.main()
