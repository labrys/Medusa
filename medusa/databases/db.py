# coding=utf-8
import logging
import os.path
import re
import sqlite3
import sys
import threading
import time
import warnings

from medusa import app

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

db_cons = {}
db_locks = {}


def db_filename(filename=None, suffix=None):
    """
    @param filename: The sqlite database filename to use. If not specified,
                     will be made to be application db file
    @param suffix: The suffix to append to the filename. A '.' will be added
                   automatically, i.e. suffix='v0' will make dbfile.db.v0
    @return: the correct location of the database file.
    """
    filename = filename or app.APPLICATION_DB
    if suffix:
        filename = f'{filename}.{suffix}'
    return os.path.join(app.DATA_DIR, filename)


class DBConnection:
    def __init__(self, filename=None, suffix=None, row_type=None):

        self.filename = filename or app.APPLICATION_DB
        self.suffix = suffix
        self.row_type = row_type

        try:
            if self.filename not in db_cons or not db_cons[self.filename]:
                db_locks[self.filename] = threading.Lock()

                self.connection = sqlite3.connect(db_filename(self.filename, self.suffix), 20, check_same_thread=False)

                db_cons[self.filename] = self.connection
            else:
                self.connection = db_cons[self.filename]

            # start off row factory configured as before out of
            # paranoia but wait to do so until other potential users
            # of the shared connection are done using
            # it... technically not required as row factory is reset
            # in all the public methods after the lock has been
            # aquired
            with db_locks[self.filename]:
                self._set_row_factory()

        except sqlite3.OperationalError:
            log.warning(
                u'Please check your database owner/permissions: {}'.format(db_filename(self.filename, self.suffix)))
        except Exception as e:
            log.debug(u"DB error: {}".format(e))
            raise

    def _set_row_factory(self):
        """Once lock is acquired we can configure the connection for this particular instance of DBConnection."""
        if self.row_type == "dict":
            self.connection.row_factory = DBConnection._dict_factory
        else:
            self.connection.row_factory = sqlite3.Row

    def _execute(self, query, args=None, fetchall=False, fetchone=False):
        """
        Execute a DB query.

        :param query: Query to execute
        :param args: Arguments in query
        :param fetchall: Boolean to indicate all results must be fetched
        :param fetchone: Boolean to indicate one result must be fetched (to walk results for instance)
        :return: query results
        """
        try:
            cursor = self.connection.cursor()
            if not args:
                sql_results = cursor.execute(query)
            else:
                sql_results = cursor.execute(query, args)
            if fetchall:
                return sql_results.fetchall()
            elif fetchone:
                return sql_results.fetchone()
            return sql_results
        except sqlite3.OperationalError as e:
            # This errors user should be able to fix it.
            if 'unable to open database file' in e.args[0] or \
                            'database is locked' in e.args[0] or \
                            'database or disk is full' in e.args[0]:
                log.warning(u'DB error: {0!r}'.format(e))
            else:
                log.info(u"Query: '{0}'. Arguments: '{1}'".format(query, args))
                log.debug(u'DB error: {0!r}'.format(e))
                raise
        except Exception as e:
            log.debug(u'DB error: {0!r}'.format(e))
            raise

    def check_db_version(self):
        """
        Fetch major and minor database version.

        :return: Integer indicating current DB major version
        """
        if self.has_column('db_version', 'db_minor_version'):
            warnings.warn('Deprecated: Use the version property', DeprecationWarning)
        db_minor_version = self.check_db_minor_version()
        if db_minor_version is None:
            db_minor_version = 0
        return self.check_db_major_version(), db_minor_version

    def check_db_major_version(self):
        """
        Fetch database version.

        :return: Integer inidicating current DB version
        """
        result = None

        try:
            if self.has_table('db_version'):
                result = self.select("SELECT db_version FROM db_version")
        except sqlite3.OperationalError:
            return None

        if result:
            return int(result[0]["db_version"])
        else:
            return None

    def check_db_minor_version(self):
        """
        Fetch database version.

        :return: Integer inidicating current DB major version
        """
        result = None

        try:
            if self.has_column('db_version', 'db_minor_version'):
                result = self.select("SELECT db_minor_version FROM db_version")
        except sqlite3.OperationalError:
            return None

        if result:
            return int(result[0]["db_minor_version"])
        else:
            return None

    @property
    def version(self):
        """
        The database version.

        :return: A tuple containing the major and minor versions
        """
        return self.check_db_major_version(), self.check_db_minor_version()

    def mass_action(self, querylist=None, log_transaction=False, fetchall=False):
        """
        Execute multiple queries.

        :param querylist: list of queries
        :param log_transaction: Boolean to wrap all in one transaction
        :param fetchall: Boolean, when using a select query force returning all results
        :return: list of results
        """
        querylist = querylist or []
        # remove None types
        querylist = [i for i in querylist if i is not None and len(i)]

        sql_results = []
        attempt = 0

        with db_locks[self.filename]:
            self._set_row_factory()
            while attempt < 5:
                try:
                    for qu in querylist:
                        if len(qu) == 1:
                            if log_transaction:
                                log.debug(qu[0])
                            sql_results.append(self._execute(qu[0], fetchall=fetchall))
                        elif len(qu) > 1:
                            if log_transaction:
                                log.debug(qu[0] + " with args " + str(qu[1]))
                            sql_results.append(self._execute(qu[0], qu[1], fetchall=fetchall))
                    self.connection.commit()
                    log.debug(u"Transaction with " + str(len(querylist)) + u" queries executed")

                    # finished
                    break
                except sqlite3.OperationalError as e:
                    sql_results = []
                    if self.connection:
                        self.connection.rollback()
                    if "unable to open database file" in e.args[0] or "database is locked" in e.args[0]:
                        log.warning(u"DB error: {}".format(e))
                        attempt += 1
                        time.sleep(1)
                    else:
                        log.debug(u"DB error: {}".format(e))
                        raise
                except sqlite3.DatabaseError as e:
                    if self.connection:
                        self.connection.rollback()
                    log.debug(u"Fatal error executing query: {}".format(e))
                    raise

            # time.sleep(0.02)

            return sql_results

    def action(self, query, args=None, fetchall=False, fetchone=False):
        """
        Execute a single query.

        :param query: Query string
        :param args: Arguments to query string
        :param fetchall: Boolean to indicate all results must be fetched
        :param fetchone: Boolean to indicate one result must be fetched (to walk results for instance)
        :return: query results
        """
        if query is None:
            return

        if isinstance(query, bytes):
            log.debug('Decoding query: {!r}'.format(query))
            query = query.decode()

        sql_results = None
        attempt = 0

        with db_locks[self.filename]:
            self._set_row_factory()
            while attempt < 5:
                try:
                    if args is None:
                        log.debug(self.filename + ": " + query)
                    else:
                        log.debug(self.filename + ": " + query + " with args " + str(args))

                    sql_results = self._execute(query, args, fetchall=fetchall, fetchone=fetchone)
                    self.connection.commit()

                    # get out of the connection attempt loop since we were successful
                    break
                except sqlite3.OperationalError as e:
                    if "unable to open database file" in e.args[0] or "database is locked" in e.args[0]:
                        log.warning(u"DB error: {}".format(e))
                        attempt += 1
                        time.sleep(1)
                    else:
                        log.debug(u"DB error: {}".format(e))
                        raise
                except sqlite3.DatabaseError as e:
                    log.debug(u"Fatal error executing query: {}".format(e))
                    raise

            # time.sleep(0.02)

            return sql_results

    def select(self, query, args=None):
        """
        Perform single select query on database.

        :param query: query string
        :param args:  arguments to query string
        :return: query results
        """
        sql_results = self.action(query, args, fetchall=True)

        if sql_results is None:
            return []

        return sql_results

    def select_one(self, query, args=None):
        """
        Perform single select query on database, returning one result.

        :param query: query string
        :param args: arguments to query string
        :return: query results
        """
        sql_results = self.action(query, args, fetchone=True)

        if sql_results is None:
            return []

        return sql_results

    def upsert(self, table_name, value_dict, key_dict):
        """
        Update values, or if no updates done, insert values.

        :param table_name: table to update/insert
        :param value_dict: values in table to update/insert
        :param key_dict:  columns in table to update/insert
        """
        # TODO: Make this return true/false on success/error
        changes_before = self.connection.total_changes

        def gen_params(my_dict):
            return [x + " = ?" for x in my_dict.keys()]

        query = "UPDATE [" + table_name + "] SET " + ", ".join(gen_params(value_dict)) + " WHERE " + " AND ".join(
            gen_params(key_dict))

        values = list(value_dict.values()) + list(key_dict.values())
        keys = list(value_dict.keys()) + list(key_dict.keys())
        self.action(query, values)

        if self.connection.total_changes == changes_before:
            query = "INSERT INTO [" + table_name + "] (" + ", ".join(keys) + ")" + \
                    " VALUES (" + ", ".join(["?"] * len(keys)) + ")"
            self.action(query, values)

    def table_info(self, table_name):
        """
        Return information on a database table.

        :param table_name: name of table
        :return: array of name/type info
        """
        sql_results = self.select("PRAGMA table_info(`%s`)" % table_name)
        columns = {}
        for column in sql_results:
            columns[column['name']] = {'type': column['type']}
        return columns

    @staticmethod
    def _dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def has_table(self, table_name):
        """
        Check if a table exists in database.

        :param table_name: table name to check
        :return: True if table exists, False if it does not
        """
        return len(self.select("SELECT 1 FROM sqlite_master WHERE name = ?;", (table_name,))) > 0

    def has_column(self, table_name, column):
        """
        Check if a table has a column.

        :param table_name: Table to check
        :param column: Column to check for
        :return: True if column exists, False if it does not
        """
        return column in self.table_info(table_name)

    def add_column(self, table, column, column_type="NUMERIC", default=0):
        """
        Adds a column to a table, default column type is NUMERIC.

        :param table: Table to add column too
        :param column: Column name to add
        :param column_type: Column type to add
        :param default: Default value for column
        """
        # TODO: Make this return true/false on success/failure
        self.action("ALTER TABLE [%s] ADD %s %s" % (table, column, column_type))
        self.action("UPDATE [%s] SET %s = ?" % (table, column), (default,))


def sanity_check_database(connection, sanity_check):
    sanity_check(connection).check()


class DBSanityCheck:
    def __init__(self, connection):
        self.connection = connection

    def check(self):
        pass


# ===============
# = Upgrade API =
# ===============

def upgrade_database(connection, schema):
    """
    Perform database upgrade and provide logging.

    :param connection: Existing DB Connection to use
    :param schema: New schema to upgrade to
    """
    log.debug(u"Checking database structure..." + connection.filename)
    _process_upgrade(connection, schema)


def pretty_name(class_name):
    return ' '.join([x.group() for x in re.finditer("([A-Z])([a-z0-9]+)", class_name)])


def restore_database(version):
    """
    Restore a database to a previous version.

    A backup file of the version must still exist.

    :param version: Version to restore to
    :return: True if restore succeeds, False if it fails
    """
    from medusa import helpers
    log.info(u"Restoring database before trying upgrade again")
    if not helpers.restore_versioned_file(db_filename(suffix='v' + str(version)), version):
        log.error(u"Database restore failed, abort upgrading database")
        sys.exit()
    else:
        return True


def _process_upgrade(connection, upgrade_class):
    instance = upgrade_class(connection)
    log.debug(u"Checking " + pretty_name(upgrade_class.__name__) + " database upgrade")
    if not instance.test():
        log.debug(u"Database upgrade required: " + pretty_name(upgrade_class.__name__))
        try:
            instance.execute()
        except Exception as e:
            log.debug("Error in " + str(upgrade_class.__name__) + ": " + str(e))
            raise

        log.debug(upgrade_class.__name__ + " upgrade completed")
    else:
        log.debug(upgrade_class.__name__ + " upgrade not required")

    for upgradeSubClass in upgrade_class.__subclasses__():
        _process_upgrade(connection, upgradeSubClass)


# Base migration class. All future DB changes should be subclassed from this class
class SchemaUpgrade:
    def __init__(self, connection):
        self.connection = connection

    def has_table(self, table_name):
        return len(self.connection.select("SELECT 1 FROM sqlite_master WHERE name = ?;", (table_name,))) > 0

    def has_column(self, table_name, column):
        return column in self.connection.table_info(table_name)

    def add_column(self, table, column, column_type="NUMERIC", default=0):
        self.connection.action("ALTER TABLE [%s] ADD %s %s" % (table, column, column_type))
        self.connection.action("UPDATE [%s] SET %s = ?" % (table, column), (default,))

    def check_db_version(self):
        return self.connection.check_db_version()

    def inc_db_version(self):
        new_version = self.check_db_version() + 1
        self.connection.action("UPDATE db_version SET db_version = ?", [new_version])
        return new_version

    @property
    def major_version(self):
        return self.check_db_version()[0]
