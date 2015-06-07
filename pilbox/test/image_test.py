from __future__ import absolute_import, division, with_statement

import itertools
import os
import os.path
import re

import PIL.Image
from tornado.test.util import unittest

from pilbox import errors
from pilbox.image import color_hex_to_dec_tuple, Image

try:
    import cv
except ImportError:
    cv = None


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

    cases.append(_criteria_to_resize_case(
        "test space.jpg", _get_simple_criteria_combinations()[0]))

    for criteria in _get_advanced_criteria_combinations():
        cases.append(_criteria_to_resize_case("test-advanced.jpg", criteria))

    for criteria in _get_example_criteria_combinations():
        cases.append(_criteria_to_resize_case("example.jpg", criteria))

    for criteria in _get_transparent_criteria_combinations():
        cases.append(_criteria_to_resize_case("test2.png", criteria))

    return list(filter(bool, cases))


def get_image_rotate_cases():
    """Returns a list of test cases of the form:
    [dict(source_path, expected_path, degree, expand, ...), ...]
    """
    criteria_combinations = _make_combinations(
        [dict(values=[[90, 180, 315], [1, 0]],
              fields=["degree", "expand"])])

    cases = []
    for criteria in criteria_combinations:
        cases.append(_criteria_to_rotate_case("test1.jpg", criteria))


    criteria_combinations = _make_combinations(
        [dict(values=[["auto"], [0]], fields=["degree", "expand"])])

    for criteria in criteria_combinations:
        cases.append(_criteria_to_rotate_case("test-orientation.jpg", criteria))
        cases.append(_criteria_to_rotate_case("test-bad-exif.jpg", criteria))
        cases.append(_criteria_to_rotate_case("test1.jpg", criteria))
        cases.append(_criteria_to_rotate_case("test2.png", criteria))

    return list(filter(bool, cases))


def get_image_region_cases():
    """Returns a list of test cases of the form:
    [dict(source_path, expected_path, rect, ...), ...]
    """
    criteria_combinations = _make_combinations(
        [dict(values=[["150,150,100,100", "200,175,50,50"]],
              fields=["rect"])])

    cases = []
    for criteria in criteria_combinations:
        cases.append(_criteria_to_region_case("test1.jpg", criteria))

    return list(filter(bool, cases))


def get_image_chained_cases():
    """Returns a list of test cases of the form:
    [dict(source_path, expected_path, operation, size, ...), ...]
    """
    criteria_combinations = _make_combinations(
        [dict(values=[[("resize", "rotate"), ("rotate", "resize")],
                      [(150, 75), (75, 150)],
                      [90]],
              fields=["operation", "size", "degree"]),
         dict(values=[[("resize", "region", "rotate")],
                     [(150, 75), (75, 150)],
                     ["5,5,65,65"],
                     [90]],
              fields=["operation", "size", "rect", "degree"]),
         dict(values=[[("region", "resize", "rotate")],
                     [(150, 75), (75, 150)],
                     ["50,50,150,150"],
                     [90]],
              fields=["operation", "size", "rect", "degree"])])

    cases = []
    for criteria in criteria_combinations:
        cases.append(_criteria_to_chained_case("test1.jpg", criteria))

    return list(filter(bool, cases))


def get_image_exif_cases():
    """Returns a list of test cases of the form:
    [dict(source_path, expected_path, preserve_exif, ...), ...]
    """
    criteria_combinations = _make_combinations(
        [dict(values=[[1, 0], [300], [300]],
              fields=["preserve_exif", "width", "height"])])

    cases = []
    for criteria in criteria_combinations:
        cases.append(_criteria_to_exif_case("test-orientation.jpg", criteria))

    return list(filter(bool, cases))


class ImageTest(unittest.TestCase):

    def test_resize(self):
        for case in get_image_resize_cases():
            if case.get("mode") == "crop" and case.get("position") == "face":
                continue
            self._assert_expected_resize(case)

    def test_rotate(self):
        for case in get_image_rotate_cases():
            self._assert_expected_rotate(case)

    def test_region(self):
        for case in get_image_region_cases():
            self._assert_expected_region(case)

    def test_chained(self):
        for case in get_image_chained_cases():
            self._assert_expected_chained(case)

    def test_exif(self):
        for case in get_image_exif_cases():
            self._assert_expected_exif(case)

    @unittest.skipIf(cv is None, "OpenCV is not installed")
    def test_face_crop_resize(self):
        for case in get_image_resize_cases():
            if case.get("mode") == "crop" and case.get("position") == "face":
                self._assert_expected_resize(case)

    def test_valid_degree(self):
        for deg in [0, 90, "90", 45, "45", 300, 359]:
            Image.validate_degree(deg)

    def test_invalid_degree(self):
        for deg in [None, "a", "", 45.34, "93.20", -2, 360]:
            self.assertRaises(errors.DegreeError, Image.validate_degree, deg)

    def test_valid_dimensions(self):
        Image.validate_dimensions(100, 100)
        Image.validate_dimensions("100", "100")

    def test_invalid_dimensions_none(self):
        self.assertRaises(
            errors.DimensionsError, Image.validate_dimensions, None, None)
        self.assertRaises(
            errors.DimensionsError, Image.validate_dimensions, "", "")

    def test_invalid_dimensions_not_integer(self):
        self.assertRaises(
            errors.DimensionsError, Image.validate_dimensions, "a", 100)
        self.assertRaises(
            errors.DimensionsError, Image.validate_dimensions, 100, "a")

    def test_valid_rectangle(self):
        Image.validate_rectangle("100,100,200,200")
        Image.validate_rectangle("100,200,50,100")

    def test_invalid_rectangle(self):
        invalid_rectangles = ["", None, "100,100,200", "100,200,300,400.5",
                              "0,-1,100,100", "100,100,-100,-100"]
        for rect in invalid_rectangles:
            self.assertRaises(
                errors.RectangleError, Image.validate_rectangle, rect)

    def test_out_of_bounds_rectangle(self):
        path = os.path.join(os.path.dirname(__file__), "data", "test1.jpg")
        invalid_rectangles = ["0,0,10000,10000", "10000,10000,0,0"]
        for rect in invalid_rectangles:
            with open(path, "rb") as f:
                img = Image(f)
                self.assertRaises(
                    errors.RectangleError, img.region, rect.split(","))

    def test_valid_default_options(self):
        Image.validate_options(dict())

    def test_valid_default_options_with_empty_values(self):
        opts = dict(mode=None, filter=None, background=None, optimize=None,
                    position=None, quality=None, progressive=None,
                    preserve_exif=None)
        Image.validate_options(opts)

    def test_nonimage_file(self):
        with open(__file__, "rb") as f:
            self.assertRaises(errors.ImageFormatError, Image, f)

    def test_bad_image_format(self):
        path = os.path.join(DATADIR, "test-bad-format.ico")
        with open(path, "rb") as f:
            self.assertRaises(errors.ImageFormatError, Image, f)

    def test_bad_mode(self):
        self.assertRaises(
            errors.ModeError, Image.validate_options, dict(mode="foo"))

    def test_bad_filter(self):
        self.assertRaises(
            errors.FilterError, Image.validate_options, dict(filter="foo"))

    def test_bad_format(self):
        self.assertRaises(
            errors.FormatError, Image.validate_options, dict(format="foo"))

    def test_bad_background_invalid_number(self):
        self.assertRaises(errors.BackgroundError,
                          Image.validate_options,
                          dict(background="foo"))

    def test_bad_background_wrong_length(self):
        self.assertRaises(errors.BackgroundError,
                          Image.validate_options,
                          dict(background="0f"))
        self.assertRaises(errors.BackgroundError,
                          Image.validate_options,
                          dict(background="0f0f0"))
        self.assertRaises(errors.BackgroundError,
                          Image.validate_options,
                          dict(background="0f0f0f0f0"))

    def test_bad_position(self):
        self.assertRaises(
            errors.PositionError, Image.validate_options, dict(position="foo"))

    def test_bad_position_ratio(self):
        self.assertRaises(errors.PositionError,
                          Image.validate_options,
                          dict(position="1.2,5.6"))

    def test_valid_position_ratio(self):
        for pos in ["0.0,0.5", "1.0,1.0", "0.111111,0.999999"]:
            Image.validate_options(dict(position=pos))

    def test_bad_quality_invalid_number(self):
        self.assertRaises(
            errors.QualityError, Image.validate_options, dict(quality="foo"))

    def test_bad_quality_invalid_range(self):
        self.assertRaises(
            errors.QualityError, Image.validate_options, dict(quality=101))
        self.assertRaises(
            errors.QualityError, Image.validate_options, dict(quality=-1))

    def test_bad_optimize_invalid_bool(self):
        self.assertRaises(
            errors.OptimizeError, Image.validate_options, dict(optimize="b"))

    def test_bad_preserve_exif_invalid_bool(self):
        self.assertRaises(errors.PreserveExifError,
                          Image.validate_options,
                          dict(preserve_exif="b"))

    def test_bad_progressive_invalid_bool(self):
        self.assertRaises(errors.ProgressiveError,
                          Image.validate_options,
                          dict(progressive="b"))

    def test_bad_retain_invalid_range(self):
        self.assertRaises(
            errors.RetainError, Image.validate_options, dict(retain=101))
        self.assertRaises(
            errors.RetainError, Image.validate_options, dict(retain=-1))

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

    def test_save_failure(self):
        img = Image(os.path.join(DATADIR, 'test5.gif'))
        self.assertRaises(errors.ImageSaveError,
                          lambda: img.save(format="webp"))

    def _assert_expected_resize(self, case):
        with open(case["source_path"], "rb") as f:
            img = Image(f).resize(
                case["width"], case["height"], mode=case["mode"],
                background=case.get("background"), filter=case.get("filter"),
                position=case.get("position"), retain=case.get("retain"))
            rv = img.save(
                format=case.get("format"),
                optimize=case.get("optimize"),
                progressive=case.get("progressive"),
                quality=case.get("quality"))

            with open(case["expected_path"], "rb") as expected:
                msg = "%s does not match %s" \
                    % (case["source_path"], case["expected_path"])
                self.assertEqual(rv.read(), expected.read(), msg)

    def _assert_expected_rotate(self, case):
        with open(case["source_path"], "rb") as f:

            img = Image(f).rotate(
                case["degree"], expand=case.get("expand"),
                filter=case.get("filter"))
            rv = img.save(
                format=case.get("format"),
                optimize=case.get("optimize"),
                progressive=case.get("progressive"),
                quality=case.get("quality"))

            with open(case["expected_path"], "rb") as expected:
                msg = "%s does not match %s" \
                    % (case["source_path"], case["expected_path"])
                self.assertEqual(rv.read(), expected.read(), msg)

    def _assert_expected_region(self, case):
        with open(case["source_path"], "rb") as f:
            img = Image(f).region(case["rect"].split(","))
            rv = img.save(
                format=case.get("format"),
                optimize=case.get("optimize"),
                progressive=case.get("progressive"),
                quality=case.get("quality"))

            with open(case["expected_path"], "rb") as expected:
                msg = "%s does not match %s" \
                    % (case["source_path"], case["expected_path"])
                self.assertEqual(rv.read(), expected.read(), msg)

    def _assert_expected_chained(self, case):
        with open(case["source_path"], "rb") as f:

            img = Image(f)
            for operation in case["operation"]:
                if operation == "resize":
                    img.resize(case["width"], case["height"])
                elif operation == "rotate":
                    img.rotate(case["degree"])
                elif operation == "region":
                    img.region(case["rect"].split(","))

            rv = img.save()

            with open(case["expected_path"], "rb") as expected:
                msg = "%s does not match %s" \
                    % (case["source_path"], case["expected_path"])
                self.assertEqual(rv.read(), expected.read(), msg)

    def _assert_expected_exif(self, case):
        with open(case["source_path"], "rb") as f:
            img = Image(f).resize(case["width"], case["height"])
            rv = img.save(preserve_exif=case['preserve_exif'])

            with open(case["expected_path"], "rb") as expected:
                msg = "%s does not match %s" \
                    % (case["source_path"], case["expected_path"])
                self.assertEqual(rv.read(), expected.read(), msg)


def _get_simple_criteria_combinations():
    return _make_combinations(
        [dict(values=[Image.MODES, [(400, 300), (300, 300), (100, 200)]],
              fields=["mode", "size"]),
         dict(values=[["crop"], [(200, 100)], ["center", "face"]],
              fields=["mode", "size", "position"])])


def _get_example_criteria_combinations():
    return [dict(mode="adapt", width=500, height=400, retain=80),
            dict(mode="adapt", width=500, height=400, retain=99,
                 background="ccc"),
            dict(mode="clip", width=500, height=400),
            dict(mode="crop", width=500, height=400),
            dict(mode="fill", width=500, height=400, background="ccc"),
            dict(mode="scale", width=500, height=400)]


def _get_advanced_criteria_combinations():
    return _make_combinations(
        [dict(values=[["adapt"], [(125, 75)], [99, 80, 60, 40]],
              fields=["mode", "size", "retain"]),
         dict(values=[["fill"], [(125, 75)], ["F00", "cccccc"]],
              fields=["mode", "size", "background"]),
         dict(values=[["crop"], [(125, 75)], Image.POSITIONS],
              fields=["mode", "size", "position"]),
         dict(values=[["crop"], [(125, 75)], ["0.25,0.75", "0.25,0.25"]],
              fields=["mode", "size", "position"]),
         dict(values=[["crop"], [(125, 75)], Image.FILTERS],
              fields=["mode", "size", "filter"]),
         dict(values=[["crop"], [(125, 75)], [50, 75, 90, "keep"]],
              fields=["mode", "size", "quality"]),
         dict(values=[["crop"], [(125, 75)], [1, 0]],
              fields=["mode", "size", "optimize"]),
         dict(values=[["crop"], [(125, 75)], [1, 0]],
              fields=["mode", "size", "progressive"]),
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
            if "size" in combo:
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
    fields = ["mode", "filter", "quality", "background",
              "position", "optimize", "progressive", "retain"]
    opts_desc = "-".join(["%s=%s" % (x, str(criteria.get(x)))
                          for x in fields if criteria.get(x)])
    expected = "%s-%sx%s%s.%s" \
        % (m.group(1),
           criteria.get("width") or "",
           criteria.get("height") or "",
           ("-%s" % opts_desc) if opts_desc else "",
           criteria.get("format") or m.group(2))
    case["expected_path"] = os.path.join(EXPECTED_DATADIR, expected)
    return case


def _criteria_to_rotate_case(filename, criteria):
    m = re.match(r"^([^\.]+)\.([^\.]+)$", filename)
    if not m:
        return None
    case = dict(source_path=os.path.join(DATADIR, filename))
    case.update(criteria)
    fields = ["degree", "expand"]
    opts_desc = "-".join(["%s=%s" % (x, str(criteria.get(x)))
                          for x in fields if criteria.get(x)])
    expected = "%s-rotate%s.%s" \
        % (m.group(1),
           ("-%s" % opts_desc) if opts_desc else "",
           criteria.get("format") or m.group(2))
    case["expected_path"] = os.path.join(EXPECTED_DATADIR, expected)
    return case


def _criteria_to_region_case(filename, criteria):
    m = re.match(r"^([^\.]+)\.([^\.]+)$", filename)
    if not m:
        return None
    case = dict(source_path=os.path.join(DATADIR, filename))
    case.update(criteria)
    fields = ["rect"]
    opts_desc = "-".join(["%s=%s" % (x, str(criteria.get(x)))
                          for x in fields if criteria.get(x)])
    expected = "%s-region%s.%s" \
        % (m.group(1),
           ("-%s" % opts_desc) if opts_desc else "",
           criteria.get("format") or m.group(2))
    case["expected_path"] = os.path.join(EXPECTED_DATADIR, expected)
    return case


def _criteria_to_chained_case(filename, criteria):
    m = re.match(r"^([^\.]+)\.([^\.]+)$", filename)
    if not m:
        return None
    case = dict(source_path=os.path.join(DATADIR, filename))
    case.update(criteria)
    fields = ["degree", "rect"]
    opts_desc = "-".join(["%s=%s" % (x, str(criteria.get(x)))
                          for x in fields if criteria.get(x)])
    expected = "%s-chained-%s-%sx%s%s.%s" \
        % (m.group(1),
           ",".join(criteria.get("operation", [])),
           criteria.get("width") or "",
           criteria.get("height") or "",
           ("-%s" % opts_desc) if opts_desc else "",
           m.group(2))
    case["expected_path"] = os.path.join(EXPECTED_DATADIR, expected)
    return case


def _criteria_to_exif_case(filename, criteria):
    m = re.match(r"^([^\.]+)\.([^\.]+)$", filename)
    if not m:
        return None
    case = dict(source_path=os.path.join(DATADIR, filename))
    case.update(criteria)
    fields = ["preserve_exif"]
    opts_desc = "-".join(["%s=%s" % (x, str(criteria.get(x)))
                          for x in fields if criteria.get(x) is not None])
    expected = "%s-exif-%s.%s" \
        % (m.group(1),
           opts_desc or "",
           m.group(2))
    case["expected_path"] = os.path.join(EXPECTED_DATADIR, expected)
    return case
