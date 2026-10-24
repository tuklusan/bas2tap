# Python BAS2TAP — Convert ZX Spectrum BASIC to TAP with Python

**python-bas2tap** (also called **pybas2tap**) is a pure-Python **ZX Spectrum BASIC-to-TAP converter**. Turn a
numbered, plain-text Sinclair BASIC listing (`.bas`) into a tokenized **ZX Spectrum `.tap` tape image** for a
Spectrum emulator. It supports the BASIC vocabulary of the **ZX Spectrum 48K and 128K**, runs on **Python 3.10+**, and needs **no C compiler or third-party Python packages** for normal use.

**[Get python-bas2tap](https://github.com/tuklusan/python-bas2tap)** · [Quick start](#quick-start-convert-bas-to-tap) ·
[CLI options](#command-line-options) · [Python API](#use-bas2tap-from-python) ·
[Original BAS2TAP](#credits-and-upstream-bas2tap)

This repository contains the working Python program, `bas2tap.py`, plus a separate Python BASIC syntax checker.
The original C implementation is retained for reference and comparison. **The tool to run for this port is
`bas2tap.py`**, not a compiled C executable. The name *pybas2tap* is a convenient way to refer to the port;
there is no separate `pybas2tap` command or package in this repository.

## Why use python-bas2tap?

- **BASIC to TAP in one command.** Convert a numbered ASCII `.bas` listing into the classic Spectrum tape-file format.
- **Python only.** Run the converter with Python's standard library. There is no build step and no `pip install` step.
- **Real Spectrum BASIC tokens.** The port encodes Sinclair keywords, line records, numeric values, and BASIC
  tape blocks instead of putting plain text into a file with a `.tap` extension. A new filename alone has never
  persuaded a Spectrum to load anything.
- **Syntax checking by default.** The separate `bas2tap_syntax.py` module implements the original BAS2TAP
  C-style syntax checks; use `-n` when you deliberately want tokenization without that check.
- **Useful tape settings.** Choose the tape program name and an optional auto-start line.
- **Made for scripted workflows.** Call the converter from a terminal, or import its functions to obtain BASIC
  or TAP bytes directly in Python.
- **Compared with BAS2TAP C.** The included test suite checks encoding and syntax behavior against the
  original C implementation where a C compiler is available.

## Quick start: convert BAS to TAP

### 1. Get the Python port

```sh
git clone https://github.com/tuklusan/python-bas2tap.git
cd python-bas2tap
python3 --version
```

Use Python **3.10+**. On Windows, `py -3` can replace `python3` in the commands below if the Python launcher is
installed. You do not need to build `bas2tap.c` to run this port.

### 2. Make a numbered Sinclair BASIC listing

Create a plain-text file named `hello.bas`:

```text
10 PRINT "HELLO FROM PYTHON BAS2TAP"
20 GO TO 10
```

Each BASIC program line belongs on its own text line and starts with a Spectrum line number. The converter reads
ASCII text, not a saved tokenized BASIC file. Use standard Spectrum keyword spelling. For example, `GO TO` and `GO SUB` need spaces.

### 3. Generate the ZX Spectrum TAP file

```sh
python3 bas2tap.py -sHELLO -a10 hello.bas hello.tap
```

This creates `hello.tap`. Its tape header uses `HELLO` as the program name and requests automatic execution from
BASIC line `10` after loading. The file contains the ordinary Spectrum BASIC header and data blocks, with TAP
length fields and XOR checksums.

You can also let Python BAS2TAP choose the output name:

```sh
python3 bas2tap.py hello.bas
```

That writes `hello.tap` beside `hello.bas`. Open or load the `.tap` file in a ZX Spectrum emulator that supports
TAP tapes. The sample program keeps printing until stopped; this is vintage computing's idea of a screensaver.

## Command-line options

Run `python3 bas2tap.py -h` to see the built-in help. The basic form is:

```text
python3 bas2tap.py [-q] [-w] [-e] [-c] [-n] [-s NAME] [-a LINE] input.bas [output.tap]
```

| Option | What the Python port does |
| --- | --- |
| `input.bas` | Reads a numbered ASCII ZX Spectrum BASIC listing. |
| `output.tap` | Selects the destination TAP file; omit it to use the input filename with a `.tap` suffix. |
| `-sHELLO` or `-s HELLO` | Sets the Spectrum tape name; up to 10 ASCII characters. |
| `-a10` or `-a 10` | Sets BASIC line 10 as the auto-start line; without this option, auto-start is disabled. |
| `-c` | Matches BASIC keywords without regard to letter case. |
| `-n` | Skips the Python syntax-checking pass; tokenization checks still apply. |
| `-q` | Suppresses the normal success message. |
| `-w` | Suppresses warnings. |
| `-e` | Sends errors to standard output instead of standard error. |
| `-h` | Shows help. |

For example, convert a listing containing lowercase BASIC keywords:

```sh
python3 bas2tap.py -c -sDEMO -a10 demo.bas demo.tap
```

Use `-c` with care: an identifier that looks like a BASIC keyword can be read as that keyword. Without `-c`,
write Sinclair keywords in uppercase. Multiword keywords still need their proper spaces. Python BAS2TAP follows
the original converter's token matching rules; it does not guess what you meant to type.

**By default, syntax checking is enabled.** The checker follows the original C program's BASIC grammar,
including supported extension commands. It is **not** the original ZX Spectrum ROM syntax checker, and
converting a listing does not prove that the program will run correctly on every Spectrum model.

## What happens to the BASIC listing?

Python BAS2TAP reads each numbered source line, recognizes Sinclair BASIC keywords, and writes the matching
Spectrum token bytes. It also creates the internal numeric data used by Spectrum BASIC, handles statement
separators, and preserves strings and `REM` text according to the converter's rules. The result is encoded as
Spectrum line-numbered BASIC records.

The TAP writer then puts those records into two standard tape blocks: a BASIC program header and a data block.
Each block has a length and an XOR checksum. The output is a **`.tap` tape image**, not a `.tzx`, `.wav`,
compiled Z80 program, or snapshot.

Input requirements and practical limits follow the port's source:

- Input text must be ASCII. Each program line must have a line number from `0` through `9999`, in
  nondecreasing order. Duplicate line numbers can produce warnings.
- BASIC keywords normally use uppercase. Multiword keywords such as `GO TO`, `GO SUB`, `DEF FN`, and `OPEN #`
  must retain their spelling and spaces.
- A single physical input line must fit the original converter's buffer limit of fewer than 1,024 characters,
  counting its line ending where present.
- Encoded BASIC program data has a **41,500-byte** limit, inherited from BAS2TAP.
- The tape header name is limited to **10 ASCII characters**.
- The tool writes **TAP only**. If your workflow needs TZX or audio, use a separate, suitable tape conversion
  tool afterwards.

### Spectrum graphics, UDGs, and control codes

Text listings can include BAS2TAP's brace escapes for Spectrum character bytes and display controls. For example:

```text
10 PRINT "{INK 2}RED INK"
20 PRINT "{A}"
30 PRINT AT 10,5;"HELLO"
```

`{A}` through `{U}` select the Spectrum user-defined graphic (UDG) character codes. Other supported forms
include hex byte escapes such as `{7F}`, block graphics such as `{+1}` and `{-1}`, `{(C)}`, `{CODE}`, `{CAT}`,
and display controls such as `{PAPER 3}` and `{AT 1,10}`. The UDG `T`/`U` character codes conflict with certain
128K-only keyword tokens; the converter checks for that conflict.

The full escape and token behavior is implemented in [`bas2tap.py`](bas2tap.py). For background on the Python
implementation, see [`PYTHON-PORT.md`](PYTHON-PORT.md).

## Use BAS2TAP from Python

The converter can be imported directly from `bas2tap.py`. This works well for scripts that build ZX Spectrum
tape images from generated or edited BASIC source.

```python
from pathlib import Path
from bas2tap import convert

listing = '10 PRINT "HELLO"\n20 GO TO 10\n'
tap_bytes = convert(listing, name="HELLO", autostart=10, syntax_check=True)
Path("hello.tap").write_bytes(tap_bytes)
```

The public functions accept and return in-memory data:

| Function | Result |
| --- | --- |
| `tokenize_line(body, line_number=10)` | Sinclair-tokenized BASIC line body, ending in carriage return. |
| `encode_program(listing, syntax_check=False)` | Spectrum line records as bytes, without a tape header. |
| `make_tap(program, name="", autostart=32768)` | A TAP file containing the BASIC header and data blocks. |
| `convert(listing, name="", autostart=32768, syntax_check=False)` | Full ASCII BASIC-to-TAP conversion as bytes. |

For library use, **syntax checking is off unless you request `syntax_check=True`** on `encode_program()` or
`convert()`. This differs from the command line, where syntax checking is on by default. Keyword case matching
can also be selected using `case_insensitive=True` when tokenizing or encoding a program.

A second example keeps the two stages separate:

```python
from bas2tap import encode_program, make_tap

source = '10 PRINT "READY"\n'
program = encode_program(source, syntax_check=True)
tap_bytes = make_tap(program, name="READY", autostart=10)
```

Neither example launches an emulator or runs the BASIC program. They build the tape data that an emulator can load.

## Test the Python port

From the repository root, run:

```sh
python3 -m unittest discover -s tests -v
```

Tests cover Sinclair token values, number encoding, strings and remarks, escape sequences, tape headers,
checksums, and syntax behavior. The repository also contains C-versus-Python comparison tests. Those tests
compile the preserved `bas2tap.c` with GCC when GCC is available; the Python converter itself does not need GCC.

### Troubleshooting

**The program reports a line or syntax error.** Check the indicated BASIC line, spelling, spaces, quote marks,
and brackets. Try `-n` only if you specifically want output without the syntax-checking pass. Disabling a check
does not fix the BASIC program.

**Lowercase `print` is rejected.** Use `PRINT`, or pass `-c` and accept the keyword-name collision risk.

**The output is `.tap`, not `.tzx`.** That is expected. Python BAS2TAP writes TAP tape blocks. The extension is
not an optional fashion accessory.

**`pip install pybas2tap` is not the documented way to run this repository.** Clone or download the source, then
use `python3 bas2tap.py`. There is no `pybas2tap.py` entry point in this source tree.

**The TAP loads but the BASIC behaves unexpectedly.** Successful conversion establishes that tape bytes were
written, not that the listing's runtime logic is correct. Test the tape in the Spectrum model or emulator you
intend to use.

## Credits and upstream BAS2TAP

This Python version is based on **BAS2TAP 2.6** by **Martijn van der Heide**, **ThunderWare Research Center**
(20 January 2013). The original BAS2TAP program, written in C, established the converter's Sinclair BASIC
tokenization, syntax, and tape-writing behavior. We keep [`bas2tap.c`](bas2tap.c) in this repository and
acknowledge that work with thanks.

For the original C project, see **[speccyorg/bas2tap](https://github.com/speccyorg/bas2tap)**. The original
documentation also points to the historical [World of Spectrum utilities](http://www.worldofspectrum.org/utilities.html). For this repository's Python-specific notes, see
**[PYTHON-PORT.md](PYTHON-PORT.md)**.

**python-bas2tap / pybas2tap** is the Python port featured here. When you need **Sinclair BASIC text to a ZX
Spectrum TAP image using Python**, start with [`bas2tap.py`](bas2tap.py). The original BAS2TAP deserves its
place in Spectrum history; the present-day job of this README is to help you run the Python version.

## License

This repository retains the original BAS2TAP GPL terms: **GNU General Public License, version 2 or (at your
option) any later version**. See the complete [`LICENSE`](LICENSE) file. The software is distributed without
warranty.
