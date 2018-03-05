
"""Black and White List module."""

from __future__ import unicode_literals

import logging

from adba.aniDBerrors import AniDBCommandTimeoutError

from medusa import app, db, helpers
from medusa.logger.adapters.style import BraceAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceAdapter(log)


class BlackAndWhiteList(object):
    """Black and White List."""

    def __init__(self, series_obj):
        """Init method.

        :param series_obj:
        :type series_obj: Series
        """
        if not series_obj.indexerid:
            raise BlackWhitelistNoShowIDException()
        self.series_obj = series_obj
        self.blacklist = []
        self.whitelist = []
        self.load()

    def load(self):
        """Build black and whitelist."""
        log.debug('Building black and white list for {id}',
                  {'id': self.series_obj.name})
        self.blacklist = self._load_list('blacklist')
        self.whitelist = self._load_list('whitelist')

    def _add_keywords(self, table, values):
        """Add keywords into database for current show.

        :param table: SQL table to add keywords to
        :param values: Values to be inserted in table
        """
        main_db_con = db.DBConnection()
        for value in values:
            main_db_con.action(
                'INSERT INTO [{table}] (show_id, keyword, indexer_id) '
                'VALUES (?, ?, ?)'.format(table=table),
                [self.series_obj.series_id, value, self.series_obj.indexer]
            )

    def set_black_keywords(self, values):
        """Set blacklist to new value.

        :param values: Complete list of keywords to be set as blacklist
        """
        self._del_all_keywords('blacklist')
        self._add_keywords('blacklist', values)
        self.blacklist = values
        log.debug('Blacklist set to: {blacklist}',
                  {'blacklist': self.blacklist})

    def set_white_keywords(self, values):
        """Set whitelist to new values.

        :param values: Complete list of keywords to be set as whitelist
        """
        self._del_all_keywords('whitelist')
        self._add_keywords('whitelist', values)
        self.whitelist = values
        log.debug('Whitelist set to: {whitelist}',
                  {'whitelist': self.whitelist})

    def _del_all_keywords(self, table):
        """Remove all keywords for current show.

        :param table: SQL table remove keywords from
        """
        main_db_con = db.DBConnection()
        main_db_con.action(
            'DELETE FROM [{table}] '
            'WHERE show_id = ? AND indexer_id = ?'.format(table=table),
            [self.series_obj.series_id, self.series_obj.indexer]
        )

    def _load_list(self, table):
        """Fetch keywords for current show.

        :param table: Table to fetch list of keywords from

        :return: keywords in list
        """
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            'SELECT keyword '
            'FROM [{table}] '
            'WHERE show_id = ? AND indexer_id = ?'.format(table=table),
            [self.series_obj.series_id, self.series_obj.indexer]
        )

        groups = [result['keyword']
                  for result in sql_results
                  ] if sql_results else []

        if groups:
            log.debug(
                'BWL: {id} loaded keywords from {table}: {groups}', {
                    'id': self.series_obj.series_id,
                    'table': table,
                    'groups': groups,
                }
            )

        return groups

    def is_valid(self, result):
        """Check if result is valid according to white/blacklist for current show.

        :param result: Result to analyse
        :return: False if result is not allowed in white/blacklist, True if it is
        """
        if not (self.whitelist or self.blacklist):
            log.debug(u'No Whitelist and Blacklist defined, check passed.')
            return True
        elif not result.release_group:
            log.debug('Invalid result, no release group detected')
            return False

        whitelist = [x.lower() for x in self.whitelist]
        white_result = result.release_group.lower() in whitelist if self.whitelist else True

        blacklist = [x.lower() for x in self.blacklist]
        black_result = result.release_group.lower() not in blacklist if self.blacklist else True

        log.debug(
            'Whitelist check: {white}. Blacklist check: {black}', {
                'white': 'Passed' if white_result else 'Failed',
                'black': 'Passed' if black_result else 'Failed',
            }
        )
        return white_result and black_result


class BlackWhitelistNoShowIDException(Exception):
    """No show_id was given."""


def short_group_names(groups):
    """Find AniDB short group names for release groups.

    :param groups: list of groups to find short group names for
    :return: list of shortened group names
    """
    groups = groups.split(',')
    short_group_list = []
    if helpers.set_up_anidb_connection():
        for group_name in groups:
            try:
                group = app.ADBA_CONNECTION.group(gname=group_name)
            except AniDBCommandTimeoutError:
                log.debug('Timeout loading AniDB group.'
                          ' Trying next group')
            except Exception:
                log.debug('Failed while loading AniDB group.'
                          ' Trying next group')
            else:
                for line in group.datalines:
                    if line['shortname']:
                        short_group_list.append(line['shortname'])
                    else:
                        if group_name not in short_group_list:
                            short_group_list.append(group_name)
    else:
        short_group_list = groups
    return short_group_list
