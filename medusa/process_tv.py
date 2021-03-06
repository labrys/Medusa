# coding=utf-8

"""Process TV module."""

from __future__ import unicode_literals

import logging
import os
import shutil
import stat

from medusa import app, db, failed_processor, helpers, notifiers, post_processor
from medusa.clients import torrent
from medusa.helper.common import is_sync_file
from medusa.helper.exceptions import EpisodePostProcessingFailedException, FailedPostProcessingFailedException, ex
from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from medusa.subtitles import accept_any, accept_unknown, get_embedded_subtitles

import shutil_custom

from unrar2 import RarFile
from unrar2.rar_exceptions import (ArchiveHeaderBroken, FileOpenError, IncorrectRARPassword, InvalidRARArchive,
                                   InvalidRARArchiveUsage)

shutil.copyfile = shutil_custom.copyfile_custom
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ProcessResult(object):

    IGNORED_FOLDERS = ('@eaDir', '#recycle',)

    def __init__(self, path, process_method=None):

        self._output = []
        self.directory = path
        self.process_method = process_method
        self.resource_name = None
        self.result = True
        self.succeeded = True
        self.missedfiles = []
        self.unwanted_files = []
        self.allowed_extensions = app.ALLOWED_EXTENSIONS

    @property
    def directory(self):
        """Return the root directory we are going to process."""
        return getattr(self, '_directory')

    @directory.setter
    def directory(self, path):
        directory = None
        if os.path.isdir(path):
            self.log(logging.DEBUG, 'Processing path: {0}'.format(path))
            directory = os.path.realpath(path)

        # If the client and the application are not on the same machine,
        # translate the directory into a network directory
        elif all([app.TV_DOWNLOAD_DIR, os.path.isdir(app.TV_DOWNLOAD_DIR),
                  os.path.normpath(path) == os.path.normpath(app.TV_DOWNLOAD_DIR)]):
            directory = os.path.join(
                app.TV_DOWNLOAD_DIR,
                os.path.abspath(path).split(os.path.sep)[-1]
            )
            self.log(logging.DEBUG, 'Trying to use folder: {0}'.format(directory))
        else:
            self.log(
                logging.WARNING,
                "Unable to figure out what folder to process."
                " If your download client and Medusa aren't on the same"
                " machine, make sure to fill out the Post Processing Dir"
                " field in the config."
            )
        setattr(self, '_directory', directory)

    @property
    def paths(self):
        """Return the paths we are going to try to process."""
        if self.directory:
            yield self.directory
            if self.resource_name:
                return
            for root, dirs, files in os.walk(self.directory):
                del files  # unused variable
                for folder in dirs:
                    path = os.path.join(root, folder)
                    yield path
                break

    @property
    def video_files(self):
        return getattr(self, '_video_files', [])

    @video_files.setter
    def video_files(self, value):
        setattr(self, '_video_files', value)

    @property
    def output(self):
        return '\n'.join(self._output)

    def log(self, level, message):
        log.log(level, message)
        self._output.append(message)

    def process(self, resource_name=None, force=False, is_priority=None, delete_on=False, failed=False,
                proc_type='auto', ignore_subs=False):
        """
        Scan through the files in the root directory and process whatever media files are found.

        :param resource_name: The resource that will be processed directly
        :param force: True to postprocess already postprocessed files
        :param is_priority: Boolean for whether or not is a priority download
        :param delete_on: Boolean for whether or not it should delete files
        :param failed: Boolean for whether or not the download failed
        :param proc_type: Type of postprocessing auto or manual
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        if not self.directory:
            return self.output

        if resource_name:
            self.resource_name = resource_name

        if app.POSTPONE_IF_NO_SUBS:
            self.log(logging.INFO, "Feature 'postpone post-processing if no subtitle available' is enabled.")

        for path in self.paths:

            if not self.should_process(path, failed):
                continue

            self.result = True

            for dir_path, filelist in self._get_files(path):

                sync_files = (filename
                              for filename in filelist
                              if is_sync_file(filename))

                # Don't process files if they are still being synced
                postpone = app.POSTPONE_IF_SYNC_FILES and any(sync_files)
                if not postpone:

                    self.log(logging.DEBUG, 'Processing folder: {0}'.format(dir_path))

                    self.prepare_files(dir_path, filelist, force)
                    self.process_files(dir_path, force=force, is_priority=is_priority,
                                       ignore_subs=ignore_subs)
                    self._clean_up(dir_path, proc_type, delete=delete_on)

                else:
                    self.log(logging.INFO, 'Found temporary sync files in folder: {0}'.format(dir_path))
                    self.log(logging.INFO, 'Skipping post-processing for folder: {0}'.format(dir_path))
                    self.missedfiles.append('{0}: Sync files found'.format(dir_path))

        if self.succeeded:
            self.log(logging.INFO, 'Successfully processed.')

            # Clean Kodi library
            if app.KODI_LIBRARY_CLEAN_PENDING and notifiers.kodi_notifier.clean_library():
                app.KODI_LIBRARY_CLEAN_PENDING = False

            if self.missedfiles:
                self.log(logging.INFO, 'I did encounter some unprocessable items: ')
                for missedfile in self.missedfiles:
                    self.log(logging.INFO, '{0}'.format(missedfile))
        else:
            self.log(logging.WARNING, 'Problem(s) during processing, failed for the following files/folders: ')
            for missedfile in self.missedfiles:
                self.log(logging.WARNING, '{0}'.format(missedfile))

        if app.USE_TORRENTS and app.PROCESS_METHOD in ('hardlink', 'symlink') and app.TORRENT_SEED_LOCATION:
            to_remove_hashes = app.RECENTLY_POSTPROCESSED.items()
            for info_hash, release_names in to_remove_hashes:
                if self.move_torrent(info_hash, release_names):
                    app.RECENTLY_POSTPROCESSED.pop(info_hash, None)

        return self.output

    def _clean_up(self, path, proc_type, delete=False):
        """Clean up post-processed folder based on the checks below."""
        # Always delete files if they are being moved or if it's explicitly wanted
        clean_folder = proc_type == 'manual' and delete
        if self.process_method == 'move' or clean_folder:

            for folder in self.IGNORED_FOLDERS:
                self.delete_folder(os.path.join(path, folder))

            if self.unwanted_files:
                self.delete_files(path, self.unwanted_files)

            if all([not app.NO_DELETE or clean_folder, self.process_method in ('move', 'copy'),
                    os.path.normpath(path) != os.path.normpath(app.TV_DOWNLOAD_DIR)]):

                check_empty = False if self.process_method == 'copy' else True
                if self.delete_folder(path, check_empty=check_empty):
                    self.log(logging.DEBUG, 'Deleted folder: {0}'.format(path))

    def should_process(self, path, failed=False):
        """
        Determine if a directory should be processed.

        :param path: Path we want to verify
        :param failed: (optional) Mark the directory as failed
        :return: True if the directory is valid for processing, otherwise False
        :rtype: Boolean
        """
        if not self._is_valid_folder(path, failed):
            return False

        folder = os.path.basename(path)
        if helpers.is_hidden_folder(path) or any(f == folder for f in self.IGNORED_FOLDERS):
            self.log(logging.DEBUG, 'Ignoring folder: {0}'.format(folder))
            self.missedfiles.append('{0}: Hidden or ignored folder'.format(path))
            return False

        for root, dirs, files in os.walk(path):
            for subfolder in dirs:
                if not self._is_valid_folder(os.path.join(root, subfolder), failed):
                    return False
            for each_file in files:
                if helpers.is_media_file(each_file) or helpers.is_rar_file(each_file):
                    return True
            # Stop at first subdirectories if post-processing path
            if self.directory == path:
                break

        self.log(logging.DEBUG, 'No processable items found in folder: {0}'.format(path))
        return False

    def _is_valid_folder(self, path, failed):
        """Verify folder validity based on the checks below."""
        folder = os.path.basename(path)

        if folder.startswith('_FAILED_'):
            self.log(logging.DEBUG, 'The directory name indicates it failed to extract.')
            failed = True
        elif folder.startswith('_UNDERSIZED_'):
            self.log(logging.DEBUG, 'The directory name indicates that it was previously rejected for being undersized.')
            failed = True

        if failed:
            self.process_failed(path)
            self.missedfiles.append('{0}: Failed download'.format(path))
            return False

        if folder.startswith('_unpack'):
            self.log(logging.DEBUG, 'The directory name indicates that this release is in the process of being unpacked.')
            self.missedfiles.append('{0}: Being unpacked'.format(path))
            return False

        return True

    def _get_files(self, path):
        """Return the path to a folder and its contents as a tuple."""
        # If resource_name is a file and not an NZB, process it directly
        if self.resource_name and (not self.resource_name.endswith('.nzb') and
                                   os.path.isfile(os.path.join(path, self.resource_name))):
            yield path, [self.resource_name]
        else:
            topdown = True if self.directory == path else False
            for root, dirs, files in os.walk(path, topdown=topdown):
                if files:
                    yield root, files
                if topdown:
                    break
                del dirs  # unused variable

    def prepare_files(self, path, files, force=False):
        """Prepare files for post-processing."""
        video_files = []
        rar_files = []
        for each_file in files:
            if helpers.is_media_file(each_file):
                video_files.append(each_file)
            elif helpers.is_rar_file(each_file):
                rar_files.append(each_file)

        rar_content = []
        video_in_rar = []
        if rar_files:
            rar_content = self.unrar(path, rar_files, force)
            files.extend(rar_content)
            video_in_rar = [each_file for each_file in rar_content if helpers.is_media_file(each_file)]
            video_files.extend(video_in_rar)

        self.log(logging.DEBUG, 'Post-processing files: {0}'.format(files))
        self.log(logging.DEBUG, 'Post-processing video files: {0}'.format(video_files))

        if rar_content:
            self.log(logging.DEBUG, 'Post-processing rar content: {0}'.format(rar_content))
            self.log(logging.DEBUG, 'Post-processing video in rar: {0}'.format(video_in_rar))

        unwanted_files = [filename
                          for filename in files
                          if filename not in video_files and
                          helpers.get_extension(filename) not in
                          self.allowed_extensions]
        if unwanted_files:
            self.log(logging.DEBUG, 'Found unwanted files: {0}'.format(unwanted_files))

        self.video_files = video_files
        self.rar_content = rar_content
        self.video_in_rar = video_in_rar
        self.unwanted_files = unwanted_files

    def process_files(self, path, force=False, is_priority=None, ignore_subs=False):
        """Post-process and delete the files in a given path."""
        # TODO: Replace this with something that works for multiple video files
        if self.resource_name and len(self.video_files) > 1:
            self.resource_name = None

        if self.video_in_rar:
            video_files = set(self.video_files + self.video_in_rar)

            if self.process_method in ('hardlink', 'symlink'):
                process_method = self.process_method
                # Move extracted video files instead of hard/softlinking them
                self.process_method = 'move'
                self.process_media(path, self.video_in_rar, force, is_priority, ignore_subs)
                if not self.postpone_processing:
                    self.delete_files(path, self.rar_content)
                # Reset process method to initial value
                self.process_method = process_method

                self.process_media(path, video_files - set(self.video_in_rar), force,
                                   is_priority, ignore_subs)
            else:
                self.process_media(path, video_files, force, is_priority, ignore_subs)

                if app.DELRARCONTENTS and not self.postpone_processing:
                    self.delete_files(path, self.rar_content)

        else:
            self.process_media(path, self.video_files, force, is_priority, ignore_subs)

    @staticmethod
    def delete_folder(folder, check_empty=True):
        """
        Remove a folder from the filesystem.

        :param folder: Path to folder to remove
        :param check_empty: Boolean, check if the folder is empty before removing it, defaults to True
        :return: True on success, False on failure
        """
        # check if it's a folder
        if not os.path.isdir(folder):
            return False

        # check if it isn't TV_DOWNLOAD_DIR
        if app.TV_DOWNLOAD_DIR:
            if helpers.real_path(folder) == helpers.real_path(app.TV_DOWNLOAD_DIR):
                return False

        # check if it's empty folder when wanted checked
        if check_empty:
            check_files = os.listdir(folder)
            if check_files:
                log.info('Not deleting folder {0} found the following files: {1}'.format(folder, check_files))
                return False

            try:
                log.info("Deleting folder (if it's empty): {0}".format(folder))
                os.rmdir(folder)
            except (OSError, IOError) as error:
                log.warning('Unable to delete folder: {0}: {1}'.format(folder, ex(error)))
                return False
        else:
            try:
                log.info('Deleting folder: {0}'.format(folder))
                shutil.rmtree(folder)
            except (OSError, IOError) as error:
                log.warning('Unable to delete folder: {0}: {1}'.format(folder, ex(error)))
                return False

        return True

    def delete_files(self, path, files, force=False):
        """
        Remove files from filesystem.

        :param path: path to process
        :param files: files we want to delete
        :param force: Boolean, force deletion, defaults to false
        """
        if not files:
            return

        if not self.result and force:
            self.log(logging.DEBUG, 'Forcing deletion of files, even though last result was not successful.')
        elif not self.result:
            return

        # Delete all file not needed
        for cur_file in files:
            cur_file_path = os.path.join(path, cur_file)

            if not os.path.isfile(cur_file_path):
                continue  # Prevent error when a notwantedfiles is an associated files

            self.log(logging.DEBUG, 'Deleting file: {0}'.format(cur_file))

            # check first the read-only attribute
            file_attribute = os.stat(cur_file_path)[0]
            if not file_attribute & stat.S_IWRITE:
                # File is read-only, so make it writeable
                self.log(logging.DEBUG, 'Changing read-only flag for file: {0}'.format(cur_file))
                try:
                    os.chmod(cur_file_path, stat.S_IWRITE)
                except OSError as error:
                    self.log(logging.DEBUG, 'Cannot change permissions of {0}: {1}'.format(cur_file_path, ex(error)))
            try:
                os.remove(cur_file_path)
            except OSError as error:
                self.log(logging.DEBUG, 'Unable to delete file {0}: {1}'.format(cur_file, ex(error)))

    def unrar(self, path, rar_files, force=False):
        """
        Extract RAR files.

        :param path: Path to look for files in
        :param rar_files: Names of RAR files
        :param force: process currently processing items
        :return: List of unpacked file names
        """
        unpacked_files = []

        if app.UNPACK and rar_files:
            self.log(logging.DEBUG, 'Packed files detected: {0}'.format(rar_files))

            for archive in rar_files:
                self.log(logging.DEBUG, 'Unpacking archive: {0}'.format(archive))

                failure = None
                try:
                    rar_handle = RarFile(os.path.join(path, archive))

                    # Skip extraction if any file in archive has previously been extracted
                    skip_extraction = False
                    for file_in_archive in [os.path.basename(each.filename)
                                            for each in rar_handle.infolist()
                                            if not each.isdir]:
                        if not force and self.already_postprocessed(file_in_archive):
                            self.log(logging.DEBUG, 'Archive file already post-processed, extraction skipped: {0}'.format
                                     (file_in_archive))
                            skip_extraction = True
                            break

                        if app.POSTPONE_IF_NO_SUBS and os.path.isfile(os.path.join(path, file_in_archive)):
                            self.log(logging.DEBUG, 'Archive file already extracted, extraction skipped: {0}'.format
                                     (file_in_archive))
                            skip_extraction = True
                            break

                    if not skip_extraction:
                        rar_handle.extract(path=path, withSubpath=False, overwrite=False)

                    for each in rar_handle.infolist():
                        if not each.isdir:
                            basename = os.path.basename(each.filename)
                            unpacked_files.append(basename)

                    del rar_handle

                except ArchiveHeaderBroken:
                    failure = ('Archive Header Broken', 'Unpacking failed because the Archive Header is Broken')
                except IncorrectRARPassword:
                    failure = ('Incorrect RAR Password', 'Unpacking failed because of an Incorrect Rar Password')
                except FileOpenError:
                    failure = ('File Open Error, check the parent folder and destination file permissions.',
                               'Unpacking failed with a File Open Error (file permissions?)')
                except InvalidRARArchiveUsage:
                    failure = ('Invalid Rar Archive Usage', 'Unpacking Failed with Invalid Rar Archive Usage')
                except InvalidRARArchive:
                    failure = ('Invalid Rar Archive', 'Unpacking Failed with an Invalid Rar Archive Error')
                except Exception as error:
                    failure = (ex(error), 'Unpacking failed for an unknown reason')

                if failure is not None:
                    self.log(logging.WARNING, 'Failed unpacking archive {0}: {1}'.format(archive, failure[0]))
                    self.missedfiles.append('{0}: Unpacking failed: {1}'.format(archive, failure[1]))
                    self.result = False
                    continue

            self.log(logging.DEBUG, 'Extracted content: {0}'.format(unpacked_files))

        return unpacked_files

    def already_postprocessed(self, video_file):
        """
        Check if we already post processed a file.

        :param video_file: File name
        :return:
        """
        main_db_con = db.DBConnection()
        history_result = main_db_con.select(
            'SELECT * FROM history '
            "WHERE action LIKE '%04' "
            'AND resource LIKE ?',
            ['%' + video_file])

        if history_result:
            self.log(logging.DEBUG, "You're trying to post-process a file that has already "
                     "been processed, skipping: {0}".format(video_file))
            return True

    def process_media(self, path, video_files, force=False, is_priority=None, ignore_subs=False):
        """
        Postprocess media files.

        :param path: Path to postprocess in
        :param video_files: Filenames to look for and postprocess
        :param force: Postprocess currently postprocessing file
        :param is_priority: Boolean, is this a priority download
        :param ignore_subs: True to ignore setting 'postpone if no subs'
        """
        self.postpone_processing = False

        for video in video_files:
            file_path = os.path.join(path, video)

            if not force and self.already_postprocessed(video):
                self.log(logging.DEBUG, 'Skipping already processed file: {0}'.format(video))
                continue

            try:
                processor = post_processor.PostProcessor(file_path, self.resource_name,
                                                         self.process_method, is_priority)

                if app.POSTPONE_IF_NO_SUBS:
                    if not self._process_postponed(processor, file_path, video, ignore_subs):
                        continue

                self.result = processor.process()
                process_fail_message = ''
            except EpisodePostProcessingFailedException as error:
                processor = None
                self.result = False
                process_fail_message = ex(error)

            if processor:
                self._output.append(processor.output)

            if self.result:
                self.log(logging.INFO, 'Processing succeeded for {0}'.format(file_path))
            else:
                self.log(logging.WARNING, 'Processing failed for {0}: {1}'.format(file_path, process_fail_message))
                self.missedfiles.append('{0}: Processing failed: {1}'.format(file_path, process_fail_message))
                self.succeeded = False

    def _process_postponed(self, processor, path, video, ignore_subs):
        if not ignore_subs:
            if self.subtitles_enabled(path, self.resource_name):
                embedded_subs = set() if app.IGNORE_EMBEDDED_SUBS else get_embedded_subtitles(path)

                # We want to ignore embedded subtitles and video has at least one
                if accept_unknown(embedded_subs):
                    self.log(logging.INFO, "Found embedded unknown subtitles and we don't want to ignore them. "
                             "Continuing the post-processing of this file: {0}".format(video))
                elif accept_any(embedded_subs):
                    self.log(logging.INFO, 'Found wanted embedded subtitles. '
                             'Continuing the post-processing of this file: {0}'.format(video))
                else:
                    associated_subs = processor.list_associated_files(path, subtitles_only=True)
                    if not associated_subs:
                        self.log(logging.DEBUG, 'No subtitles associated. Postponing the post-processing of this file: '
                                 '{0}'.format(video))
                        self.postpone_processing = True
                        return False
                    else:
                        self.log(logging.INFO, 'Found associated subtitles. '
                                 'Continuing the post-processing of this file: {0}'.format(video))
            else:
                self.log(logging.INFO, 'Subtitles disabled for this show. '
                         'Continuing the post-processing of this file: {0}'.format(video))
        else:
            self.log(logging.INFO, 'Subtitles check was disabled for this episode in manual post-processing. '
                     'Continuing the post-processing of this file: {0}'.format(video))
        return True

    def process_failed(self, path):
        """Process a download that did not complete correctly."""
        if app.USE_FAILED_DOWNLOADS:
            try:
                processor = failed_processor.FailedProcessor(path, self.resource_name)
                self.result = processor.process()
                process_fail_message = ''
            except FailedPostProcessingFailedException as error:
                processor = None
                self.result = False
                process_fail_message = ex(error)

            if processor:
                self._output.append(processor.output)

            if app.DELETE_FAILED and self.result:
                if self.delete_folder(path, check_empty=False):
                    self.log(logging.DEBUG, 'Deleted folder: {0}'.format(path))

            if self.result:
                self.log(logging.INFO, 'Failed Download Processing succeeded: {0}, {1}'.format
                         (self.resource_name, path))
            else:
                self.log(logging.WARNING, 'Failed Download Processing failed: {0}, {1}: {2}'.format
                         (self.resource_name, path, process_fail_message))

    @staticmethod
    def subtitles_enabled(*args):
        """Try to parse names to a show and check whether the show has subtitles enabled.

        :param args:
        :return:
        :rtype: bool
        """
        for name in args:
            if not name:
                continue

            try:
                parse_result = NameParser().parse(name)
                if parse_result.series.indexerid:
                    main_db_con = db.DBConnection()
                    sql_results = main_db_con.select("SELECT subtitles FROM tv_shows WHERE indexer = ? AND indexer_id = ? LIMIT 1",
                                                     [parse_result.series.indexer, parse_result.series.indexerid])
                    return bool(sql_results[0][b'subtitles']) if sql_results else False

                log.warning('Empty indexer ID for: {name}'.format(name=name))
            except (InvalidNameException, InvalidShowException):
                log.warning(
                    'Not enough information to parse filename into a valid'
                    ' show. Consider adding scene exceptions or improve naming'
                    ' for: {name}'.format(name=name)
                )
        return False

    @staticmethod
    def move_torrent(info_hash, release_names):
        """Move torrent to a given seeding folder after PP."""
        if release_names:
            # Log 'release' or 'releases'
            s = 's' if len(release_names) > 1 else ''
            release_names = ', '.join(release_names)
        else:
            s = ''
            release_names = 'N/A'

        log.debug('Trying to move torrent after post-processing')
        client = torrent.get_client_class(app.TORRENT_METHOD)()
        torrent_moved = False
        try:
            torrent_moved = client.move_torrent(info_hash)
        except AttributeError:
            log.warning("Your client doesn't support moving torrents to new location")
            return False

        if torrent_moved:
            log.debug(
                "Moved torrent for release{s} '{release}' with hash: {hash}"
                " to: '{path}'".format(
                    release=release_names, hash=info_hash,
                    path=app.TORRENT_SEED_LOCATION, s=s
                )
            )
            return True
        else:
            log.warning(
                "Couldn't move torrent for release{s} '{release}' with"
                " hash: {hash} to: '{path}'. Please check logs.".format(
                    release=release_names, hash=info_hash,
                    s=s, path=app.TORRENT_SEED_LOCATION
                )
            )
            return False
