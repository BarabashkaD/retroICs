# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""simrun run: compiles and runs the tests of components with Icarus Verilog, and their faults.

Pass rule: vvp exits 0, prints a line that starts with PASS and no line that starts with ERROR or
contains FATAL (lines stripped); with a golden file, its compare passes too.

A fault (a [[negative]] of the manifest) is applied to copies of only the files its patch changes,
taken from the repo that owns the patch (a dependency's fault patches a file of that dependency's
repo), under <test folder>/neg_<fault>/copy/<path in that repo>. It is CAUGHT when the run fails
and its first ERROR/FATAL line (match = "first") or any line (match = "anywhere") contains the
expected text, '*' matching any characters; MISSED otherwise. A patch that does not apply, or that
changes a file the test does not compile, is STALE. A fault whose patch changes only files replaced
by --replace is SKIPPED.

Outputs: <out>/<run-id>/<component>/<test>/ (vvp.log, iverilog.log, data hex files), the faults in
neg_<fault>/ below it, and <out>/<run-id>/summary.json. Without keep, the .vvp and the patched
copies of a passing test or a caught fault are removed.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import filelist, hexdata
from .manifest import (LOCAL_FAULT, TIERS, WORD, Component, Negative, Test, fault_name,
                       fault_path, resolve)
from .negative import apply_patch, patched_files

REQUIRED_IVERILOG = "13.0"
TEST_STATUSES = ("PASS", "FAIL")
FAULT_STATUSES = ("CAUGHT", "MISSED", "STALE", "SKIPPED")


class ToolError(RuntimeError):
    """iverilog or vvp missing, or not the required version."""


class RunError(ValueError):
    """A bad option value (--replace, --param, --tier, --jobs)."""


# ---- the runner's rules ----

def first_error(text):
    """The first line of a run's output that starts with ERROR or contains FATAL (stripped), or None."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('ERROR') or 'FATAL' in line:
            return line
    return None


def contains(text, expected):
    """True when text contains expected; '*' in expected matches any characters."""
    return re.search('.*'.join(re.escape(part) for part in expected.split('*')), text) is not None


def passes(returncode, text) -> bool:
    """The pass rule: exit code 0, a line that starts with PASS, no ERROR or FATAL line."""
    lines = [l.strip() for l in text.splitlines()]
    return (returncode == 0 and any(l.startswith('PASS') for l in lines)
            and not any(l.startswith('ERROR') or 'FATAL' in l for l in lines))


# ---- tools ----

def version_of(text: str):
    """The version in the output of iverilog -V ("Icarus Verilog version 13.0 ..."), or None."""
    m = re.search(r"Icarus Verilog version (\d+\.\d+)", text)
    return m.group(1) if m else None


def iverilog_version(iverilog: str):
    res = subprocess.run([iverilog, "-V"], capture_output=True, text=True)
    return version_of(res.stdout + res.stderr)


@dataclass(frozen=True)
class Tools:
    iverilog: str
    vvp: str
    env: dict
    version: str


def find_tools(iverilog=None) -> Tools:
    """iverilog (the argument, else IVERILOG, else iverilog on PATH), vvp from its folder; the
    version must be REQUIRED_IVERILOG."""
    name = iverilog or os.environ.get("IVERILOG") or "iverilog"
    path = shutil.which(name)
    if not path:
        raise ToolError("iverilog not found: %s" % name)
    bindir = os.path.dirname(os.path.abspath(path))
    vvp = shutil.which("vvp", path=bindir)
    if not vvp:
        raise ToolError("vvp not found next to %s" % name)
    version = iverilog_version(path)
    if version != REQUIRED_IVERILOG:
        raise ToolError("Icarus Verilog %s required, found %s (%s -V)"
                        % (REQUIRED_IVERILOG, version or "no version", name))
    env = dict(os.environ)
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    return Tools(path, vvp, env, version)


# ---- options ----

def parse_replace(items) -> dict[str, list[str]]:
    """--replace FILE=FILES (FILES separated by commas) -> {FILE: [FILES]}."""
    out: dict[str, list[str]] = {}
    for item in items or ():
        file, sep, rest = item.partition("=")
        files = rest.split(",")
        if not sep or not file or not rest or not all(files):
            raise RunError("--replace %r: want FILE=FILES (FILES separated by commas)" % item)
        if file in out:
            raise RunError("--replace %s given twice" % file)
        out[file] = files
    return out


def parse_param(items) -> dict[str, str]:
    """--param NAME=V -> {NAME: V}."""
    out: dict[str, str] = {}
    for item in items or ():
        name, sep, value = item.partition("=")
        if not sep or not WORD.fullmatch(name) or value == "":
            raise RunError("--param %r: want NAME=VALUE, NAME a word" % item)
        if name in out:
            raise RunError("--param %s given twice" % name)
        out[name] = value
    return out


def select(components, tier: str) -> list[tuple[Component, Test]]:
    """The tests of the components at the tier or a lower one (quick < standard < full)."""
    if tier not in TIERS:
        raise RunError("tier %r (want one of %s)" % (tier, ", ".join(TIERS)))
    limit = TIERS.index(tier)
    return [(c, t) for c in components for t in c.tests if TIERS.index(t.tier) <= limit]


GENERATION = re.compile(r"-g\d{4}(?:-[a-z]+)?")   # -g2005, -g2005-sv, -g2012, ...


def compile_flags(c: Component, search) -> list[str]:
    """The iverilog_flags of c and its dependencies, dependencies first, each once. Two different
    language generations (-g2005, -g2012, ...) are a RunError."""
    flags: list[str] = []
    gens: dict[str, str] = {}                     # generation flag -> the first component with it
    for comp in filelist.components(c, search):
        for f in comp.iverilog_flags:
            if GENERATION.fullmatch(f):
                gens.setdefault(f, comp.name)
            if f not in flags:
                flags.append(f)
    if len(gens) > 1:
        raise RunError("%s: iverilog generations differ: %s"
                       % (c.name, ", ".join("%s %s" % (n, g) for g, n in gens.items())))
    return flags


# ---- golden compare ----

def compare_exact(produced: Path, golden: Path):
    """compare = "exact": the file the test wrote, byte for byte."""
    if produced.read_bytes() == golden.read_bytes():
        return True, "INFO: golden: %s matches\n" % golden.name
    return False, "ERROR: golden: %s differs from the golden file\n" % produced.name


# compare kind -> fn(produced, golden) -> (ok, text). A consumer passes its own (e.g. a frame
# compare for "frames") through run(comparers=...).
COMPARERS = {"exact": compare_exact}


# ---- results ----

@dataclass
class Result:
    component: str
    test: str
    fault: str | None          # "<owner component>:<name>"; None for the test itself
    status: str                # PASS | FAIL, or CAUGHT | MISSED | STALE | SKIPPED
    first_error: str | None
    expect: str | None = None
    match: str | None = None
    log: str | None = None     # relative to the run folder, '/' separators

    def as_json(self) -> dict:
        d = {"component": self.component, "test": self.test}
        if self.fault is not None:
            d.update(fault=self.fault, status=self.status, expect=self.expect, match=self.match)
        else:
            d.update(status=self.status)
        d.update(first_error=self.first_error, log=self.log)
        return d


@dataclass
class Summary:
    run_id: str
    run_dir: Path
    path: Path                 # <run_dir>/summary.json
    commit: str | None
    iverilog: str
    tier: str
    negative: bool
    tests: list[Result]
    faults: list[Result]
    repos: dict = field(default_factory=dict)   # repo root, relative ('/') -> HEAD or None

    @property
    def exit_code(self) -> int:
        bad = (any(r.status != "PASS" for r in self.tests)
               or any(r.status in ("MISSED", "STALE") for r in self.faults))
        return 1 if bad else 0

    def as_json(self) -> dict:
        return {"run_id": self.run_id, "commit": self.commit, "repos": self.repos,
                "iverilog": self.iverilog, "tier": self.tier, "negative": self.negative,
                "tests": [r.as_json() for r in self.tests],
                "faults": [r.as_json() for r in self.faults]}


# ---- one run ----

def _key(p) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def _unique(paths) -> list[Path]:
    out, seen = [], set()
    for p in paths:
        if _key(p) not in seen:
            seen.add(_key(p))
            out.append(Path(p))
    return out


@dataclass
class _Unit:
    comp: Component
    test: Test
    folder: Path
    paths: list[Path]
    incdirs: list[Path]
    params: dict
    flags: list[str] = field(default_factory=list)
    neg: Negative | None = None
    fault: str | None = None
    patch: Path | None = None
    patch_label: str | None = None
    owner_root: Path | None = None
    skip: str | None = None


def _git_root(p: Path) -> Path:
    """The git work tree that holds p, else p (git apply works outside a repository too)."""
    res = subprocess.run(["git", "-C", str(p), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    return Path(res.stdout.strip()).resolve() if res.returncode == 0 and res.stdout.strip() else p


def _commit(p: Path):
    res = subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"], capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else None


def _repo_name(root: Path, base: Path) -> str:
    """root relative to base with '/' separators ("." , "lib/retroICs", "../retroICs"); the folder
    name when no relative path exists (another drive on Windows). Never absolute."""
    try:
        rel = os.path.relpath(root, base).replace(os.sep, "/")
    except ValueError:
        return root.name
    return root.name if os.path.isabs(rel) else rel


def _repo_commits(repos: list[Path], run_dir: Path) -> dict:
    """{repo root relative to the checkout that holds the output (else the current folder): HEAD
    of that root, or None outside git}."""
    base = _git_root(run_dir)
    if base == run_dir:
        base = Path.cwd().resolve()
    out: dict = {}
    for r in repos:
        out[_repo_name(r, base)] = _commit(r)
    return out


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _prepare_fault(u: _Unit, paths: list[Path]) -> list[Path]:
    """Copies the files the patch changes (from the patch's own repo) and applies it to the copies;
    returns the file list with the copies in place. Raises ValueError or OSError."""
    copy_root = u.folder / "copy"
    keys = [_key(p) for p in paths]
    rels = patched_files(str(u.patch))
    if not rels:
        raise ValueError("the patch changes no file")
    for rel in rels:
        src = (u.owner_root / rel).resolve()
        if _key(src) not in keys:
            raise ValueError("%s is not compiled in this test" % rel)
        dst = copy_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        i = keys.index(_key(src))
        paths[i] = dst
        keys[i] = _key(dst)
    try:
        apply_patch(str(_git_root(copy_root)), str(copy_root), str(u.patch))
    except ValueError as e:
        raise ValueError(str(e).replace(str(u.patch), u.patch_label)) from None
    return paths


def _execute(u: _Unit, tools: Tools, comparers: dict):
    """Builds and runs one test or one fault of it. Returns (ok, text, log): ok None when the fault
    could not be set up (STALE)."""
    u.folder.mkdir(parents=True, exist_ok=True)
    paths = list(u.paths)
    if u.patch is not None:
        try:
            paths = _prepare_fault(u, paths)
        except (ValueError, OSError) as e:
            return None, "ERROR: fault %s: %s\n" % (u.fault, e), None
    try:
        made = hexdata.write_hexfiles(u.test.data, u.folder)
    except (hexdata.HexError, OSError) as e:
        return False, "ERROR: %s\n" % e, None
    top = u.test.top
    exe = u.folder / (u.test.name + ".vvp")
    cmd = ([tools.iverilog] + list(u.flags)
           + [a for d in u.incdirs for a in ("-I", str(d))]
           + ["-s", top, "-o", str(exe)]
           + ["-P%s.%s=%s" % (top, k, v) for k, v in sorted(u.params.items())]
           + [str(p) for p in paths])
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         cwd=u.folder, env=tools.env)
    compiled = res.stdout + res.stderr
    if compiled or res.returncode:
        _write(u.folder / "iverilog.log", compiled)
    if res.returncode:
        return False, "ERROR: iverilog: " + compiled, u.folder / "iverilog.log"
    plusargs = ["+%s=%s" % (k, v) for k, v in u.test.plusargs.items()]
    plusargs += ["+%s=%s" % (k, v) for k, v in made.items()]
    try:
        res = subprocess.run([tools.vvp, "-n", str(exe)] + plusargs, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", cwd=u.folder,
                             env=tools.env, timeout=u.test.timeout_s)
        text, code = res.stdout + res.stderr, res.returncode
    except subprocess.TimeoutExpired as e:
        def s(x):
            return x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")
        text = s(e.stdout) + s(e.stderr)
        text += "\nERROR: timeout: vvp ran longer than %d s\n" % u.test.timeout_s
        code = -1
    log = u.folder / "vvp.log"
    _write(log, text)
    ok = passes(code, text)
    if ok and u.test.golden is not None:
        g = u.test.golden
        fn = comparers.get(g.compare)
        produced = u.folder / g.path.name
        if fn is None:
            ok, more = False, ("ERROR: golden: no comparer for compare = %s (the consumer passes one)\n"
                               % g.compare)
        elif not produced.is_file():
            ok, more = False, "ERROR: golden: the test wrote no %s\n" % g.path.name
        else:
            ok, more = fn(produced, g.path)
        text += more
        _write(log, text)
    return ok, text, log


def _cleanup(u: _Unit) -> None:
    for exe in u.folder.glob("*.vvp"):
        exe.unlink()
    shutil.rmtree(u.folder / "copy", ignore_errors=True)


def _fault_folder(n: Negative) -> str:
    m = LOCAL_FAULT.fullmatch(n.fault)
    return "neg_" + (m.group(1) if m else re.sub(r"[^A-Za-z0-9_.-]", "_", n.fault))


def _new_run_dir(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for i in range(1, 1000):
        d = out / (stamp if i == 1 else "%s-%d" % (stamp, i))
        try:
            d.mkdir()
            return d
        except FileExistsError:
            continue
    raise RunError("no free run folder in %s" % out.name)


def run(components, tier, jobs, negative, out, replace: dict[str, list[str]], params: dict, *,
        search=None, iverilog=None, keep=False, comparers=None, log=print) -> Summary:
    """Runs the tests of the components at the tier (and lower), with their faults when negative.
    replace: {file: [files]} compiled in place of that file (paths, relative to the current
    folder or absolute); params: {NAME: value} overriding the parameter NAME of every selected test
    that declares it. Raises RunError, ToolError, ManifestError before anything is built."""
    if not isinstance(jobs, int) or jobs < 1:
        raise RunError("jobs must be an integer >= 1")
    selected = select(components, tier)
    if not selected:
        raise RunError("no tests at tier %s" % tier)
    roots = _unique([Path(p).resolve() for p in (search or [])]
                    + [c.repo_root for c in components])
    rep = {_key(Path(k).resolve()): [Path(v).resolve() for v in vs] for k, vs in replace.items()}
    for vs in rep.values():
        for v in vs:
            if not v.is_file():
                raise RunError("--replace: %s not found" % v.name)
    comparers = {**COMPARERS, **(comparers or {})}

    units: list[_Unit] = []
    repos: list[Path] = []                         # the repo roots of the components that run
    used_files: set[str] = set()
    used_params: set[str] = set()
    for c, t in selected:
        files = _unique(list(t.files) + filelist.files(c, roots))
        used_files |= {_key(f) for f in files} & set(rep)
        paths = [m for f in files for m in rep.get(_key(f), [f])]
        incdirs = _unique(filelist.incdirs(c, roots) + list(t.incdirs))
        p = dict(t.params)
        for name, value in params.items():
            if name in p:
                p[name] = value
                used_params.add(name)
        flags = compile_flags(c, roots)
        folder_rel = Path(*c.name.split("/")) / t.name
        units.append(_Unit(c, t, folder_rel, paths, incdirs, p, flags))
        for comp in filelist.components(c, roots):
            if all(comp.repo_root != r for r in repos):
                repos.append(comp.repo_root)
        if not negative:
            continue
        folders: dict[str, str] = {}               # fault folder -> fault, per test
        for n in c.negatives:
            if n.test != t.name:
                continue
            name = fault_name(c, n)
            folder = _fault_folder(n)
            if folder.lower() in folders:
                raise RunError("%s:%s: faults %s and %s share the folder %s"
                               % (c.name, t.name, folders[folder.lower()], name, folder))
            folders[folder.lower()] = name
            patch = fault_path(c, n, roots)
            m = LOCAL_FAULT.fullmatch(n.fault)
            owner = c if m else resolve(n.fault.split(":", 1)[0], roots)
            try:
                label = patch.relative_to(owner.repo_root).as_posix()
                rels = patched_files(str(patch))
            except (OSError, ValueError) as e:
                raise RunError("fault %s: cannot read the patch: %s" % (name, e)) from None
            u = _Unit(c, t, folder_rel / folder, paths, incdirs, p, flags, neg=n, fault=name,
                      patch=patch, patch_label=label, owner_root=owner.repo_root)
            srcs = [_key((owner.repo_root / r).resolve()) for r in rels]
            if rep and srcs and all(s in rep for s in srcs):
                u.skip = "--replace: it patches only %s" % ", ".join(rels)
            units.append(u)
    unknown = sorted(k for k in replace if _key(Path(k).resolve()) not in used_files)
    if unknown:
        raise RunError("--replace %s: no selected test compiles it" % ", ".join(unknown))
    unknown = sorted(set(params) - used_params)
    if unknown:
        raise RunError("--param %s: no selected test has the parameter" % ", ".join(unknown))

    tools = find_tools(iverilog)
    run_dir = _new_run_dir(Path(out).resolve())
    for u in units:
        u.folder = run_dir / u.folder

    def work(u: _Unit):
        if u.skip:
            return None, "", None
        return _execute(u, tools, comparers)

    tests: list[Result] = []
    faults: list[Result] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(work, u) for u in units]
        for u, fut in zip(units, futures):
            ok, text, logfile = fut.result()
            rel = logfile.relative_to(run_dir).as_posix() if logfile else None
            where = "%s:%s" % (u.comp.name, u.test.name)
            first = first_error(text)
            if u.neg is None:
                status = "PASS" if ok else "FAIL"
                tests.append(Result(u.comp.name, u.test.name, None, status,
                                    None if ok else first, log=rel))
                log("%s: %s" % (where, status))
                if not ok:
                    log(text.rstrip())
                good = ok
            else:
                n = u.neg
                if u.skip:
                    status = "SKIPPED"
                    log("%s: negative %s SKIPPED (%s)" % (where, u.fault, u.skip))
                elif ok is None:
                    status = "STALE"
                    log("%s: negative %s STALE (%s)" % (where, u.fault, first))
                else:
                    anywhere = n.match == "anywhere"
                    caught = ok is False and contains(text if anywhere else first or "", n.expect)
                    status = "CAUGHT" if caught else "MISSED"
                    if caught:
                        log("%s: negative %s CAUGHT" % (where, u.fault))
                    else:
                        log("%s: negative %s MISSED (expected%s: %s; first error: %s)"
                            % (where, u.fault, " anywhere" if anywhere else "", n.expect,
                               first or "(none)"))
                        log(text.rstrip())
                faults.append(Result(u.comp.name, u.test.name, u.fault, status, first,
                                     n.expect, n.match, rel))
                good = status in ("CAUGHT", "SKIPPED")
            if good and not keep:
                _cleanup(u)

    summary = Summary(run_dir.name, run_dir, run_dir / "summary.json", _commit(run_dir),
                      tools.version, tier, bool(negative), tests, faults,
                      _repo_commits(repos, run_dir))
    _write(summary.path, json.dumps(summary.as_json(), indent=2, ensure_ascii=False) + "\n")
    caught = sum(r.status == "CAUGHT" for r in faults)
    log("%d tests, %d passed; %d faults, %d caught, %d skipped; summary: %s"
        % (len(tests), sum(r.status == "PASS" for r in tests), len(faults), caught,
           sum(r.status == "SKIPPED" for r in faults), summary.path.name))
    return summary
