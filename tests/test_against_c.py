"""Differential checks of the pure Python port against untouched bas2tap.c.

Only these development tests use a C compiler. bas2tap.py itself never does.
The real C program runs with -n: its independent syntax checker is not part
of the Python tokenizer; ZX Spectrum ROM validation remains a caller's job.
"""
from __future__ import annotations

import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bas2tap import BAS2TAPError, convert


class OriginalCParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which('gcc') is None:
            raise unittest.SkipTest('gcc is required only for development differential tests')
        cls.folder = tempfile.TemporaryDirectory(prefix='bas2tap-c-')
        cls.addClassCleanup(cls.folder.cleanup)
        cls.temp = Path(cls.folder.name)
        cls.c_bin = cls.temp / 'bas2tap-c'
        subprocess.run(['gcc', '-O2', '-Wall', str(ROOT / 'bas2tap.c'),
                        '-o', str(cls.c_bin), '-lm'], check=True,
                       capture_output=True, text=True)

    def compare(self, src: str, *, case_insensitive: bool = False, name: str = 'PORT', autostart: int = 0x8000):
        p = self.temp / 'input.bas'
        q = self.temp / 'output.tap'
        p.write_bytes(src.encode('ascii'))
        q.unlink(missing_ok=True)
        cmd = [str(self.c_bin), '-q', '-w', '-n', '-s' + name]
        if case_insensitive:
            cmd.append('-c')
        if autostart != 0x8000:
            cmd.append('-a' + str(autostart))
        result = subprocess.run(cmd + [str(p), str(q)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, (src, result.stdout, result.stderr))
        self.assertNotIn('ERROR', result.stderr.upper(), (src, result.stderr))
        self.assertTrue(q.is_file(), src)
        try:
            python_tap = convert(src, name=name, autostart=autostart,
                                 case_insensitive=case_insensitive)
        except BAS2TAPError as err:
            self.fail(f'Python rejected C-accepted listing {src!r}: {err}')
        native_tap = q.read_bytes()
        self.assertEqual(python_tap, native_tap,
                         f'Byte mismatch for {src!r}: Python {python_tap.hex()} / C {native_tap.hex()}')

    def test_statement_fixtures(self):
        listings = (
            '10 PRINT "HELLO"', '10 PRINT 42', '10 LET X=1',
            '10 PRINT  .5', '10 PRINT .', '10 PRINT 1E+',
            '10 PRINT 2.5E-3', '10 PRINT 12345.0001',
            '10 PRINT 0.0000000001', '10 PRINT 65535',
            '10 PRINT 65536', '10 PRINT 1.5',
            '10 PRINT PI', '10 PRINT BIN 101011',
            '10 FOR I=1 TO 10: NEXT I',
            '10 IF a=7THEN IF a$="{92}"THEN GO TO 5000',
            '10 DEF FN a(x,y)=x+y',
            '10 PRINT "{CODE} {CAT} {(C)} {+1}{-8}{A}{U}"',
            '10 PRINT "{INK 3}{PAPER 4}{AT 1,10}{TAB 2,3}"',
            '10 PRINT {CODE}  1', '10 PRINT {CAT}  1',
            '10 PRINT "PRINT:IF THEN"',
            '10 REM PRINT  "  A  B  "',
            '10 PRINT 1: REM hi: THERE IS NOTHING ELSE',
            '10 POKE 23609,0',
            '10 BEEP 0.01,10',
            '10 PRINT "{FA}{0E}{20}{90}"',
            '10 PRINT AT 10,2;"OK"',
            '10 PRINT   1   :   PRINT   2',
            '10 RANDOMIZE :BORDER 0:PAPER 0:INK 7:CLS',
            '10 GO SUB 9000:GO TO 10',
            '10 PRINT "UP"\n20 REM SECOND LINE\n30 PRINT 2',
            '10 PRINT "LOWER"\n20 PRINT 20\n20 PRINT 30',
            '10 PRINT 0\n20',
            '\n\n10 PRINT 20\n\n',
            '10 PRINT "WITH\tTAB"',
        )
        for n, listing in enumerate(listings):
            with self.subTest(fixture=n, listing=listing):
                self.compare(listing)

    def test_numeric_fixtures(self):
        samples = ['0','1','.','1.', '1e', '1e+','1E-', '1e0',
                   '0.0000001', '.00001', '1.0000001', '0.999999999',
                   '1.23456789', '0.123456789', '10.001', '0.1',
                   '0.00001', '0.00000001', '1e-8', '1e+5', '65535',
                   '65536', '1e-20', '1e+20', '3.1415926535897']
        rng = random.Random(0x5A48)
        samples += [f'{rng.randrange(1,999999)}.{rng.randrange(0,10**8):08d}'
                    for _ in range(256)]
        for n, sample in enumerate(samples):
            with self.subTest(n=n, decimal=sample):
                self.compare('10 PRINT ' + sample)

    def test_case_insensitive_keywords(self):
        for src in ('10 print 1', '10 let a=val "3"', '10 for i=1 to 3:next i'):
            with self.subTest(src=src):
                self.compare(src, case_insensitive=True)

    def test_flags_and_tape_name(self):
        self.compare('10 PRINT 1', name='TEN', autostart=10)
        self.compare('10 PRINT "OK"', name='', autostart=0x8000)


if __name__ == '__main__':
    unittest.main()
