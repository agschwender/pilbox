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

from pilbox import errors

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
    "bottom-left": (0.0, 1.0), "bottom": (0.5, 1.0),
    "bottom-right": (1.0, 1.0), "face": None
    }

_orientation_to_rotation = {
    3: 180,
    6: 90,
    8: 270
    }

_filters_to_pil = {
    "antialias": PIL.Image.ANTIALIAS,
    "bicubic": PIL.Image.BICUBIC,
    "bilinear": PIL.Image.BILINEAR,
    "nearest": PIL.Image.NEAREST
    }

_formats_to_pil = {
    "gif": "GIF",
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "tiff": "TIFF"
}


class Image(object):
    FILTERS = _filters_to_pil.keys()
    FORMATS = _formats_to_pil.keys()
    MODES = ["adapt", "clip", "crop", "fill", "scale"]
    POSITIONS = _positions_to_ratios.keys()

    _DEFAULTS = dict(background="fff", expand=False, filter="antialias",
                     format=None, mode="crop", optimize=False,
                     position="center", quality=90, progressive=False,
                     retain=75, preserve_exif=False)
    _CLASSIFIER_PATH = os.path.join(
        os.path.dirname(__file__), "frontalface.xml")

    def __init__(self, stream):
        self.stream = stream

        try:
            self.img = PIL.Image.open(self.stream)
        except IOError:
            raise errors.ImageFormatError("File is not an image")

        # Cache original Exif data, since it can be erased by some operations
        self._exif = self.img.info.get('exif', b'')

        if self.img.format.lower() not in self.FORMATS:
            raise errors.ImageFormatError(
                "Unknown format: %s" % self.img.format)
        self._orig_format = self.img.format

    @staticmethod
    def validate_dimensions(width, height):
        if not width and not height:
            raise errors.DimensionsError("Missing dimensions")
        elif width and not str(width).isdigit():
            raise errors.DimensionsError("Invalid width: %s" % width)
        elif height and not str(height).isdigit():
            raise errors.DimensionsError("Invalid height: %s" % height)

    @staticmethod
    def validate_degree(deg):
        if deg is None or deg == "":
            raise errors.DegreeError("Missing degree")
        elif deg == "auto":
            return
        elif not Image._isint(deg):
            raise errors.DegreeError("Invalid degree: %s" % deg)
        elif int(deg) < 0 or int(deg) >= 360:
            raise errors.DegreeError("Invalid degree: %s" % deg)

    @staticmethod
    def validate_rectangle(rect):
        if not rect:
            raise errors.RectangleError("Missing rectangle")
        rect = rect.split(",")
        if len(rect) != 4:
            raise errors.RectangleError("Invalid rectangle")
        for a in rect:
            if not Image._isint(a):
                raise errors.RectangleError("Invalid rectangle")
            elif int(a) < 0:
                raise errors.RectangleError("Region out-of-bounds")

    @staticmethod
    def validate_options(opts):
        opts = Image._normalize_options(opts)
        if opts["mode"] not in Image.MODES:
            raise errors.ModeError("Invalid mode: %s" % opts["mode"])
        elif opts["filter"] not in Image.FILTERS:
            raise errors.FilterError("Invalid filter: %s" % opts["filter"])
        elif opts["format"] and opts["format"] not in Image.FORMATS:
            raise errors.FormatError("Invalid format: %s" % opts["format"])
        elif opts["position"] not in Image.POSITIONS \
                and not opts["pil"]["position"]:
            raise errors.PositionError(
                "Invalid position: %s" % opts["position"])
        elif not Image._isint(opts["background"], 16) \
                or len(opts["background"]) not in [3, 4, 6, 8]:
            raise errors.BackgroundError(
                "Invalid background: %s" % opts["background"])
        elif opts["optimize"] and not Image._isint(opts["optimize"]):
            raise errors.OptimizeError(
                "Invalid optimize: %s", str(opts["optimize"]))
        elif opts["quality"] != "keep" and \
            (not Image._isint(opts["quality"]) or
             int(opts["quality"]) > 100 or
             int(opts["quality"]) < 0):
            raise errors.QualityError(
                "Invalid quality: %s", str(opts["quality"]))
        elif opts["preserve_exif"] and not Image._isint(opts["preserve_exif"]):
            raise errors.PreserveExifError(
                "Invalid preserve_exif: %s" % str(opts["preserve_exif"]))
        elif opts["progressive"] and not Image._isint(opts["progressive"]):
            raise errors.ProgressiveError(
                "Invalid progressive: %s", str(opts["progressive"]))
        elif (not Image._isint(opts["retain"]) or
              int(opts["retain"]) > 100 or
              int(opts["retain"]) < 0):
            raise errors.RetainError(
                "Invalid retain: %s" % str(opts["retain"]))

    def region(self, rect):
        """ Selects a sub-region of the image using the supplied rectangle,
            x, y, width, height.
        """
        box = (int(rect[0]), int(rect[1]), int(rect[0]) + int(rect[2]),
               int(rect[1]) + int(rect[3]))
        if box[2] > self.img.size[0] or box[3] > self.img.size[1]:
            raise errors.RectangleError("Region out-of-bounds")
        self.img = self.img.crop(box)
        return self

    def resize(self, width, height, **kwargs):
        """Resizes the image to the supplied width/height. Returns the
        instance. Supports the following optional keyword arguments:

        mode - The resizing mode to use, see Image.MODES
        filter - The filter to use: see Image.FILTERS
        background - The hexadecimal background fill color, RGB or ARGB
        position - The position used to crop: see Image.POSITIONS for
                   pre-defined positions or a custom position ratio
        retain - The minimum percentage of the original image to retain
                 when cropping
        """
        opts = Image._normalize_options(kwargs)
        size = self._get_size(width, height)
        if opts["mode"] == "adapt":
            self._adapt(size, opts)
        elif opts["mode"] == "clip":
            self._clip(size, opts)
        elif opts["mode"] == "fill":
            self._fill(size, opts)
        elif opts["mode"] == "scale":
            self._scale(size, opts)
        else:
            self._crop(size, opts)
        return self

    def rotate(self, deg, **kwargs):
        """ Rotates the image clockwise around its center.  Returns the
        instance. Supports the following optional keyword arguments:

        expand - Expand the output image to fit rotation
        """
        opts = Image._normalize_options(kwargs)

        if deg == "auto":
            if self._orig_format == "JPEG":
                try:
                    exif = self.img._getexif() or dict()
                    deg = _orientation_to_rotation.get(exif.get(274, 0), 0)
                except Exception:
                    logger.warn('unable to parse exif')
                    deg = 0
            else:
                deg = 0

        expand = False if int(deg) % 90 == 0 else bool(int(opts["expand"]))
        self.img = self.img.rotate(360 - int(deg), expand=expand)
        return self

    def save(self, **kwargs):
        """Returns a buffer to the image for saving, supports the
        following optional keyword arguments:

        format - The format to save as: see Image.FORMATS
        optimize - The image file size should be optimized
        preserve_exif - Preserve the Exif information in JPEGs
        progressive - The output should be progressive JPEG
        quality - The quality used to save JPEGs: integer from 1 - 100
        """
        opts = Image._normalize_options(kwargs)
        outfile = BytesIO()
        if opts["pil"]["format"]:
            fmt = opts["pil"]["format"]
        else:
            fmt = self._orig_format
        save_kwargs = dict()

        if Image._isint(opts["quality"]):
            save_kwargs["quality"] = int(opts["quality"])

        if int(opts["optimize"]):
            save_kwargs["optimize"] = True

        if int(opts["progressive"]):
            save_kwargs["progressive"] = True

        if int(opts["preserve_exif"]):
            save_kwargs["exif"] = self._exif

        if self._orig_format == "JPEG":
            self.img.format = self._orig_format
            save_kwargs["subsampling"] = "keep"
            if opts["quality"] == "keep":
                save_kwargs["quality"] = "keep"

        try:
            self.img.save(outfile, fmt, **save_kwargs)
        except IOError as e:
            raise errors.ImageSaveError(str(e))
        self.img.format = fmt
        outfile.seek(0)

        return outfile

    def _adapt(self, size, opts):
        source_aspect_ratio = float(self.img.size[0]) / float(self.img.size[1])
        aspect_ratio = float(size[0]) / float(size[1])
        if source_aspect_ratio >= aspect_ratio:
            retain = (aspect_ratio / source_aspect_ratio) * 100.0
        else:
            retain = (source_aspect_ratio / aspect_ratio) * 100.0

        if float(opts["retain"]) <= retain:
            self._crop(size, opts)
        else:
            self._fill(size, opts)

    def _clip(self, size, opts):
        self.img.thumbnail(size, opts["pil"]["filter"])

    def _crop(self, size, opts):
        if opts["position"] == "face":
            if cv is None:
                raise NotImplementedError
            else:
                pos = self._get_face_position()
        else:
            pos = opts["pil"]["position"]
        self.img = PIL.ImageOps.fit(
            self.img, size, opts["pil"]["filter"], 0, pos)

    def _fill(self, size, opts):
        self._clip(size, opts)
        if self.img.size == size:
            return  # No need to fill
        x = max(int((size[0] - self.img.size[0]) / 2.0), 0)
        y = max(int((size[1] - self.img.size[1]) / 2.0), 0)
        color = color_hex_to_dec_tuple(opts["background"])
        mode = "RGBA" if len(color) == 4 else "RGB"
        img = PIL.Image.new(mode=mode, size=size, color=color)
        img.paste(self.img, (x, y))
        self.img = img

    def _scale(self, size, opts):
        self.img = self.img.resize(size, opts["pil"]["filter"])

    def _get_size(self, width, height):
        aspect_ratio = self.img.size[0] / self.img.size[1]
        if not width:
            width = int((int(height) or self.img.size[1]) * aspect_ratio)
        if not height:
            height = int((int(width) or self.img.size[0]) / aspect_ratio)
        return (int(width), int(height))

    def _get_face_rectangles(self):
        cvim = self._pil_to_opencv()
        return cv.HaarDetectObjects(
            cvim,
            self._get_face_classifier(),
            cv.CreateMemStorage(0),
            1.3,  # Scale factor
            4,  # Minimum neighbors
            0,  # HAAR Flags
            (20, 20))

    def _get_face_position(self):
        rects = self._get_face_rectangles()
        if not rects:
            return (0.5, 0.5)
        xt, yt = (0.0, 0.0)
        for rect in rects:
            xt += rect[0][0] + (rect[0][2] / 2.0)
            yt += rect[0][1] + (rect[0][3] / 2.0)

        return (xt / (len(rects) * self.img.size[0]),
                yt / (len(rects) * self.img.size[1]))

    def _get_face_classifier(self):
        if not hasattr(Image, "_classifier"):
            classifier_path = os.path.abspath(Image._CLASSIFIER_PATH)
            Image._classifier = cv.Load(classifier_path)
        return Image._classifier

    def _pil_to_opencv(self):
        mono = self.img.convert("L")
        cvim = cv.CreateImageHeader(mono.size, cv.IPL_DEPTH_8U, 1)
        cv.SetData(cvim, mono.tostring(), mono.size[0])
        cv.EqualizeHist(cvim, cvim)
        return cvim

    @staticmethod
    def _normalize_options(options):
        opts = Image._DEFAULTS.copy()
        for k, v in options.items():
            if v is not None:
                opts[k] = v
        opts["pil"] = dict(
            filter=_filters_to_pil.get(opts["filter"]),
            format=_formats_to_pil.get(opts["format"]),
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
        pos = (float(m.group(1)), float(m.group(3)))
        if pos[0] < 0.0 or pos[0] > 1.0 or pos[1] < 0.0 or pos[1] > 1.0:
            return None
        return pos

    @staticmethod
    def _isint(v, base=10):
        try:
            if type(v) is not bool:
                int(str(v), base)
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
    import tornado.httpclient
    import tornado.options
    from tornado.options import define, options, parse_command_line

    define("operation", help="the operation to be performed", type=str,
           default="resize", metavar="|".join(["resize", "rotate", "none"]))
    define("width", help="the desired image width", type=int)
    define("height", help="the desired image height", type=int)
    define("mode", help="the resizing mode",
           metavar="|".join(Image.MODES), type=str)
    define("background", help="the hexidecimal fill background color",
           type=str)
    define("position", help="the crop position",
           metavar="|".join(Image.POSITIONS), type=str)
    define("filter", help="default filter to use when resizing",
           metavar="|".join(Image.FILTERS), type=str)
    define("degree", help="the desired rotation degree", type=int)
    define("expand", help="expand image size to accomodate rotation", type=int)
    define("rect", help="rectangle: x,y,w,h", type=str)
    define("format", help="default format to use when saving",
           metavar="|".join(Image.FORMATS), type=str)
    define("optimize", help="default to optimize when saving", type=int)
    define("progressive", help="default to progressive when saving", type=int)
    define("quality", help="default jpeg quality, 1-99 or keep")
    define("retain", help="default adaptive retain percent, 1-99", type=int)
    define("preserve_exif", help="default behavior for Exif data", type=int)

    args = parse_command_line()
    if not args:
        print("Missing image source url")
        sys.exit()
    elif options.operation == "region":
        if not options.rect:
            tornado.options.print_help()
            sys.exit()
    elif options.operation == "resize":
        if not options.width and not options.height:
            tornado.options.print_help()
            sys.exit()
    elif options.operation == "rotate":
        if not options.degree:
            tornado.options.print_help()
            sys.exit()
    elif options.operation != "noop":
        tornado.options.print_help()
        sys.exit()

    if args[0].startswith("http://") or args[0].startswith("https://"):
        client = tornado.httpclient.HTTPClient()
        resp = client.fetch(args[0])
        image = Image(resp.buffer)
    else:
        image = Image(open(args[0], "r"))

    if options.operation == "resize":
        image.resize(options.width, options.height, mode=options.mode,
                     filter=options.filter, background=options.background,
                     position=options.position, retain=options.retain)
    elif options.operation == "rotate":
        image.rotate(options.degree, expand=options.expand)
    elif options.operation == "region":
        image.region(options.rect.split(","))

    stream = image.save(format=options.format,
                        optimize=options.optimize,
                        quality=options.quality,
                        progressive=options.progressive,
                        preserve_exif=options.preserve_exif)
    sys.stdout.write(stream.read())
    stream.close()


if __name__ == "__main__":
    main()
