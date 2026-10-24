"""Freeze the reviewed BAS2TAP tokenizer bytes in both maintained copies.

Changing the tokenizer requires deliberate removal of this regression guard;
no change to the standalone ROM LLIST exporter is implied by this pin.
"""
import hashlib
import unittest
from pathlib import Path

FROZEN_SHA256 = 'c12d852652366162cb4787ebfc149fd91bc36d09fcbf8c1e44dc75b572fd016d'


class FrozenBAS2TAP(unittest.TestCase):
    def test_tokenizer_bytes_remain_frozen(self):
        root = Path(__file__).resolve().parents[1]
        candidates = (root / 'bas2tap.py', root / 'stage' / 'bas2tap.py')
        matches = [p for p in candidates if p.is_file()]
        self.assertEqual(len(matches), 1, f'Expected exactly one BAS2TAP source: {matches}')
        digest = hashlib.sha256(matches[0].read_bytes()).hexdigest()
        self.assertEqual(digest, FROZEN_SHA256,
                         'BAS2TAP source is frozen and must not be modified')


if __name__ == '__main__':
    unittest.main()
