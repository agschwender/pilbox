from __future__ import absolute_import, division, print_function, with_statement

from pilbox.app import PilboxApplication, ImageHandler
from pilbox.signature import sign
import tornado.escape
from tornado.testing import AsyncHTTPTestCase
import tornado.web
import urllib


class _AppAsyncMixin(object):
    def fetch_error(self, code, *args, **kwargs):
        response = self.fetch(*args, **kwargs)
        self.assertEqual(response.code, code)
        self.assertEqual(response.headers.get("Content-Type", None),
                         "application/json")
        return tornado.escape.json_decode(response.body)


class AppTest(AsyncHTTPTestCase, _AppAsyncMixin):
    def get_app(self):
        return PilboxApplication()

    def test_missing_url(self):
        qs = urllib.urlencode(dict(w=1, h=1))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.MISSING_URL)

    def test_missing_dimensions(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.MISSING_DIMENSIONS)

    def test_invalid_width(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w="a", h=1))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_WIDTH)

    def test_invalid_height(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h="a"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_HEIGHT)


class AppRestrictedTest(AsyncHTTPTestCase, _AppAsyncMixin):
    KEY = "abcdef"
    NAME = "abc"

    def get_app(self):
        return PilboxApplication(client_name=self.NAME,
                                 client_key=self.KEY,
                                 allowed_hosts=["foo.co", "bar.io"])

    def test_missing_client_name(self):
        params = dict(url="http://foo.co/x.jpg", w=1, h=1)
        qs = sign(self.KEY, urllib.urlencode(params))
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_CLIENT)

    def test_bad_client_name(self):
        params = dict(url="http://foo.co/x.jpg", w=1, h=1, client="123")
        qs = sign(self.KEY, urllib.urlencode(params))
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_CLIENT)

    def test_missing_signature(self):
        params = dict(url="http://foo.co/x.jpg", w=1, h=1, client=self.NAME)
        qs = urllib.urlencode(params)
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_SIGNATURE)

    def test_bad_signature(self):
        params = dict(url="http://foo.co/x.jpg", w=1, h=1, \
                          client=self.NAME, sig="abc123")
        qs = urllib.urlencode(params)
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_SIGNATURE)

    def test_bad_host(self):
        params = dict(url="http://bar.co/x.jpg", w=1, h=1, client=self.NAME)
        qs = sign(self.KEY, urllib.urlencode(params))
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_HOST)
