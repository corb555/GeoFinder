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
            Initialize and create a database connection to db_filename
        # Args:
            db_filename: Database filename
            show_message: If true, show messagebox to user on errors
            exit_on_error: If true, sys exit on significant errors
        # Raises:
            ValueError('Cannot open database')
        """
        self.logger = logging.getLogger(__name__)
        self._order_str = ''
        self._limit_str = ''
        self.cur = None
        self.total_time = 0
        self.total_lookups = 0
        self.use_wildcards = True
        self.show_message = show_message
        self.exit_on_error = exit_on_error
        self.err = ''

        # create database connection
        self.conn = self._connect(db_filename=db_filename)
        if self.conn is None:
            self.err = f"Error! cannot open database {db_filename}."
            self.logger.error(f"Error! cannot open database {db_filename}.")
            raise ValueError('Cannot open database')

    def _connect(self, db_filename: str):
        """
            Create a database connection to the SQLite database

        # Args:
            db_filename: database filename
        # Returns:
            Connection object or None. Self.err is set to Exception text. Shows Messagebox and/or exits on error if flags set.   
        """
        self.err = ''
        try:
            conn = sqlite3.connect(db_filename)
            self.logger.info(f'DB {db_filename} connected')
            return conn
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database Connection Error\n {e}')
            self.err = e
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()
            else:
                return None

    @property
    def order_string(self):
        """
        Get value of  ORDER BY   
        Returns: value of  ORDER BY
        """
        return self._order_str

    @order_string.setter
    def order_string(self, order_str: str):
        """
        Set value for ORDER BY parameter

        # Args:
            order_str:   

        # Returns: None
        """
        self._order_str = order_str

    @property
    def limit_string(self):
        """
        Get value of  Limit parameter   
        Returns: value of LIMIT parameter
        """
        return self._limit_str

    @limit_string.setter
    def limit_string(self, limit_str: str):
        """
        Set value for LIMIT parameter

        # Args:
            limit_str:   

        # Returns: None
        """
        self._limit_str = limit_str

    def set_pragma(self, pragma: str):
        """
        Set a sqlite3 PRAGMA e.g. 'temp_store = memory'   
        # Args:
            pragma: pragma statement

        Returns: None
        """
        cur = self.conn.cursor()
        cur.execute(pragma)
        self.conn.commit()

    def create_table(self, create_table_sql: str):
        """
        Execute a SQL create table statement   
        # Args:
            create_table_sql: a full CREATE TABLE SQL statement   

        # Returns: True if error.  Self.err is set to Exception text. Shows Messagebox and/or exits on error if flags set.   
        # Raises: Nothing.  DB exceptions are suppressed.  
        """
        self.err = ''
        try:
            c = self.conn.cursor()
            c.execute(create_table_sql)
            self.conn.commit()
            #self.logger.debug(f'Create DB table \n{create_table_sql}')  # Print  table name for logging
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', e)
            self.err = e
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()
            return True
        return False

    def create_index(self, create_index_sql: str):
        """
        Execute a SQL create index statement
        # Args:
            create_index_sql: a full CREATE INDEX SQL statement

        # Returns: True if error.  Self.err is set to Exception text. Shows Messagebox and/or exits on error if flags set.   
        # Raises: Nothing.  DB exceptions are suppressed. 
        """
        self.err = ''
        try:
            c = self.conn.cursor()
            c.execute(create_index_sql)
            self.conn.commit()
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', e)
            self.err = e
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()
            return True
        return False

    def delete_table(self, tbl):
        """
        Delete table

        # Args:
            tbl:  table name
                # Returns: True if error.  Self.err is set to Exception text. Shows Messagebox and/or exits on error if flags set.   
        # Raises: Nothing.  DB exceptions are suppressed.   
        """
        self.err = ''
        cur = self.conn.cursor()
        try:
            # noinspection SqlWithoutWhere
            cur.execute(f'DELETE FROM {tbl}')
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database delete table error\n {e}')
            self.err = e
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()
            return True
        return False

    def get_row_count(self, table_name):
        """
        Get row count of specified table
        # Args:
            table_name: 
        Returns: row count of specified table
        """
        cur = self.conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM {table_name}')
        res = cur.fetchall()
        count = res[0][0]
        return count

    def begin(self):
        """ Begin transaction """
        self.cur = self.conn.cursor()
        self.cur.execute('BEGIN')

    def execute(self, sql, args):
        """
        Execute a SQL statement
        # Args:
            sql: a full SQL statement

        # Returns: True if error.  Self.err is set to Exception text. Shows Messagebox and/or exits on error if flags set.   
        # Raises: Nothing.  DB exceptions are suppressed. 
        """
        self.err = ''
        try:
            self.cur.execute(sql, args)
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database Error\n {e}')
            self.err = e
            self.logger.error(e)
            return True

        return False

    def commit(self):
        """ Commit transaction """
        self.cur.execute("commit")

    def select(self, select_str, where, from_tbl, args):
        """
        Execute a SELECT statement   

        # Args:   
            select_str: string for SELECT xx   
            where: Where clause   
            from_tbl: Table name   
            args: Args tuple for Select   
            Note - ORDER clause and LIMIT clause are filled in with previously set values

        # Returns: Result list.  Self.err is set to Exception text. Shows Messagebox and/or exits on error if flags set.   
        # Raises: Nothing.  DB exceptions are suppressed. 

        """
        self.err = ''
        cur = self.conn.cursor()
        sql = f"SELECT {select_str} FROM {from_tbl} WHERE {where} {self.order_string} {self.limit_string}"
        try:
            cur.execute(sql, args)
            result_list = cur.fetchall()
        except Exception as e:
            if self.show_message:
                messagebox.showwarning('Error', f'Database select error\n\n'
            f'SELECT\n {select_str}\n FROM {from_tbl} WHERE\n {where}\n'
            f'{args}\n\n {e}')
            self.err = e
            self.logger.error(e)
            if self.exit_on_error:
                sys.exit()
            else:
                result_list = None
        return result_list

    def table_exists(self, table_name)->bool:
        """
            Returns whether table exists
        # Args:
            table_name:
        # Returns:
            True if table exists
        # Raises: Nothing.  DB exceptions are suppressed
        """
        # SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';
        self.err = ''
        where = "type=? AND name=?"
        from_tbl = 'sqlite_master'
        select_str = 'name'
        args = ('table', table_name)

        cur = self.conn.cursor()

        # See if  Table exists.
        sql = f"SELECT {select_str} FROM {from_tbl} WHERE {where} {self.order_string} {self.limit_string}"

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
            self.err = e
            return False

    def test_database(self, select_str: str, from_tbl: str, where: str, args):
        """
            Execute a test SELECT query on database
        # Args:
            select_str: SELECT parameter
            from_tbl: table name
            where: where clause
            args: argument tuple for where clause
        # Returns:
            True if error
        # Raises: Nothing.  DB exceptions are suppressed
        """
        self.err = ''
        cur = self.conn.cursor()
        sql = f"SELECT {select_str} FROM {from_tbl} WHERE {where} {self.order_string} {self.limit_string}"

        self.logger.debug(f'db test sql={sql} args=[{args}]')
        try:
            cur.execute(sql, args)
            res = cur.fetchall()
            self.logger.debug('DB no error')
            return False
        except Exception as e:
            self.logger.warning(f'DB ERROR {e}')
            self.err = e
            return True

    def set_speed_pragmas(self):
        """
        Set DB pragmas for speed.  **Use with caution as these can lead to corruption!**   
        'PRAGMA temp_store = memory'   
        'PRAGMA journal_mode = off'   
        'PRAGMA locking_mode = exclusive'   
        'PRAGMA synchronous = 0   
        """
        self.logger.debug('Database pragmas set for speed')
        self.conn.isolation_level = None
        for txt in ['PRAGMA temp_store = memory',
                    'PRAGMA journal_mode = off',
                    'PRAGMA locking_mode = exclusive',
                    'PRAGMA synchronous = 0']:
            self.set_pragma(txt)

    def set_optimize_pragma(self):
        """
        Set 'PRAGMA optimize'
        """
        self.logger.info(' Database Optimize pragma')
        for txt in ['PRAGMA optimize',
                    ]:
            self.set_pragma(txt)
