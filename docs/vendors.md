# Vendor folder names

The `<vendor>` of `ics/<vendor>/<part>/` and of the module name `<vendor>_<part>`. Lower case, no
spaces. A part goes under the vendor of its original design; second sources and Soviet equivalents
are listed in that folder's `equivalents.md`.

| Folder | Vendor | Examples |
|---|---|---|
| `intel` | Intel | 8080A, 8255A, 8257, 8275, 8253 |
| `amd` | Advanced Micro Devices | second sources: in the Intel folder's `equivalents.md` |
| `nec` | NEC | μPD parts of their own design |
| `zilog` | Zilog | Z80 family |
| `national` | National Semiconductor | parts of their own design |
| `ti` | Texas Instruments | 7400-series TTL with a model of its own |
| `ussr` | Soviet designs without a foreign prototype | parts with no Intel or TI original |

- A Soviet copy of a foreign part (КР580ВВ55А of the 8255A, КР580ВТ57 of the 8257) goes under the
  foreign vendor. Its Cyrillic name and transliteration are in `equivalents.md`.
- A new vendor gets a row here in the same commit as its first folder.
