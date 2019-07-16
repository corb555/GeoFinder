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
import time
from operator import itemgetter

import DB
import Place
from GeoKeys import Query, Result


class Entry:
    NAME = 0
    ISO = 1
    ADM1 = 2
    ADM2 = 3
    LAT = 4
    LON = 5
    FEAT = 6
    ID = 7


class GeoDB:
    """
    Manage the geoname data database.  Create tables, indices, add items, look up items
    """

    def __init__(self, database):
        self.logger = logging.getLogger(__name__)
        self.start = 0
        self.db = DB.DB(database)
        if self.db.err:
            self.logger.error(f"Error! cannot open database {database}.")
            raise ValueError('Cannot open database')
        else:
            self.create_tables()

        self.db.set_speed_pragmas()
        self.db.set_params(select_str='name, country, admin1_id, admin2_id, lat, lon, f_code', order_str='', limit_str='LIMIT 300')

    def insert(self, geo_row: (), feat_code: str):
        # We split the data into 3 separate tables, ADM1, ADM2 data, and general data
        if feat_code == 'ADM1':
            sql = ''' INSERT OR IGNORE INTO admin1(name,country, admin1_id,admin2_id,lat,lon,f_code, geoid)
                      VALUES(?,?,?,?,?,?,?,?) '''
        elif feat_code == 'ADM2':
            sql = ''' INSERT OR IGNORE INTO admin2(name,country, admin1_id,admin2_id,lat,lon,f_code, geoid)
                      VALUES(?,?,?,?,?,?,?,?) '''
        else:
            sql = ''' INSERT OR IGNORE INTO geodata(name, country, admin1_id, admin2_id, lat, lon, f_code, geoid)
                      VALUES(?,?,?,?,?,?,?,?) '''

        return self.db.execute(sql, geo_row)

    def create_tables(self):
        # name, country, admin1_id, admin2_id, lat, lon, f_code, geoid
        sql_geodata_table = """CREATE TABLE IF NOT EXISTS geodata    (
                id           integer primary key autoincrement not null,
                name     text,
                country     text,
                admin1_id     text,
                admin2_id text,
                lat      text,
                lon       text,
                f_code      text,
                geoid      text
                                    );"""

        # name, country, admin1_id, admin2_id, lat, lon, f_code, geoid
        sql_admin1_table = """CREATE TABLE IF NOT EXISTS admin1    (
                id           integer primary key autoincrement not null,
                name     text,
                country     text,
                admin1_id     text,
                admin2_id text,
                lat      text,
                lon       text,
                f_code      text,
                geoid      text
                                    );"""

        # name, country, admin1_id, admin2_id, lat, lon, f_code, geoid
        sql_admin2_table = """CREATE TABLE IF NOT EXISTS admin2    (
                id           integer primary key autoincrement not null,
                name     text,
                country     text,
                admin1_id     text,
                admin2_id text,
                lat      text,
                lon       text,
                f_code      text,
                geoid      text
                                    );"""

        for tbl in [sql_geodata_table, sql_admin1_table, sql_admin2_table]:
            self.db.create_table(tbl)

    def lookup_place(self, place: Place.Place) -> []:
        """
        Lookup a place in our geoname.org dictionary and update place with Geo_result with lat, long, District, etc
        The dictionary geo_result entry contains: Lat, Long, districtID (County or State or Province ID)
        There can be multiple entries if a city name isnt unique in a country
        """
        self.start = time.time()
        # Default result type to NOT IDENTICAL until we find an exact match
        place.result_type = Result.PARTIAL_MATCH

        if place.place_type == Place.PlaceType.ADMIN1:
            self.select_admin1(place)
        elif place.place_type == Place.PlaceType.ADMIN2:
            self.get_admin1_id(place=place)
            self.select_admin2(place)
        elif place.place_type == Place.PlaceType.COUNTRY:
            self.select_country(place)
        else:
            self.get_admin1_id(place=place)
            self.get_admin2_id(place=place)
            self.select_city(place)

        if len(place.georow_list) == 0:
            place.result_type = Result.NO_MATCH
        elif len(place.georow_list) > 1:
            place.result_type = Result.MULTIPLE_MATCHES

    def select_city(self, place: Place):
        """
        Search for  entry - try the most exact match first, then less exact matches
        """
        from_tbl = 'main.geodata'
        lookup_target = place.target
        if len(lookup_target) == 0:
            return
        pattern = self.db.convert_wildcard(lookup_target)

        self.logger.debug(f'CITY lookup. Targ=[{lookup_target}] adm1 id=[{place.admin1_id}]'
                          f' adm2 id=[{place.admin2_id}] iso=[{place.country_iso}]')

        if len(place.admin1_name) > 0 and len(place.admin2_name) > 0:
            # Try fully qualified lookup with admin1 and with admin2
            where = 'name = ? AND country= ? AND admin1_id = ? AND admin2_id = ?'
            place.georow_list = self.db.select(where, from_tbl, (lookup_target, place.country_iso, place.admin1_id, place.admin2_id))
            self.build_result_list(place.georow_list)
            if len(place.georow_list) == 1:
                place.result_type = Result.EXACT_MATCH

        if len(place.georow_list) == 0 and len(place.admin1_name) > 0:
            # No match - Try lookup without Admin2
            where = 'name = ? AND country = ? AND admin1_id = ?'
            place.georow_list = self.db.select(where, from_tbl, (lookup_target, place.country_iso, place.admin1_id))
            # self.logger.debug(f'lkp without adm2 ad2len={len(place.admin2_name)} rowlen={len(place.georow_list)}')
            self.build_result_list(place.georow_list)
            if len(place.georow_list) == 1 and len(place.admin2_name) == 0:
                # self.logger.debug('match')
                place.result_type = Result.EXACT_MATCH

        if len(place.georow_list) == 0 and len(place.admin1_name) > 0 and len(place.admin2_name) > 0:
            # Try wildcard with  admin1 and with admin2
            where = 'name like ? AND country= ? AND admin1_id = ? AND admin2_id = ?'
            place.georow_list = self.db.select(where, from_tbl, (pattern, place.country_iso, place.admin1_id, place.admin2_id))

        if len(place.georow_list) == 0 and len(place.admin1_name) > 0:
            # Try with wildcard and ADMIN1
            where = 'name LIKE ? AND country = ? AND admin1_id = ? '
            place.georow_list = self.db.select(where, from_tbl, (pattern, place.country_iso, place.admin1_id))

        if len(place.georow_list) == 0:
            # No match - Try exact name without adm1 or adm2
            where = 'name = ? AND country = ? '
            place.georow_list = self.db.select(where, from_tbl, (lookup_target, place.country_iso))
            if len(place.georow_list) == 1 and len(place.admin1_name) == 0 and len(place.admin2_name) == 0:
                place.result_type = Result.EXACT_MATCH

        if len(place.georow_list) == 0:
            # No match - Try with wildcard without ADMIN1 or 2
            # self.logger.debug(f'city wildcard [{pattern}]')
            where = 'name LIKE ? AND country = ?'
            place.georow_list = self.db.select(where, from_tbl, (pattern, place.country_iso))

        self.build_result_list(place.georow_list)
        return

    def select_admin2(self, place: Place):
        """Search for Admin2 entry"""
        lookup_target = place.admin2_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND admin1_id = ?",
                  args=(lookup_target, place.country_iso, place.admin1_id),
                  result=Result.EXACT_MATCH),
            Query(where="name = ? AND country = ?",
                  args=(lookup_target, place.country_iso),
                  result=Result.PARTIAL_MATCH),
            Query(where="name LIKE ? AND country = ?",
                  args=(self.db.convert_wildcard(lookup_target), place.country_iso),
                  result=Result.PARTIAL_MATCH)
        ]

        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin2', query_list=query_list)

    def select_admin1(self, place: Place):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? ",
                  args=(lookup_target, place.country_iso),
                  result=Result.EXACT_MATCH),
            Query(where="name LIKE ? AND country = ? ",
                  args=(self.db.convert_wildcard(lookup_target), place.country_iso),
                  result=Result.PARTIAL_MATCH)]

        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin1', query_list=query_list)

    def get_admin1_id(self, place: Place):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ?",
                  args=(lookup_target, place.country_iso),
                  result=Result.EXACT_MATCH),
            Query(where="name LIKE ? AND country = ?",
                  args=(self.db.convert_wildcard(lookup_target), place.country_iso),
                  result=Result.PARTIAL_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin1', query_list=query_list)

        if len(row_list) == 1:
            place.admin1_id = row_list[0][Entry.ADM1]

    def get_admin2_id(self, place: Place):
        """Search for Admin1 entry"""
        lookup_target = place.admin2_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND admin1_id=?",
                  args=(lookup_target, place.country_iso, place.admin1_id),
                  result=Result.EXACT_MATCH),
            Query(where="name LIKE ? AND country = ? and admin1_id = ? ",
                  args=(self.db.convert_wildcard(lookup_target), place.country_iso, place.admin1_id),
                  result=Result.PARTIAL_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin2', query_list=query_list)

        if len(row_list) == 1:
            row = row_list[0]
            place.admin2_id = row[Entry.ADM2]

    def get_admin1_name(self, place: Place) -> str:
        """Search for Admin1 entry"""
        lookup_target = place.admin1_id
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin1_id = ? AND country = ? ",
                  args=(lookup_target, place.country_iso),
                  result=Result.EXACT_MATCH)
        ]
        row_list, res = self.db.process_query_list(from_tbl='main.admin1', query_list=query_list)

        if len(row_list) == 1:
            row = row_list[0]
            place.admin1_name = row[Entry.NAME]
            # self.logger.debug(f'adm1 nm = {place.admin1_name}')
            return place.admin1_name
        else:
            return ''

    def get_admin2_name(self, place: Place) -> str:
        """Search for Admin1 entry"""
        lookup_target = place.admin2_id
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin2_id = ? AND country = ? AND admin1_id = ?",
                  args=(lookup_target, place.country_iso, place.admin1_id),
                  result=Result.EXACT_MATCH),
            Query(where="admin2_id = ? AND country = ?",
                  args=(lookup_target, place.country_iso),
                  result=Result.PARTIAL_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin2', query_list=query_list)

        if len(row_list) == 1:
            row = row_list[0]
            place.admin2_name = row[Entry.NAME]
            # self.logger.debug(f'adm2 nm = {place.admin2_name}')
            return place.admin2_name
        else:
            return ''

    def select_country(self, place: Place):
        """Search for country entry - Countries are not in DB so we create a fake response"""
        place.result_type = Result.EXACT_MATCH
        place.georow_list.append(self.dummy_georow(name=place.name, adm1='0', adm2='0'))
        self.build_result_list(place.georow_list)

    def get_geodata(self, row, place: Place):
        # Copy data from DB row into Place
        place.city1 = row[Entry.NAME]
        place.country_iso = row[Entry.ISO]
        place.admin1_id = row[Entry.ADM1]
        place.admin2_id = row[Entry.ADM2]
        place.lat = row[Entry.LAT]
        place.lon = row[Entry.LON]
        place.feature = row[Entry.FEAT]

        place.admin1_name = self.get_admin1_name(place)
        place.admin2_name = self.get_admin2_name(place)

        if place.admin2_name is None:
            place.admin2_name = ''
        if place.admin1_name is None:
            place.admin1_name = ''
        if place.city1 is None:
            place.city1 = ''

    @staticmethod
    def build_result_list(georow_list):
        # Create a sorted version of result_list without any dupes
        # Add note if we hit the lookup limit
        if len(georow_list) > 299:
            georow_list.append(GeoDB.dummy_georow(name='(plus more...)', adm1='0', adm2='0'))

        # sort list by State/Province, and County
        list_copy = sorted(georow_list, key=itemgetter(Entry.ADM1, Entry.ADM2))
        georow_list.clear()
        prev_lat = 99.0
        prev_lon = 99.0
        prev_city = ''
        distance_cutoff = 0.5  # Value to determine if two lat/longs are similar

        # Go through list and remove dupes (any adjacent items with same name and same lat/lon)
        for geo_row in list_copy:
            lat = float(geo_row[Entry.LAT])
            lon = float(geo_row[Entry.LON])
            # Find if two items are similar lat/lon (within Box Distance of 0.5 degrees)
            if abs(prev_lat - lat) + abs(prev_lon - lon) > distance_cutoff or geo_row[Entry.NAME] != prev_city:
                # Lat/lon are different.  Add item
                georow_list.append(geo_row)

            prev_city = geo_row[Entry.NAME]
            prev_lat = lat
            prev_lon = lon

    def clear_geoname_data(self):
        # Delete all the geoname data
        for tbl in ['geodata', 'admin1', 'admin2']:
            # noinspection SqlWithoutWhere
            self.db.delete_table(tbl)

    def create_indices(self):
        # Create indices
        self.db.create_index(create_table_sql='CREATE INDEX name_idx ON geodata(name)')
        self.db.create_index(create_table_sql='CREATE INDEX country_idx ON geodata(country)')
        self.db.create_index(create_table_sql='CREATE INDEX admin1_idx ON geodata(admin1_id)')

        self.db.create_index(create_table_sql='CREATE INDEX name_idx ON admin1(name)')
        self.db.create_index(create_table_sql='CREATE INDEX country_idx ON admin1(country)')

        self.db.create_index(create_table_sql='CREATE INDEX name_idx ON admin2(name)')
        self.db.create_index(create_table_sql='CREATE INDEX country_idx ON admin2(country)')
        self.db.create_index(create_table_sql='CREATE INDEX admin1_idx ON admin2(admin1_id)')

    @staticmethod
    def dummy_georow(name: str, adm1: str, adm2: str) -> ():
        # Return a dummy geo-row
        res = (name, '', adm1, adm2, 99.0, 99.0, 'ADM0', 'A1')
        return res

    def get_stats(self) -> int:
        return self.db.get_row_count()
