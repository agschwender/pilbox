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

from __future__ import absolute_import, division, with_statement

import logging
import socket

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
    from urlparse import urlparse, urljoin
except ImportError:
    from urllib.parse import urlparse, urljoin


# general settings
define("config", help="path to configuration file",
       callback=lambda path: parse_config_file(path, final=False))
define("debug", help="run in debug mode", type=bool, default=False)
define("port", help="run on the given port", type=int, default=8888)

# security related settings
define("client_name", help="client name")
define("client_key", help="client key")
define("allowed_hosts", help="list of valid hosts", default=[], multiple=True)

# request related settings
define("max_requests", help="max concurrent requests", type=int, default=40)
define("timeout", help="request timeout in seconds", type=float, default=10)
define("implicit_base_url", help="prepend protocol/host to url paths")
define("validate_cert", help="validate certificates", type=bool, default=True)

# default image option settings
define("background", help="default hexadecimal bg color (RGB or ARGB)")
define("expand", help="default to expand when rotating", type=int)
define("filter", help="default filter to use when resizing")
define("format", help="default format to use when outputting")
define("mode", help="default mode to use when resizing")
define("optimize", help="default to optimize when saving", type=int)
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
                        expand=options.expand,
                        filter=options.filter,
                        format=options.format,
                        mode=options.mode,
                        position=options.position,
                        optimize=options.optimize,
                        quality=options.quality,
                        max_requests=options.max_requests,
                        timeout=options.timeout,
                        implicit_base_url=options.implicit_base_url,
                        validate_cert=options.validate_cert)
        settings.update(kwargs)
        tornado.web.Application.__init__(self, self.get_handlers(), **settings)

    def get_handlers(self):
        return [(r"/", ImageHandler)]


class ImageHandler(tornado.web.RequestHandler):
    FORWARD_HEADERS = ['Cache-Control', 'Expires', 'Last-Modified']
    OPERATIONS = ["region", "resize", "rotate", "noop"]

    _FORMAT_TO_MIME = {
        "gif": "image/gif",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp"}

    @tornado.gen.coroutine
    def get(self):
        self._validate_request()

        url = self.get_argument("url")
        if self.settings.get("implicit_base_url") \
                and urlparse(url).hostname is None:
            url = urljoin(self.settings.get("implicit_base_url"), url)

        client = tornado.httpclient.AsyncHTTPClient(
            max_clients=self.settings.get("max_requests"))
        try:
            resp = yield client.fetch(
                url,
                request_timeout=self.settings.get("timeout"),
                validate_cert=self.settings.get("validate_cert"))
        except (socket.gaierror, tornado.httpclient.HTTPError) as e:
            logger.warn("Fetch error for %s: %s"
                        % (self.get_argument("url"), str(e)))
            raise errors.FetchError()

        outfile = self._process_response(resp)
        self._forward_headers(resp.headers)
        for block in iter(lambda: outfile.read(65536), b""):
            self.write(block)
        outfile.close()

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

    def _process_response(self, resp):
        ops = self._get_operations()
        if "noop" in ops:
            return resp.buffer

        image = Image(resp.buffer)
        for operation in ops:
            if operation == "resize":
                self._image_resize(image)
            elif operation == "rotate":
                self._image_rotate(image)
            elif operation == "region":
                self._image_region(image)

        return self._image_save(image)

    def _image_region(self, image):
        image.region(self.get_argument("rect").split(","))

    def _image_resize(self, image):
        opts = self._get_resize_options()
        image.resize(self.get_argument("w"), self.get_argument("h"), **opts)

    def _image_rotate(self, image):
        opts = self._get_rotate_options()
        image.rotate(self.get_argument("deg"), **opts)

    def _image_save(self, image):
        opts = self._get_save_options()
        return image.save(**opts)

    def _forward_headers(self, headers):
        mime = self._FORMAT_TO_MIME.get(
            self.get_argument("fmt", self.settings.get("format")),
            headers['Content-Type'])
        self.set_header('Content-Type', mime)
        for k in ImageHandler.FORWARD_HEADERS:
            if k in headers and headers[k]:
                self.set_header(k, headers[k])

    def _get_operations(self):
        return self.get_argument("op", "resize").split(",")

    def _get_resize_options(self):
        return self._get_options(
            dict(mode=self.get_argument("mode"),
                 filter=self.get_argument("filter"),
                 position=self.get_argument("pos"),
                 background=self.get_argument("bg")))

    def _get_rotate_options(self):
        return self._get_options(
            dict(expand=self.get_argument("expand")))

    def _get_save_options(self):
        return self._get_options(
            dict(format=self.get_argument("fmt"),
                 optimize=self.get_argument("opt"),
                 quality=self.get_argument("q")))

    def _get_options(self, opts):
        for k, v in opts.items():
            if v is None:
                opts[k] = self.settings.get(k, None)
        return opts

    def _validate_request(self):
        self._validate_operation()
        self._validate_url()
        self._validate_signature()
        self._validate_client()
        self._validate_host()

        opts = self._get_save_options()
        ops = self._get_operations()
        if "resize" in ops:
            Image.validate_dimensions(
                self.get_argument("w"), self.get_argument("h"))
            opts.update(self._get_resize_options())
        if "rotate" in ops:
            Image.validate_degree(self.get_argument("deg"))
            opts.update(self._get_rotate_options())
        if "region" in ops:
            Image.validate_rectangle(self.get_argument("rect"))

        Image.validate_options(opts)

    def _validate_operation(self):
        operations = set(self._get_operations())
        if not operations.issubset(set(ImageHandler.OPERATIONS)):
            raise errors.OperationError("Unsupported operation")

    def _validate_url(self):
        url = self.get_argument("url")
        if not url:
            raise errors.UrlError("Missing url")
        elif url.startswith("http://") or url.startswith("https://"):
            return
        elif self.settings.get("implicit_base_url") and url.startswith("/"):
            return
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
