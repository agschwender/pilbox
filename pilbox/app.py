#!/usr/bin/env python

import cStringIO
import Image, ImageOps
import logging
import magic
import os.path
import tornado.gen
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

define("config", help="run using configuration file", type=str)
define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8888, help="run on the given port", type=int)

logger = logging.getLogger("tornado.process")

class PilboxApplication(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", ImageHandler),
            ]
        settings = dict(debug=options.debug)
        tornado.web.Application.__init__(self, handlers, **settings)


class ImageHandler(tornado.web.RequestHandler):
    MODES = ["crop", "scale", "clip"]
    FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG"}

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        self._validate_request()
        client = tornado.httpclient.AsyncHTTPClient()
        resp = yield client.fetch(self.get_argument("url"))
        img = cStringIO.StringIO(resp.body)
        mime = self._determine_image_type(img)
        self.set_header('Content-Type', mime)
        self.write(self._resize_image(img, self.FORMATS[mime]).read())
        self.finish()

    def _determine_image_type(self, infile):
        mime = magic.from_buffer(infile.read(1024), mime=True)
        if mime not in self.FORMATS.keys():
            raise tornado.web.HTTPError(415, "Unsupported image type")
        infile.reset()
        return mime

    def _resize_image(self, infile, format):
        img = Image.open(infile)
        size = (int(self.get_argument("w")), int(self.get_argument("h")))
        logger.info(self.get_argument("mode"))
        if self.get_argument("mode") == "clip":
            resized = img
            resized.thumbnail(size)
        elif self.get_argument("mode") == "scale":
            resized = img.resize(size)
        else:
            resized = ImageOps.fit(img, size, Image.NEAREST, 0, (0.5, 0.5))
        outfile = cStringIO.StringIO()
        resized.save(outfile, format)
        outfile.reset()
        return outfile

    def _validate_request(self):
        if not self.get_argument("url"):
            raise tornado.web.HTTPError(400, "Missing image url")
        elif not self.get_argument("w") and not self.get_argument("h"):
            raise tornado.web.HTTPError(400, "Missing image width and height")
        elif self.get_argument("w") and not self.get_argument("w").isdigit():
            raise tornado.web.HTTPError(400, "Invalid image width")
        elif self.get_argument("h") and not self.get_argument("h").isdigit():
            raise tornado.web.HTTPError(400, "Invalid image height")
        elif self.get_argument("mode", "crop") not in self.MODES:
            raise tornado.web.HTTPError(400, "Invalid mode")


def main():
    tornado.options.parse_command_line()
    if options.config:
        tornado.options.parse_config_file(options.config)
    tornado.options.parse_command_line() # override with command line
    server = tornado.httpserver.HTTPServer(PilboxApplication())
    logger.info("Starting server...")
    try:
        if options.debug:
            server.listen(options.port)
        else:
            server.bind(options.port)
            server.start(0)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()

if __name__ == "__main__":
    main()
