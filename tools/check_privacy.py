# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Privacy checker: no local paths, emails or personal metadata in files, PDFs or git history.

Usage: python -B tools/check_privacy.py [--all | --history BASE]

Default: every tracked and untracked-not-ignored file of the working tree. --all adds every
commit reachable from HEAD (blobs, messages, author and committer); --history BASE adds the
commits of BASE..HEAD only.

privacy-allow.txt, one entry per line, "<kind> <pattern> # <reason>" (the reason is required;
lines starting with # and blank lines are ignored):
  path <glob>                  the whole file is not scanned (repo-relative, fnmatch)
  allow <glob> :: <literal>    the literal is ignored in files matching the glob
  trailer <regex>              a commit message line matching it is ignored
  author <regex>               "Name <email>" of an author or committer matching it is accepted
  watch <name>                 a name that must not appear in PDF /Creator or /Producer
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

# local paths, lifted from the Pocket's scripts/check_repo.py
LOCAL_PATH = re.compile(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]+(?![^\s`\'"]*<)[A-Za-z0-9_.$-]'
                        r'|\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_.$-]'
                        r'|/(home|Users|mnt/[a-z])/(?![^\s`\'"]*<)[A-Za-z0-9_.-]+')
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+')
NOREPLY_DOMAIN = "users.noreply.github.com"
KINDS = ("path", "allow", "trailer", "author", "watch")


@dataclass
class Allow:
    paths: list[str] = field(default_factory=list)
    allows: list[tuple[str, str]] = field(default_factory=list)
    trailers: list[re.Pattern] = field(default_factory=list)
    authors: list[re.Pattern] = field(default_factory=list)
    watch: list[str] = field(default_factory=list)


def parse_allow(text: str) -> Allow:
    a = Allow()
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " # " not in line:
            raise ValueError("allow line %d: reason ' # ...' is required" % n)
        body, _ = line.split(" # ", 1)
        kind, _, pat = body.strip().partition(" ")
        pat = pat.strip()
        if kind not in KINDS or not pat:
            raise ValueError("allow line %d: unknown kind or empty pattern" % n)
        if kind == "path":
            a.paths.append(pat)
        elif kind == "allow":
            glob, sep, lit = pat.partition(" :: ")
            if not sep or not lit.strip():
                raise ValueError("allow line %d: want 'allow <glob> :: <literal>'" % n)
            a.allows.append((glob.strip(), lit.strip()))
        elif kind == "trailer":
            a.trailers.append(re.compile(pat))
        elif kind == "author":
            a.authors.append(re.compile(pat))
        else:
            a.watch.append(pat)
    return a


def load_allow(path: Path) -> Allow:
    p = Path(path)
    return parse_allow(p.read_text(encoding="utf-8")) if p.is_file() else Allow()


def _match(name: str, glob: str) -> bool:
    return fnmatch.fnmatch(name, glob) or fnmatch.fnmatch(name, "*/" + glob)


def _text_problems(text: str, name: str, allow: Allow) -> list[str]:
    out: list[str] = []
    literals = [lit for g, lit in allow.allows if _match(name, g)]
    for n, line in enumerate(text.splitlines(), 1):
        for lit in literals:
            line = line.replace(lit, "")
        m = LOCAL_PATH.search(line)
        if m:
            out.append("%s:%d: an absolute local path %r" % (name, n, m.group(0)))
        for e in EMAIL.finditer(line):
            if e.group(0).endswith("@" + NOREPLY_DOMAIN):
                continue
            out.append("%s:%d: an email address %r" % (name, n, e.group(0)))
    return out


def scan_bytes(name: str, data: bytes, allow: Allow) -> list[str]:
    if any(_match(name, g) for g in allow.paths):
        return []
    if b"%PDF-" in data[:1024] or name.lower().endswith(".pdf"):
        return _pdf_problems(name, data, allow)
    if b"\0" in data[:8192]:
        # binary: check the printable ASCII runs of 4 or more characters
        runs = re.findall(rb"[\x20-\x7e]{4,}", data)
        return _text_problems(b"\n".join(runs).decode("ascii"), name, allow)
    return _text_problems(data.decode("utf-8", errors="replace"), name, allow)


def scan_text(path: Path, allow: Allow) -> list[str]:
    p = Path(path)
    return scan_bytes(p.as_posix(), p.read_bytes(), allow)


_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_STR = rb"(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>)"
_AUTHOR = re.compile(rb"/Author\s*" + _STR, re.S)
_TOOL = re.compile(rb"/(Creator|Producer)\s*" + _STR, re.S)


def _pdf_string(raw: bytes) -> str:
    if raw.startswith(b"<"):
        hexs = re.sub(rb"\s", b"", raw[1:-1])
        if len(hexs) % 2:
            hexs += b"0"
        b = bytes.fromhex(hexs.decode("ascii"))
        return b.decode("utf-16-be", "replace") if b.startswith(b"\xfe\xff") else b.decode("latin-1")
    inner = raw[1:-1]
    inner = re.sub(rb"\\(.)", lambda m: m.group(1), inner, flags=re.S)
    return inner.decode("latin-1")


MAX_INFLATE = 16 * 1024 * 1024        # per Flate stream
MAX_INFLATE_TOTAL = 64 * 1024 * 1024  # per file


def _pdf_chunks(data: bytes) -> tuple[list[bytes], bool]:
    """The raw bytes and every inflated stream; the flag says a limit was hit."""
    chunks = [data]
    total = 0
    limited = False
    for m in _STREAM.finditer(data):
        room = min(MAX_INFLATE, MAX_INFLATE_TOTAL - total)
        if room <= 0:
            limited = True
            break
        d = zlib.decompressobj()
        try:
            part = d.decompress(m.group(1), room)
        except zlib.error:
            continue
        if d.unconsumed_tail:
            limited = True
        total += len(part)
        chunks.append(part)
    return chunks, limited


def _pdf_problems(name: str, data: bytes, allow: Allow) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(msg: str) -> None:
        if msg not in seen:
            seen.add(msg)
            out.append("%s: %s" % (name, msg))

    chunks, limited = _pdf_chunks(data)
    if limited:
        add("stream too large to check (inflate limit reached)")
    for chunk in chunks:
        if b"<?xpacket" in chunk or b"<x:xmpmeta" in chunk:
            add("an XMP metadata packet (strip it, e.g. with qpdf)")
        for m in _AUTHOR.finditer(chunk):
            if _pdf_string(m.group(1)).strip():
                add("/Author is not empty")
        for m in _TOOL.finditer(chunk):
            key = m.group(1).decode()
            val = _pdf_string(m.group(2))
            bad = (LOCAL_PATH.search(val) or EMAIL.search(val)
                   or any(w.lower() in val.lower() for w in allow.watch))
            if bad:
                add("/%s holds a path, an email or a watched name" % key)
    return out


def scan_pdf(path: Path, allow: Allow) -> list[str]:
    p = Path(path)
    return _pdf_problems(p.as_posix(), p.read_bytes(), allow)


# ---- history ----

def _git(repo: Path, *args: str, input: bytes | None = None) -> bytes:
    r = subprocess.run(["git", "-C", str(repo), *args], input=input, capture_output=True)
    if r.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.decode(errors="replace")))
    return r.stdout


def _has_head(repo: Path) -> bool:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q", "HEAD"],
                       capture_output=True)
    return r.returncode == 0


def _ident_ok(ident: str, allow: Allow, role: str = "author") -> bool:
    addrs = [m.group(0) for m in EMAIL.finditer(ident)]
    if not addrs:
        return False
    # "Rebase and merge" commits carry this committer (never an author)
    if role == "committer" and ident == "GitHub <noreply" + "@github.com>":  # split: keeps this file free of the address
        return True
    if all(a.endswith("@" + NOREPLY_DOMAIN) for a in addrs):
        return True
    return any(p.search(ident) for p in allow.authors)


def scan_history(repo: Path, all_commits: bool, base: str | None,
                 allow: Allow | None = None) -> list[str]:
    allow = allow or Allow()
    repo = Path(repo)
    if base is not None and not base.strip():
        # an empty base (e.g. a failed `git merge-base` in CI) must not pass as "no history"
        raise ValueError("history base is empty")
    if not (all_commits or base) or not _has_head(repo):
        return []
    rng = "HEAD" if all_commits else "%s..HEAD" % base
    out: list[str] = []
    fmt = "%H%x1f%an <%ae>%x1f%cn <%ce>%x1f%B%x1e"
    log = _git(repo, "log", "--format=" + fmt, rng).decode("utf-8", "replace")
    for rec in log.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, author, committer, msg = rec.split("\x1f", 3)
        short = sha[:10]
        for role, ident in (("author", author), ("committer", committer)):
            if not _ident_ok(ident, allow, role):
                out.append("commit %s: %s %r is not a noreply address" % (short, role, ident))
        kept = "\n".join(l for l in msg.splitlines()
                         if not any(t.search(l) for t in allow.trailers))
        out += _text_problems(kept, "commit %s message" % short, allow)
    # blobs
    blobs: dict[str, str] = {}
    shas = _git(repo, "rev-list", rng).decode().split()
    for sha in shas:
        raw = _git(repo, "diff-tree", "--root", "-r", "-m", "--no-renames", "--diff-filter=AMT",
                   "-z", "--no-commit-id", sha)
        parts = raw.split(b"\0")
        i = 0
        while i + 1 < len(parts):
            meta, path = parts[i], parts[i + 1]
            if not meta.startswith(b":"):
                i += 1
                continue
            fields = meta.split()
            if fields[1] != b"160000":  # a submodule gitlink is a commit of another repo
                blobs.setdefault(fields[3].decode(), path.decode("utf-8", "replace"))
            i += 2
    if blobs:
        proc = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            for sha, name in blobs.items():
                proc.stdin.write(sha.encode() + b"\n")
                proc.stdin.flush()
                header = proc.stdout.readline().split()
                if len(header) < 3 or header[1] == b"missing":
                    out.append("blob %s (%s): object is missing, not scanned" % (sha[:10], name))
                    continue
                data = proc.stdout.read(int(header[2]))
                proc.stdout.read(1)  # the newline after the content
                for p in scan_bytes(name, data, allow):
                    out.append("blob %s (%s): %s" % (sha[:10], name, p))
        finally:
            proc.stdin.close()
            proc.stdout.close()
            proc.wait()
    return out


def working_tree_files(repo: Path) -> list[Path]:
    raw = _git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return [Path(repo) / n.decode("utf-8", "replace") for n in raw.split(b"\0") if n]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="also every commit reachable from HEAD")
    g.add_argument("--history", metavar="BASE", help="also the commits of BASE..HEAD")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    if args.history is not None and not args.history.strip():
        ap.error("--history needs a base commit (got an empty value)")
    repo = args.repo
    allow = load_allow(repo / "privacy-allow.txt")
    out: list[str] = []
    for f in working_tree_files(repo):
        if f.is_file():
            out += scan_bytes(f.relative_to(repo).as_posix(), f.read_bytes(), allow)
    out += scan_history(repo, args.all, args.history, allow)
    for line in out:
        print(line)
    if out:
        return 1
    print("PASS privacy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
