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

import logging
import os.path
import tornado.escape
import tornado.gen
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import urlparse

from image import Image, ImageFormatError
from signature import verify_signature

from tornado.options import define, options, parse_config_file

define("config", help="path to configuration file", type=str,
       callback=lambda path: parse_config_file(path, final=False))
define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8888, help="run on the given port", type=int)
define("client_name", help="client name", type=str)
define("client_key", help="client key", type=str)
define("allowed_hosts", default=[], help="list of allowed image hosts",
       type=str, multiple=True)


logger = logging.getLogger("tornado.application")


class PilboxApplication(tornado.web.Application):
    TESTDATADIR = os.path.join(os.path.dirname(__file__), "test", "data")

    def __init__(self, **kwargs):
        handlers = [
            (r"/test-data/(.*)",
             tornado.web.StaticFileHandler,
             {"path": self.TESTDATADIR}),
            (r"/", ImageHandler)]
        settings = dict(debug=options.debug,
                        client_name=options.client_name,
                        client_key=options.client_key,
                        allowed_hosts=options.allowed_hosts)
        settings.update(kwargs)
        tornado.web.Application.__init__(self, handlers, **settings)


class ImageHandler(tornado.web.RequestHandler):
    MISSING_URL = "Missing image url"
    MISSING_DIMENSIONS = "Missing image width and height"
    INVALID_WIDTH = "Invalid image width"
    INVALID_HEIGHT = "Invalid image height"
    INVALID_MODE = "Invalid mode"
    INVALID_CLIENT = "Invalid client"
    INVALID_SIGNATURE = "Invalid signature"
    INVALID_HOST = "Invalid image host"
    INVALID_BACKGROUND = "Invalid background color"
    INVALID_POSITION = "Invalid crop position"
    UNSUPPORTED_IMAGE_TYPE = "Unsupported image type"

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        self._validate_request()
        client = tornado.httpclient.AsyncHTTPClient()
        resp = yield client.fetch(self.get_argument("url"))
        image = Image(resp.buffer)
        try:
            resized = image.resize(self.get_argument("w", None),
                                   self.get_argument("h", None),
                                   mode=self.get_argument("mode", "crop"),
                                   bg=self.get_argument("bg", None),
                                   pos=self.get_argument("pos", None))
        except ImageFormatError:
            raise tornado.web.HTTPError(415, self.UNSUPPORTED_IMAGE_TYPE)
        self._import_headers(resp.headers)
        self.write(resized.read())
        self.finish()

    def _import_headers(self, headers):
        self.set_header('Content-Type', headers['Content-Type'])
        for k in ['Cache-Control', 'Expires', 'Last-Modified']:
            if k in headers and headers[k]:
                self.set_header(k, headers[k])

    def write_error(self, status_code, **kwargs):
        err = None
        if "exc_info" in kwargs:
            err = kwargs["exc_info"][1]
        if isinstance(err, tornado.web.HTTPError):
            self.set_header('Content-Type', 'application/json')
            resp = dict(code=status_code, error=err.log_message)
            self.finish(tornado.escape.json_encode(resp))
        else:
            super(ImageHandler, self).write_error(status_code, **kwargs)

    def _validate_request(self):
        s = self.application.settings
        if not self.get_argument("url", None):
            raise tornado.web.HTTPError(400, self.MISSING_URL)
        elif not self.get_argument("w", None) \
                and not self.get_argument("h", None):
            raise tornado.web.HTTPError(400, self.MISSING_DIMENSIONS)
        elif self.get_argument("w", None) \
                and not self.get_argument("w").isdigit():
            raise tornado.web.HTTPError(400, self.INVALID_WIDTH)
        elif self.get_argument("h", None) \
                and not self.get_argument("h").isdigit():
            raise tornado.web.HTTPError(400, self.INVALID_HEIGHT)
        elif self.get_argument("mode", "crop") not in Image.MODES:
            raise tornado.web.HTTPError(400, self.INVALID_MODE)
        elif self.get_argument("mode", "crop") == "fill" \
                and not self._validate_background():
            raise tornado.web.HTTPError(400, self.INVALID_BACKGROUND)
        elif self.get_argument("mode", "crop") == "crop" \
                and self.get_argument("pos", "center") not in Image.POSITIONS:
            raise tornado.web.HTTPError(400, self.INVALID_POSITION)
        elif s.get("client_name") \
                and self.get_argument("client", None) != s.get("client_name"):
            raise tornado.web.HTTPError(403, self.INVALID_CLIENT)
        elif s.get("client_key") and not self._validate_signature():
            raise tornado.web.HTTPError(403, self.INVALID_SIGNATURE)
        elif s.get("allowed_hosts") and not self._validate_host():
            raise tornado.web.HTTPError(403, self.INVALID_HOST)

    def _validate_signature(self):
        if not self.get_argument("sig", None):
            return False
        parsed = urlparse.urlparse(self.request.uri)
        return verify_signature(self.settings.get("client_key"), parsed.query)

    def _validate_host(self):
        parsed = urlparse.urlparse(self.get_argument("url"))
        if parsed.hostname not in self.settings.get("allowed_hosts", []):
            return False
        return True

    def _validate_background(self):
        try:
            if self.get_argument("bg", None):
                int(self.get_argument("bg"), 16)
        except ValueError:
            return False
        return len(self.get_argument("bg", "")) in [0, 3, 6]


def main():
    tornado.options.parse_command_line()
    server = tornado.httpserver.HTTPServer(PilboxApplication())
    logger.info("Starting server...")
    try:
        server.bind(options.port)
        server.start(1 if options.debug else 0)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()


if __name__ == "__main__":
    main()
