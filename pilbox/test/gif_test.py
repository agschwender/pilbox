from __future__ import absolute_import, division, with_statement

import itertools
import os
import os.path
import re
from sys import platform as _platform
from io import BytesIO

from PIL import Image, ImageChops, ImageSequence
from PIL.GifImagePlugin import getheader, getdata

import pilbox.image
from tornado.test.util import unittest

DATADIR = os.path.join(os.path.dirname(__file__), "data")
ANIMATED_GIF = os.path.join(DATADIR, "animated.gif")
EXPECTED_GIF = os.path.join(DATADIR, "expected", "animated.gif")

# stolen from https://github.com/python-pillow/Pillow/blob/master/Scripts/gifmaker.py
def write_gif(fp, sequence):
    frames = 0
    previous = None
    for im in sequence:
        if not previous:
            for s in getheader(im)[0] + getdata(im, duration=60, loop=0):
                fp.write(s)
        else:
            delta = ImageChops.subtract_modulo(im, previous)
            bbox = delta.getbbox()
            if bbox:
                for s in getdata(im.crop(bbox), offset=bbox[:2]):
                    fp.write(s)
            else:
                pass
        previous = im.copy()
        frames += 1
    fp.write(";")


class GifTest(unittest.TestCase):

    def test_resize(self):
        # collect and resize all the frames of a gif
        frames = []
        for im in ImageSequence.Iterator(Image.open(ANIMATED_GIF)):
            print im.info
            frames.append(im.copy())
            # outfile = BytesIO()
            # im.save(outfile, 'gif')
            # i = pilbox.image.Image(outfile)
            # i.resize(100, 75)
            # frames.append(i.img.copy())

        # write the result
        with open(EXPECTED_GIF, "wb") as fp:
             write_gif(fp, frames)

