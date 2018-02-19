# coding=utf-8

"""
NZB Client API for NZBGet.

https://nzbget.net/
https://nzbget.net/api/
https://github.com/nzbget/nzbget
"""

from __future__ import unicode_literals

import datetime
import logging
from base64 import standard_b64encode

from six.moves.http_client import socket
from six.moves.xmlrpc_client import ProtocolError, ServerProxy

from medusa import app
from medusa.common import Quality
from medusa.helper.common import try_int
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def nzb_connection(url):
    """
    Connect to NZBget client.

    :param url: nzb url to connect
    :return: True if connected, else False
    """
    nzb_get_rpc = ServerProxy(url)
    try:
        if nzb_get_rpc.writelog('INFO', 'Medusa connected to test connection.'):
            log.debug('Successfully connected to NZBget')
        else:
            log.warning('Successfully connected to NZBget but unable to'
                        ' send a message')
        return True

    except socket.error:
        log.warning('Please check your NZBget host and port (if it is'
                    ' running). NZBget is not responding to this combination')
        return False

    except ProtocolError as e:
        if e.errmsg == 'Unauthorized':
            log.warning('NZBget username or password is incorrect.')
        else:
            log.error('Protocol Error: {msg}', {'msg': e.errmsg})
        return False


def test_nzb(host, username, password, use_https):
    """Test NZBget client connection.

    :param host: nzb host to connect
    :param username: nzb username
    :param password: nzb password
    :param use_https: If we should use https or not

    :return  True if connected. Else False
    """
    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if use_https else '',
        username,
        password,
        host)
    return nzb_connection(url)


def send_nzb(nzb, proper=False):
    """
    Send NZB to NZBGet client.

    :param nzb: nzb object
    :param proper: True if a Proper download, False if not.
    """
    if app.NZBGET_HOST is None:
        log.warning('No NZBget host found in configuration.'
                    ' Please configure it.')
        return False

    add_to_top = False
    nzbget_priority = 0
    category = app.NZBGET_CATEGORY
    if nzb.series.is_anime:
        category = app.NZBGET_CATEGORY_ANIME

    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if app.NZBGET_USE_HTTPS else '',
        app.NZBGET_USERNAME,
        app.NZBGET_PASSWORD,
        app.NZBGET_HOST)

    if not nzb_connection(url):
        return False

    nzb_get_rpc = ServerProxy(url)

    duplicate_key = ''
    duplicate_score = 0
    # if it aired recently make it high priority and generate DupeKey/Score
    for cur_ep in nzb.episodes:
        if duplicate_key == '':
            if cur_ep.series.indexer == 1:
                duplicate_key = 'Medusa-' + str(cur_ep.series.indexerid)
            elif cur_ep.series.indexer == 2:
                duplicate_key = 'Medusa-tvr' + str(cur_ep.series.indexerid)
        duplicate_key += '-' + str(cur_ep.season) + '.' + str(cur_ep.episode)
        if datetime.date.today() - cur_ep.airdate <= datetime.timedelta(days=7):
            add_to_top = True
            nzbget_priority = app.NZBGET_PRIORITY
        else:
            category = app.NZBGET_CATEGORY_BACKLOG
            if nzb.series.is_anime:
                category = app.NZBGET_CATEGORY_ANIME_BACKLOG

    if nzb.quality != Quality.UNKNOWN:
        duplicate_score = nzb.quality * 100
    if proper:
        duplicate_score += 10

    nzbcontent64 = None
    if nzb.result_type == 'nzbdata':
        data = nzb.extra_info[0]
        nzbcontent64 = standard_b64encode(data)

    log.info('Sending NZB to NZBget')
    log.debug('URL: {}', url)

    try:
        # Find out if nzbget supports priority (Version 9.0+),
        # old versions beginning with a 0.x will use the old command
        nzbget_version_str = nzb_get_rpc.version()
        nzbget_version = try_int(
            nzbget_version_str[:nzbget_version_str.find('.')]
        )
        if nzbget_version == 0:
            if nzbcontent64:
                nzbget_result = nzb_get_rpc.append(
                    nzb.name + '.nzb',
                    category,
                    add_to_top,
                    nzbcontent64
                )
            else:
                if nzb.result_type == 'nzb':
                    if not nzb.provider.login():
                        return False

                    # TODO: Check if this needs exception handling
                    data = nzb.provider.session(nzb.url).content
                    if data is None:
                        return False

                    nzbcontent64 = standard_b64encode(data)

                nzbget_result = nzb_get_rpc.append(
                    nzb.name + '.nzb',
                    category,
                    add_to_top,
                    nzbcontent64
                )
        elif nzbget_version == 12:
            if nzbcontent64 is not None:
                nzbget_result = nzb_get_rpc.append(
                    nzb.name + '.nzb', category, nzbget_priority, False,
                    nzbcontent64, False, duplicate_key, duplicate_score, 'score'
                )
            else:
                nzbget_result = nzb_get_rpc.appendurl(
                    nzb.name + '.nzb', category, nzbget_priority, False, nzb.url,
                    False, duplicate_key, duplicate_score, 'score'
                )
        # v13+ has a new combined append method that accepts both (url and
        # content) also the return value has changed from boolean to integer
        # (Positive number representing NZBID of the queue item. 0 and negative
        # numbers represent error codes.)
        elif nzbget_version >= 13:
            nzbget_result = nzb_get_rpc.append(
                nzb.name + '.nzb',
                nzbcontent64 if nzbcontent64 is not None else nzb.url,
                category, nzbget_priority, False, False, duplicate_key, duplicate_score,
                'score'
            ) > 0
        else:
            if nzbcontent64 is not None:
                nzbget_result = nzb_get_rpc.append(
                    nzb.name + '.nzb', category, nzbget_priority, False,
                    nzbcontent64
                )
            else:
                nzbget_result = nzb_get_rpc.appendurl(
                    nzb.name + '.nzb', category, nzbget_priority, False, nzb.url
                )

        if nzbget_result:
            log.debug('NZB sent to NZBget successfully')
            return True
        else:
            log.warning('NZBget could not add {name}.nzb to the queue',
                        {'name': nzb.name})
            return False
    except Exception:
        log.warning('Connect Error to NZBget: could not add {file}.nzb to the'
                    ' queue', {'name': nzb.name})
        return False
