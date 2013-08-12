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

import cStringIO
import cv
import logging
from PIL import Image as PilImage
from PIL import ImageOps as PilImageOps
import os.path
import tornado.httpclient


logger = logging.getLogger("tornado.application")


class Image(object):
    MODES = ["crop", "scale", "clip", "face"]
    FORMATS = ["PNG", "JPEG", "JPG"]
    CLASSIFIER_PATH = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "config", "frontalface.xml"))
    _classifier = None

    def __init__(self, stream):
        self.stream = stream

    def resize(self, width, height, mode=None):
        """Returns a buffer to the resized image for saving"""
        if mode is not None and mode not in self.MODES:
            raise ImageModeError("Invalid image mode: '%s'" % mode)
        img = PilImage.open(self.stream)
        if img.format not in self.FORMATS:
            raise ImageFormatError("Unknown format: '%s'" % img.format)
        size = (int(width), int(height))
        if mode == "clip":
            resized = img
            resized.thumbnail(size, PilImage.ANTIALIAS)
        elif mode == "scale":
            resized = img.resize(size, PilImage.ANTIALIAS)
        elif mode == "face":
            pos = self._get_face_position(img)
            resized = PilImageOps.fit(img, size, PilImage.ANTIALIAS, 0, pos)
        else:
            pos = (0.5, 0.5)
            resized = PilImageOps.fit(img, size, PilImage.ANTIALIAS, 0, pos)
        outfile = cStringIO.StringIO()
        resized.save(outfile, img.format, quality=90)
        outfile.reset()
        return outfile

    def _get_face_rectangles(self, img):
        cvim = self._pil_to_opencv(img)
        return cv.HaarDetectObjects(
            cvim,
            self._get_face_classifier(),
            cv.CreateMemStorage(0),
            1.3, # Scale factor
            4, # Minimum neighbors
            0, # HAAR Flags
            (20, 20))

    def _get_face_position(self, img):
        rects = self._get_face_rectangles(img)
        if not rects:
            return (0.5, 0.5)

        xt, yt = (0.0, 0.0)
        for rect in rects:
            xt += float(rect[0][0]) + (float(rect[0][2]) / 2.0)
            yt += float(rect[0][1]) + (float(rect[0][3]) / 2.0)

        return (xt / (float(len(rects)) * float(img.size[0])),
                yt / (float(len(rects)) * float(img.size[1])))

    def _get_face_classifier(self):
        if not Image._classifier:
            Image._classifier = cv.Load(Image.CLASSIFIER_PATH)
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

    args = parse_command_line()
    if None in [options.width, options.height, options.mode]:
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
    stream = image.resize(options.width, options.height, mode=options.mode)
    sys.stdout.write(stream.read())

if __name__ == "__main__":
    main()
