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
import os.path

import tornado.escape
import tornado.gen
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define, options, parse_config_file
import tornado.web

from pilbox import errors
from pilbox.image import Image
from pilbox.signature import verify_signature

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


define("config", help="path to configuration file", type=str,
       callback=lambda path: parse_config_file(path, final=False))
define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8888, help="run on the given port", type=int)

# security related settings
define("client_name", help="client name", type=str)
define("client_key", help="client key", type=str)
define("allowed_hosts", default=[], help="list of allowed image hosts",
       type=str, multiple=True)

# default resizing option settings
define("background", help="default hexadecimal bg color (RGB or ARGB)",
       type=str)
define("filter", help="default filter to use when resizing", type=str)
define("position", help="default cropping position", type=str)
define("quality", help="default jpeg quality, 0-100", type=int)


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
                        allowed_hosts=options.allowed_hosts or [],
                        background=options.background,
                        filter=options.filter,
                        position=options.position,
                        quality=options.quality)
        settings.update(kwargs)
        tornado.web.Application.__init__(self, handlers, **settings)


class ImageHandler(tornado.web.RequestHandler):
    FORWARD_HEADERS = ['Cache-Control', 'Expires', 'Last-Modified']

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        self._validate_request()
        client = tornado.httpclient.AsyncHTTPClient()
        resp = yield client.fetch(self.get_argument("url"))
        image = Image(resp.buffer, self.settings)
        opts = self._get_resize_options()
        resized = image.resize(
            self.get_argument("w"), self.get_argument("h"), **opts)
        self._forward_headers(resp.headers)
        while True:
            s = resized.read(16384)
            if not s:
                break
            self.write(s)
        resized.close()
        self.finish()

    def get_argument(self, name, default=None):
        return super(ImageHandler, self).get_argument(name, default)

    def write_error(self, status_code, **kwargs):
        err = None
        if "exc_info" in kwargs:
            err = kwargs["exc_info"][1]
        if isinstance(err, errors.PilboxError):
            self.set_header('Content-Type', 'application/json')
            resp = dict(status_code=status_code,
                        error_code=err.get_code(),
                        error=err.log_message)
            self.finish(tornado.escape.json_encode(resp))
        else:
            super(ImageHandler, self).write_error(status_code, **kwargs)

    def _forward_headers(self, headers):
        self.set_header('Content-Type', headers['Content-Type'])
        for k in ImageHandler.FORWARD_HEADERS:
            if k in headers and headers[k]:
                self.set_header(k, headers[k])

    def _get_resize_options(self):
        return dict(mode=self.get_argument("mode"),
                    filter=self.get_argument("filter"),
                    position=self.get_argument("pos"),
                    background=self.get_argument("bg"),
                    quality=self.get_argument("q"))

    def _validate_request(self):
        self._validate_url()
        self._validate_signature()
        self._validate_client()
        self._validate_host()
        Image.validate_dimensions(
            self.get_argument("w"), self.get_argument("h"))
        Image.validate_options(self._get_resize_options())

    def _validate_url(self):
        if not self.get_argument("url"):
            raise errors.UrlError("Missing url")

    def _validate_client(self):
        client = self.settings.get("client_name")
        if client and self.get_argument("client") != client:
            raise errors.ClientError("Invalid client")

    def _validate_signature(self):
        key = self.settings.get("client_key")
        if key and not verify_signature(key, urlparse(self.request.uri).query):
            raise errors.SignatureError("Invalid signature")

    def _validate_host(self):
        hosts = self.settings.get("allowed_hosts", [])
        if hosts and urlparse(self.get_argument("url")).hostname not in hosts:
            raise errors.HostError("Invalid host")


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
