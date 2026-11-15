# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""The private-wording scan of the working tree: generic patterns that point at private planning
documents, and the words of an untracked list (RETRO_PRIVATE_WORDS). Used by
test_private_wording.py; a helper module of this repo's tests, not an interface for other repos."""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_privacy as cp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
# Wording that points at private planning documents, generic patterns only. The
# lines that define the patterns end with the marker below; in OWN_FILES only, those lines are
# exempt from the generic patterns (never from the private word list).
PATTERN_MARK = "# wording-pattern"
PLAN_WORDING = re.compile(r"\bthe plan\b|\bplan's\b|\bTasks? \d+|\bStep \d|\bspec \d"  # wording-pattern
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
# the files whose marked lines are exempt from the generic patterns (never from the words)
OWN_FILES = ("tools/tests/wordscan.py", "tools/tests/test_private_wording.py")
# private words in imported text that is already public upstream: (path, word) -> reason. The scan
# drops only that word, and only for that path; every entry must still match a line of its file (a
# stale entry fails). Each word is written in two parts, so this file holds none of them.
WORD_EXEMPT = {}
# generic-pattern hits in text that is still to be reworded: (path, hit) ->
# the rewrite that removes it; each hit written in two parts, so this file holds none of them. An
# entry whose hit is gone fails (stale).
GENERIC_PENDING = {}


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


def wording_hits(text, words=(), skip_marked=False, generic=True):
    """Every private wording in text: the generic patterns and the given words. With skip_marked,
    a line ending with PATTERN_MARK is exempt from the generic patterns only; generic=False skips
    them on every line. The words are checked on every line."""
    found = set()
    for line in text.splitlines():
        if generic and not (skip_marked and line.rstrip().endswith(PATTERN_MARK)):
            found |= {m.group(0) for m in PLAN_WORDING.finditer(line)}
            found |= {m.group(0) for m in CONTROLLER_ACTOR.finditer(line)}
        low = line.lower()
        found |= {w for w in words if w in low}
    return sorted(found)


def wording_files(repo=ROOT):
    """The files of the working tree as check_privacy sees them (tracked, and untracked but not
    ignored), as (repo-relative name, bytes). Skipped: binary files (a NUL byte in the first 8 KiB,
    or a PDF, which may have none there; no wording to read: check_privacy scans the PDFs) and
    LICENSES/*.txt (the official licence texts, kept byte for byte)."""
    repo = Path(repo)
    out = []
    for f in cp.working_tree_files(repo):
        if not f.is_file():
            continue
        rel = f.relative_to(repo).as_posix()
        if rel.startswith("LICENSES/") and rel.endswith(".txt"):
            continue
        data = f.read_bytes()
        if b"\0" in data[:8192] or data.startswith(b"%PDF-"):
            continue
        out.append((rel, data))
    return sorted(out)


def words_for(rel, words, exempt=None):
    """The words to check in the file rel: words without those exempt for rel."""
    exempt = WORD_EXEMPT if exempt is None else exempt
    return [w for w in words if (rel, w) not in exempt]


def stale_word_exemptions(repo, exempt=None):
    """The entries of exempt (default WORD_EXEMPT) whose word is in no line of their file."""
    out = []
    for rel, word in sorted(WORD_EXEMPT if exempt is None else exempt):
        p = Path(repo) / rel
        lines = p.read_text(encoding="utf-8").lower().splitlines() if p.is_file() else []
        if not any(word in line for line in lines):
            out.append((rel, word))
    return out


def scan_repo(repo, words, exempt=None, pending=None):
    """{name: hits} of every file of wording_files(repo) with a hit (WORD_EXEMPT and
    GENERIC_PENDING honoured)."""
    pending = GENERIC_PENDING if pending is None else pending
    out = {}
    for rel, data in wording_files(repo):
        hits = wording_hits(data.decode("utf-8", errors="replace"), words_for(rel, words, exempt),
                            skip_marked=(rel in OWN_FILES))
        hits = [h for h in hits if (rel, h) not in pending]
        if hits:
            out[rel] = hits
    return out


def stale_pending(repo, pending=None):
    """The entries of pending (default GENERIC_PENDING) whose hit is no longer in their file."""
    pending = GENERIC_PENDING if pending is None else pending
    out = []
    for rel, hit in sorted(pending):
        p = Path(repo) / rel
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        if hit not in wording_hits(text):
            out.append((rel, hit))
    return out
