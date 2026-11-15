# Intel 8275: data sheets

The sources that `../record.md` cites, and the entries of the documents whose home is this index
(`docs/sources.md`). Fields and the checks before a file is stored: `docs/sources-policy.md`.
Fields not printed in the document or the record are "not recorded". Licence checks and hashes:
2026-11-15.

| ID | Home | File | SHA-256 |
|---|---|---|---|
| [D79] | this index | `1979_8275.pdf` | ae43eeffbd6efe5cc40d5f58857b47c183c77257e36453fa6f5a37e34927217f |
| [D84] | this index | `1984_8275.pdf` | 907d8309355f68182102af0135d73e40559c36f8e868ac56adad248de4b81a58 |
| [D8275K] | this index | | aec733a972739cd70361560ba26249ec139f919f71f50167cdfde30a72826736 |
| [AP-62] | this index | `1984_AP-62.pdf` | 7238ff45a1035faef8ba4e365c4d42c541dc52087e97c208669c20f19e3897b0 |
| [DG81] | this index | `1981_8275_design.pdf` | 9796f0c44771a05794798f287a34ddfdf13015ee78eda24a01ba9bf82a722832 |
| [R86] | retroComputersDocs/computers/rk86/index.md | see home | see home |
| [K14] | retroComputersDocs/computers/rk86/index.md | see home | see home |
| [MON] | retroComputersDocs/computers/rk86/index.md | see home | see home |
| [APG] | retroComputersDocs/computers/rk86/index.md | see home | see home |
| [MAME] | retroComputersDocs/computers/rk86/index.md | see home | see home |
| [EMU] | retroComputersDocs/computers/rk86/index.md | see home | see home |

## [D79]

| Field | Value |
|---|---|
| Title | 8275 Programmable CRT Controller (`1979_8275.pdf`) |
| Vendor | Intel |
| Document | 00224A, "preliminary" |
| Edition | 1979 ("© Intel Corporation, 1979", p. 1-162) |
| Pages used | printed pp. 1-162..1-185 = PDF pp. 1-24 (PDF p. = printed page - 161); the 1-185 text layer is garbled |
| Origin | bitsavers, `components/intel/8275/1979_8275.pdf` (a scan with a text layer) |
| Copied from | bitsavers (2026-11-09); as copied: byte-identical to the file on bitsavers.org (checked 2026-11-15); stored: metadata rewritten (both hashes below) |
| Download | http://www.bitsavers.org/components/intel/8275/1979_8275.pdf |
| Licence | Intel copyright: "© INTEL CORPORATION, 1979" (p. 1-162) and "INTEL CORPORATION ASSUMES NO RESPONSIBILITY FOR THE USE OF ANY CIRCUITRY OTHER THAN CIRCUITRY EMBODIED IN AN INTEL PRODUCT. NO OTHER CIRCUIT PATENT LICENSES ARE IMPLIED." No ban on redistribution found in the text layer: stored |
| SHA-256 | ae43eeffbd6efe5cc40d5f58857b47c183c77257e36453fa6f5a37e34927217f (this file); 746de8ae40e39319e2c5e86b3fa1382e1f8a05e0840340c84e7d03276acf6707 (as copied, before the rewrite) |
| File | `1979_8275.pdf` |

## [D84]

| Field | Value |
|---|---|
| Title | 8275 Programmable CRT Controller (`1984_8275.pdf`) |
| Vendor | Intel |
| Document | AFN-00224B (two waveform pages AFN-00224C) |
| Edition | "April 1982" on p. 1; the 1984 data sheet |
| Pages used | printed pp. 8-50..8-73 = PDF pp. 1-24 (PDF p. = printed - 49) |
| Origin | bitsavers, `components/intel/8275/1984_8275.pdf` (a scan with a text layer) |
| Copied from | bitsavers (2026-11-09); as copied: byte-identical to the file on bitsavers.org (checked 2026-11-15); stored: metadata rewritten (both hashes below) |
| Download | http://www.bitsavers.org/components/intel/8275/1984_8275.pdf |
| Licence | Intel copyright, p. 8-50: "© INTEL CORPORATION, 1982" and "Intel Corporation Assumes No Responsibility for the Use of Any Circuitry Other Than Circuitry Embodied in an Intel Product. No Other Circuit Patent Licenses are Implied." No ban on redistribution found in the text layer: stored |
| SHA-256 | 907d8309355f68182102af0135d73e40559c36f8e868ac56adad248de4b81a58 (this file); 162cfe2962161dd57c839b33cfb633451f2fbde39e6f71eca5d82cf804ba235e (as copied, before the rewrite) |
| File | `1984_8275.pdf` |

## [D8275K]

| Field | Value |
|---|---|
| Title | 8275 Programmable CRT Controller (`8275_from_kiselev_repo.pdf`); scanned |
| Vendor | Intel |
| Document | AFN-00224B; no order number on any page |
| Edition | no date on any page; banner "Fully MCS-80 and MCS-85 Compatible" |
| Pages used | printed pp. 8-223..8-246 (PDF p. = printed - 222); checked 8-223, 8-233, 8-236, 8-240, 8-242, 8-243, 8-245 and the footers of all 24 pages |
| Origin | The DatasheetArchive (datasheetarchive.com), named in the file's metadata; the pages are an Intel data book section |
| Copied from | skiselev/radio-86rk at c5e9cb7, `Documentation/Intel - 8275.pdf` (added in f44a0e3, 2022-06-14); kept locally as `8275_from_kiselev_repo.pdf`, byte-identical |
| Download | https://github.com/skiselev/radio-86rk/raw/c5e9cb7/Documentation/Intel%20-%208275.pdf |
| Licence | No copyright notice and no statement on reproduction on p. 8-223 (checked). The file's metadata reads "The DatasheetArchive - Datasheet Search Engine". The PDF is encrypted with an owner password that forbids changes, and the metadata rewrite would remove that protection. The repository it was copied from is GPL-3.0 for its own work; a vendor PDF found there keeps the vendor's terms, not the GPL. Status unclear: not stored ([D84] and [D79] are stored editions of the same data sheet) |
| SHA-256 | aec733a972739cd70361560ba26249ec139f919f71f50167cdfde30a72826736 (as copied; not stored) |
| File | |

## [AP-62]

| Field | Value |
|---|---|
| Title | "A Low Cost CRT Terminal Using the 8275", application note AP-62 (`1984_AP-62.pdf`) |
| Vendor | Intel |
| Document | AP-62; AFN-01304A in the footer of the last page; the same note as [DG81] |
| Edition | November 1979 ("© Intel Corporation, 1979", p. 1), reprinted in a 1984 handbook, pp. 8-1 and on (1984 also in the bitsavers file name) |
| Pages used | PDF p. 6 (section 3.2, Fig. 3-4) |
| Origin | bitsavers, `components/intel/8275/1984_AP-62.pdf` (a scan with a text layer) |
| Copied from | bitsavers (2026-11-09); as copied: byte-identical to the file on bitsavers.org (checked 2026-11-15); stored: metadata rewritten (both hashes below) |
| Download | http://www.bitsavers.org/components/intel/8275/1984_AP-62.pdf |
| Licence | Intel copyright, p. 1: "© Intel Corporation, 1979". No ban on redistribution found in the text layer: stored |
| SHA-256 | 7238ff45a1035faef8ba4e365c4d42c541dc52087e97c208669c20f19e3897b0 (this file); 3e8a8539ac06d4190495663e311ea11c5a691858704415c57dcf64f67b832619 (as copied, before the rewrite) |
| File | `1984_AP-62.pdf` |

## [DG81]

| Field | Value |
|---|---|
| Title | "A Low Cost CRT Terminal Using the 8275" (`1981_8275_design.pdf`) |
| Vendor | Intel |
| Document | AP-62, AFN-01304A in the footer of the last page: the same application note as [AP-62] (November 1979), reprinted in a 1981 handbook, pp. 2-439..2-478 |
| Edition | the 1981 handbook reprint (1981 by the bitsavers file name); no date in the text layer |
| Pages used | the blink text (pages not recorded) |
| Origin | bitsavers, `components/intel/8275/1981_8275_design.pdf` (a scan with a text layer) |
| Copied from | bitsavers (2026-11-09); as copied: byte-identical to the file on bitsavers.org (checked 2026-11-15); stored: metadata rewritten (both hashes below) |
| Download | http://www.bitsavers.org/components/intel/8275/1981_8275_design.pdf |
| Licence | No copyright notice and no statement on reproduction found in the text layer: stored |
| SHA-256 | 9796f0c44771a05794798f287a34ddfdf13015ee78eda24a01ba9bf82a722832 (this file); 7c45b4d91f4cc2a6a128d4fb944147a99308234a3afa6fa1a68f7e3fa5bda6da (as copied, before the rewrite) |
| File | `1981_8275_design.pdf` |
