# coding=utf-8

import logging
import os
import subprocess

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier:
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

    def move_folder(self, old_path, new_path):
        self.move_object(old_path, new_path)

    def move_file(self, old_file, new_file):
        self.move_object(old_file, new_file)

    def move_object(self, old_path, new_path):
        if app.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-N', os.path.abspath(new_path),
                             os.path.abspath(old_path)]
            log.debug(u'Executing command {0}', synoindex_cmd)
            log.debug(u'Absolute path to command: {0}', os.path.abspath(synoindex_cmd[0]))
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     cwd=app.PROG_DIR)
                out, _ = p.communicate()
                log.debug(u'Script result: {0}', out)
            except OSError as e:
                log.error(u'Unable to run synoindex: {0}', e)

    def delete_folder(self, cur_path):
        self.make_object('-D', cur_path)

    def add_folder(self, cur_path):
        self.make_object('-A', cur_path)

    def delete_file(self, cur_file):
        self.make_object('-d', cur_file)

    def add_file(self, cur_file):
        self.make_object('-a', cur_file)

    def make_object(self, cmd_arg, cur_path):
        if app.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', cmd_arg, os.path.abspath(cur_path)]
            log.debug(u'Executing command {0}', synoindex_cmd)
            log.debug(u'Absolute path to command: {0}', os.path.abspath(synoindex_cmd[0]))
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     cwd=app.PROG_DIR)
                out, _ = p.communicate()
                log.debug(u'Script result: {0}', out)
            except OSError as e:
                log.error(u'Unable to run synoindex: {0}', e)
