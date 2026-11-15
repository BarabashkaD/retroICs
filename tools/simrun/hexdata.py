# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Binary data files of a test as hex for $readmemh: one byte per line, two lower-case digits.

write_hex: size check, FFh padding up to a size, a larger image as it is; write_hexfiles:
<prefix><name>.hex in the output folder, returns {name: file name}.
"""
from __future__ import annotations

from pathlib import Path

from .manifest import DataFile


class HexError(ValueError):
    pass


def write_hex(src, dst, sizes=(), pad_to=0) -> int:
    """Writes src as hex to dst; sizes: the allowed sizes in bytes (empty: any); pad_to: pads with
    FFh up to this size. Returns the number of bytes written."""
    src = Path(src)
    data = src.read_bytes()
    if sizes and len(data) not in sizes:
        raise HexError("%s is %d bytes, expected %s"
                       % (src.name, len(data), " or ".join(map(str, sizes))))
    data += b"\xff" * (max(pad_to, len(data)) - len(data))
    with open(dst, "w", encoding="ascii", newline="\n") as f:
        f.write("".join("%02x\n" % b for b in data))
    return len(data)


def write_hexfiles(data: dict[str, DataFile], out_dir, prefix="") -> dict[str, str]:
    """Writes each data file as <out_dir>/<prefix><name>.hex. Returns {name: file name} (bare
    names, relative to out_dir), for +<name>=<file> on the vvp line."""
    made = {}
    for name, d in data.items():
        fname = "%s%s.hex" % (prefix, name)
        try:
            write_hex(d.path, Path(out_dir) / fname, d.sizes, d.pad_to)
        except HexError as e:
            raise HexError("data %s: %s" % (name, e)) from None
        made[name] = fname
    return made
