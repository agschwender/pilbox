from __future__ import absolute_import, division, print_function, \
    with_statement

import collections
import itertools
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
            [dict(source_path, expected_path, width, height, mode, bg), ...]
        """
        params = []

        sizes = [(400, 300), (300, 300), (100, 200)]
        for a in list(itertools.product(*[Image.MODES, sizes])):
            params.append(dict(mode=a[0], width=a[1][0], height=a[1][1]))

        fill_choices = [["fill"], [(100, 100)], ["F00", "cccccc"]]
        for a in list(itertools.product(*fill_choices)):
            params.append(dict(mode=a[0], width=a[1][0], height=a[1][1],
                               bg=a[2]))

        crop_choices = [["crop"], [(100, 100)], Image.POSITIONS]
        for a in list(itertools.product(*crop_choices)):
            params.append(dict(mode=a[0], width=a[1][0], height=a[1][1],
                               pos=a[2]))

        cases = []
        for filename in os.listdir(DATADIR):
            m = re.match(r"^test(\d+)\.([^\.]+)$", filename)
            if not m:
                continue
            for p in params:
                case = dict(source_path=os.path.join(DATADIR, filename))
                case.update(p)
                if p.get("bg", None):
                    expected = "test%d-%dx%d-%s-%s.%s" \
                        % (int(m.group(1)), p["width"], p["height"], p["mode"],
                           p["bg"], m.group(2))
                elif p.get("pos", None):
                    expected = "test%d-%dx%d-%s-%s.%s" \
                        % (int(m.group(1)), p["width"], p["height"], p["mode"],
                           p["pos"], m.group(2))
                else:
                    expected = "test%d-%dx%d-%s.%s" \
                        % (int(m.group(1)), p["width"], p["height"], p["mode"],
                           m.group(2))
                case["expected_path"] = os.path.join(EXPECTED_DATADIR, expected)
                cases.append(case)

        return cases

    def test_resize(self):
        cases = ImageTest.get_image_resize_cases()
        if not cases:
            self.fail("no valid images for testing")

        for case in cases:
            with open(case["source_path"]) as f:
                img = Image(f).resize(
                    case["width"], case["height"], mode=case["mode"],
                    bg=case.get("bg", None), pos=case.get("pos", None))
                with open(case["expected_path"]) as expected:
                    msg = "%s does not match %s" \
                        % (case["source_path"], case["expected_path"])
                    self.assertEqual(img.read(), expected.read(), msg)

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
