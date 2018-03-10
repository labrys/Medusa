# coding=utf-8

from __future__ import unicode_literals

from tornroutes import route

from medusa import app, ui
from medusa.helper.common import try_int
from medusa.server.web.core.base import PageTemplate, WebRoot
from medusa.show.history import History as HistoryTool


@route('/history(/?.*)')
class History(WebRoot):
    def __init__(self, *args, **kwargs):
        super(History, self).__init__(*args, **kwargs)

        self.history = HistoryTool()

    def index(self, limit=None):
        if limit is None:
            if app.HISTORY_LIMIT:
                limit = int(app.HISTORY_LIMIT)
            else:
                limit = 100
        else:
            limit = try_int(limit, 100)

        app.HISTORY_LIMIT = limit

        app.instance.save_config()

        history = self.history.get(limit)

        t = PageTemplate(rh=self, filename='history.mako')
        submenu = [
            {'title': 'Clear History', 'path': 'history/clear_history', 'icon': 'ui-icon ui-icon-trash', 'class': 'clearhistory', 'confirm': True},
            {'title': 'Trim History', 'path': 'history/trim_history', 'icon': 'menu-icon-cut', 'class': 'trimhistory', 'confirm': True},
        ]

        return t.render(historyResults=history.detailed, compactResults=history.compact, limit=limit,
                        submenu=submenu[::-1], title='History', header='History',
                        topmenu='history', controller='history', action='index')

    def clear_history(self):
        # @TODO: Replace this with DELETE /api/v2/history
        self.history.clear()

        ui.notifications.message('History cleared')

        return self.redirect('/history/')

    def trim_history(self):
        # @TODO: Replace this with DELETE /api/v2/history?gt={days}
        # gt and lt would be greater than and less than x days old
        self.history.trim()

        ui.notifications.message('Removed history entries older than 30 days')

        return self.redirect('/history/')
