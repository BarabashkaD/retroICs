# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Record checker: IDs defined once, every reference resolvable, source IDs registered.

Usage: python -B tools/check_records.py [--legacy FILE] [--docs DIR]

Inputs, relative to the repository root:
  docs/record-ids.md  registry table  | Prefix | Home | Status | IDs |
                      Status: here (defined in ics/**/record.md), pending (home does not exist
                      yet, nothing checked), external (defined in another repo; checked only with
                      --docs). IDs: optional comma list; the row then covers only those IDs of
                      the prefix (a prefix may be split over several rows).
  docs/sources.md     source table    | ID | Home | Kind |   (ID in brackets, e.g. [C78])
  ics/**/record.md    records; an ID is defined by the first cell of a table row.
  ics/**/*.md         every markdown file: its record ID and bracket source ID references.

Output: one line per problem, or PASS records. Lines starting with NOTE are not problems.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ID_RE = r"[A-Z][A-Z0-9]{1,9}(?:-DEV)?-[DEM]?\d+"
ID_FULL = re.compile(ID_RE)
# a reference in prose: not part of a longer word or bracket token like [AP-62]
ID_REF = re.compile(r"(?<![\w\[\-/])(" + ID_RE + r")(?![\w\-])")
# a bracket source ID: a Latin or Cyrillic capital first ([C78], [ГФ24]) or at least four digits
# first ([7490], [74198]); not a bit range ([15:8]), a short number ([12]) or a markdown link
BRACKET = re.compile(r"\[((?:[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9]*|\d{4,}[A-Za-z0-9]*)"
                     r"(?:-[A-Za-z0-9…]+)*)\](?!\()")
STATUSES = ("here", "pending", "external")
KINDS = ("vendor", "board", "listing", "comparison-only")
SILENT_HEAD = re.compile(r"^#### SILENT \((.+?)\)\s*$")


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


def legacy_ids(md_text: str) -> set[str]:
    out = defined_ids(md_text)
    for line in md_text.splitlines():
        m = _LIST_ID.match(line)
        if m:
            out.add(m.group(1))
    return out


def silent_bullets(md_text: str, prefix: str) -> list[str]:
    bullets: list[str] = []
    inside = False
    for line in md_text.splitlines():
        m = SILENT_HEAD.match(line)
        if m:
            inside = m.group(1) == prefix
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


def check(repo_root: Path, legacy: Path | None, docs_root: Path | None) -> list[str]:
    root = Path(repo_root)
    problems: list[str] = []
    notes: list[str] = []
    reg_path = root / "docs" / "record-ids.md"
    if not reg_path.is_file():
        return ["docs/record-ids.md: missing"]
    try:
        reg = load_registry(reg_path)
    except ValueError as e:
        return ["docs/record-ids.md: %s" % e]
    src_path = root / "docs" / "sources.md"
    sources: set[str] | None = None
    if src_path.is_file():
        sources = load_sources(src_path, problems)

    # definitions
    defined: dict[str, str] = {}
    texts: dict[str, str] = {}
    for rec in sorted((root / "ics").rglob("record.md")) if (root / "ics").is_dir() else []:
        rel = rec.relative_to(root).as_posix()
        text = rec.read_text(encoding="utf-8")
        texts[rel] = text
        for cells in table_rows(text):
            first = _clean(cells[0])
            if not ID_FULL.fullmatch(first):
                continue
            if first in defined:
                problems.append("%s: %s defined twice (also in %s)" % (rel, first, defined[first]))
                continue
            defined[first] = rel
            row = resolve(reg, first)
            if row is None:
                problems.append("%s: %s has a prefix that is not in the registry" % (rel, first))
            elif row.status != "here":
                problems.append("%s: %s is registered as %s (home %s), not here"
                                % (rel, first, row.status, row.home))

    ext_seen = False
    ext_defined: set[str] | None = None
    if docs_root is not None:
        d = Path(docs_root)
        if not d.is_dir():
            problems.append("docs root %s not found" % d.name)
        else:
            ext_defined = set()
            for md in d.rglob("*.md"):
                ext_defined |= defined_ids(md.read_text(encoding="utf-8", errors="replace"))

    def judge(id_: str, where: str) -> None:
        nonlocal ext_seen
        row = resolve(reg, id_)
        if row is None:
            problems.append("%s: %s has a prefix that is not in the registry" % (where, id_))
        elif row.status == "here":
            if id_ not in defined:
                problems.append("%s: %s is not defined in any record" % (where, id_))
        elif row.status == "external":
            if ext_defined is None:
                ext_seen = True
            elif id_ not in ext_defined:
                problems.append("%s: %s is not defined in the docs root (home %s)"
                                % (where, id_, row.home))

    # references in every markdown file under ics/ (records, READMEs, equivalents, AGENTS, indexes)
    refs: dict[str, str] = {}
    for md in sorted((root / "ics").rglob("*.md")) if (root / "ics").is_dir() else []:
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

    # legacy gate
    if legacy is not None:
        for id_ in sorted(legacy_ids(Path(legacy).read_text(encoding="utf-8"))):
            judge(id_, "legacy")

    if ext_seen and docs_root is None:
        notes.append("NOTE: board IDs not checked (no --docs): their definitions are in another repo")
    return problems + notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--legacy", type=Path, help="the legacy record whose IDs must all be accounted for")
    ap.add_argument("--docs", type=Path, help="checkout of the docs repo, to check external IDs")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    out = check(args.repo, args.legacy, args.docs)
    for line in out:
        print(line)
    bad = [l for l in out if not l.startswith("NOTE")]
    if bad:
        return 1
    print("PASS records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
