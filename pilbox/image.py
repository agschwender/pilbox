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
from PIL import Image as PilImage
from PIL import ImageOps as PilImageOps
import tornado.httpclient


class Image(object):
    MODES = ["crop", "scale", "clip"]
    FORMATS = ["PNG", "JPEG", "JPG"]

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
        else:
            pos = (0.5, 0.5)
            resized = PilImageOps.fit(img, size, PilImage.ANTIALIAS, 0, pos)
        outfile = cStringIO.StringIO()
        resized.save(outfile, img.format, quality=90)
        outfile.reset()
        return outfile


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
