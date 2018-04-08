# coding=utf-8

"""General utility functions."""

from collections import Iterable


def generate(it):
    """
    Generate items from an iterable.

    :param it: an iterable
    :return: items from an iterable
        If the iterable is a string yield the entire string
        If the item is not iterable, yield the item
    """
    if isinstance(it, Iterable) and not isinstance(it, str):
        for item in it:
            yield item
    else:
        yield it


def split_and_strip(value, sep=','):
    """Split a value based on the passed separator, and remove whitespace for each individual value."""
    if isinstance(value, str):
        return [
            item.strip()
            for item in value.split(sep)
            if value != ''
        ]
    else:
        return value


def safe_get(dct, keys, default=''):
    """
    Iterate over a dict with a tuple of keys to get the last value.

    :param dct: a dictionary
    :param keys: a tuple of keys
    :param default: default value to return in case of error
    :return: value from the last key in the tuple or default
    """
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return default
    return dct
