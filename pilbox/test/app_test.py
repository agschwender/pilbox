from __future__ import absolute_import, division, print_function, \
    with_statement

import os.path
import tornado.escape
from tornado.testing import AsyncHTTPTestCase
import tornado.web
import urllib

from ..app import PilboxApplication
from ..errors import SignatureError, ClientError, HostError, \
    BackgroundError, DimensionsError, FilterError, ModeError, PositionError, \
    QualityError, UrlError, FormatError
from ..signature import sign
from . import image_test


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
        cases = image_test.get_image_resize_cases()
        if not cases:
            self.fail("no valid images for testing")

        m = dict(background="bg", filter="filter", position="pos", quality="q")
        for i, case in enumerate(cases):
            path = "/test-data/%s" % os.path.basename(case["source_path"])
            cases[i]["source_query_params"] = dict(
                url=self.get_url(path),
                w=case["width"] or "",
                h=case["height"] or "",
                mode=case["mode"])
            for k in m.keys():
                if k in case:
                    cases[i]["source_query_params"][m.get(k)] = case[k]
        return cases


class AppTest(AsyncHTTPTestCase, _AppAsyncMixin):
    def get_app(self):
        return PilboxApplication()

    def test_missing_url(self):
        qs = urllib.urlencode(dict(w=1, h=1))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), UrlError.get_code())

    def test_missing_dimensions(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), DimensionsError.get_code())

    def test_invalid_width(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w="a", h=1))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), DimensionsError.get_code())

    def test_invalid_height(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h="a"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), DimensionsError.get_code())

    def test_invalid_mode(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   mode="foo"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), ModeError.get_code())

    def test_invalid_hexadecimal_background(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   mode="fill", bg="r"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), BackgroundError.get_code())

    def test_invalid_long_background(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   mode="fill", bg="0f0f0f0f"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), BackgroundError.get_code())

    def test_invalid_position(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   pos="foo"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), PositionError.get_code())

    def test_invalid_filter(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   filter="bar"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), FilterError.get_code())

    def test_invalid_integer_quality(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   q="a"))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), QualityError.get_code())

    def test_outofbounds_quality(self):
        qs = urllib.urlencode(dict(url="http://foo.co/x.jpg", w=1, h=1,
                                   q=200))
        resp = self.fetch_error(400, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), QualityError.get_code())

    def test_bad_format(self):
        path = "/test-data/test-bad-format.gif"
        qs = urllib.urlencode(dict(url=self.get_url(path), w=1, h=1))
        resp = self.fetch_error(415, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), FormatError.get_code())

    def test_valid(self):
        cases = self.get_image_resize_cases()
        for case in cases:
            qs = urllib.urlencode(case["source_query_params"])
            resp = self.fetch_success("/?%s" % qs)
            msg = "/?%s does not match %s" \
                % (qs, case["expected_path"])
            with open(case["expected_path"]) as expected:
                self.assertEqual(resp.buffer.getvalue(), expected.read(), msg)


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
        self.assertEqual(resp.get("error_code"), ClientError.get_code())

    def test_bad_client_name(self):
        params = dict(url="http://foo.co/x.jpg", w=1, h=1, client="123")
        qs = sign(self.KEY, urllib.urlencode(params))
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), ClientError.get_code())

    def test_missing_signature(self):
        params = dict(url="http://foo.co/x.jpg", w=1, h=1, client=self.NAME)
        qs = urllib.urlencode(params)
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), SignatureError.get_code())

    def test_bad_signature(self):
        params = dict(url="http://foo.co/x.jpg", w=1, h=1,
                      client=self.NAME, sig="abc123")
        qs = urllib.urlencode(params)
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), SignatureError.get_code())

    def test_bad_host(self):
        params = dict(url="http://bar.co/x.jpg", w=1, h=1, client=self.NAME)
        qs = sign(self.KEY, urllib.urlencode(params))
        resp = self.fetch_error(403, "/?%s" % qs)
        self.assertEqual(resp.get("error_code"), HostError.get_code())

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
                self.assertEqual(resp.buffer.getvalue(), expected.read(), msg)
