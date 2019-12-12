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


class DB:
    """
    Sqlite3  helper functions
    """

    def __init__(self, db_filename: str, show_message: bool, exit_on_error: bool):
        """
        DB Helper routines
        :param db_filename: Database filename
        :param show_message: If true, show messagebox to user on errors
        :param exit_on_error: If true, sys exit on significant errors
        """
        self.logger = logging.getLogger(__name__)
        self.order_str = ''
        self.limit_str = ''
        self.cur = None
        self.total_time = 0
        self.total_lookups = 0
        self.use_wildcards = True
        self.show_message = show_message
        self.exit_on_error = exit_on_error

        # create database connection
        self.conn = self.connect(db_filename=db_filename)
        if self.conn is None:
            self.err = True
            self.logger.error(f"Error! cannot open database {db_filename}.")
            raise ValueError('Cannot open database')
        else:
            self.err = False

    def connect(self, db_filename: str):
        """
        Create a database connection to the SQLite database
        :param db_filename: database filename
        :return: Connection object or None
        """
        try:
            conn = sqlite3.connect(db_filename)
            self.logger.info(f'DB {db_filename} connected')
            return conn
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database Connection Error\n {e}')
            self.err = True
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()
            else:
                return None

    @property
    def order_string(self):
        # Get value of  ORDER BY
        return self.order_str

    @order_string.setter
    def order_string(self, order_str: str):
        # Set value of  ORDER BY
        self.order_str = order_str

    @property
    def limit_string(self):
        # Get value for  LIMIT
        return self.limit_str

    @limit_string.setter
    def limit_string(self, limit_str: str):
        # Set value for  LIMIT
        self.limit_str = limit_str

    def set_pragma(self, pragma: str):
        # Set PRAGMA e.g. temp_store = memory;
        cur = self.conn.cursor()
        cur.execute(pragma)
        self.conn.commit()

    def create_table(self, create_table_sql: str):
        """
        Create a table
        :param create_table_sql: a CREATE TABLE statement
        """
        try:
            c = self.conn.cursor()
            c.execute(create_table_sql)
            self.conn.commit()
            self.logger.debug(f'Create DB table \n{create_table_sql}')  # Print  table name for logging
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', e)
            self.err = True
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()

    def create_index(self, create_table_sql: str):
        try:
            c = self.conn.cursor()
            c.execute(create_table_sql)
            self.conn.commit()
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', e)
            self.err = True
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()

    def delete_table(self, tbl):
        cur = self.conn.cursor()
        try:
            # noinspection SqlWithoutWhere
            cur.execute(f'DELETE FROM {tbl}')
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database delete table error\n {e}')
            self.err = True
            self.logger.error(e)
            if self.exit_on_error:
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
        try:
            self.cur.execute(sql, args)
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database Error\n {e}')
            self.err = True
            self.logger.error(e)

        return self.cur.lastrowid

    def commit(self):
        # Commit transaction
        self.cur.execute("commit")

    def select(self, select_str, where, from_tbl, args):
        cur = self.conn.cursor()
        sql = f"SELECT {select_str} FROM {from_tbl} WHERE {where} {self.order_str} {self.limit_str}"
        try:
            cur.execute(sql, args)
            result_list = cur.fetchall()
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database select error\n\n'
            f'SELECT\n {select_str}\n FROM {from_tbl} WHERE\n {where}\n'
            f'{args}\n\n {e}')
            self.err = True
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()
            else:
                result_list = False
        return result_list

    def table_exists(self, table_name)->bool:
        """
        Determine if table exists
        :param table_name:
        :return: True if table exists
        """
        # SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';
        where = "type=? AND name=?"
        from_tbl = 'sqlite_master'
        select_str = 'name'
        args = ('table', table_name)

        cur = self.conn.cursor()

        # See if  Table exists.
        sql = f"SELECT {select_str} FROM {from_tbl} WHERE {where} {self.order_str} {self.limit_str}"

        try:
            cur.execute(sql, args)
            res = cur.fetchall()
            if len(res) > 0:
                return True
            else:
                self.logger.debug(f'{table_name} table NOT FOUND')
                return False
        except Exception as e:
            self.logger.warning(f'DB ERROR {e}')
            return False

    def test_database(self, from_tbl: str, where: str, args):
        """
        Execute a test query on database
        :param from_tbl: table name
        :param where: where clause
        :param args: argument tuple for where clause
        :return: True if error
        """
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

    def set_speed_pragmas(self):
        # Set DB pragmas for speed.  These can lead to corruption!
        self.logger.info('Database pragmas set for speed')
        self.conn.isolation_level = None
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
