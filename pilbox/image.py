#!/usr/bin/env python
#
# Copyright 2013 Adam Gschwender
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, \
    with_statement

import logging
import re
import os.path

import PIL.Image
import PIL.ImageOps
import tornado.httpclient

from pilbox.errors import BackgroundError, DimensionsError, FilterError, \
    FormatError, ModeError, PositionError, QualityError, ImageFormatError, AngleError

try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO

try:
    import cv
except ImportError:
    cv = None

logger = logging.getLogger("tornado.application")

_positions_to_ratios = {
    "top-left": (0.0, 0.0), "top": (0.5, 0.0), "top-right": (1.0, 0.0),
    "left": (0.0, 0.5), "center": (0.5, 0.5), "right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0), "bottom": (0.5, 1.0), "bottom-right": (1.0, 1.0),
    "face": None
    }

_filters_to_pil = {
    "antialias": PIL.Image.ANTIALIAS,
    "bicubic": PIL.Image.BICUBIC,
    "bilinear": PIL.Image.BILINEAR,
    "nearest": PIL.Image.NEAREST
    }

_formats_to_pil = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP"
}

class Image(object):
    FILTERS = _filters_to_pil.keys()
    FORMATS = _formats_to_pil.keys()
    MODES = ["clip", "crop", "fill", "scale"]
    POSITIONS = _positions_to_ratios.keys()

    _DEFAULTS = dict(background="fff", filter="antialias", format=None,
                     mode="crop", position="center", quality=90)
    _CLASSIFIER_PATH = os.path.join(
        os.path.dirname(__file__), "..", "config", "frontalface.xml")

    def __init__(self, stream, defaults=None):
        self.stream = stream

        # check for defaults and set, to avoid mutable default parameter.
        if not defaults:
            defaults = {}

        self.defaults = Image._normalize_options(defaults)

    @staticmethod
    def validate_dimensions(width, height):
        if not width and not height:
            raise DimensionsError("Missing dimensions")
        elif width and not str(width).isdigit():
            raise DimensionsError("Invalid width: %s" % width)
        elif height and not str(height).isdigit():
            raise DimensionsError("Invalid height: %s" % height)

    @staticmethod
    def validate_angle(angle):
        if not angle:
            raise AngleError("Missing angle")
        elif angle and not Image._isfloat(angle):
            raise AngleError("Invalid angle: %s" % angle)

    @staticmethod
    def validate_options(opts):
        opts = Image._normalize_options(opts)
        if opts["mode"] not in Image.MODES:
            raise ModeError("Invalid mode: %s" % opts["mode"])
        elif opts["filter"] not in Image.FILTERS:
            raise FilterError("Invalid filter: %s" % opts["filter"])
        elif opts["format"] and opts["format"] not in Image.FORMATS:
            raise FormatError("Invalid format: %s" % opts["format"])
        elif opts["position"] not in Image.POSITIONS \
             and not opts["pil"]["position"]:
            raise PositionError("Invalid position: %s" % opts["position"])
        elif opts["pil"]["position"] \
             and (opts["pil"]["position"][0] < 0.0
                  or opts["pil"]["position"][0] > 1.0
                  or opts["pil"]["position"][1] < 0.0
                  or opts["pil"]["position"][1] > 1.0):
            raise PositionError("Invalid position ratio: %s" % opts["position"])
        elif not Image._isint(opts["background"], 16) \
                or len(opts["background"]) not in [3, 4, 6, 8]:
            raise BackgroundError("Invalid background: %s" % opts["background"])
        elif not Image._isint(opts["quality"]) \
                or int(opts["quality"]) > 100 or int(opts["quality"]) < 0:
            raise QualityError("Invalid quality: %s", str(opts["quality"]))

    def resize(self, width, height, **kwargs):
        """Returns a buffer to the resized image for saving, supports the
        following optional keyword arguments:

        mode - The resizing mode to use, see Image.MODES
        filter - The filter to use: see Image.FILTERS
        format - The format to save as: see Image.FORMATS
        background - The hexadecimal background fill color, RGB or ARGB
        position - The position used to crop: see Image.POSITIONS for
                   pre-defined positions or a custom position ratio
        quality - The quality used to save JPEGs: integer from 1 - 100
        """
        img = PIL.Image.open(self.stream)
        if img.format.lower() not in self.FORMATS:
            raise ImageFormatError("Unknown format: %s" % img.format)

        opts = Image._normalize_options(kwargs, self.defaults)
        resized = self._resize(img, self._get_size(img, width, height), opts)
        outfile = BytesIO()
        format_ = opts["pil"]["format"] if opts["pil"]["format"] else img.format
        resized.save(outfile, format_, quality=int(opts["quality"]))
        outfile.seek(0)
        return outfile

    def rotate(self, angle, **kwargs):
        """ Returns a buffer to the rotated (clockwise around its centre) image for saving.
        Supports the following optional keyword arguments:

        quality - The quality used to save JPEGs: integer from 1 - 100
        """
        img = PIL.Image.open(self.stream)
        if img.format.lower() not in self.FORMATS:
            raise ImageFormatError("Unknown format: %s" % img.format)

        opts = Image._normalize_options(kwargs, self.defaults)

        # use bicubic resample as default, can be changed in the future.
        rotated = img.rotate(float(angle), resample=_filters_to_pil["bicubic"], expand=1)

        outfile = BytesIO()
        rotated.save(outfile, img.format, quality=int(opts["quality"]))
        outfile.seek(0)

        return outfile

    def _resize(self, image, size, opts):
        if opts["mode"] == "clip":
            return self._clip(image, size, opts)
        elif opts["mode"] == "fill":
            return self._fill(image, size, opts)
        elif opts["mode"] == "scale":
            return self._scale(image, size, opts)
        else:
            return self._crop(image, size, opts)

    def _clip(self, image, size, opts):
        image.thumbnail(size, opts["pil"]["filter"])
        return image

    def _crop(self, image, size, opts):
        if opts["position"] == "face":
            if cv is None:
                raise NotImplementedError
            else:
                pos = self._get_face_position(image)
        else:
            pos = opts["pil"]["position"]
        return PIL.ImageOps.fit(image, size, opts["pil"]["filter"], 0, pos)

    def _fill(self, image, size, opts):
        clipped = self._clip(image, size, opts)
        if clipped.size == size:
            return clipped # No need to fill
        x = max(int((size[0] - clipped.size[0]) / 2.0), 0)
        y = max(int((size[1] - clipped.size[1]) / 2.0), 0)
        color = color_hex_to_dec_tuple(opts["background"])
        mode = "RGBA" if len(color) == 4 else "RGB"
        img = PIL.Image.new(mode=mode, size=size, color=color)
        img.paste(clipped, (x, y))
        return img

    def _scale(self, image, size, opts):
        return image.resize(size, opts["pil"]["filter"])

    def _get_size(self, image, width, height):
        aspect_ratio = image.size[0] / image.size[1]
        if not width:
            width = int((int(height) or image.size[1]) * aspect_ratio)
        if not height:
            height = int((int(width) or image.size[0]) / aspect_ratio)
        return (int(width), int(height))

    def _get_face_rectangles(self, image):
        cvim = self._pil_to_opencv(image)
        return cv.HaarDetectObjects(
            cvim,
            self._get_face_classifier(),
            cv.CreateMemStorage(0),
            1.3,  # Scale factor
            4,  # Minimum neighbors
            0,  # HAAR Flags
            (20, 20))

    def _get_face_position(self, image):
        rects = self._get_face_rectangles(image)
        if not rects:
            return (0.5, 0.5)
        xt, yt = (0.0, 0.0)
        for rect in rects:
            xt += rect[0][0] + (rect[0][2] / 2.0)
            yt += rect[0][1] + (rect[0][3] / 2.0)

        return (xt / (len(rects) * image.size[0]),
                yt / (len(rects) * image.size[1]))

    def _get_face_classifier(self):
        if not hasattr(Image, "_classifier"):
            Image._classifier = cv.Load(os.path.abspath(Image._CLASSIFIER_PATH))
        return Image._classifier

    def _pil_to_opencv(self, pi):
        mono = pi.convert("L")
        cvim = cv.CreateImageHeader(mono.size, cv.IPL_DEPTH_8U, 1)
        cv.SetData(cvim, mono.tostring(), mono.size[0])
        cv.EqualizeHist(cvim, cvim)
        return cvim

    @staticmethod
    def _normalize_options(options, defaults=None):
        if not defaults:
            defaults = Image._DEFAULTS
        opts = defaults.copy()
        opts.update(dict([(k,v) for k,v in options.items() if v]))
        opts["pil"] = dict(
            filter=_filters_to_pil.get(opts["filter"]),
            format=_formats_to_pil.get(opts["format"], None),
            position=Image._get_custom_position(opts["position"]))

        if not opts["pil"]["position"]:
            opts["pil"]["position"] = _positions_to_ratios.get(
                opts["position"], None)

        return opts

    @staticmethod
    def _get_custom_position(pos):
        m = re.match(r'^(\d+(\.\d+)?),(\d+(\.\d+)?)$', pos)
        if not m:
            return None
        return (float(m.group(1)), float(m.group(3)))

    @staticmethod
    def _isint(v, base=10):
        try:
            int(str(v), base)
        except ValueError:
            return False
        return True

    @staticmethod
    def _isfloat(v):
        try:
            float(v)
        except ValueError:
            return False
        return True


def color_hex_to_dec_tuple(color):
    """Converts a color from hexadecimal to decimal tuple, color can be in
    the following formats: 3-digit RGB, 4-digit ARGB, 6-digit RGB and
    8-digit ARGB.
    """
    assert len(color) in [3, 4, 6, 8]
    if len(color) in [3, 4]:
        color = "".join([c*2 for c in color])
    n = int(color, 16)
    t = ((n >> 16) & 255, (n >> 8) & 255, n & 255)
    if len(color) == 8:
        t = t + ((n >> 24) & 255,)
    return t


def main():
    import sys
    import tornado.options
    from tornado.options import define, options, parse_command_line

    define("width", help="the desired image width", type=int)
    define("height", help="the desired image height", type=int)
    define("mode", help="the resizing mode",
           metavar="|".join(Image.MODES), type=str)
    define("background", help="the hexidecimal fill background color", type=str)
    define("position", help="the crop position",
           metavar="|".join(Image.POSITIONS), type=str)
    define("filter", help="default filter to use when resizing",
           metavar="|".join(Image.FILTERS), type=str)
    define("format", help="default format to use when saving",
           metavar="|".join(Image.FORMATS), type=str)
    define("quality", help="default jpeg quality, 0-100", type=int)

    args = parse_command_line()
    if not options.width and not options.height:
        tornado.options.print_help()
        sys.exit()
    elif not args:
        print("Missing image source url")
        sys.exit()

    if args[0].startswith("http://") or args[0].startswith("https://"):
        client = tornado.httpclient.HTTPClient()
        resp = client.fetch(args[0])
        image = Image(resp.buffer)
    else:
        image = Image(open(args[0], "r"))
    stream = image.resize(options.width, options.height, mode=options.mode,
                          filter=options.filter, background=options.background,
                          position=options.position, quality=options.quality)
    sys.stdout.write(stream.read())
    stream.close()


if __name__ == "__main__":
    main()
