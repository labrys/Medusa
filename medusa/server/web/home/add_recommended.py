# coding=utf-8
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



from tornroutes import route

from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home


@route('/add_recommended(/?.*)')
class HomeAddRecommended(Home):
    """Landing page for the recommended shows."""

    def __init__(self, *args, **kwargs):
        """Initialize route."""
        super(HomeAddRecommended, self).__init__(*args, **kwargs)

    def index(self):
        """Render template for route /home/addRecommeded."""
        t = PageTemplate(rh=self, filename="add_recommended.mako")
        return t.render(title='Add Recommended Shows', header='Add Recommended Shows',
                        topmenu='home', controller="add_series", action="index")
