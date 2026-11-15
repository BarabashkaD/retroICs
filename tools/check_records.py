# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Record checker: IDs defined once, every reference resolvable, source IDs registered.

Usage: python -B tools/check_records.py [--repo DIR] [--records DIR ...] [--external NAME=DIR ...]

Inputs, relative to the repository root (--repo, default this repo):
  docs/record-ids.md  registry table  | Prefix | Home | Status | IDs |
                      Home: <repo>/<path>; the `here` rows all name this repo. Status: here
                      (defined in this repo), pending (home does not exist yet, nothing checked),
                      external (defined in the repo <repo>; checked only with --external
                      <repo>=DIR, else one NOTE per repo), retired (Home "-": defined nowhere here
                      any more; never defined again, references allowed). IDs: optional comma
                      list; the row then covers only those IDs of the prefix (a prefix may be split
                      over several rows); an empty list covers the whole prefix.
  docs/sources.md     source table    | ID | Home | Kind |   (ID in brackets, e.g. [C78])
  <records>/**/record.md   records (--records, default ics); an ID is defined by the first cell of
                      a table row. The Home file of a `here` row defines IDs too, but only of its
                      own prefix (a board record that is not named record.md).
  <records>/**/*.md   every markdown file: its record ID and bracket source ID references.

Output: one line per problem, or PASS records. Lines starting with NOTE are not problems.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

ID_RE = r"[A-Z][A-Z0-9]{1,9}(?:-DEV)?-[DEM]?\d+"
ID_FULL = re.compile(ID_RE)
# a reference in prose: not part of a longer word or bracket token like [AP-62]
ID_REF = re.compile(r"(?<![\w\[\-/])(" + ID_RE + r")(?![\w\-])")
# a bracket source ID: a Latin or Cyrillic capital first ([C78], [ВГ75]) or at least four digits
# first ([8275], [74198]); not a bit range ([15:8]), a short number ([12]) or a markdown link
BRACKET = re.compile(r"\[((?:[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9]*|\d{4,}[A-Za-z0-9]*)"
                     r"(?:-[A-Za-z0-9…]+)*)\](?!\()")
STATUSES = ("here", "pending", "external", "retired")
KINDS = ("vendor", "board", "listing", "comparison-only")
# a section of one prefix: "## SILENT (CRT)" (two to four "#")
SECTION_HEAD = re.compile(r"^#{2,4} (.+?) \((.+?)\)\s*$")


@dataclass(frozen=True)
class RegistryRow:
    prefix: str
    home: str
    status: str
    ids: frozenset[str] | None


def prefix_of(id_: str) -> str:
    return id_.rsplit("-", 1)[0]


def _cells(line: str) -> list[str] | None:
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def _clean(cell: str) -> str:
    return cell.strip().strip("*`").strip()


def table_rows(md_text: str):
    for line in md_text.splitlines():
        cells = _cells(line)
        if cells:
            yield cells


def defined_ids(md_text: str) -> set[str]:
    return {c for cells in table_rows(md_text)
            if ID_FULL.fullmatch(c := _clean(cells[0]))}


_LIST_ID = re.compile(r"^- (" + ID_RE + r")(?![\w])")


def silent_bullets(md_text: str, prefix: str) -> list[str]:
    return section_bullets(md_text, "SILENT", prefix)


def section_bullets(md_text: str, title: str, prefix: str) -> list[str]:
    """The bullets (continuation lines joined) of the section '<title> (<prefix>)', up to the
    next heading."""
    bullets: list[str] = []
    inside = False
    for line in md_text.splitlines():
        m = SECTION_HEAD.match(line)
        if m:
            inside = m.group(1) == title and m.group(2) == prefix
            continue
        if line.startswith("#"):
            inside = False
            continue
        if not inside:
            continue
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif line.strip() and line[:1] in " \t" and bullets:
            bullets[-1] += " " + line.strip()
    return bullets


def bullet_ids(bullet: str, prefix: str) -> list[str]:
    """The IDs of the prefix that a bullet names before its first ': ' ("CRT-25: ...",
    "DMA-7 / DMA-29: ...")."""
    head = bullet.split(": ", 1)[0]
    return [i for i in ID_REF.findall(head) if prefix_of(i) == prefix]


def load_registry(path: Path) -> dict[str, RegistryRow]:
    """Key: the prefix; a row with a listed IDs cell is keyed 'PREFIX#home'."""
    reg: dict[str, RegistryRow] = {}
    for cells in table_rows(Path(path).read_text(encoding="utf-8")):
        if len(cells) < 3 or cells[0] in ("Prefix",) or set(cells[0]) <= set("-: "):
            continue
        prefix, home, status = (_clean(c) for c in cells[:3])
        if status not in STATUSES:
            raise ValueError("registry row %s: bad status %r" % (prefix, status))
        ids_cell = cells[3] if len(cells) > 3 else ""
        ids = frozenset(i.strip() for i in ids_cell.split(",") if i.strip()) or None
        key = prefix if ids is None else "%s#%s" % (prefix, home)
        if key in reg:
            raise ValueError("registry: %s listed twice" % key)
        reg[key] = RegistryRow(prefix, home, status, ids)
    return reg


def resolve(reg: dict[str, RegistryRow], id_: str) -> RegistryRow | None:
    pre = prefix_of(id_)
    for row in reg.values():
        if row.ids is not None and id_ in row.ids:
            return row
    for row in reg.values():
        if row.prefix == pre and row.ids is None:
            return row
    return None


def load_sources(path: Path, problems: list[str]) -> set[str]:
    ids: set[str] = set()
    for cells in table_rows(Path(path).read_text(encoding="utf-8")):
        if len(cells) < 3:
            continue
        first = _clean(cells[0])
        if first in ("ID",) or set(first) <= set("-: "):
            continue
        sid = first.strip("[]")
        kind = _clean(cells[2])
        if sid in ids:
            problems.append("sources: %s listed twice" % sid)
        ids.add(sid)
        if kind not in KINDS:
            problems.append("sources: %s has kind %r (want one of %s)" % (sid, kind, ", ".join(KINDS)))
    return ids


def _source_known(sid: str, sources: set[str]) -> bool:
    if sid in sources:
        return True
    return any(s.endswith("…") and sid.startswith(s[:-1]) for s in sources)


def own_repo(reg: dict[str, RegistryRow]) -> tuple[str | None, list[str]]:
    """The repo named by the `here` rows (the first segment of their Home), and the problems."""
    repos = sorted({r.home.partition("/")[0] for r in reg.values() if r.status == "here"})
    if len(repos) > 1:
        return None, ["docs/record-ids.md: the here rows name more than one repo (%s)"
                      % ", ".join(repos)]
    return (repos[0] if repos else None), []


def home_file(root: Path, row: RegistryRow, own: str | None) -> Path | None:
    """The Home of a row as a file of this repo; None for another repo's home."""
    repo, _, rel = row.home.partition("/")
    return Path(root) / rel if own is not None and repo == own and rel else None


def external_ids(external: Mapping[str, Path], problems: list[str]) -> dict[str, set[str]]:
    """{repo: the IDs that the table rows of its .md files define} for each --external root."""
    out: dict[str, set[str]] = {}
    for name, d in sorted(external.items()):
        d = Path(d)
        if not d.is_dir():
            problems.append("external root %s (%s) not found" % (name, d.name))
            continue
        ids: set[str] = set()
        for md in d.rglob("*.md"):
            ids |= defined_ids(md.read_text(encoding="utf-8", errors="replace"))
        out[name] = ids
    return out


def not_checked_note(repo: str) -> str:
    return "NOTE: IDs of %s not checked (no --external %s=DIR)" % (repo, repo)


def check(repo_root: Path, external: Mapping[str, Path] | None = None,
          record_dirs: Sequence[str] = ("ics",)) -> list[str]:
    root = Path(repo_root)
    external = dict(external or {})
    problems: list[str] = []
    reg_path = root / "docs" / "record-ids.md"
    if not reg_path.is_file():
        return ["docs/record-ids.md: missing"]
    try:
        reg = load_registry(reg_path)
    except ValueError as e:
        return ["docs/record-ids.md: %s" % e]
    own, own_problems = own_repo(reg)
    if own_problems:
        return own_problems
    src_path = root / "docs" / "sources.md"
    sources: set[str] | None = None
    if src_path.is_file():
        sources = load_sources(src_path, problems)
    dirs = [root / d for d in record_dirs]

    # definitions: every record.md under the record folders, and each `here` row's Home file
    defined: dict[str, str] = {}
    texts: dict[str, str] = {}

    def define(path: Path, only_prefix: str | None) -> None:
        rel = path.relative_to(root).as_posix()
        text = texts.get(rel)
        if text is None:
            text = texts[rel] = path.read_text(encoding="utf-8")
        for cells in table_rows(text):
            first = _clean(cells[0])
            if not ID_FULL.fullmatch(first):
                continue
            if only_prefix is not None and prefix_of(first) != only_prefix:
                continue
            if first in defined:
                if defined[first] != rel:
                    problems.append("%s: %s defined twice (also in %s)" % (rel, first, defined[first]))
                continue
            defined[first] = rel
            row = resolve(reg, first)
            if row is None:
                problems.append("%s: %s has a prefix that is not in the registry" % (rel, first))
            elif row.status == "retired":
                problems.append("%s: %s is retired (it left this repo); never define it again"
                                % (rel, first))
            elif row.status != "here":
                problems.append("%s: %s is registered as %s (home %s), not here"
                                % (rel, first, row.status, row.home))

    records = sorted({rec for d in dirs if d.is_dir() for rec in d.rglob("record.md")})
    for rec in records:
        define(rec, None)
    for row in reg.values():
        f = home_file(root, row, own) if row.status == "here" else None
        if f is not None and f.is_file() and f not in records:
            define(f, row.prefix)

    ext_defined = external_ids(external, problems)
    unchecked: set[str] = set()

    def judge(id_: str, where: str) -> None:
        row = resolve(reg, id_)
        if row is None:
            problems.append("%s: %s has a prefix that is not in the registry" % (where, id_))
        elif row.status == "here":
            if id_ not in defined:
                problems.append("%s: %s is not defined in any record" % (where, id_))
        elif row.status == "external":
            repo = row.home.partition("/")[0]
            if repo in ext_defined:
                if id_ not in ext_defined[repo]:
                    problems.append("%s: %s is not defined in %s (home %s)"
                                    % (where, id_, repo, row.home))
            elif repo not in external:
                unchecked.add(repo)

    # references in every markdown file under the record folders
    refs: dict[str, str] = {}
    for md in sorted({m for d in dirs if d.is_dir() for m in d.rglob("*.md")}):
        rel = md.relative_to(root).as_posix()
        refs[rel] = texts.get(rel) or md.read_text(encoding="utf-8")
    for rel, text in refs.items():
        for id_ in sorted(set(ID_REF.findall(text))):
            # signal and chip names (D7, A1, PC2, SHA-256) look like IDs: a reference counts
            # only with a registered prefix, or a DEV prefix; unknown prefixes fail in definitions
            if resolve(reg, id_) is None and not prefix_of(id_).endswith("-DEV"):
                continue
            judge(id_, rel)
        if sources is not None:
            for sid in sorted(set(BRACKET.findall(text))):
                if len(sid) > 1 and not _source_known(sid, sources):
                    problems.append("%s: source [%s] is not in docs/sources.md" % (rel, sid))

    return problems + [not_checked_note(r) for r in sorted(unchecked)]


def _external_arg(text: str) -> tuple[str, Path]:
    name, sep, path = text.partition("=")
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError("want NAME=DIR, got %r" % text)
    return name, Path(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--records", action="append", metavar="DIR",
                    help="a folder of records and their docs, relative to --repo (repeatable; "
                         "default ics)")
    ap.add_argument("--external", action="append", type=_external_arg, default=[],
                    metavar="NAME=DIR", help="a checkout of the repo NAME, to check its IDs")
    args = ap.parse_args(argv)
    out = check(args.repo, dict(args.external), tuple(args.records or ("ics",)))
    for line in out:
        print(line)
    bad = [l for l in out if not l.startswith("NOTE")]
    if bad:
        return 1
    print("PASS records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
