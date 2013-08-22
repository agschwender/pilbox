from __future__ import absolute_import, division, print_function, \
    with_statement

import hashlib
import hmac

from tornado.test.util import unittest

from pilbox.signature import derive_signature, sign, verify_signature

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


class SignatureTest(unittest.TestCase):
    def test_derive(self):
        key = "abc123"
        qs_list = ["x=1&y=2&z=3", "x=%20%2B%2F!%40%23%24%25%5E%26"]
        for qs in qs_list:
            m = hmac.new(key.encode(), None, hashlib.sha1)
            m.update(qs.encode())
            self.assertEqual(derive_signature(key, qs), m.hexdigest())

    def test_sign(self):
        key = "abc123"
        qs_list = ["x=1&y=2&z=3", "x=%20%2B%2F!%40%23%24%25%5E%26"]
        for qs in qs_list:
            o = urlparse.parse_qs(sign(key, qs))
            self.assertTrue("sig" in o)
            self.assertTrue(o["sig"])

    def test_verify(self):
        key = "abc123"
        qs_list = ["x=1&y=2&z=3", "x=%20%2B%2F!%40%23%24%25%5E%26"]
        for qs in qs_list:
            self.assertTrue(verify_signature(key, sign(key, qs)))

    def test_bad_signature(self):
        key1 = "abc123"
        key2 = "def456"
        qs_list = ["x=1&y=2&z=3", "x=%20%2B%2F!%40%23%24%25%5E%26"]
        for qs in qs_list:
            self.assertFalse(verify_signature(key1, sign(key2, qs)))
