"""Fresh-source audit of the original 2013 C token and syntax classes."""
from __future__ import annotations
import re
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bas2tap import TOKENS
from bas2tap_syntax import GRAMMAR, NUM_FN, STR_FN, PRINT_FN, COLORS


def original_keywords():
    c=(ROOT/'bas2tap.c').read_text(encoding='latin-1')
    begin=c.index('   {"SPECTRUM",')
    end=c.index('#define MAXLINELENGTH',begin)
    table=c[begin:end]
    pattern=re.compile(r'\{\s*"([^"\n]+)",\s*([0-6]),\s*\{\s*([^{}]*?)\s*\}\s*\}',re.S)
    rows=[]
    for word,kind,params in pattern.findall(table):
        cls=[]
        for field in params.split(','):
            value=field.strip()
            if not value or value=='0':
                continue
            if re.fullmatch(r"'[^']'",value):
                cls.append(ord(value[1]))
            else:
                cls.append(int(value,0))
        rows.append((word,int(kind),tuple(cls)))
    return rows


class FreshCAudit(unittest.TestCase):
    def test_full_93_keyword_table_and_syntax_classes(self):
        rows=original_keywords()
        self.assertEqual(len(rows),93,rows)
        for n,(word,kind,classes) in enumerate(rows):
            code=0xA3+n
            with self.subTest(code=f'{code:02X}',word=word):
                self.assertEqual(TOKENS[code],word)
                self.assertEqual(GRAMMAR.get(word,()),classes)
                if kind==3:
                    self.assertIn(code,NUM_FN)
                if kind==4:
                    self.assertIn(code,STR_FN)
                if kind==5:
                    self.assertIn(code,PRINT_FN)
                if kind==2 and code in range(0xD9,0xDF) or code==0xE4:
                    self.assertIn(code,COLORS)
                if kind in (0,1,2) and code>=0xCE:
                    self.assertNotIn(code,NUM_FN|STR_FN|PRINT_FN)

    def test_checker_methods_cover_15_original_classes(self):
        from bas2tap_syntax import _Parser
        for name in ('var','expr','slice_string','items','arguments','def_fn',
                     'stream','channel','filename','filetype','io',
                     'colors','variables','pair','numeric','string','signature','check'):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(_Parser,name,None)),name)
        c=(ROOT/'bas2tap.c').read_text(encoding='latin-1')
        for number in range(1,16):
            with self.subTest(class_no=number):
                self.assertRegex(c,r'bool HandleClass'+f'{number:02d}'+r'\s*\(')
        self.assertIn('bool CheckSyntax (int BasicLineNo, byte *Line)',c)
        self.assertIn('bool ScanExpression (int BasicLineNo',c)
        self.assertIn('bool ScanVariable (int BasicLineNo',c)

if __name__=='__main__':
    unittest.main()