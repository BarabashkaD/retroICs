# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Command line of simrun (tools/ on the module path, e.g. $env:PYTHONPATH = 'tools').

  python -B -m simrun filelist <component> --format f|qsf|prj [--relative-to DIR] [--search DIR ...]
  python -B -m simrun trace [<component> ...] [--external NAME=DIR ...] [--search DIR ...] [--registry FILE]
  python -B -m simrun run <path> ... [--tier T] [--jobs N] [--negative] [--replace FILE=FILES ...]
      [--param NAME=V ...] [--keep] [--out DIR] [--iverilog PATH] [--search DIR ...]

<component>: a name ("intel/8255a", "machines/<name>"), or a folder holding a component.toml, or
the file itself. --search: the repo roots to find components and dependencies in (repeatable;
default: the current folder, then this retroICs checkout). trace without components takes every
component of the search roots. Exit code 0, 1 on trace problems, 2 on a manifest error.

run: <path> is a component (as above) or a folder searched for component.toml files (build/ and
.git/ left out). --tier: the tests of that tier and lower (quick < standard < full; default full);
--negative: also their faults; --replace FILE=FILES: compile FILES (comma-separated) in place of
FILE; --param NAME=V: the parameter NAME of every test that declares it; --keep: keep the .vvp and the patched copies of passing runs; --out:
default build/simrun; --iverilog: default IVERILOG, else iverilog on PATH (version 13.0). With no
test at the tier it prints "no components ..." and exits 0. Exit code 0 when every test passes and
every fault is caught (or skipped), 1 otherwise, 2 on a manifest, option or tool error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import check_records as cr

from . import filelist, manifest, trace
from . import run as runner


def default_search() -> list[Path]:
    out: list[Path] = []
    for p in (Path.cwd(), trace.REPO):
        if p.resolve() not in out:
            out.append(p.resolve())
    return out


def component_arg(arg: str, search: list[Path]) -> manifest.Component:
    p = Path(arg)
    if p.is_file() and p.name == manifest.MANIFEST:
        return manifest.load(p)
    if (p / manifest.MANIFEST).is_file():
        return manifest.load(p / manifest.MANIFEST)
    return manifest.resolve(arg, search)


def discover(search: list[Path]) -> list[manifest.Component]:
    """Every component of the search roots: <root>/ics/<vendor>/<part>, <root>/<group>/<name>."""
    found: list[Path] = []
    for root in search:
        root = Path(root)
        paths = sorted(root.glob("ics/*/*/" + manifest.MANIFEST))
        paths += sorted(p for p in root.glob("*/*/" + manifest.MANIFEST)
                        if p.relative_to(root).parts[0] != "ics")
        for p in paths:
            if p.resolve() not in found:
                found.append(p.resolve())
    return [manifest.load(p) for p in found]


SKIP_DIRS = {"build", ".git"}


def components_at(args: list[str], search: list[Path]) -> list[manifest.Component]:
    """run's <path> arguments: a component.toml, a folder holding one, a folder searched for them,
    or a component name; each component once, in argument order (found files sorted)."""
    out: list[manifest.Component] = []
    seen: set[Path] = set()
    for arg in args:
        p = Path(arg)
        if (p.is_file() and p.name == manifest.MANIFEST) or (p / manifest.MANIFEST).is_file():
            comps = [component_arg(arg, search)]
        elif p.is_dir():
            comps = [manifest.load(f) for f in sorted(p.rglob(manifest.MANIFEST))
                     if not SKIP_DIRS & set(f.relative_to(p).parts)]
        else:
            comps = [manifest.resolve(arg, search)]
        for c in comps:
            if c.root not in seen:
                seen.add(c.root)
                out.append(c)
    return out


def run_command(a, search: list[Path]) -> int:
    replace = runner.parse_replace(a.replace)
    params = runner.parse_param(a.param)
    comps = components_at(a.paths, search)
    if not runner.select(comps, a.tier):
        print("no components with tests at tier %s in %s (%d component%s found)"
              % (a.tier, ", ".join(a.paths), len(comps), "" if len(comps) == 1 else "s"))
        return 0
    s = runner.run(comps, a.tier, a.jobs, a.negative, a.out, replace, params, search=search,
                   iverilog=a.iverilog, keep=a.keep)
    return s.exit_code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="simrun", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    fl = sub.add_parser("filelist", help="the RTL file list of a component, dependencies first")
    fl.add_argument("component")
    fl.add_argument("--format", required=True, choices=filelist.FORMATS)
    fl.add_argument("--relative-to", type=Path, help="write paths relative to this folder")
    fl.add_argument("--search", type=Path, action="append", help="a repo root (repeatable)")
    tr = sub.add_parser("trace", help="record ID -> tests -> killing faults -> status")
    tr.add_argument("components", nargs="*")
    tr.add_argument("--external", action="append", type=cr._external_arg, default=[],
                    metavar="NAME=DIR", help="a checkout of the repo NAME, to check its IDs")
    tr.add_argument("--search", type=Path, action="append", help="a repo root (repeatable)")
    tr.add_argument("--registry", type=Path, help="the record ID registry (default: this repo's)")
    rn = sub.add_parser("run", help="compile and run the tests (and faults) of components")
    rn.add_argument("paths", nargs="+")
    rn.add_argument("--tier", choices=manifest.TIERS, default="full")
    rn.add_argument("--jobs", type=int, default=1)
    rn.add_argument("--negative", action="store_true", help="also run the faults")
    rn.add_argument("--replace", action="append", default=[], metavar="FILE=FILES")
    rn.add_argument("--param", action="append", default=[], metavar="NAME=V")
    rn.add_argument("--keep", action="store_true")
    rn.add_argument("--out", type=Path, default=Path("build") / "simrun")
    rn.add_argument("--iverilog", help="the iverilog program (default: IVERILOG, else PATH)")
    rn.add_argument("--search", type=Path, action="append", help="a repo root (repeatable)")
    a = ap.parse_args(argv)
    search = [p.resolve() for p in a.search] if a.search else default_search()
    if a.command == "run":
        try:
            return run_command(a, search)
        except (manifest.ManifestError, runner.RunError, runner.ToolError) as e:
            print("ERROR: %s" % e)
            return 2
        except Exception as e:  # anything else: one line, no traceback, exit 2
            print("ERROR: %s: %s" % (type(e).__name__, " ".join(str(e).split())))
            return 2
    try:
        if a.command == "filelist":
            c = component_arg(a.component, search)
            for line in filelist.render(c, search + [c.repo_root], a.format, a.relative_to):
                print(line)
            return 0
        comps = ([component_arg(n, search) for n in a.components] if a.components
                 else discover(search))
        rows = trace.matrix(comps, dict(a.external), registry=a.registry)
    except manifest.ManifestError as e:
        print("ERROR: %s" % e)
        return 2
    except trace.TraceError as e:
        for p in e.problems:
            print("ERROR: %s" % p)
        return 1
    for line in trace.table(rows) + rows.notes:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
