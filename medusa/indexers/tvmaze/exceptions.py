"""Custom exceptions used or raised by tvdb_api."""

__author__ = "p0psicles"
__version__ = "1.0"

__all__ = ["tvdb_error", "tvdb_userabort", "tvdb_shownotfound", "tvdb_showincomplete",
           "tvdb_seasonnotfound", "tvdb_episodenotfound", "tvdb_attributenotfound"]


class tvdb_exception(Exception):
    """Any exception generated by tvdb_api."""


class tvdb_error(tvdb_exception):
    """An error with thetvdb.com (Cannot connect, for example)."""


class tvdb_userabort(tvdb_exception):
    """User aborted the interactive selection (via the q command, ^c etc)."""


class tvdb_shownotfound(tvdb_exception):
    """Show cannot be found on thetvdb.com (non-existant show)."""


class tvdb_showincomplete(tvdb_exception):
    """Show found but incomplete on thetvdb.com (incomplete show)."""


class tvdb_seasonnotfound(tvdb_exception):
    """Season cannot be found on thetvdb.com."""


class tvdb_episodenotfound(tvdb_exception):
    """Episode cannot be found on thetvdb.com"""


class tvdb_attributenotfound(tvdb_exception):
    """Raised if an episode does not have the requested attribute (such as a episode name)."""
