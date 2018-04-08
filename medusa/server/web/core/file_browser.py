# coding=utf-8



import json
import os

from tornroutes import route

from medusa.browser import list_folders
from medusa.server.web.core.base import WebRoot


@route('/browser(/?.*)')
class WebFileBrowser(WebRoot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def index(self, path='', include_files=False, *args, **kwargs):
        # @TODO: Move all cache control headers to the whole API end point so nothing's cached
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'application/json')
        return json.dumps(list_folders(path, True, bool(int(include_files))))

    def complete(self, term, include_files=0, *args, **kwargs):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'application/json')
        paths = [entry['path'] for entry in list_folders(os.path.dirname(term), include_files=bool(int(include_files)))
                 if 'path' in entry]

        return json.dumps(paths)
