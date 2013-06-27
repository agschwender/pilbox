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
from image import Image, ImageFormatError
from signature import verify_signature
import tornado.gen
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import urlparse

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
    def __init__(self):
        handlers = [
            (r"/", ImageHandler),
            ]
        settings = dict(debug=options.debug)
        tornado.web.Application.__init__(self, handlers, **settings)


class ImageHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        self._validate_request()
        client = tornado.httpclient.AsyncHTTPClient()
        resp = yield client.fetch(self.get_argument("url"))
        image = Image(resp.buffer)
        self._import_headers(resp.headers)
        try:
            resized = image.resize(self.get_argument("w"),
                                   self.get_argument("h"),
                                   mode=self.get_argument("mode"))
        except ImageFormatError:
            raise tornado.web.HTTPError(415, "Unsupported image type")
        self.write(resized.read())
        self.finish()

    def _import_headers(self, headers):
        self.set_header('Content-Type', headers['Content-Type'])
        for k in ['Cache-Control', 'Expires', 'Last-Modified']:
            if k in headers and headers[k]:
                self.set_header(k, headers[k])

    def _validate_request(self):
        if not self.get_argument("url", None):
            raise tornado.web.HTTPError(400, "Missing image url")
        elif not self.get_argument("w", None) \
                and not self.get_argument("h", None):
            raise tornado.web.HTTPError(400, "Missing image width and height")
        elif self.get_argument("w", None) \
                and not self.get_argument("w").isdigit():
            raise tornado.web.HTTPError(400, "Invalid image width")
        elif self.get_argument("h", None) \
                and not self.get_argument("h").isdigit():
            raise tornado.web.HTTPError(400, "Invalid image height")
        elif self.get_argument("mode", "crop") not in Image.MODES:
            raise tornado.web.HTTPError(400, "Invalid mode")
        elif options.client_name \
                and self.get_argument("client", None) != options.client_name:
            raise tornado.web.HTTPError(400, "Invalid client")
        elif options.client_key and not self._validate_signature():
            raise tornado.web.HTTPError(400, "Invalid signature")
        elif not options.client_key and not self._validate_host():
            raise tornado.web.HTTPError(400, "Invalid image host")

    def _validate_signature(self):
        if not self.get_argument("sig", None):
            return False
        parsed = urlparse.urlparse(self.request.uri)
        return verify_signature(options.client_key, parsed.query)

    def _validate_host(self):
        if options.allowed_hosts:
            parsed = urlparse.urlparse(self.get_argument("url"))
            if parsed.hostname not in options.allowed_hosts:
                return False
        return True


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
