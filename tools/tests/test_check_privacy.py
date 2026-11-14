# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
import io
import os
import subprocess
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_privacy as cp  # noqa: E402

# Strings that must be flagged are assembled from fragments, so that this file itself is clean.
AT = "@"
EMAIL = "someone" + AT + "example.org"
NOREPLY = "12345+someone" + AT + "users.noreply.github.com"
DRIVE_PATH = "C" + ":" + "\\" + "Users" + "\\" + "someone" + "\\" + "file.txt"
DRIVE_PATH_FWD = "D" + ":/" + "Projects/x"
UNC = "\\\\" + "host" + "\\" + "share"
HOME_PATH = "/" + "home" + "/someone/x"
WATCHED = "Some Person"
CLAUDE_TRAILER = "Co-Authored-By: Claude Opus 5.5 <noreply" + AT + "anthropic.com>"

ALLOW = cp.parse_allow(
    "# comment\n"
    "trailer ^Co-Authored-By: Claude [A-Za-z0-9. ]+ <noreply[@]anthropic[.]com>$ # agent trailer\n"
    "watch " + WATCHED + " # name to keep out of PDF tool fields\n"
    "allow ics/intel/8080a/hdr.v :: " + "author" + AT + "example.net # upstream header\n"
    "author ^Third Party <third" + AT + "example.net>$ # public upstream author\n"
)


def pdf(info: str = "", extra_objects: bytes = b"", stream: bytes | None = None) -> bytes:
    body = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    if info:
        body += b"2 0 obj\n<< " + info.encode("latin-1") + b" >>\nendobj\n"
    body += extra_objects
    if stream is not None:
        body += (b"3 0 obj\n<< /Type /Metadata /Subtype /XML /Filter /FlateDecode /Length "
                 + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n")
    return body + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"


XMP = (b"<?xpacket begin='x'?><x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF>"
       b"<dc:creator>nobody</dc:creator></rdf:RDF></x:xmpmeta><?xpacket end='w'?>")


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name: str, data) -> Path:
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        p.write_bytes(data)
        return p


class PdfScan(Base):
    def test_pdf_author_flagged(self):
        p = self.write("a.pdf", pdf("/Author (A Name)"))
        out = cp.scan_pdf(p, ALLOW)
        self.assertTrue(any("/Author" in l for l in out), out)

    def test_pdf_empty_author_passes(self):
        p = self.write("a.pdf", pdf("/Author ()"))
        self.assertEqual(cp.scan_pdf(p, ALLOW), [])

    def test_pdf_xmp_raw_flagged(self):
        p = self.write("x.pdf", pdf(extra_objects=b"4 0 obj\n" + XMP + b"\nendobj\n"))
        out = cp.scan_pdf(p, ALLOW)
        self.assertTrue(any("XMP" in l for l in out), out)

    def test_pdf_xmp_compressed_flagged(self):
        p = self.write("z.pdf", pdf(stream=zlib.compress(XMP)))
        out = cp.scan_pdf(p, ALLOW)
        self.assertTrue(any("XMP" in l for l in out), out)

    def test_pdf_compressed_author_flagged(self):
        p = self.write("z.pdf", pdf(stream=zlib.compress(b"<< /Author (Hidden Name) >>")))
        self.assertTrue(any("/Author" in l for l in cp.scan_pdf(p, ALLOW)))

    def test_pdf_producer_tool_name_passes(self):
        p = self.write("c.pdf", pdf("/Producer (qpdf)"))
        self.assertEqual(cp.scan_pdf(p, ALLOW), [])

    def test_pdf_producer_with_path_email_or_watched_name_flagged(self):
        for value in (DRIVE_PATH.replace("\\", "/"), EMAIL, WATCHED):
            p = self.write("c.pdf", pdf("/Creator (" + value + ")"))
            self.assertTrue(cp.scan_pdf(p, ALLOW), value)

    def test_plain_flate_stream_without_metadata_passes(self):
        p = self.write("c.pdf", pdf(stream=zlib.compress(b"BT /F1 12 Tf (hello) Tj ET")))
        self.assertEqual(cp.scan_pdf(p, ALLOW), [])


class Hardening(Base):
    def test_pdf_header_after_junk_flagged(self):
        data = b"J" * 100 + pdf("/Author (A Name)")
        p = self.write("noext.bin", data)
        self.assertTrue(any("/Author" in l for l in cp.scan_text(p, ALLOW)))

    def test_pdf_by_extension_flagged(self):
        p = self.write("A.PDF", b"no header\n/Author (A Name)\n")
        self.assertTrue(cp.scan_text(p, ALLOW))

    def test_binary_printable_run_flagged(self):
        p = self.write("b.bin", b"\0\1\2" + DRIVE_PATH.encode() + b"\0\3ab\0")
        self.assertTrue(any("absolute local path" in l for l in cp.scan_text(p, ALLOW)))

    def test_binary_clean_passes(self):
        p = self.write("b.bin", bytes(range(256)) * 4)
        self.assertEqual(cp.scan_text(p, ALLOW), [])

    def test_inflate_limit_reported(self):
        big = zlib.compress(b"A" * 5000)
        p = self.write("big.pdf", pdf(stream=big))
        old = cp.MAX_INFLATE
        cp.MAX_INFLATE = 1000
        try:
            out = cp.scan_pdf(p, ALLOW)
        finally:
            cp.MAX_INFLATE = old
        self.assertTrue(any("too large" in l for l in out), out)
        self.assertEqual(cp.scan_pdf(p, ALLOW), [])

    def test_inflate_total_limit_reported(self):
        s = zlib.compress(b"A" * 800)
        data = pdf(stream=s) + b"5 0 obj\nstream\n" + s + b"\nendstream\nendobj\n"
        p = self.write("tot.pdf", data)
        old = cp.MAX_INFLATE_TOTAL
        cp.MAX_INFLATE_TOTAL = 1000
        try:
            out = cp.scan_pdf(p, ALLOW)
        finally:
            cp.MAX_INFLATE_TOTAL = old
        self.assertTrue(any("too large" in l for l in out), out)


class Idents(unittest.TestCase):
    GH = "GitHub <noreply" + AT + "github.com>"

    def test_github_committer_only(self):
        self.assertTrue(cp._ident_ok(self.GH, ALLOW, "committer"))
        self.assertFalse(cp._ident_ok(self.GH, ALLOW, "author"))

    def test_two_addresses_need_both_allowed(self):
        ok = "x <" + NOREPLY + ">"
        self.assertTrue(cp._ident_ok(ok, ALLOW, "author"))
        self.assertFalse(cp._ident_ok(ok + " <" + EMAIL + ">", ALLOW, "author"))
        self.assertFalse(cp._ident_ok("x <" + EMAIL + "> <" + NOREPLY + ">", ALLOW, "author"))

    def test_no_address_is_a_problem(self):
        self.assertFalse(cp._ident_ok("Just A Name", ALLOW, "author"))
        self.assertFalse(cp._ident_ok("Just A Name <>", ALLOW, "committer"))


class TextScan(Base):
    def test_text_drive_path_flagged(self):
        for s in (DRIVE_PATH, DRIVE_PATH_FWD, UNC, HOME_PATH, "/" + "Users" + "/someone", "/mnt/" + "c/x"):
            p = self.write("t.txt", "see " + s + " here\n")
            self.assertTrue(cp.scan_text(p, ALLOW), s)

    def test_placeholders_and_urls_pass(self):
        bs = chr(92)
        text = ("C" + ":" + bs + "Users" + bs + "<name>" + bs + "x\n" + "/" + "home" + "/<name>/x\n"
                "https://example.org/a\n" + "/" + "Users" + "/<name>\n")
        p = self.write("t.txt", text)
        self.assertEqual(cp.scan_text(p, ALLOW), [])

    def test_text_email_flagged(self):
        p = self.write("t.txt", "mail " + EMAIL + "\n")
        out = cp.scan_text(p, ALLOW)
        self.assertEqual(len(out), 1)

    def test_noreply_allowed(self):
        p = self.write("t.txt", "mail " + NOREPLY + "\n")
        self.assertEqual(cp.scan_text(p, ALLOW), [])

    def test_allow_list_line(self):
        text = "// author " + "author" + AT + "example.net\n"
        inside = self.write("ics/intel/8080a/hdr.v", text)
        outside = self.write("ics/other/hdr.v", text)
        self.assertEqual(cp.scan_text(inside, ALLOW), [])
        self.assertEqual(len(cp.scan_text(outside, ALLOW)), 1)

    def test_path_entry_skips_whole_file(self):
        allow = cp.parse_allow("path tools/tests/fixtures/* # fixtures\n")
        p = self.write("tools/tests/fixtures/f.txt", "mail " + EMAIL + "\n")
        self.assertEqual(cp.scan_text(p, allow), [])

    def test_bad_allow_line(self):
        with self.assertRaises(ValueError):
            cp.parse_allow("bogus x # y\n")
        with self.assertRaises(ValueError):
            cp.parse_allow("trailer x\n")  # no reason


def git(repo: Path, *args: str, env_extra=None) -> str:
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": NOREPLY,
                "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": NOREPLY})
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True,
                       text=True, check=True)
    return r.stdout.strip()


class History(Base):
    def repo(self) -> Path:
        r = self.tmp / "repo"
        r.mkdir()
        git(r, "init", "-q", "-b", "main")
        return r

    def commit(self, r, msg, name="f.txt", content="x\n", env_extra=None):
        (r / name).write_text(content, encoding="utf-8", newline="\n")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", msg, env_extra=env_extra)

    def test_history_clean(self):
        r = self.repo()
        self.commit(r, "one\n\n" + CLAUDE_TRAILER)
        self.assertEqual(cp.scan_history(r, True, None, ALLOW), [])

    def test_history_message_flagged(self):
        r = self.repo()
        self.commit(r, "one")
        self.commit(r, "two " + EMAIL, content="y\n")
        out = cp.scan_history(r, True, None, ALLOW)
        self.assertEqual(len(out), 1)
        out = cp.scan_history(r, False, "HEAD~1", ALLOW)
        self.assertEqual(len(out), 1)
        out = cp.scan_history(r, False, "HEAD", ALLOW)
        self.assertEqual(out, [])

    def test_history_author_flagged(self):
        r = self.repo()
        self.commit(r, "one", env_extra={"GIT_AUTHOR_EMAIL": EMAIL})
        out = cp.scan_history(r, True, None, ALLOW)
        self.assertTrue(any("author" in l for l in out), out)

    def test_history_committer_flagged_and_author_allow(self):
        r = self.repo()
        self.commit(r, "one", env_extra={"GIT_AUTHOR_NAME": "Third Party",
                                         "GIT_AUTHOR_EMAIL": "third" + AT + "example.net"})
        self.assertEqual(cp.scan_history(r, True, None, ALLOW), [])
        self.commit(r, "two", content="z\n", env_extra={"GIT_COMMITTER_EMAIL": EMAIL})
        out = cp.scan_history(r, True, None, ALLOW)
        self.assertTrue(any("committer" in l for l in out), out)

    def test_history_blob_flagged_even_if_deleted_later(self):
        r = self.repo()
        self.commit(r, "one", name="leak.txt", content="mail " + EMAIL + "\n")
        git(r, "rm", "-q", "leak.txt")
        git(r, "commit", "-q", "-m", "remove")
        out = cp.scan_history(r, True, None, ALLOW)
        self.assertTrue(any("leak.txt" in l for l in out), out)

    def test_all_covers_two_roots(self):
        r = self.repo()
        self.commit(r, "root one")
        git(r, "checkout", "-q", "--orphan", "other")
        git(r, "rm", "-rfq", ".")
        self.commit(r, "root two " + EMAIL, name="g.txt")
        git(r, "checkout", "-q", "main")
        git(r, "merge", "-q", "--allow-unrelated-histories", "-m", "join", "other")
        out = cp.scan_history(r, True, None, ALLOW)
        self.assertEqual(len([l for l in out if "message" in l]), 1, out)

    def test_github_committer_in_history_passes_author_fails(self):
        r = self.repo()
        self.commit(r, "one", env_extra={"GIT_COMMITTER_NAME": "GitHub",
                                         "GIT_COMMITTER_EMAIL": "noreply" + AT + "github.com"})
        self.assertEqual(cp.scan_history(r, True, None, ALLOW), [])
        self.commit(r, "two", content="y\n", env_extra={"GIT_AUTHOR_NAME": "GitHub",
                                                        "GIT_AUTHOR_EMAIL": "noreply" + AT + "github.com"})
        out = cp.scan_history(r, True, None, ALLOW)
        self.assertTrue(any("author" in l for l in out), out)

    def test_gitlink_in_history_is_skipped(self):
        r = self.repo()
        self.commit(r, "one")
        git(r, "update-index", "--add", "--cacheinfo", "160000," + "a" * 40 + ",sub")
        git(r, "commit", "-q", "-m", "add submodule")
        self.assertEqual(cp.scan_history(r, True, None, ALLOW), [])

    def test_no_commits_is_clean(self):
        r = self.repo()
        self.assertEqual(cp.scan_history(r, True, None, ALLOW), [])

    def test_empty_history_base_is_an_error(self):
        r = self.repo()
        self.commit(r, "one")
        for base in ("", "  "):
            with self.assertRaises(ValueError):
                cp.scan_history(r, False, base, ALLOW)

    def test_main_rejects_empty_history_base(self):
        r = self.repo()
        self.commit(r, "one")
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            cp.main(["--repo", str(r), "--history", ""])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("--history", err.getvalue())


if __name__ == "__main__":
    unittest.main()
