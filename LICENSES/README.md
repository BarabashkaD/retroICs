# Licence texts

| File | Licence | Source of the text |
|---|---|---|
| `BSD-3-Clause.txt` | BSD-3-Clause: the owner's files other than Markdown | texts from spdx/license-list-data, `text/BSD-3-Clause.txt` |
| `CC-BY-4.0.txt` | CC BY 4.0: the owner's Markdown files | texts from spdx/license-list-data, `text/CC-BY-4.0.txt` |
| `CC-BY-3.0.txt` | CC BY 3.0 Unported: the die-derived 8080 model | texts from spdx/license-list-data, `text/CC-BY-3.0.txt` |
| `LicenseRef-Tselikov-BSD.txt` | Dmitry Tselikov's BSD-style licence: the 8257 and 8275 models | `LICENSE.TXT` of MiSTer-devel/Apogee_MiSTer at `4b37da2` (the base of both models), CR LF changed to LF |

- The three SPDX texts are kept byte for byte as downloaded on 2026-11-14 from the `main` branch of
  https://github.com/spdx/license-list-data. `tools/tests/test_docs.py` pins the SHA-256 of every
  file here.
- `LicenseRef-Tselikov-BSD.txt`: its text equals the SPDX `BSD-2-Clause` text under the SPDX
  matching guidelines (two conditions and the standard disclaimer; the bullets and "All rights
  reserved." are allowed variations). The identifier stays `LicenseRef-Tselikov-BSD`, the name of
  the `LICENSE.TXT` that Tselikov's notice in the model headers points to.
- The owner's copyright line is in `../LICENSE`; the attribution line is in `../NOTICE`.
