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

**Syntax checking:** the standalone pure-Python bas2tap_syntax.py now
implements the original C statement and expression syntax checker, including
variable and string forms, data definitions, and original cassette/extension
syntax. The CLI validates by default and -n disables the syntax pass,
matching the C command line. Library calls may request syntax_check=True.
The independent 48K Spectrum ROM syntax checker must still be used by RBC;
C-checker agreement does not replace ROM behavior.

The C/Python source audit and differential suite in
tests/test_syntax_against_c.py compare both acceptance and rejection.

The Python port is upstream in this fork; it does **not** update RBC, the
ZX-UX SDK, the frozen release or the original collection of BASIC/TZX files.
