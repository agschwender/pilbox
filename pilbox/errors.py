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

import tornado.web


class PilboxError(tornado.web.HTTPError):
    @staticmethod
    def get_code():
        raise NotImplementedError()


class BadRequestError(PilboxError):
    def __init__(self, msg=None, *args, **kwargs):
        super(BadRequestError, self).__init__(400, msg, *args, **kwargs)


class BackgroundError(BadRequestError):
    @staticmethod
    def get_code():
        return 1


class DimensionsError(BadRequestError):
    @staticmethod
    def get_code():
        return 2


class FilterError(BadRequestError):
    @staticmethod
    def get_code():
        return 3


class FormatError(BadRequestError):
    @staticmethod
    def get_code():
        return 4


class ModeError(BadRequestError):
    @staticmethod
    def get_code():
        return 5


class PositionError(BadRequestError):
    @staticmethod
    def get_code():
        return 6


class QualityError(BadRequestError):
    @staticmethod
    def get_code():
        return 7


class UrlError(BadRequestError):
    @staticmethod
    def get_code():
        return 8


class DegreeError(BadRequestError):
    @staticmethod
    def get_code():
        return 9


class OperationError(BadRequestError):
    @staticmethod
    def get_code():
        return 10


class RectangleError(BadRequestError):
    @staticmethod
    def get_code():
        return 11


class OptimizeError(BadRequestError):
    @staticmethod
    def get_code():
        return 12


class PreserveExifError(BadRequestError):
    @staticmethod
    def get_code():
        return 15


class ProgressiveError(BadRequestError):
    @staticmethod
    def get_code():
        return 13


class RetainError(BadRequestError):
    @staticmethod
    def get_code():
        return 14


class FetchError(PilboxError):
    def __init__(self, msg=None, *args, **kwargs):
        super(FetchError, self).__init__(404, msg, *args, **kwargs)

    @staticmethod
    def get_code():
        return 301


class ForbiddenError(PilboxError):
    def __init__(self, msg=None, *args, **kwargs):
        super(ForbiddenError, self).__init__(403, msg, *args, **kwargs)


class SignatureError(ForbiddenError):
    @staticmethod
    def get_code():
        return 101


class ClientError(ForbiddenError):
    @staticmethod
    def get_code():
        return 102


class HostError(ForbiddenError):
    @staticmethod
    def get_code():
        return 103


class UnsupportedError(PilboxError):
    def __init__(self, msg=None, *args, **kwargs):
        super(UnsupportedError, self).__init__(415, msg, *args, **kwargs)


class ImageFormatError(UnsupportedError):
    @staticmethod
    def get_code():
        return 201


class ImageSaveError(UnsupportedError):
    @staticmethod
    def get_code():
        return 202
