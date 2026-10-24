"""Differential test for untouched BAS2TAP C syntax checker and Python port.

Calls original C without -n. C sometimes returns status 0 on a syntax
failure, so the program's reported ERROR diagnostic decides acceptance.
"""
from __future__ import annotations
import itertools
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bas2tap import BAS2TAPError, encode_program
from bas2tap_syntax import SpectrumSyntaxError, check_program


class CheckCSyntaxParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('gcc'):
            raise unittest.SkipTest('gcc required for C/Python syntax differential')
        cls.folder=tempfile.TemporaryDirectory(prefix='bas2tap-c-syntax-')
        cls.addClassCleanup(cls.folder.cleanup)
        cls.cwd=Path(cls.folder.name)
        cls.bin=cls.cwd/'bas2tap-c'
        subprocess.run(['gcc','-O2','-Wall',str(ROOT/'bas2tap.c'),'-o',str(cls.bin),'-lm'],
                       check=True,capture_output=True,text=True)

    def test_syntax_curated_and_generated(self):
        corpus=[
            'PRINT "HELLO"','LET X=1','FOR I=1 TO 10: NEXT I','IF A=7 THEN GO TO 5000',
            'BEEP 1,2','POKE 23609,0','PRINT VAL "1"','REM 14PRINT x',
            'PRINT AT 10,2;"OK"','DEF FN A(X,Y)=X+Y','DIM A(10)','LET A$="ABC"',
            'PRINT 1;2,3','PLOT INK 2;3,4','PRINT NOT 3','PRINT "ABC"(1 TO 3)',
            'PRINT A$(1 TO 3)','PRINT A(1,2)','INPUT LINE A$','SAVE "ABC" CODE 32768,10',
            'LOAD "" CODE','PRINT (1+2)','LET A=INKEY$="A"','PRINT RND * 4',
            'LET A$=3','LET A="B"','IF A= THEN PRINT 1','FOR I=1 TO 10 STEP',
            'PRINT SIN "ABC"','BEEP "A",3','NEXT A$','POKE 3,','DIM ABC(10)',
            'DEF FN ABC(X)=X','PRINT VAL +1', 'PRINT 1+2*3', 'PRINT 4<5',
            'PRINT NOT A', 'PRINT A$( TO 2)', 'PRINT A$(1 TO )',
            'PRINT ""(1)', 'PRINT ""()', 'PRINT ("ABC")(1 TO 2)',
            'PRINT A(1,2,3)', 'PRINT A$(1,2)', 'PRINT X$(1 TO 2,3)',
            'INPUT "PROMPT";A$', 'INPUT LINE A','READ A,B$,C(1)',
            'GO SUB 100','GO TO 10','RUN','RANDOMIZE','RESTORE',
            'CLS:PRINT 1', 'STOP','CLEAR #','PRINT 3 OR 4',
            'PRINT 1 AND 2','PRINT "HELLO" AND 1','PRINT "HELLO" OR 1',
            'PRINT (1) OR 2','PRINT (1=1) OR 2',
            'PRINT INT (1=1 AND 1<2) OR 3',
            'PRINT INKEY$="A"', 'PRINT USR "a"','PRINT USR 32768',
            'DEF FN A(X)=X*X', 'DEF FN A(X$)=X$', 'DEF FN A()=1',
            'PLOT PAPER 3;INK 1;10,20','DRAW 1,2','DRAW 1,2,3',
            'CIRCLE 15,20,7','CIRCLE 15,20,7,3', 'LIST', 'LIST 10',
            'LLIST', 'SAVE "ABC" LINE 100','SAVE ""', 'VERIFY "ABC"',
            'LOAD "GAME" SCREEN$', 'LOAD "GAME" DATA A()', 'SAVE "GAME" DATA A()',
            'PRINT SIN (1+2)', 'PRINT SIN 1+2','PRINT STR$ 8',
            'PRINT CHR$ 65','PRINT PEEK 23672','PRINT VAL$ "123"',
            'PRINT FN A(1)','PRINT POINT (1,2)','PRINT ATTR (1,2)',
            'PRINT SCREEN$ (1,2)', 'IF A=1 THEN : PRINT 1',
            'IF 0 THEN IF 1 THEN PRINT "YES"',
            'LET X=VAL "3"','LET X$=VAL$ "8"','BORDER 0:PAPER 7:INK 1',
            'DATA 1,2,"HI"','DATA 1,,2','READ A$','DIM A$(10,20)',
            'CAT 0', 'FORMAT "m";1;"vol"', 'OPEN # 4;"m";1;"FILE"',
            'CLOSE # 4', 'ERASE "m";1;"X"','MOVE "k" TO "s"',
        ]
        rng=random.Random(0x48C48)
        operands=['1','A','A$','"A"','PI','RND','(1)','(A$)','SIN 1','VAL "1"','USR "a"','-1','A(2)','"ABC"(1 TO 2)']
        for command in ('PRINT','LET A=','LET A$=','IF','POKE 1,','BEEP 1,',
                        'PAUSE','BORDER','PAPER','INK','GO TO','NEXT','RESTORE'):
            for value in operands:
                corpus.append(command+(' ' if command[-1].isalpha() else '')+value)
        for left,operator,right in itertools.product(('1','A$','"A"'),
                                                      ('+','-','*','=','AND','OR','<'),
                                                      ('1','B$','"B"')):
            corpus.append('PRINT '+left+' '+operator+' '+right)
        for _ in range(300):
            parts=[rng.choice(('1','2','3','A','B','PI','RND','"X"'))]
            for _ in range(rng.randrange(1,4)):
                parts.extend((rng.choice(('+','-','*','/','AND','OR','=','<')),rng.choice(('1','2','A','B','"X"'))))
            corpus.append('PRINT '+' '.join(parts))
        mismatches=[]
        for i,body in enumerate(corpus):
            listing='10 '+body+'\n'
            p=self.cwd/'input.bas'
            tap=self.cwd/'output.tap'
            p.write_text(listing,encoding='ascii')
            tap.unlink(missing_ok=True)
            c=subprocess.run([str(self.bin),'-q','-w',str(p),str(tap)],
                             capture_output=True,text=True,timeout=2)
            c_ok='ERROR' not in c.stderr.upper() and c.returncode==0
            try:
                check_program(encode_program(listing))
                py_ok=True
                py_err=''
            except (SpectrumSyntaxError,BAS2TAPError) as err:
                py_ok=False
                py_err=str(err)
            if c_ok!=py_ok:
                mismatches.append((i,body,c_ok,py_ok,c.stderr.strip()[:130],py_err[:130]))
        self.assertFalse(mismatches,'C/Python DIFFERENCES total=%s\n%s' %
                         (len(mismatches),'\n'.join(map(str,mismatches[:80]))))

if __name__=='__main__':
    unittest.main()