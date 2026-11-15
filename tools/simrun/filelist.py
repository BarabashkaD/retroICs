# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""The RTL file list of a component: its dependencies first (in rtl.depends order, each once),
then its own rtl.files; written for Icarus (f), Quartus (qsf) or ISE (prj)."""
from __future__ import annotations

import os
from pathlib import Path

from .manifest import Component, ManifestError, resolve

FORMATS = ("f", "qsf", "prj")


def components(c: Component, search) -> list[Component]:
    """c and every component it depends on, dependencies first, each once."""
    out: list[Component] = []
    done: set[str] = set()

    def visit(comp: Component, chain: list[str]) -> None:
        for dep in comp.depends:
            if dep in chain:
                raise ManifestError("dependency cycle: %s" % " -> ".join(chain + [dep]))
            if dep not in done:
                visit(resolve(dep, search), chain + [dep])
        if comp.name not in done:
            done.add(comp.name)
            out.append(comp)

    visit(c, [c.name])
    return out


def _unique(paths) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p not in out:
            out.append(p)
    return out


def files(c: Component, search) -> list[Path]:
    """The RTL files of c and its dependencies, dependencies first, each file once."""
    return _unique(f for comp in components(c, search) for f in comp.rtl_files)


def incdirs(c: Component, search) -> list[Path]:
    """The include folders of c and its dependencies, in the same order, each once."""
    return _unique(d for comp in components(c, search) for d in comp.incdirs)


def _show(p: Path, relative_to) -> str:
    if relative_to is None:
        return p.as_posix()
    try:
        return os.path.relpath(p, Path(relative_to).resolve()).replace(os.sep, "/")
    except ValueError as e:  # Windows: another drive
        raise ManifestError("%s cannot be written relative to %s: %s"
                            % (p.as_posix(), Path(relative_to).as_posix(), e))


def _quote(s: str) -> str:
    return '"%s"' % s if " " in s else s


def render(c: Component, search, fmt: str, relative_to=None) -> list[str]:
    """The lines of the file list in one format; paths relative to relative_to when given
    (POSIX separators), else absolute."""
    if fmt not in FORMATS:
        raise ValueError("format %r (want one of %s)" % (fmt, ", ".join(FORMATS)))
    fs = [_show(p, relative_to) for p in files(c, search)]
    ds = [_show(p, relative_to) for p in incdirs(c, search)]
    if fmt == "f":
        return ["+incdir+" + d for d in ds] + fs
    if fmt == "qsf":
        out = ["set_global_assignment -name SEARCH_PATH " + _quote(d) for d in ds]
        for f in fs:
            kind = "SYSTEMVERILOG_FILE" if f.endswith(".sv") else "VERILOG_FILE"
            out.append("set_global_assignment -name %s %s" % (kind, _quote(f)))
        return out
    # prj (ISE): files only; a .prj has no include folders
    return ['verilog work "%s"' % f for f in fs]


def prj_files(prj) -> list[Path]:
    """The RTL files of a .prj (lines 'verilog work "<path>"', paths relative to its folder), as
    absolute paths, for a .prj written by render(fmt="prj") or kept
    by a consumer."""
    prj = Path(prj).resolve()
    files: list[Path] = []
    for line in prj.read_text(encoding="utf-8").splitlines():
        parts = line.split('"')
        if line.startswith("verilog") and len(parts) >= 3:
            files.append(Path(os.path.normpath(prj.parent / parts[1])))
    return files
