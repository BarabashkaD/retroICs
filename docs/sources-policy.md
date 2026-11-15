# Sources policy

All retro sources are public: data sheets go with their ICs (`ics/<vendor>/<part>/datasheets/`),
everything else (schematics, magazine scans, manuals, ROM listings) goes to the repo that documents
the system it belongs to.
Stored data sheets are third-party copyrighted documents, not licensed by this repo: they are kept
as archival copies, each with its status in its index, and are removed on request (open an issue).
Tags are immutable and history is hard to rewrite, so every file passes the checklist below before
its first push. The licence check is a checklist step, not a gate: its result is written down.

## Source IDs

- Each source has one bracket ID (`[C78]`), registered once in `docs/sources.md` with its home index
  and its kind: `vendor`, `board`, `listing` or `comparison-only`.
- `comparison-only` sources (emulators, other cores) are cited by repo and commit and never stored as
  files here. They are never a source of behaviour.
- A record cites the ID, the page and the figure or table: `[C78] 12-109`, `[D79] Fig. 26 p. 1-183`.

## Index fields

Each source has an entry in its home index (`datasheets/index.md` of the IC, or the index of the
repo that holds it) with these fields:

| Field | Content |
|---|---|
| ID | the bracket ID of `docs/sources.md` |
| Title | the title as printed |
| Vendor | the maker or publisher |
| Document | the document or order number, when printed |
| Edition | the date or revision, as printed |
| Pages used | the pages the records cite (printed numbers, and PDF pages when they differ) |
| Origin | where the document first came from (publisher, archive) |
| Copied from | the repo or site the file was taken from, with its commit or date |
| Download | a direct download link, when one exists |
| Licence | the licence status found and where it was checked; "no statement found" is a result |
| SHA-256 | of the committed file first; then of the file as copied, before the rewrite changed it |
| File | the file name; empty when the document is listed without the file (the reason in Licence) |

An index starts with a summary table `ID | Home | File | SHA-256`: one row per source the records
cite. A row whose home is this index repeats its `File` and the first hash of its `SHA-256`; a row
whose home is another index has `see home` in both. `tools/tests/test_datasheets.py` checks the
fields, the hashes and that every stored PDF is indexed and rewritten.

## Checklist before the first push

1. Provenance: origin, copied from, download link written in the index.
2. Licence: status checked and written in the index. A document with an explicit ban on
   redistribution is the rare exception: it is listed by title, edition, pages and hash, without the
   file (`File` empty). So is a document whose status is unclear (for example an encrypted PDF that
   forbids changes, which the rewrite would need), and a file above 50 MB (GitHub warns at 50 MB
   and refuses 100 MB): listed with its hash and download link.
3. Metadata: stripped by the PDF rewrite below. Images: no EXIF or embedded paths.
4. SHA-256 recorded (`Get-FileHash -Algorithm SHA256 <file>` in PowerShell).
5. `python -B tools/check_privacy.py` passes on the working tree, then `--all` before the push.

## The PDF rewrite

The maintainer runs it with `qpdf` (a maintainer tool; committed code never calls it):

1. Clear the document information dictionary (`/Info`: Author, Creator, Producer, Title, Subject,
   Keywords and the dates) and remove the XMP `/Metadata` stream of the catalog (and of any page or
   object that carries one).
2. Rewrite the whole file with `qpdf` and object streams disabled. A full rewrite keeps only the
   objects reachable from the new trailer, so the old revisions of incremental updates, and the
   metadata in them, are gone. Without object streams every object stays visible to the checker.

   With qpdf 12.4 this takes two runs, because `--remove-info` keeps `/ModDate`:

   ```text
   qpdf --remove-info --remove-metadata --object-streams=disable in.pdf stage1.pdf
   qpdf --json=2 --json-key=qpdf --json-object=trailer stage1.pdf      (gives "/Info": "N 0 R")
   qpdf --update-from-json=update.json --object-streams=disable --compress-streams=y --deterministic-id stage1.pdf out.pdf
   ```

   `update.json` replaces the Info dictionary by an empty one:
   `{"qpdf": [{"jsonversion": 2, "pushedinheritedpageresources": false, "calledgetallpages": false,
   "maxobjectid": M}, {"obj:N 0 R": {"value": {}}}]}` (M from the first entry of the second
   command's output). `--deterministic-id` makes the result the same on every run. An encrypted file
   is not rewritten (the rewrite would remove its protection); it is listed without the file.
3. Run `python -B tools/check_privacy.py`. It reports an XMP packet, a non-empty `/Author`, and a
   path, email or watched name in `/Creator` or `/Producer`. It checks a PDF's metadata, not its
   body text: a path or a name in the page content, an annotation or a form field passes it.
4. Check the body by hand: make a decoded copy (`qpdf --qdf --object-streams=disable out.pdf
   check.pdf`, outside the repository), search it for local paths (drive letters, `\\` shares,
   `/home/`, `/Users/`), user and host names and e-mail addresses, and read every hit (image data
   gives random matches). Delete the copy; only `out.pdf` is committed.
5. Record the SHA-256 of the rewritten file in the index.

## Other rules

- Text extracts and page renders made from a source are derived files: same home, same ID, noted in
  the index as derived, with the tool and the date; they pass the same checks.
- A source file is never edited after its first push. A better copy is a new file with its own index
  entry, or a new edition with its own ID.
- Agents read the markdown records, not the PDFs, unless they check a statement against its source.
