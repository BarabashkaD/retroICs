# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Comment-only check of a commit range: every changed line is a comment line of a file header.

Usage: python -B tools/check_comment_only.py [--repo DIR] [--paths GLOB ...] [--anywhere] <base> <head>

Every file changed between base and head (git diff --no-renames) must be one of:
- a source file (.v, .vh, .sv: '//'; .py, .toml: '#') whose added, removed and changed lines are
  all comment lines inside the leading comment block (the header) of the file, before and after;
  with --anywhere, comment lines anywhere in the file, and code lines whose line comment alone
  changed (the code part before the comment the same, in order). Each line is judged on its own:
  in a .py file a '#' line inside a multi-line string counts as a comment (a limit of the check);
- a fault (.patch, git diff output): applied with git apply, at base to its files at base and at
  head to its files at head, it must make the same edit: the patched files differ from each other
  exactly as the unpatched files do.
Any other change (a new, deleted or other file, a code line) fails. Every fault at head that
patches a changed file is checked as a fault too, changed or not. Exit code 0 and
"PASS comment-only (...)", else 1 with one line per problem.
"""
from __future__ import annotations

import argparse
import difflib
import fnmatch
import re
import subprocess
import sys
import tempfile
from pathlib import Path

COMMENT = {".v": "//", ".vh": "//", ".sv": "//", ".py": "#", ".toml": "#"}
TARGET = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.M)


def comment_prefix(path: str) -> str | None:
    """The line comment of the file type ('//', '#'), None for any other file."""
    return COMMENT.get(Path(path).suffix.lower())


def is_comment(line: str, prefix: str) -> bool:
    return line.lstrip().startswith(prefix)


def lines_of(data: bytes) -> list[str]:
    return data.decode("utf-8").split("\n")


def leading_block(lines: list[str], prefix: str) -> int:
    """The number of leading lines that are comment lines (the header)."""
    n = 0
    while n < len(lines) and is_comment(lines[n], prefix):
        n += 1
    return n


def changes(old: list[str], new: list[str]) -> list[tuple]:
    """The differences of two line lists: (i1, i2, j1, j2, old lines, new lines) per changed run."""
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    return [(i1, i2, j1, j2, tuple(old[i1:i2]), tuple(new[j1:j2]))
            for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def code_part(line: str, prefix: str) -> str:
    """The line up to its line comment (the first prefix outside a string literal: "..." for '//',
    "..." and '...' for '#', backslash escapes honoured), trailing blanks removed."""
    quotes = '"' if prefix == "//" else "\"'"
    quote = None
    i = 0
    while i < len(line):
        c = line[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c in quotes:
            quote = c
        elif line.startswith(prefix, i):
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def comment_problems(old: bytes, new: bytes, prefix: str, header_only: bool = True,
                     trailing: bool = False) -> list[str]:
    """Why new is not old with comment lines changed only; [] when it is. header_only: the changed
    lines must also lie inside the leading comment block of old and of new. trailing: a changed
    code line is allowed when only its line comment changed (added, reworded or removed): the code
    lines of a changed run, comment lines left out, have the same code parts, in order."""
    a, b = lines_of(old), lines_of(new)
    ha, hb = leading_block(a, prefix), leading_block(b, prefix)
    out = []
    for i1, i2, j1, j2, la, lb in changes(a, b):
        where = "old lines %d-%d, new lines %d-%d" % (i1 + 1, i2, j1 + 1, j2)
        if not all(is_comment(l, prefix) for l in la + lb):
            code_a = [code_part(l, prefix) for l in la if not is_comment(l, prefix)]
            code_b = [code_part(l, prefix) for l in lb if not is_comment(l, prefix)]
            if not (trailing and code_a == code_b):
                out.append("%s: a changed line is not a %s comment%s"
                           % (where, prefix, " (its code part changed)" if trailing else ""))
        elif header_only and (i2 > ha or j2 > hb):
            out.append("%s: a changed comment line outside the header" % where)
    return out


def replace_lines(data: bytes, pairs) -> bytes:
    """data with each (old, new) text replaced in every line that holds it."""
    if not pairs:
        return data
    out = []
    for line in lines_of(data):
        for a, b in pairs:
            if a in line:
                line = line.replace(a, b)
        out.append(line)
    return "\n".join(out).encode("utf-8")


def targets(patch: bytes) -> list[str]:
    """The files a fault patches (no renames)."""
    out = []
    for a, b in TARGET.findall(patch.decode("utf-8")):
        if a != b:
            raise ValueError("a rename in a fault patch: %s -> %s" % (a, b))
        out.append(a)
    return out


def _git(repo: Path | None, *args: str, cwd: Path | None = None) -> bytes:
    cmd = ["git", *args] if repo is None else ["git", "-C", str(repo), *args]
    r = subprocess.run(cmd, capture_output=True, cwd=cwd)
    if r.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), r.stderr.decode(errors="replace").strip()))
    return r.stdout


def blob(repo: Path, ref: str, path: str) -> bytes | None:
    """path at the commit ref; None when it is not there."""
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", "%s:%s" % (ref, path)],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def apply_patch(files: dict[str, bytes], patch: bytes) -> dict[str, bytes]:
    """The files after git apply of the patch (exact, no fuzz), in a temporary folder outside any
    repository; RuntimeError when it does not apply."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for rel, data in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
        (root / "fault.patch").write_bytes(patch)
        _git(None, "-c", "core.autocrlf=false", "apply", "fault.patch", cwd=root)
        return {rel: (root / rel).read_bytes() for rel in files}


def fault_problems(patch_old: bytes, files_old: dict[str, bytes], patch_new: bytes,
                   files_new: dict[str, bytes], pairs: dict[str, list] | None = None) -> list[str]:
    """Why the fault patch_new on files_new is not the edit of patch_old on files_old; [] when it
    is. The targets are paired in order; pairs: {new target: [(old text, new text)]}, replacements
    made on the old side first (the module names of a renamed file)."""
    pairs = pairs or {}
    try:
        t_old, t_new = targets(patch_old), targets(patch_new)
    except (ValueError, UnicodeDecodeError) as e:
        return [str(e)]
    if len(t_old) != len(t_new) or not t_new:
        return ["patches %s, before %s" % (t_new, t_old)]
    missing = [t for t in t_old if t not in files_old] + [t for t in t_new if t not in files_new]
    if missing:
        return ["a patched file is missing: %s" % ", ".join(missing)]
    try:
        after_old = apply_patch({t: files_old[t] for t in t_old}, patch_old)
        after_new = apply_patch({t: files_new[t] for t in t_new}, patch_new)
    except (RuntimeError, OSError) as e:
        return [str(e)]
    out = []
    for p, q in zip(t_old, t_new):
        if after_new[q] == files_new[q]:
            out.append("%s: the fault changes nothing" % q)
            continue
        before = replace_lines(files_old[p], pairs.get(q))
        after = replace_lines(after_old[p], pairs.get(q))
        if changes(lines_of(before), lines_of(files_new[q])) != \
                changes(lines_of(after), lines_of(after_new[q])):
            out.append("%s: the patched file differs from the old fault's beyond the file's own "
                       "change" % q)
    return out


def check_range(repo: Path, base: str, head: str, paths: list[str] | None = None,
                anywhere: bool = False) -> tuple[list[str], dict[str, int]]:
    """(problems, counts) of the comment-only check of base..head; with paths (fnmatch patterns,
    `*` crossing `/`), only the changed files that match one of them, and their faults. anywhere:
    comment lines anywhere in a file count, and so does the line comment of a code line whose code
    part is unchanged (comment_problems with header_only=False, trailing=True); the faults on the
    changed files are checked all the same."""
    repo = Path(repo)
    raw = _git(repo, "diff", "--name-status", "--no-renames", "-z", base, head).split(b"\0")
    entries = [(raw[i].decode(), raw[i + 1].decode()) for i in range(0, len(raw) - 1, 2)]
    if paths:
        entries = [(s, p) for s, p in entries if any(fnmatch.fnmatchcase(p, g) for g in paths)]
    problems: list[str] = []
    counts = {"files": 0, "faults": 0}
    changed = set()
    for status, path in entries:
        if status != "M":
            problems.append("%s: %s (only changes of existing files are allowed)"
                            % (path, {"A": "added", "D": "deleted"}.get(status, status)))
            continue
        changed.add(path)
        if path.endswith(".patch"):
            continue
        prefix = comment_prefix(path)
        if prefix is None:
            problems.append("%s: not a source file with line comments" % path)
            continue
        old, new = blob(repo, base, path), blob(repo, head, path)
        try:
            found = comment_problems(old, new, prefix, header_only=not anywhere, trailing=anywhere)
        except UnicodeDecodeError:
            found = ["not UTF-8"]
        problems += ["%s: %s" % (path, p) for p in found]
        counts["files"] += 1
    listing = _git(repo, "ls-tree", "-r", "-z", "--name-only", head).split(b"\0")
    for path in sorted(p.decode() for p in listing if p.endswith(b".patch")):
        new = blob(repo, head, path)
        try:
            files = targets(new)
        except (ValueError, UnicodeDecodeError) as e:
            problems.append("%s: %s" % (path, e))
            continue
        if path not in changed and not changed.intersection(files):
            continue
        old = blob(repo, base, path)
        if old is None:
            problems.append("%s: not at %s" % (path, base))
            continue
        try:
            old_files = targets(old)
        except (ValueError, UnicodeDecodeError) as e:
            problems.append("%s: %s" % (path, e))
            continue
        files_old = {t: blob(repo, base, t) for t in old_files}
        files_new = {t: blob(repo, head, t) for t in files}
        files_old = {k: v for k, v in files_old.items() if v is not None}
        files_new = {k: v for k, v in files_new.items() if v is not None}
        problems += ["%s: %s" % (path, p) for p in fault_problems(old, files_old, new, files_new)]
        counts["faults"] += 1
    return problems, counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base")
    ap.add_argument("head")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--paths", action="append", metavar="GLOB",
                    help="check only the changed files that match (repeatable; * crosses /)")
    ap.add_argument("--anywhere", action="store_true",
                    help="comment lines anywhere in a file, and the line comment of an unchanged "
                         "code line, count as comment changes (each line on its own: a '#' line "
                         "inside a Python multi-line string counts as a comment)")
    a = ap.parse_args(argv)
    try:
        problems, counts = check_range(a.repo, a.base, a.head, a.paths, a.anywhere)
    except RuntimeError as e:
        print("ERROR: %s" % e)
        return 1
    for p in problems:
        print("ERROR: %s" % p)
    if problems:
        return 1
    what = "comment lines and line comments only" if a.anywhere else "header comment lines only"
    print("PASS comment-only (%d source files: %s; %d faults on them: the same edit) %s..%s"
          % (counts["files"], what, counts["faults"], a.base, a.head))
    return 0


if __name__ == "__main__":
    sys.exit(main())
