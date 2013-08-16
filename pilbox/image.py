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

from __future__ import division

import cStringIO
import cv
import logging
from PIL import Image as PilImage
from PIL import ImageOps as PilImageOps
import os.path
import tornado.httpclient


logger = logging.getLogger("tornado.application")

_positions_to_ratios = {
    "top-left": (0.0, 0.0), "top": (0.5, 0.0), "top-right": (1.0, 0.0),
    "left": (0.0, 0.5), "center": (0.5, 0.5), "right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0), "bottom": (0.5, 1.0), "bottom-right": (1.0, 1.0),
    "face": None}


class Image(object):
    MODES = ["clip", "crop", "fill", "scale"]
    POSITIONS_TO_RATIOS = _positions_to_ratios
    POSITIONS = _positions_to_ratios.keys()
    FORMATS = ["PNG", "JPEG", "JPG"]
    CLASSIFIER_PATH = os.path.join(
        os.path.dirname(__file__), "..", "config", "frontalface.xml")
    _classifier = None

    def __init__(self, stream):
        self.stream = stream

    def resize(self, width, height, mode=None, bg=None, pos=None):
        """Returns a buffer to the resized image for saving"""
        if mode is not None and mode not in self.MODES:
            raise ImageModeError("Invalid image mode: '%s'" % mode)
        img = PilImage.open(self.stream)
        if img.format not in self.FORMATS:
            raise ImageFormatError("Unknown format: '%s'" % img.format)
        size = self._get_size(img, width, height)
        if mode == "clip":
            resized = self._clip(img, size)
        elif mode == "fill":
            resized = self._fill(img, size, bg)
        elif mode == "scale":
            resized = self._scale(img, size)
        else:
            resized = self._crop(img, size, pos)
        outfile = cStringIO.StringIO()
        resized.save(outfile, img.format, quality=90)
        outfile.reset()
        return outfile

    def _clip(self, image, size):
        image.thumbnail(size, PilImage.ANTIALIAS)
        return image

    def _crop(self, image, size, pos):
        if pos == "face":
            pos_ratio = self._get_face_position(image)
        else:
            pos_ratio = Image.POSITIONS_TO_RATIOS.get(pos, (0.5, 0.5))
        return PilImageOps.fit(image, size, PilImage.ANTIALIAS, 0, pos_ratio)

    def _fill(self, image, size, bg):
        clipped = self._clip(image, size)
        if clipped.size == size:
            return clipped # No need to fill
        bg = bg or "fff"
        x = max(int((size[0] - clipped.size[0]) / 2.0), 0)
        y = max(int((size[1] - clipped.size[1]) / 2.0), 0)
        img = PilImage.new(mode=clipped.mode, size=size, color="#" + bg)
        img.paste(clipped, (x, y))
        return img

    def _scale(self, image, size):
        return image.resize(size, PilImage.ANTIALIAS)

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
        if not Image._classifier:
            Image._classifier = cv.Load(os.path.abspath(Image.CLASSIFIER_PATH))
        return Image._classifier

    def _pil_to_opencv(self, pi):
        mono = pi.convert("L")
        cvim = cv.CreateImageHeader(mono.size, cv.IPL_DEPTH_8U, 1)
        cv.SetData(cvim, mono.tostring(), mono.size[0])
        cv.EqualizeHist(cvim, cvim)
        return cvim


class ImageModeError(Exception):
    pass


class ImageFormatError(Exception):
    pass


def main():
    import sys
    import tornado.options
    from tornado.options import define, options, parse_command_line

    define("width", help="the desired image width", type=int)
    define("height", help="the desired image height", type=int)
    define("mode", help="the resizing mode",
           metavar="|".join(Image.MODES), default="crop", type=str)
    define("background", help="the hexidecimal fill background color",
           default="ffffff", type=str)
    define("position", help="the crop position",
           metavar="|".join(Image.POSITIONS), default="center", type=str)

    args = parse_command_line()
    if None in [options.width, options.height, options.mode, options.background,
                options.position]:
        tornado.options.print_help()
        sys.exit()
    elif not args:
        print "Missing image source url"
        sys.exit()

    if args[0].startswith("http://") or args[0].startswith("https://"):
        client = tornado.httpclient.HTTPClient()
        resp = client.fetch(args[0])
        image = Image(resp.buffer)
    else:
        image = Image(open(args[0], "r"))
    stream = image.resize(options.width, options.height, mode=options.mode,
                          bg=options.background, pos=options.position)
    sys.stdout.write(stream.read())

if __name__ == "__main__":
    main()
