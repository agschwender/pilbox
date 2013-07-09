from __future__ import absolute_import, division, print_function, with_statement

import cStringIO
import os
import os.path
import re
from tornado.test.util import unittest
from ..image import Image, ImageFormatError, ImageModeError


DATADIR = os.path.join(os.path.dirname(__file__), "data")
EXPECTED_DATADIR = os.path.join(DATADIR, "expected")

class ImageTest(unittest.TestCase):

    @staticmethod
    def get_image_resize_cases():
        """Returns a list of test cases of the form:
            [dict(source_path, expected_path, width, height, mode), ...]
        """
        cases = []
        for filename in os.listdir(EXPECTED_DATADIR):
            m = re.match(r"^(.*)\-(\d+)x(\d+)\-([a-z]+)\.(.*)$", filename)
            if not m:
                continue
            source_filename = "%s.%s" % m.group(1, 5)
            cases.append(
                dict(source_path=os.path.join(DATADIR, source_filename),
                     expected_path=os.path.join(EXPECTED_DATADIR, filename),
                     width=m.group(2),
                     height=m.group(3),
                     mode=m.group(4))
                )
        return cases

    def test_resize(self):
        cases = ImageTest.get_image_resize_cases()
        if not cases:
            self.fail("no valid images for testing")

        for case in cases:
            with open(case["source_path"]) as f:
                img = Image(f).resize(
                    case["width"], case["height"], mode=case["mode"])
                with open(case["expected_path"]) as expected:
                    self.assertEqual(img.read(), expected.read())

    def test_bad_format(self):
        path = os.path.join(DATADIR, "test-bad-format.gif")
        with open(path) as f:
            image = Image(f)
            self.assertRaises(ImageFormatError, image.resize, 100, 100)

    def test_bad_mode(self):
        path = os.path.join(DATADIR, "test1.jpg")
        with open(path) as f:
            image = Image(f)
            self.assertRaises(
                ImageModeError, image.resize, 100, 100, mode="foo")
