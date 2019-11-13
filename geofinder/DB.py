#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#  Copyright (c) 2019.       Mike Herbert
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
import logging
import sqlite3
import sys
import time
from tkinter import messagebox

from geofinder.GeoUtil import Query, Result, Entry


class DB:
    """
    Sqlite3  helper functions
    """

    def __init__(self, db_filename: str):
        self.logger = logging.getLogger(__name__)
        self.order_str = ''
        self.limit_str = ''
        self.cur = None
        self.total_time = 0
        self.use_wildcards = True

        # create a database connection
        self.conn = self.connect(db_filename=db_filename)
        if self.conn is None:
            self.err = True
            self.logger.error(f"Error! cannot open database {db_filename}.")
            raise ValueError('Cannot open database')
        else:
            self.err = False
            self.conn.isolation_level = None

    def connect(self, db_filename: str):
        """ create a database connection to the SQLite database
            specified by db_file
        :param db_filename: database filename
        :return: Connection object or None
        """
        try:
            conn = sqlite3.connect(db_filename)
            self.logger.info(f'DB {db_filename} connected')
            return conn
        except Exception as e:
            messagebox.showwarning('Error', f'Database Connection Error\n {e}')
            self.err = True
            self.logger.error(e)
            sys.exit()

    def set_params(self, order_str: str, limit_str: str):
        # Set values for SELECT, ORDER BY, and LIMIT
        self.order_str = order_str
        self.limit_str = limit_str

    def set_pragma(self, pragma: str):
        # Set PRAGMA e.g. temp_store = memory;
        cur = self.conn.cursor()
        cur.execute(pragma)
        self.conn.commit()

    def create_table(self, create_table_sql: str):
        """ create a table from the create_table_sql statement
        :param create_table_sql: a CREATE TABLE statement
        """
        try:
            c = self.conn.cursor()
            c.execute(create_table_sql)
            self.conn.commit()
            self.logger.info(f'Create DB table {create_table_sql[27:36]}')  # Lazy attempt to get table name for logging
        except Exception as e:
            messagebox.showwarning('Error', e)
            self.err = True
            self.logger.error(e)
            sys.exit()

    def create_index(self, create_table_sql: str):
        #self.logger.debug(f'Create idx {create_table_sql}')
        try:
            c = self.conn.cursor()
            c.execute(create_table_sql)
            self.conn.commit()
        except Exception as e:
            messagebox.showwarning('Error', e)
            self.err = True
            self.logger.error(e)
            sys.exit()

    def delete_table(self, tbl):
        cur = self.conn.cursor()
        try:
            # noinspection SqlWithoutWhere
            cur.execute(f'DELETE FROM {tbl}')
        except Exception as e:
            messagebox.showwarning('Error', f'Database delete table error\n {e}')
            self.err = True
            self.logger.error(e)
            sys.exit()

    def get_row_count(self):
        cur = self.conn.cursor()
        cur.execute('SELECT COUNT(*) FROM main.geodata')
        res = cur.fetchall()
        count = res[0][0]
        return count

    def begin(self):
        self.cur = self.conn.cursor()
        self.cur.execute('BEGIN')

    def execute(self, sql, args):
        # try:
        if True:
            self.cur.execute(sql, args)
        """
        except Exception as e:
            messagebox.showwarning('Error', f'{DB_CORRUPT_MSG}\n {e}')
            self.err = True
            self.logger.error(e)
            sys.exit()
        """
        return self.cur.lastrowid

    def commit(self):
        # Commit transaction
        self.cur.execute("commit")

    def select(self, select_str, where, from_tbl, args):
        error = False
        cur = self.conn.cursor()
        sql = f"SELECT {select_str} FROM {from_tbl} WHERE {where} {self.order_str} {self.limit_str}"
        try:
            cur.execute(sql, args)
            res = cur.fetchall()
        except Exception as e:
            messagebox.showwarning('Error', f'Database select error\n\n'
            f'SELECT\n {select_str}\n FROM {from_tbl} WHERE\n {where}\n'
            f'{args}\n\n {e}')
            self.err = True
            self.logger.error(e)
            error = True
            sys.exit()
        return res

    def table_exists(self, table_name):
        # SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';
        where = "type=? AND name=?"
        from_tbl = 'sqlite_master'
        select_str = 'name'
        args = ('table', table_name)

        cur = self.conn.cursor()

        # See if  Table exists.  If it does not, then the version is 1.0
        sql = f"SELECT {select_str} FROM {from_tbl} WHERE {where} {self.order_str} {self.limit_str}"

        #self.logger.debug(f'{table_name} sql={sql} args=[{args}]')
        try:
            cur.execute(sql, args)
            res = cur.fetchall()
            #self.logger.debug(f'DB {table_name} tbl: {res}')
            if len(res) > 0:
                #self.logger.debug(f'{table_name} table exists')
                return True
            else:
                self.logger.debug(f'{table_name} table NOT FOUND')
                return False
        except Exception as e:
            self.logger.warning(f'DB ERROR {e}')
            return False

    def test_database(self, from_tbl: str):
        where = 'name = ? AND country = ?'
        args = ('ba', 'fr')

        cur = self.conn.cursor()
        sql = f"SELECT {'name'} FROM {from_tbl} WHERE {where} {self.order_str} {self.limit_str}"

        self.logger.debug(f'db test sql={sql} args=[{args}]')
        try:
            cur.execute(sql, args)
            res = cur.fetchall()
            self.logger.debug('DB no error')
            return False
        except Exception as e:
            self.logger.warning(f'DB ERROR {e}')
            return True

    def process_query_list(self, select_string, from_tbl: str, query_list: [Query]):
        # Perform each query in list
        row_list = None
        #result = None
        res = Result.NO_MATCH
        for query in query_list:
            # During shutdown, wildcards are turned off since there is no UI to verify results
            if self.use_wildcards == False and (query.result == Result.WILDCARD_MATCH or query.result == Result.SOUNDEX_MATCH):
                continue
            start = time.time()
            if query.result == Result.WILDCARD_MATCH:
                result = self.word_match(select_string, query.where, from_tbl,
                                         query.args)
            else:
                result = self.select(select_string, query.where, from_tbl,
                                     query.args)
            if row_list:
                row_list.extend(result)
            else:
                row_list = result
            elapsed = time.time() - start
            self.total_time += elapsed
            if elapsed > 5:
                self.logger.debug(f'[{elapsed:.4f}] [{self.total_time:.1f}] len {len(row_list)} from {from_tbl} '
                                  f'where {query.where} val={query.args} ')
            if len(row_list) > 50:
                res = query.result  # Set specified success code
                # self.logger.debug(row_list)
                # Found match.  Break out of loop
                break
        return row_list, res

    def word_match(self, select_string, where, from_tbl, args):
        """
        args[0] contains the string to search for, and may contain
        several words.  This performs a wildcard match on each word, and then
        merges the results into a single result.  During the merge, we note if
        a duplicate occurs, and mark that as a higher priority result.  We
        also note if an individual word has too many results, as we will drop
        those results from the final list after doing the priority checks.
        This should kill off common words from the results, while still
        preserving combinations.

        For example, searching for "Village of Bay", will find all three words
        to have very many results, but the combinations of "Village" and "Bay"
        or "Village" and "of" or "Bay" and "of" will show up in the results.

        The order of the words will also not matter, so results should contain
        "City of Bay Village", "Bay Village" etc.
        """
        words = args[0].split()
        results = []    # the entire merged list of result rows
        res_flags = []  # list of flags, matching results list, 'True' to keep
        for word in words:
            # redo tuple for each word; select_string still has LIKE
            n_args = (f'%{word.strip()}%', *args[1:])
            result = self.select(select_string, where, from_tbl, n_args)
            for row in result:
                # check if already in overall list
                for indx, r_row in enumerate(results):
                    if row[Entry.ID] == r_row[Entry.ID]:
                        # if has same ID as in overall list, mark to keep
                        res_flags[indx] = True
                        break
                else:  # this result row did not match anything
                    # Remove "word" from prefix
                    results.append(row)  # add it to overall list
                    # if reasonable number of results for this word, flag to
                    # keep the result
                    res_flags.append(len(result) < 20)
        # strip out any results not flagged (too many to be interesting)
        result = [results[indx] for indx in range(len(results)) if
                  res_flags[indx]]
        return result

    def set_speed_pragmas(self):
        # Set DB pragmas for speed.  These can lead to corruption!
        self.logger.info('Database pragmas set for speed')
        for txt in ['PRAGMA temp_store = memory',
                    'PRAGMA journal_mode = off',
                    'PRAGMA locking_mode = exclusive',
                    'PRAGMA synchronous = 0']:
            self.set_pragma(txt)

    def set_analyze_pragma(self):
        # Set DB pragmas for database optimize
        self.logger.info(' Database Optimize pragma')
        for txt in ['PRAGMA optimize',
                    ]:
            self.set_pragma(txt)
