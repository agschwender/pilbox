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

try:
    import pycurl
except ImportError:
    pycurl = None


# general settings
define("config", help="path to configuration file",
       callback=lambda path: parse_config_file(path, final=False))
define("debug", help="run in debug mode", type=bool, default=False)
define("port", help="run on the given port", type=int, default=8888)

# security related settings
define("client_name", help="client name")
define("client_key", help="client key")
define("allowed_hosts", help="valid hosts", default=[], multiple=True)
define("allowed_operations", help="valid ops", default=[], multiple=True)

# request related settings
define("max_requests", help="max concurrent requests", type=int, default=40)
define("timeout", help="request timeout in seconds", type=float, default=10)
define("implicit_base_url", help="prepend protocol/host to url paths")
define("ca_certs",
       help="override filename of CA certificates in PEM format",
       default=None)
define("validate_cert", help="validate certificates", type=bool, default=True)
define("proxy_host", help="proxy hostname")
define("proxy_port", help="proxy port", type=int)

# header related settings
define("content_type_from_image",
       help="override content type using image mime type",
       type=bool)

# default image option settings
define("background", help="default hexadecimal bg color (RGB or ARGB)")
define("expand", help="default to expand when rotating", type=int)
define("filter", help="default filter to use when resizing")
define("format", help="default format to use when outputting")
define("mode", help="default mode to use when resizing")
define("operation", help="default operation to perform")
define("optimize", help="default to optimize when saving", type=int)
define("position", help="default cropping position")
define("progressive", help="default to progressive when saving", type=int)
define("quality", help="default jpeg quality, 1-99 or keep")
define("retain", help="default adaptive retain percent, 1-99", type=int)
define("preserve_exif", help="default behavior for exif data", type=int)

logger = logging.getLogger("tornado.application")


class PilboxApplication(tornado.web.Application):

    def __init__(self, **kwargs):
        settings = dict(
            debug=options.debug,
            client_name=options.client_name,
            client_key=options.client_key,
            allowed_hosts=options.allowed_hosts,
            allowed_operations=set(
                options.allowed_operations or ImageHandler.OPERATIONS),
            background=options.background,
            expand=options.expand,
            filter=options.filter,
            format=options.format,
            mode=options.mode,
            operation=options.operation,
            optimize=options.optimize,
            position=options.position,
            progressive=options.progressive,
            quality=options.quality,
            max_requests=options.max_requests,
            timeout=options.timeout,
            implicit_base_url=options.implicit_base_url,
            ca_certs=options.ca_certs,
            validate_cert=options.validate_cert,
            content_type_from_image=options.content_type_from_image,
            proxy_host=options.proxy_host,
            proxy_port=options.proxy_port,
            preserve_exif=options.preserve_exif)

        settings.update(kwargs)

        if settings.get("proxy_host") and pycurl is None:  # pragma: no cover
            raise Exception("PycURL is required for proxy requests")

        if pycurl is not None:  # pragma: no cover
            tornado.httpclient.AsyncHTTPClient.configure(
                "tornado.curl_httpclient.CurlAsyncHTTPClient")

        tornado.web.Application.__init__(self, self.get_handlers(), **settings)

    def get_handlers(self):
        return [(r"/", ImageHandler)]


class ImageHandler(tornado.web.RequestHandler):
    FORWARD_HEADERS = ["Cache-Control", "Expires", "Last-Modified"]
    OPERATIONS = ["region", "resize", "rotate", "noop"]

    _FORMAT_TO_MIME = {
        "gif": "image/gif",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "tiff": "image/tiff",
    }

    @tornado.gen.coroutine
    def get(self):
        self.validate_request()
        resp = yield self.fetch_image()
        self.render_image(resp)

    def get_argument(self, name, default=None, strip=True):
        return super(ImageHandler, self).get_argument(name, default, strip)

    def validate_request(self):
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

    @tornado.gen.coroutine
    def fetch_image(self):
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
                ca_certs=self.settings.get("ca_certs"),
                validate_cert=self.settings.get("validate_cert"),
                proxy_host=self.settings.get("proxy_host"),
                proxy_port=self.settings.get("proxy_port"))
            raise tornado.gen.Return(resp)
        except (socket.gaierror, tornado.httpclient.HTTPError) as e:
            logger.warn("Fetch error for %s: %s",
                        self.get_argument("url"),
                        str(e))
            raise errors.FetchError()

    def render_image(self, resp):
        outfile, outfile_format = self._process_response(resp)
        self._set_headers(resp.headers, outfile_format)
        for block in iter(lambda: outfile.read(65536), b""):
            self.write(block)
        outfile.close()

    def write_error(self, status_code, **kwargs):
        err = kwargs["exc_info"][1] if "exc_info" in kwargs else None
        if isinstance(err, errors.PilboxError):
            self.set_header("Content-Type", "application/json")
            resp = dict(status_code=status_code,
                        error_code=err.get_code(),
                        error=err.log_message)
            self.finish(tornado.escape.json_encode(resp))
        else:
            super(ImageHandler, self).write_error(status_code, **kwargs)

    def _process_response(self, resp):
        ops = self._get_operations()
        if "noop" in ops:
            return (resp.buffer, None)

        image = Image(resp.buffer)
        for operation in ops:
            if operation == "resize":
                self._image_resize(image)
            elif operation == "rotate":
                self._image_rotate(image)
            elif operation == "region":
                self._image_region(image)

        return (self._image_save(image), image.img.format)

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

    def _set_headers(self, headers, file_format):
        if file_format and any((self.get_argument("fmt"),
                                self.settings.get("format"),
                                self.settings.get("content_type_from_image"))):
            self.set_header(
                "Content-Type", self._FORMAT_TO_MIME.get(file_format.lower()))
        elif "Content-Type" in headers:
            self.set_header("Content-Type", headers["Content-Type"])

        for k in ImageHandler.FORWARD_HEADERS:
            if k in headers and headers[k]:
                self.set_header(k, headers[k])

    def _get_operations(self):
        return self.get_argument(
            "op", self.settings.get("operation") or "resize").split(",")

    def _get_resize_options(self):
        return self._get_options(
            dict(mode=self.get_argument("mode"),
                 filter=self.get_argument("filter"),
                 position=self.get_argument("pos"),
                 background=self.get_argument("bg"),
                 retain=self.get_argument("retain")))

    def _get_rotate_options(self):
        return self._get_options(
            dict(expand=self.get_argument("expand")))

    def _get_save_options(self):
        return self._get_options(
            dict(format=self.get_argument("fmt"),
                 optimize=self.get_argument("opt"),
                 quality=self.get_argument("q"),
                 progressive=self.get_argument("prog"),
                 preserve_exif=self.get_argument("exif")))

    def _get_options(self, opts):
        for k, v in opts.items():
            if v is None:
                opts[k] = self.settings.get(k, None)
        return opts

    def _validate_operation(self):
        operations = set(self._get_operations())
        if not operations.issubset(self.settings.get("allowed_operations")):
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


def parse_command_line():  # pragma: no cover
    tornado.options.parse_command_line()


def start_server(app=None):  # pragma: no cover
    if options.debug:
        logger.setLevel(logging.DEBUG)
    server = tornado.httpserver.HTTPServer(
        app if app else PilboxApplication())
    logger.info("Starting server...")
    try:
        server.bind(options.port)
        server.start(1 if options.debug else 0)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()


def main(app=None):
    parse_command_line()
    start_server(app)


if __name__ == "__main__":
    main()
