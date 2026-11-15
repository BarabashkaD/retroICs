# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Traceability matrix: record ID -> the tests that cite it -> the faults that kill it -> status.

Rows: every ID defined in the record.md of a given component, and every ID a test or a negative
of a given component cites in `ids`. Status: tested (a test or negative cites it), else SILENT (a
bullet of the record's "SILENT (<prefix>)" section names it), else untestable (a bullet of its
"Untestable (<prefix>)" section names it), else open.

The registry (docs/record-ids.md of this repo, or --registry) gives each ID its home. A cited ID
with status `here` must be defined in its home file; `external` ones are checked only with a root of
their repo (external {repo: checkout}; else one NOTE per repo); `pending` and `retired` ones are
not checked; an unregistered prefix fails. The parsing is check_records'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import check_records as cr

from .manifest import Component, fault_name

REPO = Path(__file__).resolve().parent.parent.parent
REGISTRY = REPO / "docs" / "record-ids.md"
RECORD = "record.md"
STATUSES = ("tested", "SILENT", "untestable", "open")


@dataclass(frozen=True)
class TraceRow:
    id: str
    home: str
    tests: list[str]            # "<component>:<test>"
    killing_faults: list[str]   # "<owner component>:<fault>"
    status: str                 # tested | SILENT | untestable | open


class TraceError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


class Matrix(list):
    """The rows (a list of TraceRow), with .notes: the NOTE lines (IDs of a repo not checked)."""

    def __init__(self, rows=(), notes=()):
        super().__init__(rows)
        self.notes: list[str] = list(notes)


def _key(id_: str):
    pre, num = id_.rsplit("-", 1)
    m = re.fullmatch(r"([DEM]?)(\d+)", num)
    return (pre, m.group(1), int(m.group(2)))


def _marked(text: str, prefix: str, title: str) -> set[str]:
    return {i for b in cr.section_bullets(text, title, prefix) for i in cr.bullet_ids(b, prefix)}


def matrix(components: list[Component], external=None, registry=None) -> Matrix:
    """The rows, sorted by ID, as a Matrix (a list) whose .notes holds the NOTE lines. Raises
    TraceError with every problem."""
    reg_path = Path(registry) if registry is not None else REGISTRY
    repo_root = reg_path.resolve().parent.parent
    reg = cr.load_registry(reg_path)
    own, problems = cr.own_repo(reg)
    if problems:
        raise TraceError(problems)

    homes: dict[str, str] = {}       # id -> home
    texts: dict[str, str] = {}       # id -> the text of the record that defines it
    def define(ids, home, text):
        for i in ids:
            homes.setdefault(i, home)
            texts.setdefault(i, text)

    for c in components:
        rec = c.root / RECORD
        if rec.is_file():
            text = rec.read_text(encoding="utf-8")
            for i in sorted(cr.defined_ids(text), key=_key):
                row = cr.resolve(reg, i)
                if row is None:
                    problems.append("%s: %s has a prefix that is not in the registry" % (c.name, i))
                    continue
                define([i], row.home, text)

    tests: dict[str, set[str]] = {}
    faults: dict[str, set[str]] = {}
    for c in components:
        for t in c.tests:
            for i in t.ids:
                tests.setdefault(i, set()).add("%s:%s" % (c.name, t.name))
        for n in c.negatives:
            for i in n.ids:
                tests.setdefault(i, set()).add("%s:%s" % (c.name, n.test))
                faults.setdefault(i, set()).add(fault_name(c, n))

    external = dict(external or {})
    ext_defined = cr.external_ids(external, problems)
    unchecked: set[str] = set()
    for i in sorted(set(tests) - set(homes), key=_key):
        row = cr.resolve(reg, i)
        where = ", ".join(sorted(tests[i]))
        if row is None:
            problems.append("%s: %s has a prefix that is not in the registry" % (where, i))
            continue
        if row.status == "here":
            f = cr.home_file(repo_root, row, own)
            text = f.read_text(encoding="utf-8") if f is not None and f.is_file() else ""
            if i not in cr.defined_ids(text):
                problems.append("%s: %s is not defined in %s" % (where, i, row.home))
                continue
            define([i], row.home, text)
        else:
            if row.status == "external":
                repo = row.home.partition("/")[0]
                if repo in ext_defined:
                    if i not in ext_defined[repo]:
                        problems.append("%s: %s is not defined in %s (home %s)"
                                        % (where, i, repo, row.home))
                        continue
                elif repo not in external:
                    unchecked.add(repo)
            define([i], row.home, "")
    if problems:
        raise TraceError(problems)
    rows = Matrix(notes=[cr.not_checked_note(r) for r in sorted(unchecked)])
    for i in sorted(homes, key=_key):
        pre = cr.prefix_of(i)
        if i in tests:
            status = "tested"
        elif i in _marked(texts[i], pre, "SILENT"):
            status = "SILENT"
        elif i in _marked(texts[i], pre, "Untestable"):
            status = "untestable"
        else:
            status = "open"
        rows.append(TraceRow(i, homes[i], sorted(tests.get(i, ())), sorted(faults.get(i, ())),
                             status))
    return rows


def table(rows: list[TraceRow]) -> list[str]:
    """The matrix as markdown table lines."""
    def line(cells):
        return "|" + "|".join(" %s " % c if c else " " for c in cells) + "|"

    out = [line(("ID", "Home", "Tests", "Killing faults", "Status")), "|---|---|---|---|---|"]
    for r in rows:
        out.append(line((r.id, r.home, ", ".join(r.tests), ", ".join(r.killing_faults),
                         r.status)))
    return out
