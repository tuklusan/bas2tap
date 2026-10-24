"""Read-only C/Python acceptance and token parity for the 60 original games.

The DEVELOPMENT repository is checked out separately by CI at a fixed commit.
This never compiles native RBC programs or writes an input in the game corpus.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bas2tap import BAS2TAPError,convert,encode_program
from bas2tap_syntax import SpectrumSyntaxError,check_program


@unittest.skipUnless(os.environ.get('ZXUX_CORPUS'), 'separate DEVELOPMENT corpus checkout not present')
class CorpusParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('gcc'):
            raise unittest.SkipTest('gcc required for reference differential')
        cls.root=Path(os.environ['ZXUX_CORPUS']).resolve()
        cls.converter=Path(os.environ['ZXUX_TZX2BAS']).resolve()
        cls.games=sorted(p for p in cls.root.iterdir() if p.is_dir() and p.name[:2].isdigit() and p.name[2]=='-')
        if len(cls.games)!=60:
            raise ValueError('Expected exactly 60 game directories')
        cls.tempdir=tempfile.TemporaryDirectory(prefix='bas2tap-original-corpus-')
        cls.addClassCleanup(cls.tempdir.cleanup)
        cls.tmp=Path(cls.tempdir.name)
        cls.cbin=cls.tmp/'bas2tap-c'
        subprocess.run(['gcc','-O2','-Wall',str(ROOT/'bas2tap.c'),'-o',str(cls.cbin),'-lm'],
                       capture_output=True,text=True,check=True)

    def test_both_60_game_paths(self):
        problems=[]
        checked=0
        for game in self.games:
            bas=game/'BASIC'/(game.name+'.bas')
            tzx=game/'BASIC'/(game.name+'.tzx')
            text=bas.read_text(encoding='ascii')
            tape=subprocess.run([sys.executable,str(self.converter),str(tzx)],
                                capture_output=True,text=True,encoding='latin-1',errors='replace',timeout=20)
            if tape.returncode:
                problems.append((game.name,'TZX extraction error',tape.stderr[:160]))
                continue
            for origin,listing in (('bas',text),('tzx',tape.stdout)):
                checked+=1
                src=self.tmp/'src.bas'
                dst=self.tmp/'out.tap'
                src.write_text(listing,encoding='ascii')
                for with_syntax in (False,True):
                    dst.unlink(missing_ok=True)
                    cmd=[str(self.cbin),'-q','-w'] + ([] if with_syntax else ['-n']) + [str(src),str(dst)]
                    r=subprocess.run(cmd,capture_output=True,text=True,encoding='latin-1',errors='replace',timeout=20)
                    c_ok=r.returncode==0 and 'ERROR' not in r.stderr.upper()
                    try:
                        p=convert(listing,syntax_check=with_syntax)
                        py_ok=True
                    except (BAS2TAPError,SpectrumSyntaxError,UnicodeError) as e:
                        py_ok=False
                        err=str(e)
                    if c_ok!=py_ok:
                        problems.append((game.name,origin,'syntax' if with_syntax else 'tokenizer',
                                         'C='+str(c_ok),'Python='+str(py_ok),r.stderr[-130:],
                                         '' if py_ok else err[:130]))
                    elif c_ok and not with_syntax and dst.read_bytes()!=p:
                        problems.append((game.name,origin,'C/Python TAP byte difference',len(dst.read_bytes()),len(p)))
        self.assertEqual(checked,120,'Did not check 60 BAS and 60 TZX paths independently')
        self.assertFalse(problems,'Corpus problems: '+repr(problems[:80]))

if __name__=='__main__':
    unittest.main()