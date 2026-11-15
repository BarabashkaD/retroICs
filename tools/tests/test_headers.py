# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
"""Licence headers of the source files (.v, .vh, .py, .toml) of the working tree.

Each file has in its header (the leading comment block) an SPDX-License-Identifier line whose text
is LICENSES/<id>.txt and at least one SPDX-FileCopyrightText line; a BSD-3-Clause file carries the
owner's copyright line. Every licence pointer of a header (a file name with LICENSE in it) names a
file under LICENSES/; the one exception is the LICENSE.TXT of Dmitry Tselikov's notice, kept as it
is in the LicenseRef-Tselikov-BSD files, whose header names its text under LICENSES/.

EXEMPT: copies kept byte for byte as their sources have them, with no header; their licences are
recorded elsewhere (NOTICE, LICENSES/, tools/tests/fixtures/README.md). The upstream 8080 model
must also keep its bytes as taken (UPSTREAM_8080_SHA256).
"""
import hashlib
import re
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "tests"))
import check_comment_only as cco  # noqa: E402
import check_privacy as cp  # noqa: E402

ROOT = TOOLS.parent
SUFFIXES = (".v", ".vh", ".py", ".toml")
OWNER = ("SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), "
         "https://github.com/BarabashkaD")
UPSTREAM_8080 = "ics/intel/8080a/rtl/upstream/k580vm80a.v"
EXEMPT = {
    UPSTREAM_8080: "the die-derived 8080 model, CC BY 3.0 (LICENSES/CC-BY-3.0.txt, NOTICE)",
    "tools/tests/fixtures/component-example.toml": "the layout design's example, a test input "
                                                   "(tools/tests/fixtures/README.md)",
}
# the SHA-256 of the upstream 8080 model as taken (line endings CRLF to LF, otherwise unchanged:
# NOTICE); the file must keep these bytes
UPSTREAM_8080_SHA256 = "75919c8cf5fddace79725e11e26aab710ca5eaf3f2575ebd8282d81f15a38bac"
SPDX_ID = re.compile(r"SPDX-License-Identifier: (\S+)\s*$")
POINTER = re.compile(r"[\w./-]*LICENSE[\w./-]*")
TSELIKOV = "LicenseRef-Tselikov-BSD"


# Tselikov's notice in the 8257 and 8275 models, kept as it is
TSELIKOV_NOTICE = [
    "// ====================================================================",
    "//                Radio-86RK FPGA REPLICA",
    "//",
    "//            Copyright (C) 2011 Dmitry Tselikov",
    "//",
    "// This core is distributed under modified BSD license.",
    "// For complete licensing information see LICENSE.TXT.",
    "// --------------------------------------------------------------------",
]


def header(text, prefix):
    lines = text.split("\n")
    return lines[:cco.leading_block(lines, prefix)]


def header_problems(rel, data, root):
    """Why the file rel (bytes data) of the repo at root has no valid licence header; []."""
    prefix = cco.comment_prefix(rel)
    head = header(data.decode("utf-8"), prefix)
    ids = [m.group(1) for m in (SPDX_ID.search(l) for l in head) if m]
    out = []
    if len(ids) != 1:
        return ["%d SPDX-License-Identifier lines in the header" % len(ids)]
    lic = ids[0]
    if not (Path(root) / "LICENSES" / (lic + ".txt")).is_file():
        out.append("no LICENSES/%s.txt" % lic)
    if not any("SPDX-FileCopyrightText: " in l for l in head):
        out.append("no SPDX-FileCopyrightText line")
    if lic == "BSD-3-Clause" and not any(l.endswith(OWNER) for l in head):
        out.append("BSD-3-Clause without the owner's copyright line")
    tselikov_text = "LICENSES/%s.txt" % TSELIKOV
    for n, line in enumerate(head, 1):
        for token in POINTER.findall(line):
            token = token.rstrip(".,;:")
            if token.startswith("LICENSES/"):
                if not (Path(root) / token).is_file():
                    out.append("line %d: %s is not a file" % (n, token))
            elif not (token == "LICENSE.TXT" and lic == TSELIKOV
                      and any(tselikov_text in l for l in head)):
                out.append("line %d: the licence pointer %s names no file under LICENSES/"
                           % (n, token))
    return out


def source_files(root):
    """(repo-relative name, bytes) of every tracked or untracked-not-ignored source file."""
    root = Path(root)
    out = []
    for f in cp.working_tree_files(root):
        rel = f.relative_to(root).as_posix()
        if f.is_file() and rel.endswith(SUFFIXES):
            out.append((rel, f.read_bytes()))
    return sorted(out)


class Headers(unittest.TestCase):
    def test_every_source_file_has_a_licence_header(self):
        files = source_files(ROOT)
        self.assertGreater(len(files), 40)
        bad = {rel: header_problems(rel, data, ROOT) for rel, data in files if rel not in EXEMPT}
        self.assertEqual({k: v for k, v in bad.items() if v}, {})

    def test_exempt_files_have_no_header_and_exist(self):
        names = dict(source_files(ROOT))
        for rel in EXEMPT:
            self.assertIn(rel, names)
            self.assertNotIn(b"SPDX-License-Identifier", names[rel], rel)
        readme = (ROOT / "tools" / "tests" / "fixtures" / "README.md").read_text(encoding="utf-8")
        for rel in EXEMPT:
            if rel.startswith("tools/tests/fixtures/"):
                self.assertIn("`%s`" % Path(rel).name, readme)

    def test_upstream_8080_byte_identical(self):
        have = (ROOT / UPSTREAM_8080).read_bytes()
        self.assertEqual(hashlib.sha256(have).hexdigest(), UPSTREAM_8080_SHA256)
        self.assertNotIn(b"\r", have)
        self.assertIn(b"Licensed under CC-BY 3.0", have)
        self.assertTrue((ROOT / "LICENSES" / "CC-BY-3.0.txt").is_file())

    def test_tselikov_notice_kept(self):
        for rel in ("ics/intel/8257/rtl/intel_8257.v", "ics/intel/8275/rtl/intel_8275.v"):
            head = header((ROOT / rel).read_text(encoding="utf-8"), "//")
            self.assertIn("// SPDX-License-Identifier: " + TSELIKOV, head, rel)
            self.assertIn("// SPDX-FileCopyrightText: 2011 Dmitry Tselikov", head, rel)
            self.assertIn("// " + OWNER, head, rel)
            i = head.index(TSELIKOV_NOTICE[0])
            self.assertEqual(head[i:i + len(TSELIKOV_NOTICE)], TSELIKOV_NOTICE, rel)

    def test_header_problems(self):
        ok = ("// SPDX-License-Identifier: BSD-3-Clause\n// %s\nmodule m;\n" % OWNER).encode()
        self.assertEqual(header_problems("a.v", ok, ROOT), [])
        cases = {
            b"module m;\n": "0 SPDX",
            ok.replace(b"BSD-3-Clause", b"MIT"): "no LICENSES/MIT.txt",
            ok.replace(b"Dmitry", b"Someone"): "without the owner's",
            ok.replace(b"module m;", b"// see ../../LICENSE.TXT\nmodule m;"): "names no file",
            ok.replace(b"module m;", b"// see LICENSES/X.txt\nmodule m;"): "is not a file",
            # a pointer below the header is code, not a header pointer; an SPDX line there is
            # not in the header
            b"module m;\n// SPDX-License-Identifier: BSD-3-Clause\n": "0 SPDX",
        }
        for data, want in cases.items():
            self.assertIn(want, " ".join(header_problems("a.v", data, ROOT)), data)
        tselikov = ("# SPDX-License-Identifier: %s\n# SPDX-FileCopyrightText: 2011 x\n"
                    "# see LICENSE.TXT\nx = 1\n" % TSELIKOV)
        self.assertIn("names no file", " ".join(header_problems("a.py", tselikov.encode(), ROOT)))
        mapped = tselikov.replace("x = 1", "# LICENSE.TXT: LICENSES/%s.txt\nx = 1" % TSELIKOV)
        self.assertEqual(header_problems("a.py", mapped.encode(), ROOT), [])


if __name__ == "__main__":
    unittest.main()
