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

from geofinder.GeoKeys import Query, Result


class DB:
    """
    Sqlite3  helper functions
    """

    def __init__(self, db_filename: str):
        self.logger = logging.getLogger(__name__)

        # self.select_str = '*'
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
            #sys.exit()
        if error:
            skdfjd = hghg
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

    def db_test(self, from_tbl: str):
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

    def process_query(self, select_string, from_tbl: str, query_list: [Query]):
        # Try each query in list until we find a match
        row_list = None
        result = None
        res = Result.NO_MATCH
        for query in query_list:
            # During shutdown, wildcards are turned off since there is no UI to verify results
            if self.use_wildcards == False and (query.result == Result.WILDCARD_MATCH or query.result == Result.SOUNDEX_MATCH):
                continue
            start = time.time()
            result = self.select(select_string, query.where, from_tbl, query.args)
            if row_list:
                row_list.extend(result)
            else:
                row_list = result
            elapsed = time.time() - start
            self.total_time += elapsed
            if elapsed > 5:
                self.logger.debug(f'[{elapsed:.4f}] [{self.total_time:.1f}] len {len(row_list)} from {from_tbl} '
                                  f'where {query.where} val={query.args} ')
            if len(row_list) > 6:
                res = query.result  # Set specified success code
                # self.logger.debug(row_list)
                # Found match.  Break out of loop
                break
        return row_list, res

    def process_query_list(self, from_tbl: str, query_list: [Query]):
        # Try each query in list until we find a match
        select_str = 'name, country, admin1_id, admin2_id, lat, lon, f_code, geoid, sdx'
        row_list, res = self.process_query(select_string=select_str, from_tbl=from_tbl,
                                           query_list=query_list)
        return row_list, res

    def set_speed_pragmas(self):
        # Set DB pragmas for speed.  These can lead to corruption!   -900
        self.logger.info('Database pragmas set for speed')
        for txt in ['PRAGMA temp_store = memory',
                    'PRAGMA journal_mode = off',
                    'PRAGMA locking_mode = exclusive',
                    'PRAGMA synchronous = 0']:
            self.set_pragma(txt)

    def set_analyze_pragma(self):
        # Set DB pragmas for speed.  These can lead to corruption!   -900
        self.logger.info(' Database Analyze pragma')
        for txt in ['PRAGMA optimize',
                    ]:
            self.set_pragma(txt)
