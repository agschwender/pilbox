from __future__ import absolute_import, division, print_function, with_statement

import hashlib
from pilbox.signature import derive_signature, sign
from tornado.test.util import unittest
import urlparse

class SignatureTest(unittest.TestCase):
    def test_derive_signature(self):
        key = "abc123"
        qs_list = ["x=1&y=2&z=3", "x=%20%2B%2F!%40%23%24%25%5E%26"]
        for qs in qs_list:
            m = hashlib.md5()
            m.update("%s%s" % (qs, key))
            self.assertEqual(derive_signature(key, qs), m.hexdigest())

    def test_sign(self):
        key = "abc123"
        qs_list = ["x=1&y=2&z=3", "x=%20%2B%2F!%40%23%24%25%5E%26"]
        for qs in qs_list:
            o = urlparse.parse_qs(sign(key, qs))
            self.assertTrue("sig" in o)
            self.assertTrue(o["sig"])
