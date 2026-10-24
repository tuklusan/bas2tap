# BAS2TAP 2.6 — portable Python tokenizer

`bas2tap.py` is a standard-library-only Python port of the **tokenization and
TAP-writing parts** of `bas2tap.c` (BAS2TAP v2.6, Martijn van der Heide,
20 January 2013). The C implementation and its GPL license remain unchanged.
Python 3.10 or later is required; neither a C compiler nor any third-party
Python package is needed to **run** the port.

The module exports `tokenize_line(body, line_number=..., case_insensitive=...)`
(returning Sinclair token bytes ending in CR), `encode_program(listing)`
(returning line-numbered BASIC records), `make_tap(program, name=...,
autostart=...)`, and `convert(listing, name=..., autostart=...)`.

From the repository root:

```sh
python3 bas2tap.py -n -sHELLO hello.bas hello.tap
python3 -m unittest discover -s tests -v
```

Supported core behavior: longest-match Spectrum keyword tokenization, case
matching, statement boundaries, strings and remarks, line numbers, binary
and decimal numeric caches, `DEF FN` parameter storage, UDG/graphics/control
escapes, normal BASIC tape header blocks, auto-start line, and TAP XOR parity.

**Current boundary:** the original C program's separate, extensive syntax
checker for 48K/128K BASIC and expansion peripherals has **not** been ported.
The Python CLI therefore requires `-n` (the C program's disable-syntax-check
switch) and refuses to silently pass itself off as a full syntax checker.
For ZX-UX RBC, the independently working original 48K ROM checker must validate
the returned Sinclair token stream; no syntax validity is inferred from TAP
conversion alone. For untrusted BASIC files, use a trusted ROM check before
execution or compilation. The Python implementation has not yet been proved
byte-for-byte equivalent to the C program over its full input domain.

The Python port is upstream in this fork; it does **not** update RBC, the
ZX-UX SDK, the frozen release or the original collection of BASIC/TZX files.
