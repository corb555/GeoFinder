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
from tkinter import messagebox

from geofinder.GeoKeys import Query, Result

DB_CORRUPT_MSG = 'Database error'


class DB:
    """
    Sqlite3  helper functions
    """

    def __init__(self, db_filename: str):
        self.logger = logging.getLogger(__name__)

        self.select_str = '*'
        self.order_str = ''
        self.limit_str = ''
        self.cur = None

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
            messagebox.showwarning('Error', f'{DB_CORRUPT_MSG}\n {e}')
            self.err = True
            self.logger.error(e)
            sys.exit()

    def set_params(self, select_str: str, order_str: str, limit_str: str):
        # Set values for SELECT, ORDER BY, and LIMIT
        self.select_str = select_str
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
        # noinspection SqlWithoutWhere
        try:
            cur.execute(f'DELETE FROM {tbl}')
        except Exception as e:
            messagebox.showwarning('Error', f'{DB_CORRUPT_MSG}\n {e}')
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
        #try:
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

    def select(self, where, from_tbl, args):
        cur = self.conn.cursor()
        sql = f"SELECT {self.select_str} FROM {from_tbl} WHERE {where} {self.order_str} {self.limit_str}"
        res = [""]
        try:
            cur.execute(sql, args)
            res = cur.fetchall()
        except Exception as e:
            messagebox.showwarning('Error', f'{DB_CORRUPT_MSG}\n {e}')
            self.err = True
            self.logger.error(e)
            sys.exit()
        return res

    def db_test(self, from_tbl: str):
        where = 'name like ? AND country like ?'
        args = ('b%','b%')

        cur = self.conn.cursor()
        sql = f"SELECT {self.select_str} FROM {from_tbl} WHERE {where} {self.order_str} {self.limit_str}"

        self.logger.debug(f'db test sql={sql} args=[{args}]')
        try:
            cur.execute(sql, args)
            res = cur.fetchall()
            self.logger.debug('DB no error')
            return False
        except Exception as e:
            self.logger.debug('DB ERROR')
            return True

    def process_query_list(self, from_tbl: str, query_list: [Query]):
        # Try each query in list until we find a match
        row_list = None
        res = Result.NO_MATCH
        for query in query_list:
            row_list = self.select(query.where, from_tbl, query.args)
            #self.logger.debug(f'select x from {from_tbl}  where {query.where} val={query.args}')
            if len(row_list) > 0:
                res = query.result  # Set specified success code
                #self.logger.debug(row_list)
                # Found match.  Break out of loop
                break

        return row_list, res

    def set_speed_pragmas(self):
        # Set DB pragmas for speed.  These can lead to corruption!
        self.logger.info('Database pragmas set for speed')
        for txt in ['PRAGMA temp_store = memory',
                    'PRAGMA journal_mode = off',
                    'PRAGMA cache_size = -500',
                    'PRAGMA synchronous = 0']:
            self.set_pragma(txt)
