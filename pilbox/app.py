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

from __future__ import (absolute_import, division, print_function,
                        with_statement)

import logging
import socket
from io import BytesIO

import tornado.escape
import tornado.gen
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options, parse_config_file

from pilbox import errors
from pilbox.image import Image
from pilbox.signature import verify_signature

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


# general settings
define("config", help="path to configuration file", callback=lambda path: parse_config_file(path, final=False))
define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8888, help="run on the given port", type=int)

# security related settings
define("client_name", help="client name")
define("client_key", help="client key")
define("allowed_hosts", help="list of allowed hosts", default=[], multiple=True)

# request related settings
define("max_requests", help="max concurrent requests", type=int, default=40)
define("timeout", help="timeout of requests in seconds", type=float, default=10)

# default resizing option settings
define("background", help="default hexadecimal bg color (RGB or ARGB)")
define("filter", help="default filter to use when resizing")
define("format", help="default format to use when outputting")
define("mode", help="default mode to use when resizing")
define("position", help="default cropping position")
define("quality", help="default jpeg quality, 0-100", type=int)

logger = logging.getLogger("tornado.application")


class PilboxApplication(tornado.web.Application):

    def __init__(self, **kwargs):
        settings = dict(debug=options.debug,
                        client_name=options.client_name,
                        client_key=options.client_key,
                        allowed_hosts=options.allowed_hosts,
                        background=options.background,
                        filter=options.filter,
                        format=options.format,
                        mode=options.mode,
                        position=options.position,
                        quality=options.quality,
                        max_requests=options.max_requests,
                        timeout=options.timeout)
        settings.update(kwargs)
        tornado.web.Application.__init__(self, self.get_handlers(), **settings)

    def get_handlers(self):
        return [(r"/", ImageHandler)]


class ImageHandler(tornado.web.RequestHandler):
    FORWARD_HEADERS = ['Cache-Control', 'Expires', 'Last-Modified']
    _FORMAT_TO_MIME = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp"}

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        self._validate_request()
        client = tornado.httpclient.AsyncHTTPClient(
            max_clients=self.settings.get("max_requests"))
        try:
            resp = yield client.fetch(
                self.get_argument("url"),
                request_timeout=self.settings.get("timeout"))
        except (socket.gaierror, tornado.httpclient.HTTPError) as e:
            logger.warn("Fetch error for %s: %s"
                        % (self.get_argument("url"), str(e)))
            raise errors.FetchError()

        self._process_response(resp)

        self.finish()

    def get_argument(self, name, default=None):
        return super(ImageHandler, self).get_argument(name, default)

    def write_error(self, status_code, **kwargs):
        err = kwargs["exc_info"][1] if "exc_info" in kwargs else None
        if isinstance(err, errors.PilboxError):
            self.set_header('Content-Type', 'application/json')
            resp = dict(status_code=status_code,
                        error_code=err.get_code(),
                        error=err.log_message)
            self.finish(tornado.escape.json_encode(resp))
        else:
            super(ImageHandler, self).write_error(status_code, **kwargs)

    def _forward_headers(self, headers):
        mime = self._FORMAT_TO_MIME.get(
            self.get_argument("fmt"), headers['Content-Type'])
        self.set_header('Content-Type', mime)
        for k in ImageHandler.FORWARD_HEADERS:
            if k in headers and headers[k]:
                self.set_header(k, headers[k])

    def _get_resize_options(self):
        return dict(mode=self.get_argument("mode"),
                    filter=self.get_argument("filter"),
                    format=self.get_argument("fmt"),
                    position=self.get_argument("pos"),
                    background=self.get_argument("bg"),
                    quality=self.get_argument("q"))

    def _process_response(self, response):
        """ processes response by its arguments.

        if `rotate` is provided, it will happen after all other args.
        """
        image = Image(response.buffer, self.settings)

        output = BytesIO()
        resize, rotate = self.get_argument("w") or self.get_argument("h"), self.get_argument("rotate")

        if resize:
            opts = self._get_resize_options()
            resized = image.resize(self.get_argument("w"), self.get_argument("h"), **opts)
            output.write(resized.read())
            output.seek(0)
            resized.close()

        if rotate:
            if resize:
                output = BytesIO()

            rotated = image.rotate(self.get_argument("rotate"))
            output.write(rotated.read())
            output.seek(0)
            rotated.close()

        self._forward_headers(response.headers)
        for block in iter(lambda: output.read(65536), b""):
            self.write(block)

    def _validate_request(self):
        self._validate_transform_arguments()
        self._validate_url()
        self._validate_signature()
        self._validate_client()
        self._validate_host()

        if self.get_argument("w") or self.get_argument("h"):
            Image.validate_dimensions(self.get_argument("w"), self.get_argument("h"))

        if self.get_argument("rotate"):
            Image.validate_angle(self.get_argument("rotate"))

        Image.validate_options(self._get_resize_options())

    def _validate_url(self):
        if not self.get_argument("url"):
            raise errors.UrlError("Missing url")
        elif not self.get_argument("url").startswith("http://") \
                and not self.get_argument("url").startswith("https://"):
            raise errors.UrlError("Unsupported protocol")

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

    def _validate_transform_arguments(self):
        """ checks if at least one transformation argument is provided. """
        if not [x for x in ["w", "h", "rotate"] if self.get_argument(x)]:
            raise errors.ArgumentsError("Missing required arguments. "
                                        "Resize: require `w` or/and `h`."
                                        "Rotate: require `rotate`.")

def main():
    tornado.options.parse_command_line()
    if options.debug:
        logger.setLevel(logging.DEBUG)
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
