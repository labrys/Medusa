#!/usr/bin/env python2.7
# coding=UTF-8
# Author: Dennis Lutter <lad1337@gmail.com>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""Test searches."""

from __future__ import print_function

import unittest

import test_lib as test
from medusa import common, providers
from medusa.providers.generic_provider import GenericProvider
from medusa.tv import Episode, Series

TESTS = {
    "Game of Thrones": {
        "tvdbid": 121361, "s": 5, "e": [10],
        "s_strings": [{"Season": [u"Game of Thrones S05"]}],
        "e_strings": [{"Episode": [u"Game of Thrones S05E10"]}]
    }
}


class SearchTest(test.AppTestDBCase):
    """Test search."""

    def __init__(self, something):
        super(SearchTest, self).__init__(something)


def generator(cur_data, cur_name, cur_provider):
    """Generate test.

    :param cur_data:
    :param cur_name:
    :param cur_provider:
    :return:
    """
    def do_test(self):
        """Test to perform."""
        series = Series(1, int(cur_data["tvdbid"]))
        series.name = cur_name
        series.quality = common.ANY | common.Quality.UNKNOWN | common.Quality.RAWHDTV
        # series.save_to_db()
        # app.showList.append(series)

        for ep_number in cur_data["e"]:
            episode = Episode(series, cur_data["s"], ep_number)
            episode.status = common.WANTED

            # We aren't updating scene numbers, so fake it here
            episode.scene_season = cur_data["s"]
            episode.scene_episode = ep_number

            # episode.save_to_db()

            cur_provider.series = series
            season_strings = cur_provider._get_season_search_strings(episode)  # pylint: disable=protected-access
            episode_strings = cur_provider._get_episode_search_strings(episode)  # pylint: disable=protected-access

            fail = False
            cur_string = ''
            for cur_string in season_strings, episode_strings:
                if not all([isinstance(cur_string, list), isinstance(cur_string[0], dict)]):
                    print(" %s is using a wrong string format!" % cur_provider.name)
                    print(cur_string)
                    fail = True
                    continue

            if fail:
                continue

            try:
                assert season_strings == cur_data["s_strings"]
                assert episode_strings == cur_data["e_strings"]
            except AssertionError:
                print (" %s is using a wrong string format!" % cur_provider.name)
                print (cur_string)
                continue

            search_strings = episode_strings[0]
            # search_strings.update(season_strings[0])
            # search_strings.update({"RSS":['']})

            # print(search_strings)

            if not cur_provider.public:
                continue

            items = cur_provider.search(search_strings)  # pylint: disable=protected-access
            if not items:
                print("No results from cur_provider?")
                continue

            title, url = cur_provider._get_title_and_url(items[0])  # pylint: disable=protected-access
            for word in series.name.split(" "):
                if not word.lower() in title.lower():
                    print("Show cur_name not in title: %s. URL: %s" % (title, url))
                    continue

            if not url:
                print("url is empty")
                continue

            quality = cur_provider.get_quality(items[0])
            size = cur_provider._get_size(items[0])  # pylint: disable=protected-access

            if not series.quality & quality:
                print("Quality not in common.ANY, %r %s" % (quality, size))
                continue

    return do_test


# TODO: py.test parameters
if __name__ == '__main__':
    print("""
    ==================
    STARTING - Search TESTS
    ==================
    ######################################################################
    """)
    # create the test methods
    for force_search in (True, False):
        for name, data in TESTS.items():
            filename = name.replace(' ', '_')

            for provider in providers.sorted_provider_list():
                if provider.provider_type == GenericProvider.TORRENT:
                    if force_search:
                        test_name = 'test_manual_%s_%s_%s' % (filename, data["tvdbid"], provider.name)
                    else:
                        test_name = 'test_%s_%s_%s' % (filename, data["tvdbid"], provider.name)
                    test = generator(data, name, provider)
                    setattr(SearchTest, test_name, test)

    SUITE = unittest.TestLoader().loadTestsFromTestCase(SearchTest)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
