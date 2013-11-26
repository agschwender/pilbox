from __future__ import absolute_import, division, print_function, \
    with_statement

import collections
import itertools
import os
import os.path
import re

from tornado.test.util import unittest

from pilbox.errors import BackgroundError, DimensionsError, FilterError, \
    FormatError, ModeError, PositionError, QualityError, ImageFormatError
from pilbox.image import Image, color_hex_to_dec_tuple

try:
    import cv
except ImportError:
    cv = None

try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO


DATADIR = os.path.join(os.path.dirname(__file__), "data")
EXPECTED_DATADIR = os.path.join(DATADIR, "expected")

def get_image_resize_cases():
    """Returns a list of test cases of the form:
    [dict(source_path, expected_path, width, height, mode, ...), ...]
    """
    cases = []
    for filename in os.listdir(DATADIR):
        if not re.match(r"^test\d+\.[^\.]+$", filename):
            continue
        for criteria in _get_simple_criteria_combinations():
            cases.append(_criteria_to_resize_case(filename, criteria))

    for criteria in _get_advanced_criteria_combinations():
        cases.append(_criteria_to_resize_case("test-advanced.jpg", criteria))

    for criteria in _get_example_criteria_combinations():
        cases.append(_criteria_to_resize_case("example.jpg", criteria))

    for criteria in _get_transparent_criteria_combinations():
        cases.append(_criteria_to_resize_case("test2.png", criteria))

    return list(filter(bool, cases))


class ImageTest(unittest.TestCase):

    def test_resize(self):
        for case in get_image_resize_cases():
            if case.get("mode") == "crop" and case.get("position") == "face":
                continue
            self._assert_expected_resize(case)

    def test_resize_using_settings(self):
        for case in get_image_resize_cases():
            if case.get("mode") == "crop" and case.get("position") == "face":
                continue
            with open(case["source_path"], "rb") as f:
                img = Image(f, case).resize(
                    case["width"], case["height"], mode=case["mode"])
                with open(case["expected_path"], "rb") as expected:
                    msg = "%s does not match %s" \
                        % (case["source_path"], case["expected_path"])
                    self.assertEqual(img.read(), expected.read(), msg)

    @unittest.skipIf(cv is None, "OpenCV is not installed")
    def test_face_crop_resize(self):
        for case in get_image_resize_cases():
            if case.get("mode") == "crop" and case.get("position") == "face":
                self._assert_expected_resize(case)

    def test_valid_dimensions(self):
        Image.validate_dimensions(100, 100)
        Image.validate_dimensions("100", "100")

    def test_invalid_dimensions_none(self):
        self.assertRaises(
            DimensionsError, Image.validate_dimensions, None, None)
        self.assertRaises(
            DimensionsError, Image.validate_dimensions, "", "")

    def test_invalid_dimensions_not_integer(self):
        self.assertRaises(
            DimensionsError, Image.validate_dimensions, "a", 100)
        self.assertRaises(
            DimensionsError, Image.validate_dimensions, 100, "a")

    def test_valid_default_options(self):
        Image.validate_options(dict())

    def test_valid_default_options_with_empty_values(self):
        opts = dict(mode=None, filter=None, background=None, position=None,
                    quality=None)
        Image.validate_options(opts)

    def test_bad_image_format(self):
        path = os.path.join(DATADIR, "test-bad-format.gif")
        with open(path, "rb") as f:
            image = Image(f)
            self.assertRaises(ImageFormatError, image.resize, 100, 100)

    def test_bad_mode(self):
        self.assertRaises(
            ModeError, Image.validate_options, dict(mode="foo"))

    def test_bad_filter(self):
        self.assertRaises(
            FilterError, Image.validate_options, dict(filter="foo"))

    def test_bad_format(self):
        self.assertRaises(
            FormatError, Image.validate_options, dict(format="foo"))

    def test_bad_background_invalid_number(self):
        self.assertRaises(
            BackgroundError, Image.validate_options, dict(background="foo"))

    def test_bad_background_wrong_length(self):
        self.assertRaises(
            BackgroundError, Image.validate_options, dict(background="0f"))
        self.assertRaises(
            BackgroundError, Image.validate_options, dict(background="0f0f0"))
        self.assertRaises(BackgroundError,
                          Image.validate_options,
                          dict(background="0f0f0f0f0"))

    def test_bad_position(self):
        self.assertRaises(
            PositionError, Image.validate_options, dict(position="foo"))

    def test_bad_quality_invalid_number(self):
        self.assertRaises(
            QualityError, Image.validate_options, dict(quality="foo"))

    def test_bad_quality_invalid_range(self):
        self.assertRaises(
            QualityError, Image.validate_options, dict(quality=101))
        self.assertRaises(
            QualityError, Image.validate_options, dict(quality=-1))

    def test_color_hex_to_dec_tuple(self):
        tests  = [["fff", (255, 255, 255)],
                  ["ccc", (204, 204, 204)],
                  ["abc", (170, 187, 204)],
                  ["ffffff", (255, 255, 255)],
                  ["cccccc", (204, 204, 204)],
                  ["abcdef", (171, 205, 239)],
                  ["fabc", (170, 187, 204, 255)],
                  ["0abc", (170, 187, 204, 0)],
                  ["8abc", (170, 187, 204, 136)],
                  ["80abcdef", (171, 205, 239, 128)],
                  ["ffabcdef", (171, 205, 239, 255)],
                  ["00abcdef", (171, 205, 239, 0)]]
        for test in tests:
            self.assertTupleEqual(color_hex_to_dec_tuple(test[0]), test[1])

    def test_invalid_color_hex_to_dec_tuple(self):
        for color in ["9", "99", "99999", "9999999", "999999999"]:
            self.assertRaises(AssertionError, color_hex_to_dec_tuple, color)

    def _assert_expected_resize(self, case):
        with open(case["source_path"], "rb") as f:
            img = Image(f).resize(
                case["width"], case["height"], mode=case["mode"],
                background=case.get("background"),
                filter=case.get("filter"),
                format=case.get("format"),
                position=case.get("position"),
                quality=case.get("quality"))
            with open(case["expected_path"], "rb") as expected:
                msg = "%s does not match %s" \
                    % (case["source_path"], case["expected_path"])
                self.assertEqual(img.read(), expected.read(), msg)



def _get_simple_criteria_combinations():
    return _make_combinations(
        [dict(values=[Image.MODES, [(400, 300), (300, 300), (100, 200)]],
              fields=["mode", "size"]),
         dict(values=[["crop"], [(200, 100)], ["center", "face"]],
              fields=["mode", "size", "position"])])


def _get_example_criteria_combinations():
    return [dict(mode="clip", width=500, height=400),
            dict(mode="crop", width=500, height=400),
            dict(mode="fill", width=500, height=400, background="ccc"),
            dict(mode="scale", width=500, height=400)]


def _get_advanced_criteria_combinations():
    return _make_combinations(
        [dict(values=[["fill"], [(125, 75)], ["F00", "cccccc"]],
              fields=["mode", "size", "background"]),
         dict(values=[["crop"], [(125, 75)], Image.POSITIONS],
              fields=["mode", "size", "position"]),
         dict(values=[["crop"], [(125, 75)], ["0.25,0.75", "0.25,0.25"]],
              fields=["mode", "size", "position"]),
         dict(values=[["crop"], [(125, 75)], Image.FILTERS],
              fields=["mode", "size", "filter"]),
         dict(values=[["crop"], [(125, 75)], [50, 75, 90]],
              fields=["mode", "size", "quality"]),
         dict(values=[Image.MODES, [(125, None), (None, 125)]],
              fields=["mode", "size"]),
         dict(values=[["crop"], [(125, 75)], Image.FORMATS],
              fields=["mode", "size", "format"])])


def _get_transparent_criteria_combinations():
    return _make_combinations(
        [dict(values=[["fill"], [(75, 125)], ["1ccc", "a0cccccc"]],
              fields=["mode", "size", "background"])])


def _make_combinations(choices):
    combos = []
    for choice in choices:
        for a in list(itertools.product(*choice["values"])):
            combo = dict(zip(choice["fields"], a))
            combo["width"] = combo["size"][0]
            combo["height"] = combo["size"][1]
            del combo["size"]
            combos.append(combo)
    return combos


def _criteria_to_resize_case(filename, criteria):
    m = re.match(r"^([^\.]+)\.([^\.]+)$", filename)
    if not m:
        return None
    case = dict(source_path=os.path.join(DATADIR, filename))
    case.update(criteria)
    fields = ["mode", "filter", "quality", "background", "position"]
    opts = filter(bool, [criteria.get(x) for x in fields])
    expected = "%s-%sx%s%s.%s" \
        % (m.group(1),
           criteria.get("width") or "",
           criteria.get("height") or "",
           ("-%s" % "-".join([str(x) for x in opts])) if opts else "",
           criteria.get("format") or m.group(2))
    case["expected_path"] = os.path.join(EXPECTED_DATADIR, expected)
    return case
