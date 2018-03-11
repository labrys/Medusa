# coding=utf-8



import markdown2
from tornroutes import route

from medusa import app
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home


@route('/news(/?.*)')
class HomeNews(Home):
    def __init__(self, *args, **kwargs):
        super(HomeNews, self).__init__(*args, **kwargs)

    def index(self):
        news = app.version_check_scheduler.action.check_for_new_news(force=True)
        if not news:
            news = 'Could not load news from the repository. [Click here for news.md]({url})'.format(url=app.NEWS_URL)

        app.NEWS_LAST_READ = app.NEWS_LATEST
        app.NEWS_UNREAD = 0
        app.instance.save_config()

        t = PageTemplate(rh=self, filename='markdown.mako')
        data = markdown2.markdown(news if news else 'The was a problem connecting to GitHub, please refresh and try again', extras=['header-ids'])

        return t.render(title='News', header='News', topmenu='system', data=data, controller='news', action='index')
