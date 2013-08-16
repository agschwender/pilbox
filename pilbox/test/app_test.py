from __future__ import absolute_import, division, print_function, \
    with_statement

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
                w=case["width"] or "",
                h=case["height"] or "",
                mode=case["mode"])
            for k in ["bg", "pos"]:
                if k in case:
                    cases[i]["source_query_params"][k] = case[k]
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

    def test_invalid_mode(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   mode="foo"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_MODE)

    def test_invalid_background(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   mode="fill", bg="r"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_BACKGROUND)

        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   mode="fill", bg="0f0f0f0f"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_BACKGROUND)

    def test_invalid_position(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   pos="foo"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.INVALID_POSITION)

    def test_bad_format(self):
        path = "/test-data/test-bad-format.gif"
        qs = urllib.urlencode(dict(url=self.get_url(path), w=1, h=1))
        resp = self.fetch_error(415, "/?%s" % qs)
        self.assertEqual(resp.get("error"), ImageHandler.UNSUPPORTED_IMAGE_TYPE)

    def test_valid(self):
        cases = self.get_image_resize_cases()
        for case in cases:
            qs = urllib.urlencode(case["source_query_params"])
            resp = self.fetch_success("/?%s" % qs)
            msg = "/?%s does not match %s" \
                % (qs, case["expected_path"])
            with open(case["expected_path"]) as expected:
                self.assertEqual(resp.buffer.read(), expected.read(), msg)


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
        params = dict(url="http://foo.co/x.jpg", w=1, h=1,
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
            msg = "/?%s does not match %s" \
                % (qs, case["expected_path"])
            with open(case["expected_path"]) as expected:
                self.assertEqual(resp.buffer.read(), expected.read(), msg)
