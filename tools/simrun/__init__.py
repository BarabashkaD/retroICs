# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""simrun: the test runner of the retro repos (component.toml manifests, file lists, trace).

Run from a repo root with tools/ on the module path:
    $env:PYTHONPATH = 'tools'; python -B -m simrun filelist intel/8255a --format f
Modules: manifest (load, resolve, fault_path), filelist (files, render), trace (matrix).
"""
