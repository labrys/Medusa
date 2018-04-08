# coding=utf-8



import errno
import logging
import traceback

import certifi
import requests

import medusa.common
from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.session import factory, hooks

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceAdapter(log)


class BaseSession(requests.Session):
    """Base Session object.

    This is a Medusa base session, used to create and configure a session object with Medusa specific base
    values.
    """

    default_headers = {
        'User-Agent': medusa.common.USER_AGENT,
        'Accept-Encoding': 'gzip,deflate',
    }


class MedusaSession(BaseSession):
    """Medusa default Session object.

    This is a Medusa base session, used to create and configure a session object with Medusa specific base
    values.

    :param verify: Enable/Disable SSL certificate verification.
    :param proxies: Provide a proxy configuration in the form of a dict: {
        "http": address,
        "https": address,
    }
    Optional arguments:
    :param hooks: Provide additional 'response' hooks, provided as a list of functions.
    :cache_control: Provide a cache control dict of cache_control options.
    :example: {'cache_etags': True, 'serializer': None, 'heuristic': None}
    :return: The response as text or False.
    """

    @staticmethod
    def _get_ssl_cert(verify):
        """
        Configure the ssl verification.

        We need to overwrite this in the request method. As it's not available in the session init.
        :param verify: SSL verification on or off.
        """
        return certifi.where() if all([app.SSL_VERIFY, verify]) else False

    def __init__(self, proxies=None, **kwargs):
        """Create base Medusa session instance."""
        # Add response hooks
        self.my_hooks = kwargs.pop('hooks', [])

        # Pop the cache_control config
        cache_control = kwargs.pop('cache_control', None)

        # Initialize request.session after we've done the pop's.
        super().__init__()

        # Add cache control of provided as a dict. Needs to be attached after super init.
        if cache_control:
            factory.add_cache_control(self, cache_control)

        # add proxies
        self.proxies = proxies or factory.add_proxies()

        # Configure global session hooks
        self.hooks['response'].append(hooks.log_url)

        # Extend the hooks with kwargs provided session hooks
        self.hooks['response'].extend(self.my_hooks)

        # Set default headers.
        self.headers.update(self.default_headers)

    def request(self, method, url, data=None, params=None, headers=None, timeout=30, verify=True, **kwargs):
        return super().request(method, url, data=data, params=params, headers=headers,
                               timeout=timeout, verify=self._get_ssl_cert(verify),
                               **kwargs)

    def get_json(self, url, method='GET', *args, **kwargs):
        """Overwrite request, to be able to return the json value if possible. Else it will fail silently."""
        resp = self.request(method, url, *args, **kwargs)
        try:
            return resp.json() if resp else resp
        except ValueError:
            return None

    def get_content(self, url, method='GET', *args, **kwargs):
        """Overwrite request, to be able to return the content if possible. Else it will fail silently."""
        resp = self.request(method, url, *args, **kwargs)
        return resp.content if resp else resp

    def get_text(self, url, method='GET', *args, **kwargs):
        """Overwrite request, to be able to return the text value if possible. Else it will fail silently."""
        resp = self.request(method, url, *args, **kwargs)
        return resp.text if resp else resp


class MedusaSafeSession(MedusaSession):
    """Medusa Safe Session object.

    This is a Medusa safe session object, used to create and configure a session protected with the most common
    exception handling.

    :param verify: Enable/Disable SSL certificate verification.
    :param proxies: Provide a proxy configuration in the form of a dict: {
        "http": address,
        "https": address,
    }
    Optional arguments:
    :param hooks: Provide additional 'response' hooks, provided as a list of functions.
    :cache_control: Provide a cache control dict of cache_control options.
    :example: {'cache_etags': True, 'serializer': None, 'heuristic': None}
    :return: The response as text or False.
    """