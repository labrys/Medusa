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

"""Test XEM."""

from __future__ import print_function, unicode_literals

import re

from medusa import app
from medusa.tv import Series
from tests.legacy import test_lib as test


class XEMBasicTests(test.AppTestDBCase):
    """Perform basic xem tests."""

    @staticmethod
    def load_shows_from_db():
        """Populate the showList with shows from the database."""
        test_main_db_con = medusa.databases.db.DBConnection()
        sql_results = test_main_db_con.select("SELECT * FROM tv_shows")

        for sql_show in sql_results:
            try:
                cur_show = Series(int(sql_show["indexer"]), int(sql_show["indexer_id"]))
                app.showList.append(cur_show)
            except Exception:  # pylint: disable=broad-except
                pass

    @staticmethod
    def load_from_db():
        """Populate the showList with shows from the database."""
        test_main_db_con = medusa.databases.db.DBConnection()
        sql_results = test_main_db_con.select("SELECT * FROM tv_shows")

        for sql_show in sql_results:
            try:
                cur_show = Series(int(sql_show["indexer"]), int(sql_show["indexer_id"]))
                app.showList.append(cur_show)
            except Exception as error:  # pylint: disable=broad-except
                print("There was an error creating the show {}".format(error))

    @staticmethod
    def test_formatting():
        name = "Game.of.Thrones.S03.720p.HDTV.x264-CtrlHD"
        release = "Game of Thrones"

        # m = re.match('(?P<ep_ab_num>(?>\d{1,3})(?![ip])).+', name)

        escaped_name = re.sub('\\\\[\\s.-]', r'\W+', re.escape(release))
        cur_regex = '^' + escaped_name + r'\W+(?:(?:S\d[\dE._ -])|' + \
            r'(?:\d\d?x)|(?:\d{4}\W\d\d\W\d\d)|(?:(?:part|pt)[\._ -]?(\d|[ivx]))|' + \
            r'Season\W+\d+\W+|E\d+\W+|(?:\d{1,3}.+\d{1,}[a-zA-Z]{2}\W+[a-zA-Z]{3,}\W+\d{4}.+))'

        # print("Checking if show " + name + " matches " + curRegex)

        match = re.search(cur_regex, name, re.I)
        if match:
            # print("Matched " + curRegex + " to " + name)
            pass
