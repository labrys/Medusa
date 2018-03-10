# coding=utf-8

import logging
import os

from requests.compat import urlencode
from six.moves.urllib.error import HTTPError
from six.moves.urllib.request import Request, urlopen

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def notify_snatch(self, ep_name, is_proper):
        pass

    def notify_download(self, ep_name):
        pass

    def notify_subtitle_download(self, ep_name, lang):
        pass

    def notify_git_update(self, new_version):
        pass

    def notify_login(self, ipaddress=''):
        pass

    def update_library(self, ep_obj):

        # Values from config

        if not app.USE_PYTIVO:
            return False

        host = app.PYTIVO_HOST
        share_name = app.PYTIVO_SHARE_NAME
        tsn = app.PYTIVO_TIVO_NAME

        # There are two more values required, the container and file.
        #
        # container: The share name, show name and season
        #
        # file: The file name
        #
        # Some slicing and dicing of variables is required to get at these values.
        #
        # There might be better ways to arrive at the values, but this is the best I have been able to
        # come up with.
        #

        # Calculated values
        show_path = ep_obj.series.location
        show_name = ep_obj.series.name
        root_show_and_season = os.path.dirname(ep_obj.location)
        abs_path = ep_obj.location

        # Some show names have colons in them which are illegal in a path location, so strip them out.
        # (Are there other characters?)
        show_name = show_name.replace(':', '')

        root = show_path.replace(show_name, '')
        show_and_season = root_show_and_season.replace(root, '')

        container = share_name + '/' + show_and_season
        filename = '/' + abs_path.replace(root, '')

        # Finally create the url and make request
        request_url = 'http://' + host + '/TiVoConnect?' + urlencode(
            {'Command': 'Push', 'Container': container, 'File': filename, 'tsn': tsn})

        log.debug(u'pyTivo notification: Requesting {0}', request_url)

        request = Request(request_url)

        try:
            urlopen(request)
        except HTTPError as e:
            if hasattr(e, 'reason'):
                log.error(u'pyTivo notification: Error, failed to reach a server - {0}', e.reason)
                return False
            elif hasattr(e, 'code'):
                log.error(u'pyTivo notification: Error, the server could not fulfill the request - {0}', e.code)
            return False
        except Exception as e:
            log.error(u'PYTIVO: Unknown exception: {0}', e)
            return False
        else:
            log.info(u'pyTivo notification: Successfully requested transfer of file')
            return True
