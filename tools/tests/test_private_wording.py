# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""The private-wording scan (wordscan.py) and the working tree against it."""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_privacy as cp  # noqa: E402
from wordscan import (GENERIC_ONLY_NOTE, GENERIC_PENDING, OWN_FILES, PATTERN_MARK,  # noqa: E402
                      PRIVATE_WORDS_VAR, ROOT, WORD_EXEMPT, private_words, scan_repo,
                      stale_pending, stale_word_exemptions, wording_files, wording_hits,
                      words_for_scan)


class PrivateWording(unittest.TestCase):
    """The wording scan itself."""

    def test_generic_patterns(self):
        text = "as the plan says\nsee Step 2 and spec 4\nthe brief\nsuperpowers/x\n"  # wording-pattern
        self.assertEqual(len(wording_hits(text)), 5)
        self.assertEqual(wording_hits("the planned model\n"), [])
        self.assertEqual(wording_hits("Timing reference (Task" " 1 record)\n"), ["Task" " 1"])

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
                     *OWN_FILES, ".github/workflows/checks.yml", "ics/intel/8257/record.md"):
            self.assertIn(name, names)
        self.assertFalse(any(n.startswith("LICENSES/") and n.endswith(".txt") for n in names))

    def test_new_top_level_file_reported(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir()
            cp._git(repo, "init", "-q")
            (repo / "NEWFILE.md").write_bytes(b"as the brief says\n")  # wording-pattern
            (repo / "data.bin").write_bytes(b"\0the brief\n")  # wording-pattern
            (repo / "doc.pdf").write_bytes(b"%PDF-1.4\n\xc2\xa7 the spec\n")  # wording-pattern
            (repo / "LICENSES").mkdir()
            (repo / "LICENSES" / "X.txt").write_bytes(b"the spec\n")  # wording-pattern
            (repo / "own.py").write_bytes(b"'the spec'  " + PATTERN_MARK.encode() + b"\n")  # wording-pattern
            cp._git(repo, "add", "-A")
            self.assertEqual(scan_repo(repo, [], pending={}),
                             {"NEWFILE.md": ["the brief"], "own.py": ["the spec"]})  # wording-pattern

    def test_word_exemptions_current(self):
        self.assertTrue(all(reason for reason in WORD_EXEMPT.values()))
        self.assertTrue(all(w == w.lower() for _, w in WORD_EXEMPT))
        self.assertEqual(stale_word_exemptions(ROOT), [])
        # a word no longer in its file, or a file that is gone, is stale
        self.assertEqual(stale_word_exemptions(ROOT, {("README.md", "no-such-word-x"): "r",
                                                      ("gone.txt", "x"): "r"}),
                         [("README.md", "no-such-word-x"), ("gone.txt", "x")])

    def test_word_exemption_only_for_its_path_and_word(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir()
            cp._git(repo, "init", "-q")
            (repo / "a.txt").write_bytes(b"secret-name and other-name\n")
            (repo / "b.txt").write_bytes(b"secret-name\n")
            cp._git(repo, "add", "-A")
            exempt = {("a.txt", "secret-name"): "r"}
            words = ["secret-name", "other-name"]
            self.assertEqual(scan_repo(repo, words, exempt, pending={}),
                             {"a.txt": ["other-name"], "b.txt": ["secret-name"]})
            self.assertEqual(scan_repo(repo, words, {}, pending={}),
                             {"a.txt": ["other-name", "secret-name"], "b.txt": ["secret-name"]})

    def test_pending_entries_current(self):
        self.assertTrue(all(reason for reason in GENERIC_PENDING.values()))
        self.assertEqual(stale_pending(ROOT), [])
        self.assertEqual(stale_pending(ROOT, {("README.md", "Task 77"): "r"}),  # wording-pattern
                         [("README.md", "Task 77")])  # wording-pattern

    def test_pending_only_for_its_path_and_hit(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir()
            cp._git(repo, "init", "-q")
            (repo / "a.v").write_bytes(b"// Task 2 and the brief\n")  # wording-pattern
            (repo / "b.v").write_bytes(b"// Task 2\n")  # wording-pattern
            cp._git(repo, "add", "-A")
            pending = {("a.v", "Task 2"): "r"}  # wording-pattern
            self.assertEqual(scan_repo(repo, [], {}, pending),
                             {"a.v": ["the brief"], "b.v": ["Task 2"]})  # wording-pattern

    def test_no_private_wording(self):
        self.assertEqual(scan_repo(ROOT, words_for_scan()), {})


if __name__ == "__main__":
    unittest.main()
