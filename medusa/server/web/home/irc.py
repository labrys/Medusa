# coding=utf-8



from tornroutes import route

from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home


@route('/IRC(/?.*)')
class HomeIRC(Home):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='IRC.mako')
        return t.render(topmenu='system', header='IRC', title='IRC', controller='IRC', action='index')
