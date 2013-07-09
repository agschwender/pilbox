from __future__ import absolute_import, division, print_function, with_statement

import os.path
import tornado.escape
from tornado.testing import AsyncHTTPTestCase
import tornado.web
import urllib
from ..app import PilboxApplication, ImageHandler
from ..signature import sign
from .image_test import ImageTest


class _AppAsyncMixin(object):
    def fetch_error(self, code, *args, **kwargs):
        response = self.fetch(*args, **kwargs)
        self.assertEqual(response.code, code)
        self.assertEqual(response.headers.get("Content-Type", None),
                         "application/json")
        return tornado.escape.json_decode(response.body)

    def fetch_success(self, *args, **kwargs):
        response = self.fetch(*args, **kwargs)
        self.assertEqual(response.code, 200)
        return response

    def get_image_resize_cases(self):
        cases = ImageTest.get_image_resize_cases()
        if not cases:
            self.fail("no valid images for testing")

        for i, case in enumerate(cases):
            path = "/test-data/%s" % os.path.basename(case["source_path"])
            cases[i]["source_query_params"] = dict(
                url=self.get_url(path),
                w=case["width"],
                h=case["height"],
                mode=case["mode"])
        return cases


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

    def test_valid(self):
        cases = self.get_image_resize_cases()
        for case in cases:
            qs = urllib.urlencode(case["source_query_params"])
            resp = self.fetch_success("/?%s" % qs)
            with open(case["expected_path"]) as expected:
                self.assertEqual(resp.buffer.read(), expected.read())


class AppRestrictedTest(AsyncHTTPTestCase, _AppAsyncMixin):
    KEY = "abcdef"
    NAME = "abc"

    def get_app(self):
        return PilboxApplication(
            client_name=self.NAME,
            client_key=self.KEY,
            allowed_hosts=["foo.co", "bar.io", "localhost"])

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

    def test_valid(self):
        cases = self.get_image_resize_cases()
        for case in cases:
            params = case["source_query_params"]
            params["client"] = self.NAME
            qs = sign(self.KEY, urllib.urlencode(params))
            resp = self.fetch_success("/?%s" % qs)
            with open(case["expected_path"]) as expected:
                self.assertEqual(resp.buffer.read(), expected.read())
