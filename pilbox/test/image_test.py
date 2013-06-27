from __future__ import absolute_import, division, print_function, with_statement

import cStringIO
import os
import os.path
from pilbox.image import Image, ImageFormatError, ImageModeError
from tornado.test.util import unittest

class ImageTest(unittest.TestCase):
    DATADIR = os.path.join(os.path.dirname(__file__), "data")

    def test_resize(self):
        num_valid = 0
        for filename in os.listdir(self.DATADIR):
            path = os.path.join(self.DATADIR, filename)
            if not os.path.isfile(path):
                continue
            ext = path.rpartition(".")[2].upper()
            if ext not in Image.FORMATS:
                continue
            self._test_resize_all_combinations(path)
            num_valid += 1

        if num_valid == 0:
            self.fail("no valid image formats")


    def test_bad_format(self):
        path = os.path.join(self.DATADIR, "test-bad-format.gif")
        with open(path) as f:
            image = Image(f)
            self.assertRaises(ImageFormatError, image.resize, 100, 100)

    def test_bad_mode(self):
        path = os.path.join(self.DATADIR, "test1.jpg")
        with open(path) as f:
            image = Image(f)
            self.assertRaises(
                ImageModeError, image.resize, 100, 100, mode="foo")

    def _test_resize_all_combinations(self, path):
        sizes = [(300, 300), (400, 300)]
        for mode in Image.MODES:
            for size in sizes:
                self._test_resize_one(path, size[0], size[1], mode)

    def _test_resize_one(self, path, width, height, mode):
        with open(path) as f:
            img = Image(f).resize(width, height, mode=mode)
            base, _, ext = os.path.basename(path).rpartition(".")
            expected_path = os.path.join(
                os.path.dirname(path),
                "expected",
                "%s-%dx%d-%s.%s" % (base, width, height, mode, ext))
            with open(expected_path) as expected:
                self.assertEquals(img.read(), expected.read())
