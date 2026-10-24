"""Regression coverage for Python's BAS2TAP 2.6 tokenizer and tape format."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bas2tap import (BAS2TAPError, _expand, _float_cache, convert,
                     encode_program, main, make_tap, tokenize_line)


class TokenizerTests(unittest.TestCase):
    def test_minelay_line_122_tokenizes_then(self):
        data = tokenize_line('IF a=7THEN IF a$="{92}"THEN GO TO 5000')
        self.assertEqual(data.count(bytes([0xcb])), 2)
        self.assertIn(b'\xfa' + b'a$', data)
        self.assertIn(b'"\x92"\xcb\xec', data)

    def test_keywords_and_numeric_cache(self):
        self.assertEqual(tokenize_line('PRINT 10'), b'\xf5' + b'10' + bytes((14, 0, 0, 10, 0, 0, 13)))
        self.assertEqual(tokenize_line('LET x=65535')[-7:], bytes((14, 0, 0, 255, 255, 0, 13)))

    def test_for_to_next_and_colon(self):
        p = tokenize_line('FOR I=1 TO 10: NEXT I')
        self.assertEqual(p.count(b'\xeb'), 1)
        self.assertEqual(p.count(b'\xcc'), 1)
        self.assertEqual(p.count(b'\xf3'), 1)

    def test_quoted_words_never_keywords(self):
        self.assertEqual(tokenize_line('PRINT "PRINT THEN"'), b'\xf5"PRINT THEN"\r')

    def test_comment_bytes_are_literal(self):
        self.assertEqual(tokenize_line('REM PRINT THEN  9'), b'\xeaPRINT THEN  9\r')

    def test_escapes_inside_quotes(self):
        self.assertEqual(tokenize_line('PRINT "{91}{92}{INK 3}"'), b'\xf5"\x91\x92\x10\x03"\r')

    def test_hex_escapes_and_udg(self):
        self.assertEqual(tokenize_line('PRINT "{FA}{A}{+1}{-8}{(C)}"'),
                         b'\xf5"\xfa\x90\x8e\x80\x7f"\r')

    def test_def_fn_evaluator_room(self):
        p = tokenize_line('DEF FN a(x,y)=x+y')
        self.assertEqual(p.count(b'\x0e\0\0\0\0\0'), 2)

    def test_bin_number(self):
        self.assertIn(b'\xc4' + b'101' + bytes((14, 0, 0, 5, 0, 0)),
                      tokenize_line('PRINT BIN 101'))

    def test_case_insensitive_option(self):
        with self.assertRaises(BAS2TAPError):
            tokenize_line('print 1')
        self.assertEqual(tokenize_line('print 1', case_insensitive=True)[0], 0xf5)

    def test_unexpected_keyword_rejected(self):
        with self.assertRaisesRegex(BAS2TAPError, 'unexpected keyword'):
            tokenize_line('LET x=PRINT 1')

    def test_misplaced_keyword_boundary_is_not_guessed(self):
        with self.assertRaisesRegex(BAS2TAPError, 'unexpected keyword'):
            tokenize_line('IF RND >skTHEN PRINT "x"')

    def test_invalid_quote_brackets_and_large_bin(self):
        for body in ('PRINT "unterminated', 'PRINT (1+2', 'PRINT BIN 11111111111111111'):
            with self.subTest(body=body), self.assertRaises(BAS2TAPError):
                tokenize_line(body)

    def test_numeric_values(self):
        self.assertEqual(_float_cache(1.0, 10), bytes((14, 0, 0, 1, 0, 0)))
        self.assertEqual(_float_cache(0.5, 10), bytes((14, 128, 0, 0, 0, 0)))
        with self.assertRaises(BAS2TAPError):
            _float_cache(1e99, 10)

    def test_raw_control_and_escaped_token(self):
        self.assertEqual(_expand('{F5}xxx', 0, strip=True), (b'\xf5', 4))
        self.assertEqual(_expand('{CODE}', 0, strip=True), (b'\xaf', 6))

    def test_c_number_scanner_accepts_legacy_spellings(self):
        for lexeme, numeric in (('.', 0), ('1e', 1), ('1E+', 1),
                                ('1e-', 1), ('2.5e', 2.5)):
            with self.subTest(lexeme=lexeme):
                self.assertIn(lexeme.encode('ascii') + _float_cache(numeric, 10),
                              tokenize_line('PRINT ' + lexeme))

    def test_c_code_cat_escapes_keep_following_spaces(self):
        self.assertEqual(tokenize_line('PRINT {CODE}  1'),
                         b'\xf5\xaf  1' + _float_cache(1, 10) + b'\r')
        self.assertEqual(tokenize_line('PRINT {CAT}  1'),
                         b'\xf5\xcf  1' + _float_cache(1, 10) + b'\r')

    def test_48k_udg_and_128k_token_conflict(self):
        for s in ('10 PRINT "{T}"\n20 SPECTRUM 1',
                  '10 PLAY "a"\n20 PRINT "{U}"'):
            with self.subTest(s=s), self.assertRaisesRegex(BAS2TAPError, 'conflicts'):
                encode_program(s)



class ListingTests(unittest.TestCase):
    def test_line_structure(self):
        p = encode_program('10 PRINT "A"\n20 PRINT "B"\n')
        self.assertEqual(p[:4], b'\x00\x0a\x05\x00')
        self.assertIn(b'\x00\x14', p)

    def test_line_only_after_first_line_in_tokenizer_mode(self):
        data = encode_program('10 PRINT 1\n20')
        self.assertEqual(data[-5:], b'\x00\x14\x01\x00\r')

    def test_blank_lines(self):
        self.assertEqual(encode_program('\n10 PRINT 1\n\n'), encode_program('10 PRINT 1'))

    def test_empty_listing_has_empty_tap_like_c(self):
        self.assertEqual(encode_program(''), b'')
        self.assertEqual(encode_program('\n\n'), b'')
        self.assertEqual(int.from_bytes(convert('')[14:16], 'little'), 0)

    def test_invalid_controls_not_silently_treated_as_line_endings(self):
        for text in ('10 PRINT 1\x0b20 PRINT 2', '10 PRINT 1\x1c20 PRINT 2'):
            with self.subTest(source=text), self.assertRaisesRegex(BAS2TAPError, 'invalid character'):
                encode_program(text)

    def test_original_c_physical_buffer_limit_counts_newline(self):
        # The C fgets buffer also counts the terminating newline.
        with self.assertRaisesRegex(BAS2TAPError, 'buffer'):
            encode_program('10 REM ' + 'x' * 1017 + '\n')

    def test_warnings_from_original_c(self):
        warning_lines = []
        encode_program('\n10 PRINT "{NO}"\n10 PRINT 2', warn=warning_lines.append)
        self.assertIn('WARNING - Skipping empty ASCII line 1', warning_lines)
        self.assertIn('WARNING - Unexpandable sequence "{NO}" in line 10', warning_lines)
        duplicate = []
        encode_program('10 PRINT 1\n10 PRINT 2', warn=duplicate.append)
        self.assertIn('WARNING - Duplicate use of line number 10', duplicate)

    def test_invalid_source(self):
        for source in ('PRINT "ABC"', '1 PRINT "ABC"\n0 PRINT 1',
                       '10 PRINT "£"', '10000 PRINT 1', '10', '10 PRINT 1\n5 PRINT 2'):
            with self.subTest(source=source), self.assertRaises(BAS2TAPError):
                encode_program(source)

    def test_comment_space_preservation(self):
        self.assertIn(b'\xeaa  b', encode_program('10 REM  a  b'))

    def test_actual_minelay_fragment(self):
        listing = '1 RANDOMIZE :BORDER 0:PAPER 0:INK 7:CLS\n122 IF a=7THEN IF a$="{92}"THEN GO TO 5000'
        p = encode_program(listing)
        self.assertIn(b'\xfa' + b'a=7' + bytes((14, 0, 0, 7, 0, 0, 0xcb)), p)


class TapTests(unittest.TestCase):
    def test_golden_header_and_checksum(self):
        p = encode_program('10 PRINT "HELLO"')
        tap = make_tap(p, name='HELLO')
        self.assertEqual(tap[:5], b'\x13\0\0\0H')
        self.assertEqual(tap[4:14], b'HELLO     ')
        self.assertEqual(int.from_bytes(tap[14:16], 'little'), len(p))
        self.assertEqual(tap[16:18], b'\0\x80')
        n = int.from_bytes(tap[:2], 'little')
        m = int.from_bytes(tap[2+n:4+n], 'little')
        self.assertEqual(len(tap), n + m + 4)
        self.assertEqual(0, self.xor(tap[2:2+n]))
        self.assertEqual(0, self.xor(tap[4+n:4+n+m]))

    @staticmethod
    def xor(buf):
        result = 0
        for x in buf:
            result ^= x
        return result

    def test_conversion_equivalence(self):
        listing = '10 FOR a=1 TO 4\n20 PRINT a\n30 NEXT a\n'
        self.assertEqual(convert(listing), make_tap(encode_program(listing)))

    def test_autostart(self):
        data = convert('10 PRINT 1', autostart=10)
        self.assertEqual(data[16:18], b'\x0a\0')

    def test_too_long_name(self):
        with self.assertRaises(BAS2TAPError):
            make_tap(b'x', name='0123456789X')

    def test_cli_no_compiler(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / 'hello.bas'
            target = Path(folder) / 'hello.tap'
            src.write_text('10 PRINT "HELLO"\n', encoding='ascii')
            self.assertEqual(main(['-n', '-q', '-sHELLO', str(src), str(target)]), 0)
            self.assertEqual(target.read_bytes(), convert(src.read_text(), name='HELLO'))


if __name__ == '__main__':
    unittest.main()
