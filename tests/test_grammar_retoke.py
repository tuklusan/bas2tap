"""Sinclair 48K grammar-aware retokenization of paper BASIC listings.

Reference: Juan-Antonio Fernandez-Madrigal's ZX-Basicus LL(1) grammar v2.1.2,
particularly VARNAME, statementdeclv, printcontrol and loccontrol.
The original ROM syntax checker continues to validate the results.
"""
import unittest
from bas2tap import encode_program, tokenize_line
from bas2tap_syntax import check_program, SpectrumSyntaxError


class SpectrumPaperGrammar(unittest.TestCase):
    def test_at_variable_in_expressions(self):
        for body in ('LET AT=0', 'LET CAT=AT+2', 'IF AT=1 THEN LET AT=2',
                     'LET A$=STR$ (AT)', 'READ AT,A$', 'DIM AT(4)',
                     'PRINT AT;', 'PRINT AT,1', 'INPUT AT'):
            with self.subTest(body=body):
                tokenized = tokenize_line(body)
                self.assertIn(b'AT', tokenized)
                self.assertNotIn(b'\xac', tokenized)
                check_program(encode_program('10 ' + body))

    def test_at_controls_are_still_tokens(self):
        for body in ('PRINT AT 2,0', 'INPUT AT 2,0', 'LPRINT AT 2,0',
                     'PRINT 1;AT 2,0'):
            with self.subTest(body=body):
                self.assertIn(b'\xac', tokenize_line(body))
                check_program(encode_program('10 ' + body))

    def test_genuine_rom_errors_remain_errors(self):
        for body in ('FOR AT=1 TO 2', 'NEXT AT', 'LET AT$="X"'):
            with self.subTest(body=body), self.assertRaises(SpectrumSyntaxError):
                check_program(encode_program('10 ' + body))

    def test_literal_and_rem_bytes_unchanged(self):
        for body, expected in [('PRINT "AT"', b'"AT"'),
                               ('REM AT AT THEN', b'AT AT THEN')]:
            self.assertIn(expected, tokenize_line(body))


if __name__ == '__main__':
    unittest.main()
