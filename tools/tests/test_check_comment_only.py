# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""tools/check_comment_only.py: the rules, and a commit range in a temporary repository (with
--paths and --anywhere)."""
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_comment_only as cco  # noqa: E402

SRC = "".join(["// a model\n", "module m;\n"] + ["wire w%d;\n" % n for n in range(1, 13)]
              + ["endmodule\n"])
SPDX = "// SPDX-License-Identifier: BSD-3-Clause\n"


def fault(path, old_line, new_line, text=SRC):
    """A fault made with git diff: old_line changed to new_line in path (text before)."""
    with tempfile.TemporaryDirectory() as d:
        g = ["git", "-C", d, "-c", "core.autocrlf=false"]
        subprocess.run(g[:3] + ["init", "-q"], check=True)
        (Path(d) / path).parent.mkdir(parents=True, exist_ok=True)
        (Path(d) / path).write_bytes(text.encode())
        subprocess.run(g + ["add", "-A"], check=True)
        (Path(d) / path).write_bytes(text.replace(old_line, new_line).encode())
        return subprocess.run(g + ["diff"], check=True, capture_output=True).stdout


class Rules(unittest.TestCase):
    def test_comment_problems(self):
        old = SRC.encode()
        self.assertEqual(cco.comment_problems(old, (SPDX + SRC).encode(), "//"), [])
        self.assertEqual(cco.comment_problems(old, SRC.replace("a model", "b").encode(), "//"), [])
        # a code line, a comment line below the header (allowed only without header_only)
        self.assertTrue(cco.comment_problems(old, SRC.replace("w3;", "w33;").encode(), "//"))
        below = SRC.replace("wire w3;\n", "wire w3;\n// note\n").encode()
        self.assertIn("outside the header", cco.comment_problems(old, below, "//")[0])
        self.assertEqual(cco.comment_problems(old, below, "//", header_only=False), [])
        # the comment of the file type only
        self.assertTrue(cco.comment_problems(old, ("# x\n" + SRC).encode(), "//"))
        self.assertEqual(cco.comment_problems(b"a = 1\n", b"# x\na = 1\n", "#"), [])
        self.assertEqual(cco.comment_prefix("x/a.vh"), "//")
        self.assertIsNone(cco.comment_prefix("x/a.md"))

    def test_fault_same_edit(self):
        path = "ics/x/rtl/m.v"
        old_patch = fault(path, "wire w7;", "wire w7x;")
        new_src = SPDX + SRC
        files_old, files_new = {path: SRC.encode()}, {path: new_src.encode()}
        # the old fault itself (it applies with an offset) and one made again on the new file
        self.assertEqual(cco.fault_problems(old_patch, files_old, old_patch, files_new), [])
        regen = fault(path, "wire w7;", "wire w7x;", new_src)
        self.assertNotEqual(regen, old_patch)
        self.assertEqual(cco.fault_problems(old_patch, files_old, regen, files_new), [])
        # another edit
        other = fault(path, "wire w8;", "wire w8x;", new_src)
        self.assertTrue(cco.fault_problems(old_patch, files_old, other, files_new))
        # a fault that does not apply
        self.assertTrue(cco.fault_problems(old_patch, files_old, old_patch,
                                           {path: new_src.replace("wire w6;", "x").encode()}))

    def test_fault_with_renamed_lines(self):
        path = "ics/x/rtl/m.v"
        text = SRC.replace("module m;", "module old_m;")
        old_patch = fault(path, "module old_m;", "module old_m; // f", text)
        new_src = SPDX + SRC
        regen = fault(path, "module m;", "module m; // f", new_src)
        pairs = {path: [("module old_m;", "module m;")]}
        files_old, files_new = {path: text.encode()}, {path: new_src.encode()}
        self.assertEqual(cco.fault_problems(old_patch, files_old, regen, files_new, pairs), [])
        self.assertTrue(cco.fault_problems(old_patch, files_old, regen, files_new))


class Range(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.put("ics/x/rtl/m.v", SRC)
        self.put("ics/x/faults/f.patch", fault("ics/x/rtl/m.v", "wire w7;", "wire w7x;").decode())
        self.put("README.md", "x\n")
        self.base = self.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), "-c", "core.autocrlf=false", "-c",
                               "user.name=t", "-c", "user.email=t", *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def put(self, rel, text):
        (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / rel).write_bytes(text.encode())

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c")
        return self.git("rev-parse", "HEAD")

    def test_header_commit_passes(self):
        self.put("ics/x/rtl/m.v", SPDX + SRC)
        head = self.commit()
        problems, counts = cco.check_range(self.repo, self.base, head)
        self.assertEqual(problems, [])
        self.assertEqual(counts, {"files": 1, "faults": 1})
        out = io.StringIO()
        with redirect_stdout(out):
            rc = cco.main(["--repo", str(self.repo), self.base, head])
        self.assertEqual(rc, 0)
        self.assertTrue(out.getvalue().startswith("PASS comment-only (1 source files"))

    def test_other_changes_fail(self):
        self.put("ics/x/rtl/m.v", SPDX + SRC.replace("wire w2;", "wire w2x;"))
        self.put("README.md", "y\n")
        self.put("ics/x/rtl/new.v", SPDX)
        head = self.commit()
        problems, _ = cco.check_range(self.repo, self.base, head)
        text = "\n".join(problems)
        self.assertIn("ics/x/rtl/m.v: old lines", text)
        self.assertIn("README.md: not a source file", text)
        self.assertIn("ics/x/rtl/new.v: added", text)

    def test_fault_edit_changed_fails(self):
        self.put("ics/x/rtl/m.v", SPDX + SRC)
        self.put("ics/x/faults/f.patch",
                 fault("ics/x/rtl/m.v", "wire w8;", "wire w8x;", SPDX + SRC).decode())
        head = self.commit()
        problems, _ = cco.check_range(self.repo, self.base, head)
        self.assertEqual(len(problems), 1)
        self.assertIn("ics/x/faults/f.patch: ics/x/rtl/m.v: the patched file differs", problems[0])

    def test_paths_option(self):
        # only the files that match --paths are checked: a new file and a doc outside them pass
        self.put("ics/x/rtl/m.v", SPDX + SRC)
        self.put("README.md", "y\n")
        self.put("tools/new.py", "x = 1\n")
        head = self.commit()
        problems, counts = cco.check_range(self.repo, self.base, head, paths=["ics/*/rtl/*"])
        self.assertEqual(problems, [])
        self.assertEqual(counts, {"files": 1, "faults": 1})
        # a code line inside them still fails, also through main
        self.put("ics/x/rtl/m.v", SPDX + SRC.replace("wire w2;", "wire w2x;"))
        head = self.commit()
        problems, _ = cco.check_range(self.repo, self.base, head, paths=["ics/*/rtl/*"])
        self.assertTrue(any("ics/x/rtl/m.v" in p for p in problems), problems)
        with redirect_stdout(io.StringIO()):
            rc = cco.main(["--repo", str(self.repo), self.base, head, "--paths", "ics/*/rtl/*"])
        self.assertEqual(rc, 1)

    def test_anywhere_option(self):
        # a comment line in the body: a problem without --anywhere, none with it
        body = SRC.replace("wire w11;\n", "wire w11;\n// note\n")
        self.put("ics/x/rtl/m.v", body)
        head = self.commit()
        problems, _ = cco.check_range(self.repo, self.base, head)
        self.assertTrue(any("outside the header" in p for p in problems), problems)
        problems, counts = cco.check_range(self.repo, self.base, head, anywhere=True)
        self.assertEqual(problems, [])
        self.assertEqual(counts, {"files": 1, "faults": 1})
        # the trailing comment of a code line added, then changed: none with it, also through main
        self.put("ics/x/rtl/m.v", body.replace("wire w2;", "wire w2; // two"))
        mid = self.commit()
        self.assertEqual(cco.check_range(self.repo, self.base, mid, anywhere=True)[0], [])
        self.assertTrue(cco.check_range(self.repo, self.base, mid)[0])
        self.put("ics/x/rtl/m.v", body.replace("wire w2;", "wire w2;  // the second"))
        head = self.commit()
        self.assertEqual(cco.check_range(self.repo, mid, head, anywhere=True)[0], [])
        out = io.StringIO()
        with redirect_stdout(out):
            rc = cco.main(["--repo", str(self.repo), mid, head, "--anywhere"])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertTrue(out.getvalue().startswith("PASS comment-only (1 source files: comment"))
        # the code part changed (with or without its comment): a problem
        self.put("ics/x/rtl/m.v", body.replace("wire w2;", "wire w22; // the second"))
        head = self.commit()
        problems, _ = cco.check_range(self.repo, mid, head, anywhere=True)
        self.assertTrue(any("ics/x/rtl/m.v" in p and "code" in p for p in problems), problems)
        with redirect_stdout(io.StringIO()):
            rc = cco.main(["--repo", str(self.repo), mid, head, "--anywhere"])
        self.assertEqual(rc, 1)
        # a '//' inside a string is code, not a comment; a code line removed is a problem
        old = b'module m;\n$display("a//b");\nwire w;\nendmodule\n'
        self.assertTrue(cco.comment_problems(old, old.replace(b"a//b", b"a//c"), "//",
                                             header_only=False, trailing=True))
        self.assertTrue(cco.comment_problems(old, old.replace(b"wire w;\n", b""), "//",
                                             header_only=False, trailing=True))
        self.assertEqual(cco.comment_problems(old, old.replace(b"wire w;", b"wire w; // w"), "//",
                                              header_only=False, trailing=True), [])
        self.assertEqual(cco.code_part('x = "a#b"  # c', "#"), 'x = "a#b"')


if __name__ == "__main__":
    unittest.main()
