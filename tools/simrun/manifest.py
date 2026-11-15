# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""component.toml: load and check one manifest; find a component by name.

The schema is in docs/conventions.md ("component.toml"). Every key not listed there is an error.
Paths in a manifest are relative to its folder, with '/' separators, and stay inside its repo;
every named file and folder must exist.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

import check_records

KINDS = ("ic", "block", "machine", "adapter", "platform")
FIDELITIES = ("datasheet", "board", "extended")
TIERS = ("quick", "standard", "full")
MATCHES = ("first", "anywhere")
COMPARES = ("exact", "frames", "events")
LEVELS = ("drop-in", "function", "partial", "unverified")
MANIFEST = "component.toml"
TRANSLIT = re.compile(r"[a-z0-9]+")
# a component name: one or more lower-case path segments ("intel/8255a", "machines/demo")
NAME = re.compile(r"[a-z0-9][a-z0-9_.-]*(?:/[a-z0-9][a-z0-9_.-]*)*")
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PREFIX = re.compile(r"[A-Z][A-Z0-9]{1,9}(?:-DEV)?")
LOCAL_FAULT = re.compile(r"faults/([A-Za-z0-9_.-]+)\.patch")
DEP_FAULT = re.compile(r"(%s):([A-Za-z0-9_.-]+)" % NAME.pattern)


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class DataFile:
    """A binary written as hex (one byte per line) and passed to vvp as +<name>=<file>."""
    path: Path
    sizes: tuple[int, ...] = ()   # the allowed sizes in bytes; () = any
    pad_to: int = 0               # pad with FFh up to this size; 0 = no padding


@dataclass(frozen=True)
class Golden:
    path: Path
    compare: str                  # exact | frames | events


@dataclass
class Test:
    name: str
    tier: str
    top: str
    files: list[Path]
    incdirs: list[Path]
    params: dict
    plusargs: dict
    data: dict[str, DataFile]
    timeout_s: int | None
    golden: Golden | None
    ids: list[str]


@dataclass
class Negative:
    test: str
    fault: str                    # "faults/<name>.patch" or "<component>:<name>" of a dependency
    expect: str
    match: str
    ids: list[str]


@dataclass(frozen=True)
class Equivalent:
    """A Soviet part or second source; its differences and sources are in equivalents.md."""
    part: str
    translit: str | None          # [a-z0-9]+ (k580vv55a)
    level: str                    # drop-in | function | partial | unverified


@dataclass(frozen=True)
class BoardRecord:
    """The board record of a machine in another repo (retroComputersDocs), at a tag."""
    repo: str
    tag: str
    file: str                     # path in that repo, '/' separators


@dataclass
class Component:
    name: str
    kind: str
    title: str
    reproduces: str
    fidelity: str
    interface: int
    record_prefix: str | None
    rtl_top: str | None           # None: a docs-only ic (no [rtl])
    rtl_files: list[Path]
    depends: list[str]
    incdirs: list[Path]
    iverilog_flags: list[str]
    tests: list[Test]
    negatives: list[Negative]
    root: Path
    repo_root: Path
    equivalents: list[Equivalent] = field(default_factory=list)
    variant_of: str | None = None
    board_record: BoardRecord | None = None


# ---- value checks ----

class _Table:
    """One TOML table: typed reads, then done() rejects the keys nobody read."""

    def __init__(self, data, where: str):
        if not isinstance(data, dict):
            raise ManifestError("%s: want a table" % where)
        self.data = data
        self.where = where
        self.seen: set[str] = set()

    def get(self, key, required):
        self.seen.add(key)
        if key not in self.data:
            if required:
                raise ManifestError("%s: missing key %s" % (self.where, key))
            return None
        return self.data[key]

    def text(self, key, required=True, choices=None, pattern=None, default=None):
        v = self.get(key, required)
        if v is None:
            return default
        if not isinstance(v, str) or not v.strip():
            raise ManifestError("%s: %s must be a non-empty string" % (self.where, key))
        if choices and v not in choices:
            raise ManifestError("%s: %s = %r (want one of %s)"
                                % (self.where, key, v, ", ".join(choices)))
        if pattern and not pattern.fullmatch(v):
            raise ManifestError("%s: %s = %r is not of the form %s"
                                % (self.where, key, v, pattern.pattern))
        return v

    def number(self, key, required=True, minimum=1, default=None):
        v = self.get(key, required)
        if v is None:
            return default
        if not isinstance(v, int) or isinstance(v, bool) or v < minimum:
            raise ManifestError("%s: %s must be an integer >= %d" % (self.where, key, minimum))
        return v

    def texts(self, key, pattern=None):
        v = self.get(key, False)
        if v is None:
            return []
        if not isinstance(v, list) or not all(isinstance(x, str) and x for x in v):
            raise ManifestError("%s: %s must be a list of strings" % (self.where, key))
        if len(set(v)) != len(v):
            raise ManifestError("%s: %s lists an entry twice" % (self.where, key))
        for x in v:
            if pattern and not pattern.fullmatch(x):
                raise ManifestError("%s: %s entry %r is not of the form %s"
                                    % (self.where, key, x, pattern.pattern))
        return list(v)

    def scalars(self, key):
        """A table of name = string or integer (params, plusargs)."""
        v = self.get(key, False)
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ManifestError("%s: %s must be a table" % (self.where, key))
        for k, x in v.items():
            if not WORD.fullmatch(k):
                raise ManifestError("%s: %s name %r is not a word" % (self.where, key, k))
            if isinstance(x, bool) or not isinstance(x, (str, int)):
                raise ManifestError("%s: %s.%s must be a string or an integer"
                                    % (self.where, key, k))
        return dict(v)

    def table(self, key):
        v = self.get(key, False)
        return None if v is None else _Table(v, "%s.%s" % (self.where, key))

    def array(self, key):
        v = self.get(key, False)
        if v is None:
            return []
        if not isinstance(v, list):
            raise ManifestError("%s: %s must be an array of tables ([[%s]])"
                                % (self.where, key, key))
        return v

    def done(self):
        extra = sorted(set(self.data) - self.seen)
        if extra:
            raise ManifestError("%s: unknown key%s %s"
                                % (self.where, "s" if len(extra) > 1 else "", ", ".join(extra)))


class _Paths:
    """Manifest paths: relative to the component folder, inside the repo, existing."""

    def __init__(self, root: Path, repo_root: Path):
        self.root = root
        self.repo_root = repo_root

    def get(self, rel, where: str, want_dir=False) -> Path:
        if not isinstance(rel, str) or not rel:
            raise ManifestError("%s: a path must be a non-empty string" % where)
        if "\\" in rel or PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).drive:
            raise ManifestError("%s: %s must be relative, with '/' separators" % (where, rel))
        p = (self.root / rel).resolve()
        if p != self.repo_root and self.repo_root not in p.parents:
            raise ManifestError("%s: %s is outside the repository" % (where, rel))
        if not (p.is_dir() if want_dir else p.is_file()):
            raise ManifestError("%s: %s not found" % (where, rel))
        return p

    def many(self, t: _Table, key, want_dir=False) -> list[Path]:
        return [self.get(r, "%s.%s" % (t.where, key), want_dir) for r in t.texts(key)]


def _repo_root(root: Path, name: str, kind: str, where: str) -> Path:
    """<repo>/ics/<name> for an IC, <repo>/<name> otherwise."""
    parts = name.split("/")
    tail = list(root.parts[-len(parts):])
    if tail != parts:
        raise ManifestError("%s: name %r does not match the folder %s"
                            % (where, name, "/".join(tail)))
    base = root.parents[len(parts) - 1]
    if kind == "ic":
        if base.name != "ics":
            raise ManifestError("%s: an ic lives in <repo>/ics/%s" % (where, name))
        base = base.parent
    return base


def _data(dt: _Table, paths: _Paths, plusargs: dict) -> dict[str, DataFile]:
    data: dict[str, DataFile] = {}
    for dname in list(dt.data):
        if not WORD.fullmatch(dname):
            raise ManifestError("%s: data name %r is not a word" % (dt.where, dname))
        if dname in plusargs:
            raise ManifestError("%s: %s is both a data file and a plusarg" % (dt.where, dname))
        d = dt.table(dname)
        path = paths.get(d.text("path"), d.where + ".path")
        sizes = d.get("sizes", False) or []
        if (not isinstance(sizes, list)
                or not all(isinstance(s, int) and not isinstance(s, bool) and s > 0
                           for s in sizes)):
            raise ManifestError("%s: sizes must be a list of positive integers" % d.where)
        pad_to = d.number("pad_to", required=False, minimum=0, default=0)
        if pad_to and sizes and pad_to < max(sizes):
            raise ManifestError("%s: pad_to %d is below the largest size" % (d.where, pad_to))
        d.done()
        data[dname] = DataFile(path, tuple(sizes), pad_to)
    dt.done()
    return data


def _test(t: _Table, paths: _Paths) -> Test:
    name = t.text("name", pattern=WORD)
    t.where = "%s %s" % (t.where, name)
    tier = t.text("tier", choices=TIERS)
    top = t.text("top")
    files = paths.many(t, "files")
    if not files:
        raise ManifestError("%s: files is empty" % t.where)
    incdirs = paths.many(t, "incdirs", want_dir=True)
    params = t.scalars("params")
    plusargs = t.scalars("plusargs")
    dt = t.table("data")
    data = {} if dt is None else _data(dt, paths, plusargs)
    timeout_s = t.number("timeout_s", required=False)
    golden = None
    gt = t.table("golden")
    if gt is not None:
        golden = Golden(paths.get(gt.text("file"), gt.where + ".file"),
                        gt.text("compare", choices=COMPARES))
        gt.done()
    ids = t.texts("ids", pattern=check_records.ID_FULL)
    t.done()
    return Test(name, tier, top, files, incdirs, params, plusargs, data, timeout_s, golden, ids)


def _negative(t: _Table, paths: _Paths, tests: set[str], depends: list[str]) -> Negative:
    test = t.text("test")
    if test not in tests:
        raise ManifestError("%s: test %r is not a test of this component" % (t.where, test))
    fault = t.text("fault")
    t.where = "%s %s" % (t.where, fault)
    if LOCAL_FAULT.fullmatch(fault):
        paths.get(fault, t.where + ".fault")
    else:
        m = DEP_FAULT.fullmatch(fault)
        if not m:
            raise ManifestError("%s: fault must be faults/<name>.patch or <component>:<name>"
                                % t.where)
        if m.group(1) not in depends:
            raise ManifestError("%s: %s is not in rtl.depends" % (t.where, m.group(1)))
    expect = t.text("expect")
    match = t.text("match", required=False, choices=MATCHES, default="first")
    ids = t.texts("ids", pattern=check_records.ID_FULL)
    t.done()
    return Negative(test, fault, expect, match, ids)


def load(path) -> Component:
    """Reads and checks one component.toml."""
    path = Path(path).resolve()
    where = path.parent.name + "/" + path.name
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ManifestError("%s: cannot read: %s" % (where, e.strerror))
    except tomllib.TOMLDecodeError as e:
        raise ManifestError("%s: %s" % (where, e))
    top = _Table(raw, where)
    ct = top.table("component")
    if ct is None:
        raise ManifestError("%s: missing [component]" % where)
    name = ct.text("name", pattern=NAME)
    where = name
    ct.where = "%s [component]" % where
    kind = ct.text("kind", choices=KINDS)
    title = ct.text("title")
    reproduces = ct.text("reproduces")
    fidelity = ct.text("fidelity", choices=FIDELITIES)
    interface = ct.number("interface")
    record_prefix = ct.text("record_prefix", required=False, pattern=PREFIX)
    variant_of = ct.text("variant_of", required=False, pattern=NAME)
    if variant_of == name:
        raise ManifestError("%s: variant_of names the component itself" % ct.where)
    bt = ct.table("board_record")
    board_record = None
    if bt is not None:
        board_record = BoardRecord(bt.text("repo", pattern=re.compile(r"[A-Za-z0-9_.-]+")),
                                   bt.text("tag"), _other_repo_path(bt.text("file"), bt.where))
        bt.done()
    ct.done()

    root = path.parent
    repo_root = _repo_root(root, name, kind, where)
    paths = _Paths(root, repo_root)

    equivalents: list[Equivalent] = []
    for i, raw_e in enumerate(top.array("equivalent")):
        et = _Table(raw_e, "%s [[equivalent]] %d" % (where, i + 1))
        e = Equivalent(et.text("part"), et.text("translit", required=False, pattern=TRANSLIT),
                       et.text("level", choices=LEVELS))
        et.done()
        if any(x.part == e.part for x in equivalents):
            raise ManifestError("%s: equivalent %s listed twice" % (where, e.part))
        equivalents.append(e)

    rt = top.table("rtl")
    rtl_top, rtl_files, depends, incdirs, flags = None, [], [], [], []
    if rt is None:
        if kind != "ic":
            raise ManifestError("%s: missing [rtl] (only a docs-only ic has none)" % where)
    else:
        rt.where = "%s [rtl]" % where
        rtl_top = rt.text("top")
        rtl_files = paths.many(rt, "files")
        if not rtl_files:
            raise ManifestError("%s: files is empty" % rt.where)
        depends = rt.texts("depends", pattern=NAME)
        if name in depends:
            raise ManifestError("%s: depends on itself" % rt.where)
        incdirs = paths.many(rt, "incdirs", want_dir=True)
        flags = rt.texts("iverilog_flags")
        if any(not f.startswith("-") for f in flags):
            raise ManifestError("%s: iverilog_flags entries are options (start with '-')"
                                % rt.where)
        rt.done()
    if rt is None and (top.data.get("test") or top.data.get("negative")):
        raise ManifestError("%s: a docs-only ic (no [rtl]) has no tests or negatives" % where)

    tests: list[Test] = []
    for i, raw_t in enumerate(top.array("test")):
        t = _test(_Table(raw_t, "%s [[test]] %d" % (where, i + 1)), paths)
        if any(x.name == t.name for x in tests):
            raise ManifestError("%s: test %s defined twice" % (where, t.name))
        tests.append(t)
    negatives: list[Negative] = []
    for i, raw_n in enumerate(top.array("negative")):
        n = _negative(_Table(raw_n, "%s [[negative]] %d" % (where, i + 1)), paths,
                      {t.name for t in tests}, depends)
        if any((x.test, x.fault) == (n.test, n.fault) for x in negatives):
            raise ManifestError("%s: negative %s of %s listed twice" % (where, n.fault, n.test))
        negatives.append(n)
    top.where = where
    top.done()
    return Component(name, kind, title, reproduces, fidelity, interface, record_prefix, rtl_top,
                     rtl_files, depends, incdirs, flags, tests, negatives, root, repo_root,
                     equivalents, variant_of, board_record)


def _other_repo_path(rel: str, where: str) -> str:
    """A path in another repo: relative, '/' separators, no '..' (not checked for existence)."""
    p = PurePosixPath(rel)
    if "\\" in rel or p.is_absolute() or PureWindowsPath(rel).drive or ".." in p.parts:
        raise ManifestError("%s: file %s must be relative, with '/' separators and no '..'"
                            % (where, rel))
    return rel


def candidates(name: str, root) -> list[Path]:
    """Where a component of that name may be in one repo: <root>/ics/<name>, <root>/<name>."""
    return [Path(root) / "ics" / name / MANIFEST, Path(root) / name / MANIFEST]


def resolve(name: str, search) -> Component:
    """The component of that name in the search roots (repo roots); exactly one must exist."""
    if not NAME.fullmatch(name):
        raise ManifestError("%r is not a component name" % name)
    found: list[Path] = []
    for root in search:
        for p in candidates(name, root):
            if p.is_file() and p.resolve() not in found:
                found.append(p.resolve())
    if not found:
        raise ManifestError("component %s not found in the search roots (%s)"
                            % (name, ", ".join(Path(r).name or str(r) for r in search)))
    if len(found) > 1:
        raise ManifestError("component %s found twice: %s"
                            % (name, ", ".join(p.parent.as_posix() for p in found)))
    c = load(found[0])
    if c.name != name:
        raise ManifestError("%s: name is %r" % (found[0].parent.as_posix(), c.name))
    return c


def fault_name(c: Component, n: Negative) -> str:
    """'<owner component>:<fault>': the identity of the patch, the same in every test it kills."""
    m = LOCAL_FAULT.fullmatch(n.fault)
    return "%s:%s" % (c.name, m.group(1)) if m else n.fault


def fault_path(c: Component, n: Negative, search) -> Path:
    """The patch file of a negative: faults/<name>.patch of this component, or of the dependency
    that <component>:<name> names (found in the search roots)."""
    if LOCAL_FAULT.fullmatch(n.fault):
        return _Paths(c.root, c.repo_root).get(n.fault, "%s negative" % c.name)
    m = DEP_FAULT.fullmatch(n.fault)
    if not m:
        raise ManifestError("%s: fault %r is not faults/<name>.patch or <component>:<name>"
                            % (c.name, n.fault))
    if m.group(1) not in c.depends:
        raise ManifestError("%s: fault %s: %s is not in rtl.depends" % (c.name, n.fault, m.group(1)))
    dep = resolve(m.group(1), search)
    rel = "faults/%s.patch" % m.group(2)
    return _Paths(dep.root, dep.repo_root).get(rel, "%s negative %s (in %s)"
                                               % (c.name, n.fault, dep.name))
