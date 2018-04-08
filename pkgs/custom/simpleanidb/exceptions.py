# coding=utf-8


import six
from requests import RequestException


class BaseError(Exception):
    def __init__(self, value):
        Exception.__init__()
        self.value = value

    def __str__(self):
        return six.text_type(self.value, 'utf-8')


class GeneralError(BaseError):
    """General simpleanidb error"""


class AnidbConnectionError(GeneralError, RequestException):
    """Connection error while accessing Anidb"""


class BadRequest(AnidbConnectionError):
    """Bad request"""
