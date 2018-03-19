# coding=utf-8



import datetime
import json
import logging
import os
import re
from urllib.parse import unquote_plus

from simpleanidb import REQUEST_HOT
from tornroutes import route
from traktor import TraktApi

from medusa import app, classes, config, helpers, ui
from medusa.black_and_white_list import short_group_names
from medusa.common import Quality
from medusa.databases import db
from medusa.helper.common import sanitize_filename, try_int
from medusa.helpers import get_showname_from_indexer
from medusa.helpers.utils import generate
from medusa.indexers.api import IndexerAPI
from medusa.indexers.config import INDEXER_TVDB
from medusa.indexers.exceptions import IndexerException, IndexerUnavailable
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home
from medusa.show.recommendations.anidb import AnidbPopular
from medusa.show.recommendations.imdb import ImdbPopular
from medusa.show.recommendations.trakt import TraktPopular
from medusa.show.show import Show

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


@route('/add_series(/?.*)')
class HomeAddSeries(Home):
    def __init__(self, *args, **kwargs):
        super(HomeAddSeries, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='add_series.mako')
        return t.render(title='Add Shows', header='Add Shows', topmenu='home', controller='add_series', action='index')

    @staticmethod
    def get_indexer_languages():
        result = IndexerAPI().config['valid_languages']

        return json.dumps({'results': result})

    @staticmethod
    def sanitize_file_name(name):
        return sanitize_filename(name)

    @staticmethod
    def search_indexers_for_series_name(search_term, lang=None, indexer=None):
        if not lang or lang == 'null':
            lang = app.INDEXER_DEFAULT_LANGUAGE

        search_term = search_term

        search_terms = [search_term]

        # If search term ends with what looks like a year, enclose it in ()
        matches = re.match(r'^(.+ )([12][0-9]{3})$', search_term)
        if matches:
            search_terms.append('%s(%s)' % (matches.group(1), matches.group(2)))

        for searchTerm in search_terms:
            # If search term begins with an article, let's also search for it without
            matches = re.match(r'^(?:a|an|the) (.+)$', searchTerm, re.I)
            if matches:
                search_terms.append(matches.group(1))

        results = {}
        final_results = []

        # Query Indexers for each search term and build the list of results
        for indexer in IndexerAPI().indexers if not int(indexer) else [int(indexer)]:
            l_indexer_api_parms = IndexerAPI(indexer).api_params.copy()
            l_indexer_api_parms['language'] = lang
            l_indexer_api_parms['custom_ui'] = classes.AllShowsListUI
            try:
                indexer_api = IndexerAPI(indexer).indexer(**l_indexer_api_parms)
            except IndexerUnavailable as msg:
                log.info(u'Could not initialize Indexer {indexer}: {error}'.format(indexer=IndexerAPI(indexer).name, error=msg))
                continue

            log.debug(u'Searching for Show with searchterm(s): %s on Indexer: %s' % (search_terms, IndexerAPI(indexer).name))
            for searchTerm in search_terms:
                try:
                    indexer_results = indexer_api[searchTerm]
                    # add search results
                    results.setdefault(indexer, []).extend(indexer_results)
                except IndexerException as e:
                    log.info(u'Error searching for show: {error}'.format(error=e))

        for i, shows in results.items():
            indexer_api = IndexerAPI(i)
            result_set = {
                (
                    indexer_api.name,
                    i,
                    indexer_api.config['show_url'],
                    int(show['id']),
                    show['seriesname'],
                    show['firstaired'] or 'N/A',
                    show.get('network', '') or 'N/A',
                )
                for show in shows
            }
            final_results.extend(result_set)

        lang_id = IndexerAPI().config['langabbv_to_id'][lang]
        log.debug(final_results)
        log.debug(lang_id)
        return json.dumps({'results': final_results, 'langid': lang_id})

    def mass_add_table(self, root_dir=None):
        t = PageTemplate(rh=self, filename='home_mass_add_table.mako')

        if not root_dir:
            return 'No folders selected.'
        elif not isinstance(root_dir, list):
            root_dirs = [root_dir]
        else:
            root_dirs = root_dir

        root_dirs = [unquote_plus(x) for x in root_dirs]

        if app.ROOT_DIRS:
            default_index = int(app.ROOT_DIRS[0])
        else:
            default_index = 0

        if len(root_dirs) > default_index:
            tmp = root_dirs[default_index]
            if tmp in root_dirs:
                root_dirs.remove(tmp)
                root_dirs = [tmp] + root_dirs

        dir_list = []

        main_db_con = db.DBConnection()
        for root_dir in root_dirs:
            try:
                file_list = os.listdir(root_dir)
            except Exception as error:
                log.info('Unable to listdir {path}: {e!r}'.format(path=root_dir, e=error))
                continue

            for cur_file in file_list:

                try:
                    cur_path = os.path.normpath(os.path.join(root_dir, cur_file))
                    if not os.path.isdir(cur_path):
                        continue
                except Exception as error:
                    log.info('Unable to get current path {path} and {file}: {e!r}'.format(path=root_dir, file=cur_file, e=error))
                    continue

                cur_dir = {
                    'dir': cur_path,
                    'display_dir': '<b>{dir}{sep}</b>{base}'.format(
                        dir=os.path.dirname(cur_path), sep=os.sep, base=os.path.basename(cur_path)),
                }

                # see if the folder is in KODI already
                dir_results = main_db_con.select(
                    'SELECT indexer, indexer_id '
                    'FROM tv_shows '
                    'WHERE location = ? LIMIT 1',
                    [cur_path]
                )

                cur_dir['added_already'] = bool(dir_results)

                dir_list.append(cur_dir)

                indexer_id = show_name = indexer = None
                # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
                # is reset. This will prevent errors, when using multiple indexers and caching.
                for cur_provider in app.metadata_provider_dict.values():
                    if not (indexer_id and show_name):
                        (indexer_id, show_name, indexer) = cur_provider.retrieve_show_metadata(cur_path)

                cur_dir['existing_info'] = (indexer_id, show_name, indexer)

                if indexer_id and indexer and Show.find_by_id(app.showList, indexer, indexer_id):
                    cur_dir['added_already'] = True
        return t.render(dirList=dir_list)

    def new_series(self, show_to_add=None, other_shows=None, search_string=None):
        """
        Display new show page which collects a tvdb id, folder, and extra options and posts them to add_new_series.
        """
        t = PageTemplate(rh=self, filename='add_series_new_series.mako')
        log.debug('Attempting to add show: {}'.format(show_to_add))
        indexer, show_dir, indexer_id, show_name = self.split_extra_series(show_to_add)
        use_provided_info = bool(indexer_id and indexer and show_name)

        # use the given show_dir for the indexer search if available
        if not show_dir:
            if search_string:
                default_show_name = search_string
            else:
                default_show_name = ''

        elif not show_name:
            default_show_name = re.sub(r' \(\d{4}\)', '',
                                       os.path.basename(os.path.normpath(show_dir)))
        else:
            default_show_name = show_name

        # carry a list of other dirs if given
        if not other_shows:
            other_shows = []
        elif not isinstance(other_shows, list):
            other_shows = [other_shows]

        provided_indexer_id = int(indexer_id or 0)
        provided_indexer_name = show_name

        provided_indexer = int(indexer or app.INDEXER_DEFAULT)

        return t.render(
            enable_anime_options=True, use_provided_info=use_provided_info,
            default_show_name=default_show_name, other_shows=other_shows,
            provided_show_dir=show_dir, provided_indexer_id=provided_indexer_id,
            provided_indexer_name=provided_indexer_name, provided_indexer=provided_indexer,
            indexers=IndexerAPI().indexers, whitelist=[], blacklist=[], groups=[],
            title='New Show', header='New Show', topmenu='home',
            controller='add_series', action='new_series'
        )

    def trending_series(self, trakt_list=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and posts them to add_new_series
        """
        trakt_list = trakt_list if trakt_list else ''

        trakt_list = trakt_list.lower()

        if trakt_list == 'trending':
            page_title = 'Trakt Trending Shows'
        elif trakt_list == 'popular':
            page_title = 'Trakt Popular Shows'
        elif trakt_list == 'anticipated':
            page_title = 'Trakt Most Anticipated Shows'
        elif trakt_list == 'collected':
            page_title = 'Trakt Most Collected Shows'
        elif trakt_list == 'watched':
            page_title = 'Trakt Most Watched Shows'
        elif trakt_list == 'played':
            page_title = 'Trakt Most Played Shows'
        elif trakt_list == 'recommended':
            page_title = 'Trakt Recommended Shows'
        elif trakt_list == 'newshow':
            page_title = 'Trakt New Shows'
        elif trakt_list == 'newseason':
            page_title = 'Trakt Season Premieres'
        else:
            page_title = 'Trakt Most Anticipated Shows'

        t = PageTemplate(rh=self, filename="add_series_trending_series.mako")
        return t.render(title=page_title, header=page_title,
                        enable_anime_options=True, blacklist=[], whitelist=[], groups=[],
                        trakt_list=trakt_list, controller="add_series", action="trending_series",
                        realpage="trending_series")

    def get_trending_series(self, trakt_list=None):
        """Display the new show page which collects a tvdb id, folder, and extra options and posts them to add_new_series."""
        e = None
        t = PageTemplate(rh=self, filename="add_series_recommended.mako")
        trakt_list = trakt_list
        if trakt_list is None:
            trakt_list = ""

        trakt_list = trakt_list.lower()

        if trakt_list == "trending":
            page_url = "shows/trending"
        elif trakt_list == "popular":
            page_url = "shows/popular"
        elif trakt_list == "anticipated":
            page_url = "shows/anticipated"
        elif trakt_list == "collected":
            page_url = "shows/collected"
        elif trakt_list == "watched":
            page_url = "shows/watched"
        elif trakt_list == "played":
            page_url = "shows/played"
        elif trakt_list == "recommended":
            page_url = "recommendations/shows"
        elif trakt_list == "newshow":
            page_url = 'calendars/all/shows/new/%s/30' % datetime.date.today().strftime("%Y-%m-%d")
        elif trakt_list == "newseason":
            page_url = 'calendars/all/shows/premieres/%s/30' % datetime.date.today().strftime("%Y-%m-%d")
        else:
            page_url = "shows/anticipated"

        try:
            (trakt_blacklist, recommended_shows, removed_from_medusa) = TraktPopular().fetch_popular_series(page_url=page_url, trakt_list=trakt_list)
        except Exception as e:
            # print traceback.format_exc()
            trakt_blacklist = False
            recommended_shows = None
            removed_from_medusa = None

        return t.render(trakt_blacklist=trakt_blacklist, recommended_shows=recommended_shows, removed_from_medusa=removed_from_medusa,
                        exception=e, enable_anime_options=False, blacklist=[], whitelist=[], realpage="get_trending_series")

    def popular_series(self):
        """
        Fetches data from IMDB to show a list of popular shows.
        """
        t = PageTemplate(rh=self, filename="add_series_recommended.mako")

        recommended_shows = None
        error = None

        try:
            recommended_shows = ImdbPopular().fetch_popular_series()
        except Exception as e:
            log.debug(e)
            error = e
        finally:
            return t.render(
                title="Popular Shows",
                header="Popular Shows",
                recommended_shows=recommended_shows,
                exception=error,
                groups=[],
                topmenu="home",
                enable_anime_options=True,
                blacklist=[],
                whitelist=[],
                controller="add_series",
                action="recommended_series", realpage="popular_series")

    def popular_anime(self, list_type=REQUEST_HOT):
        """
        Fetches list recommeded shows from anidb.info.
        """
        t = PageTemplate(rh=self, filename="add_series_recommended.mako")
        e = None

        try:
            recommended_shows = AnidbPopular().fetch_popular_series(list_type)
        except Exception as e:
            # print traceback.format_exc()
            recommended_shows = None

        return t.render(title="Popular Anime Shows", header="Popular Anime Shows",
                        recommended_shows=recommended_shows, exception=e, groups=[],
                        topmenu="home", enable_anime_options=True, blacklist=[], whitelist=[],
                        controller="add_series", action="recommended_series", realpage="popular_anime")

    def add_series_to_blacklist(self, seriesid):
        # URL parameters
        data = {'shows': [{'ids': {'tvdb': seriesid}}]}

        trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        show_name = get_showname_from_indexer(INDEXER_TVDB, seriesid)
        try:
            trakt_api = TraktApi(timeout=app.TRAKT_TIMEOUT, ssl_verify=app.SSL_VERIFY, **trakt_settings)
            trakt_api.request('users/{0}/lists/{1}/items'.format
                              (app.TRAKT_USERNAME, app.TRAKT_BLACKLIST_NAME), data, method='POST')
            ui.notifications.message('Success!',
                                     "Added show '{0}' to blacklist".format(show_name))
        except Exception as e:
            ui.notifications.error('Error!',
                                   "Unable to add show '{0}' to blacklist. Check logs.".format(show_name))
            log.warning("Error while adding show '{0}' to trakt blacklist: {1}".format(show_name, e))

    def existing_series(self):
        """
        Prints out the page to add existing shows from a root dir.
        """
        t = PageTemplate(rh=self, filename='add_series_add_existing_series.mako')
        return t.render(enable_anime_options=True, blacklist=[], whitelist=[], groups=[],
                        title='Existing Show', header='Existing Show', topmenu='home',
                        controller='add_series', action='addExistingShow')

    def add_series_by_id(self, indexername=None, seriesid=None, show_name=None, which_series=None,
                         indexer_lang=None, root_dir=None, default_status=None,
                         quality_preset=None, any_qualities=None, best_qualities=None,
                         flatten_folders=None, subtitles=None, full_series_path=None,
                         other_shows=None, skip_series=None, provided_indexer=None,
                         anime=None, scene=None, blacklist=None, whitelist=None,
                         default_status_after=None, default_flatten_folders=None,
                         configure_show_options=False):
        """
        Add's a new show with provided show options by indexer_id.

        Currently only TVDB and IMDB id's supported.
        """
        series_id = seriesid
        if indexername != 'tvdb':
            series_id = helpers.get_tvdb_from_id(seriesid, indexername.upper())
            if not series_id:
                log.info(u'Unable to to find tvdb ID to add %s' % show_name)
                ui.notifications.error(
                    'Unable to add %s' % show_name,
                    'Could not add %s.  We were unable to locate the tvdb id at this time.' % show_name
                )
                return

        if Show.find_by_id(app.showList, INDEXER_TVDB, series_id):
            return

        # Sanitize the parameter allowed_qualities and preferred_qualities. As these would normally be passed as lists
        if any_qualities:
            any_qualities = any_qualities.split(',')
        else:
            any_qualities = []

        if best_qualities:
            best_qualities = best_qualities.split(',')
        else:
            best_qualities = []

        # If configure_show_options is enabled let's use the provided settings
        configure_show_options = config.checkbox_to_value(configure_show_options)

        if configure_show_options:
            # prepare the inputs for passing along
            scene = config.checkbox_to_value(scene)
            anime = config.checkbox_to_value(anime)
            flatten_folders = config.checkbox_to_value(flatten_folders)
            subtitles = config.checkbox_to_value(subtitles)

            if whitelist:
                whitelist = short_group_names(whitelist)
            if blacklist:
                blacklist = short_group_names(blacklist)

            if not any_qualities:
                any_qualities = []

            if not best_qualities or try_int(quality_preset, None):
                best_qualities = []

            if not isinstance(any_qualities, list):
                any_qualities = [any_qualities]

            if not isinstance(best_qualities, list):
                best_qualities = [best_qualities]

            quality = Quality.combine_qualities([int(q) for q in any_qualities], [int(q) for q in best_qualities])

            location = root_dir

        else:
            default_status = app.STATUS_DEFAULT
            quality = app.QUALITY_DEFAULT
            flatten_folders = app.FLATTEN_FOLDERS_DEFAULT
            subtitles = app.SUBTITLES_DEFAULT
            anime = app.ANIME_DEFAULT
            scene = app.SCENE_DEFAULT
            default_status_after = app.STATUS_DEFAULT_AFTER

            if app.ROOT_DIRS:
                root_dirs = app.ROOT_DIRS
                location = root_dirs[int(root_dirs[0]) + 1]
            else:
                location = None

        if not location:
            log.warning(u'There was an error creating the show, no root directory setting found')
            return 'No root directories setup, please go back and add one.'

        show_name = get_showname_from_indexer(INDEXER_TVDB, series_id)
        show_dir = None

        # add the show
        app.show_queue_scheduler.action.add_show(INDEXER_TVDB, int(series_id), show_dir, int(default_status), quality,
                                                 flatten_folders, indexer_lang, subtitles, anime, scene, None, blacklist,
                                                 whitelist, int(default_status_after), root_dir=location)

        ui.notifications.message('Show added', 'Adding the specified show {0}'.format(show_name))

        # done adding show
        return self.redirect('/home/')

    def add_new_series(self, which_series=None, indexer_lang=None, root_dir=None, default_status=None, quality_preset=None,
                       allowed_qualities=None, preferred_qualities=None, flatten_folders=None, subtitles=None,
                       full_series_path=None, other_shows=None, skip_series=None, provided_indexer=None, anime=None,
                       scene=None, blacklist=None, whitelist=None, default_status_after=None):
        """
        Receive tvdb id, dir, and other options and create a show from them. If extra show dirs are
        provided then it forwards back to new_series, if not it goes to /home.
        """
        provided_indexer = provided_indexer

        indexer_lang = app.INDEXER_DEFAULT_LANGUAGE if not indexer_lang else indexer_lang

        # grab our list of other dirs if given
        if not other_shows:
            other_shows = []
        elif not isinstance(other_shows, list):
            other_shows = [other_shows]

        def finish_add_series():
            # if there are no extra shows then go home
            if not other_shows:
                return self.redirect('/home/')

            # peel off the next one
            next_show_dir = other_shows[0]
            rest_of_show_dirs = other_shows[1:]

            # go to add the next show
            return self.new_series(next_show_dir, rest_of_show_dirs)

        # if we're skipping then behave accordingly
        if skip_series:
            return finish_add_series()

        # sanity check on our inputs
        if (not root_dir and not full_series_path) or not which_series:
            return 'Missing params, no Indexer ID or folder:{series!r} and {root!r}/{path!r}'.format(
                series=which_series, root=root_dir, path=full_series_path)

        # figure out what show we're adding and where
        series_pieces = which_series.split('|')
        if (which_series and root_dir) or (which_series and full_series_path and len(series_pieces) > 1):
            if len(series_pieces) < 6:
                log.error(u'Unable to add show due to show selection. Not enough arguments: %s' % (repr(series_pieces)))
                ui.notifications.error('Unknown error. Unable to add show due to problem with show selection.')
                return self.redirect('/add_series/existing_series/')

            indexer = int(series_pieces[1])
            indexer_id = int(series_pieces[3])
            show_name = series_pieces[4]
        else:
            # if no indexer was provided use the default indexer set in General settings
            if not provided_indexer:
                provided_indexer = app.INDEXER_DEFAULT

            indexer = int(provided_indexer)
            indexer_id = int(which_series)
            show_name = os.path.basename(os.path.normpath(full_series_path))

        # use the whole path if it's given, or else append the show name to the root dir to get the full show path
        if full_series_path:
            show_dir = os.path.normpath(full_series_path)
        else:
            show_dir = os.path.join(root_dir, sanitize_filename(show_name))

        # blanket policy - if the dir exists you should have used 'add existing show' numbnuts
        if os.path.isdir(show_dir) and not full_series_path:
            ui.notifications.error('Unable to add show', 'Folder {path} exists already'.format(path=show_dir))
            return self.redirect('/add_series/existing_series/')

        # don't create show dir if config says not to
        if app.ADD_SHOWS_WO_DIR:
            log.info(u'Skipping initial creation of {path} due to config.ini setting'.format(path=show_dir))
        else:
            dir_exists = helpers.make_dir(show_dir)
            if not dir_exists:
                log.error(u'Unable to create the folder {path}, can\'t add the show'.format(path=show_dir))
                ui.notifications.error('Unable to add show',
                                       'Unable to create the folder {path}, can\'t add the show'.format(path=show_dir))
                # Don't redirect to default page because user wants to see the new show
                return self.redirect('/home/')
            else:
                helpers.chmod_as_parent(show_dir)

        # prepare the inputs for passing along
        scene = config.checkbox_to_value(scene)
        anime = config.checkbox_to_value(anime)
        flatten_folders = config.checkbox_to_value(flatten_folders)
        subtitles = config.checkbox_to_value(subtitles)

        if whitelist:
            whitelist = short_group_names(whitelist)
        if blacklist:
            blacklist = short_group_names(blacklist)

        if not allowed_qualities:
            allowed_qualities = []
        if not preferred_qualities or try_int(quality_preset, None):
            preferred_qualities = []
        if not isinstance(allowed_qualities, list):
            allowed_qualities = [allowed_qualities]
        if not isinstance(preferred_qualities, list):
            preferred_qualities = [preferred_qualities]
        new_quality = Quality.combine_qualities([int(q) for q in allowed_qualities], [int(q) for q in preferred_qualities])

        # add the show
        app.show_queue_scheduler.action.add_show(indexer, indexer_id, show_dir, int(default_status), new_quality,
                                                 flatten_folders, indexer_lang, subtitles, anime,
                                                 scene, None, blacklist, whitelist, int(default_status_after))
        ui.notifications.message('Show added', 'Adding the specified show into {path}'.format(path=show_dir))

        return finish_add_series()

    @staticmethod
    def split_extra_series(extra_show):
        if not extra_show:
            return None, None, None, None
        split_vals = extra_show.split('|')
        if len(split_vals) < 4:
            indexer = split_vals[0]
            show_dir = split_vals[1]
            return indexer, show_dir, None, None
        indexer = split_vals[0]
        show_dir = split_vals[1]
        indexer_id = split_vals[2]
        show_name = '|'.join(split_vals[3:])

        return indexer, show_dir, indexer_id, show_name

    def add_existing_series(self, series_to_add=None, prompt_for_settings=None):
        """
        Receives a dir list and add them. Adds the ones with given TVDB IDs first, then forwards along to the new_series page.
        """
        log.debug('Attempting to add: {!r}'.format(series_to_add))
        prompt_for_settings = prompt_for_settings

        # grab a list of other shows to add, if provided
        series_to_add = [
            unquote_plus(show)
            for show in generate(series_to_add)
        ]

        prompt_for_settings = config.checkbox_to_value(prompt_for_settings)

        indexer_id_given = []
        dirs_only = []
        # separate all the ones with Indexer IDs
        for cur_dir in series_to_add:
            log.debug('Processing: {!r}'.format(cur_dir))
            if '|' in cur_dir:
                split_vals = cur_dir.split('|')
                if len(split_vals) < 3:
                    dirs_only.append(cur_dir)
            if '|' not in cur_dir:
                dirs_only.append(cur_dir)
            else:
                indexer, show_dir, indexer_id, show_name = self.split_extra_series(cur_dir)
                if indexer and show_dir and not indexer_id:
                    dirs_only.append(cur_dir)

                if not show_dir or not indexer_id or not show_name:
                    continue

                indexer_id_given.append((int(indexer), show_dir, int(indexer_id), show_name))

        # if they want me to prompt for settings then I will just carry on to the new_series page
        if prompt_for_settings and series_to_add:
            return self.new_series(series_to_add[0], series_to_add[1:])

        # if they don't want me to prompt for settings then I can just add all the nfo shows now
        num_added = 0
        for cur_show in indexer_id_given:
            indexer, show_dir, indexer_id, show_name = cur_show

            if indexer is not None and indexer_id is not None:
                # add the show
                app.show_queue_scheduler.action.add_show(
                    indexer, indexer_id, show_dir,
                    default_status=app.STATUS_DEFAULT,
                    quality=app.QUALITY_DEFAULT,
                    flatten_folders=app.FLATTEN_FOLDERS_DEFAULT,
                    subtitles=app.SUBTITLES_DEFAULT,
                    anime=app.ANIME_DEFAULT,
                    scene=app.SCENE_DEFAULT,
                    default_status_after=app.STATUS_DEFAULT_AFTER
                )
                num_added += 1

        if num_added:
            ui.notifications.message('Shows Added',
                                     'Automatically added {quantity} from their existing metadata files'.format(quantity=num_added))

        # if we're done then go home
        if not dirs_only:
            return self.redirect('/home/')

        # for the remaining shows we need to prompt for each one, so forward this on to the new_series page
        return self.new_series(dirs_only[0], dirs_only[1:])
