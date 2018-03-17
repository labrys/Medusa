# coding=utf-8



from tornroutes import route

from medusa.processing import tv
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home


@route('/home/postprocess(/?.*)')
class HomePostProcess(Home):
    def __init__(self, *args, **kwargs):
        super(HomePostProcess, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='home_post_process.mako')
        return t.render(title='Post Processing', header='Post Processing', topmenu='home',
                        controller='home', action='post_process')

    def process_episode(self, proc_dir=None, nzb_name=None, job_name=None, quiet=None, process_method=None, force=None,
                        is_priority=None, delete_on='0', failed='0', proc_type='auto', ignore_subs=None, *args, **kwargs):

        def arg_to_bool(argument):
            if isinstance(argument, str):
                _arg = argument.strip().lower()
            else:
                _arg = argument

            if _arg in ['1', 'on', 'true', True]:
                return True
            elif _arg in ['0', 'off', 'false', False]:
                return False

            return argument

        if not proc_dir:
            return self.redirect('/home/postprocess/')
        else:
            resource_name = nzb_name or None

            result = tv.ProcessResult(proc_dir, process_method=process_method).process(
                resource_name=resource_name, force=arg_to_bool(force), is_priority=arg_to_bool(is_priority),
                delete_on=arg_to_bool(delete_on), failed=arg_to_bool(failed), proc_type=type,
                ignore_subs=arg_to_bool(ignore_subs)
            )

            if quiet is not None and int(quiet) == 1:
                return result

            result = result.replace('\n', '<br>\n')
            return self._generic_message('Postprocessing results', result)
