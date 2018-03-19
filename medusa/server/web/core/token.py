# coding=utf-8
"""Handle the requests fro /token."""


from tornado.web import authenticated

from medusa import app
from medusa.server.web.core.base import BaseHandler


class TokenHandler(BaseHandler):
    """Handle the request for /token, and return the app.API_KEY if authenticated."""

    def __init__(self, *args, **kwargs):
        """Initialize token handler."""
        super().__init__(*args, **kwargs)

    @authenticated
    def get(self, *args, **kwargs):
        """Return the app.API_KEY for /token get requests."""
        self.finish({'token': app.API_KEY})
