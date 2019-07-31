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
import re
import time

from geofinder import DB, Place
from geofinder.GeoKeys import Query, Result, Entry


class GeoDB:
    """
    geoname data database.  Add items, look up items, create tables, indices
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
        self.db.set_params(select_str='name, country, admin1_id, admin2_id, lat, lon, f_code, geoid', order_str='', limit_str='LIMIT 300')
        self.geoid_main_dict = {}  # Key is GEOID, Value is DB ID for entry
        self.geoid_admin_dict = {}  # Key is GEOID, Value is DB ID for entry

    def insert(self, geo_row: (), feat_code: str):
        # We split the data into 3 separate tables, 1) Admin: ADM0/ADM1/ADM2,  and 2) city data

        if feat_code == 'ADM1' or feat_code == 'ADM0' or feat_code == 'ADM2':
            sql = ''' INSERT OR IGNORE INTO admin(name,country, admin1_id,admin2_id,lat,lon,f_code, geoid)
                      VALUES(?,?,?,?,?,?,?,?) '''
            row_id = self.db.execute(sql, geo_row)
            # Add name to dictionary.  Used by AlternateNames for fast lookup during DB build
            self.geoid_admin_dict[geo_row[Entry.ID]] = row_id
        else:
            sql = ''' INSERT OR IGNORE INTO geodata(name, country, admin1_id, admin2_id, lat, lon, f_code, geoid)
                      VALUES(?,?,?,?,?,?,?,?) '''
            row_id = self.db.execute(sql, geo_row)
            # Add name to dictionary.  Used by AlternateNames for fast lookup during DB build
            self.geoid_main_dict[geo_row[Entry.ID]] = row_id

        return row_id

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
        sql_admin_table = """CREATE TABLE IF NOT EXISTS admin    (
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

        for tbl in [sql_geodata_table, sql_admin_table]:
            self.db.create_table(tbl)

    def lookup_place(self, place: Place.Place) -> []:
        """
        Lookup a place in our geoname.org dictionary and update place with Geo_result with lat, long, District, etc
        The dictionary geo_result entry contains: Lat, Long, districtID (County or State or Province ID)
        There can be multiple entries if a city name isnt unique in a country
        """
        self.start = time.time()
        place.result_type = Result.EXACT_MATCH

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

        if place.result_type == Result.EXACT_MATCH and len(place.prefix) > 0:
            place.result_type = Result.PARTIAL_MATCH

    def select_city(self, place: Place):
        """
        Search for  entry - try the most exact match first, then less exact matches
        """
        lookup_target = place.target
        if len(lookup_target) == 0:
            return
        pattern = self.create_wildcard(lookup_target)
        self.logger.debug(f'CITY lookup. Targ=[{lookup_target}] adm1 id=[{place.admin1_id}]'
                          f' adm2 id=[{place.admin2_id}] iso=[{place.country_iso}] patt =[{pattern}]')

        query_list = []

        if len(place.country_iso) == 0:
            # No country present - try lookup by name.   No other queries
            query_list.append(Query(where="name = ?",
                                    args=(lookup_target,),
                                    result=Result.PARTIAL_MATCH))
            place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)
            return

        # Build query list - try each query in order until a match is found
        # Start with the most exact match depending on the data provided.
        if len(place.admin1_name) > 0:
            if len(place.admin2_name) > 0:
                # lookup by name, admin1, admin2
                query_list.append(Query(where="name = ? AND country = ? AND admin1_id = ? AND admin2_id = ?",
                                        args=(lookup_target, place.country_iso, place.admin1_id, place.admin2_id),
                                        result=Result.EXACT_MATCH))

            # lookup by name, admin1
            query_list.append(Query(where="name = ? AND country = ? AND admin1_id = ?",
                                    args=(lookup_target, place.country_iso, place.admin1_id),
                                    result=Result.EXACT_MATCH))

            # lookup by wildcard name, admin1
            query_list.append(Query(where="name LIKE ? AND country = ? AND admin1_id = ?",
                                    args=(pattern, place.country_iso, place.admin1_id),
                                    result=Result.PARTIAL_MATCH))
        elif len(place.admin2_name) == 0:
            # lookup by name
            # admin1 and admin2 werent entered, so a match here is an exact match
            query_list.append(Query(where="name = ? AND country = ?",
                                    args=(lookup_target, place.country_iso),
                                    result=Result.EXACT_MATCH))
        elif len(place.admin2_name) > 0:
            # lookup by name
            # admin1 wasnt entered, so a match here is an exact match
            query_list.append(Query(where="name = ? AND admin2_id=? AND country = ?",
                                    args=(lookup_target, place.admin2_id, place.country_iso),
                                    result=Result.EXACT_MATCH))
        else:
            # lookup by name (partial match since user specified admin)
            query_list.append(Query(where="name = ? AND country = ?",
                                    args=(lookup_target, place.country_iso),
                                    result=Result.PARTIAL_MATCH))

        # lookup by name (partial match since user specified admin)
        query_list.append(Query(where="name LIKE ? AND country = ?",
                                args=(pattern, place.country_iso),
                                result=Result.PARTIAL_MATCH))

        # Try each query in list until we find a match
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)

    def select_admin2(self, place: Place):
        """Search for Admin2 entry"""
        lookup_target = place.admin2_name
        if len(lookup_target) == 0:
            return
        place.target = lookup_target

        # Prioritize an EXACT city match over County match.  (Try admin2 as city first)
        self.logger.debug(f'Try admin2 as city: [{place.target}]')

        query_list = [
            Query(where="name = ? AND country = ? AND admin1_id = ?",
                  args=(lookup_target, place.country_iso, place.admin1_id),
                  result=Result.EXACT_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)

        if len(place.georow_list) > 0:
            # Found match as a City
            place.city1 = place.admin2_name
            place.admin2_name = ''
            place.place_type = Place.PlaceType.CITY
            return

        # Try Admin query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND admin1_id = ? AND f_code=?",
                  args=(lookup_target, place.country_iso, place.admin1_id, 'ADM2'),
                  result=Result.EXACT_MATCH),
            Query(where="name = ? AND country = ? AND f_code=?",
                  args=(lookup_target, place.country_iso, 'ADM2'),
                  result=Result.PARTIAL_MATCH),
            Query(where="name LIKE ? AND country = ? AND f_code=?",
                  args=(self.create_wildcard(lookup_target), place.country_iso, 'ADM2'),
                  result=Result.PARTIAL_MATCH)
        ]

        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(place.georow_list) == 0:
            # Try city rather than County match.
            save_admin2 = place.admin2_name
            place.city1 = place.admin2_name
            place.admin2_name = ''
            self.logger.debug(f'Try admin2 as city: [{place.target}]')

            self.select_city(place)

            if len(place.georow_list) == 0:
                #  not found.  restore admin
                place.admin2_name = save_admin2
                place.city1 = ''
            else:
                # Found match as a City
                place.place_type = Place.PlaceType.CITY
                return

    def select_admin1(self, place: Place):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name

        pattern = self.create_wildcard(lookup_target)
        if len(lookup_target) == 0:
            return

        # self.logger.debug(f'sel adm1 patt={pattern} iso={place.country_iso}')

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND f_code = ? ",
                  args=(lookup_target, place.country_iso, 'ADM1'),
                  result=Result.EXACT_MATCH),
            Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                  args=(pattern, place.country_iso, 'ADM1'),
                  result=Result.PARTIAL_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        # if nothing found, Try admin1 as city instead
        if len(place.georow_list) == 0:
            save_admin1 = place.admin1_name
            place.city1 = place.admin1_name
            place.target = place.city1
            place.admin1_name = ''
            self.logger.debug(f'Try admin as city: [{place.target}]')

            self.select_city(place)

            if len(place.georow_list) == 0:
                # still not found.  restore admin1
                place.admin1_name = save_admin1
                place.city1 = ''
            else:
                place.place_type = Place.PlaceType.CITY

    def get_admin1_id(self, place: Place):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND f_code = ? ",
                  args=(lookup_target, place.country_iso, 'ADM1'),
                  result=Result.EXACT_MATCH),
            Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                  args=(self.create_wildcard(lookup_target), place.country_iso, 'ADM1'),
                  result=Result.PARTIAL_MATCH),
            Query(where="name = ?  AND f_code = ?",
                  args=(lookup_target, 'ADM1'),
                  result=Result.PARTIAL_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            place.admin1_id = row_list[0][Entry.ADM1]
            if place.country_iso == '':
                place.country_iso = row_list[0][Entry.ISO]

    def get_admin2_id(self, place: Place):
        """Search for Admin1 entry"""
        lookup_target = place.admin2_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = []
        if len(place.admin1_id) > 0:
            query_list.append(Query(where="name = ? AND country = ? AND admin1_id=? AND f_code=?",
                                    args=(lookup_target, place.country_iso, place.admin1_id, 'ADM2'),
                                    result=Result.EXACT_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? and admin1_id = ? AND f_code=?",
                                    args=(self.create_wildcard(lookup_target), place.country_iso, place.admin1_id, 'ADM2'),
                                    result=Result.PARTIAL_MATCH))
        else:
            query_list.append(Query(where="name = ? AND country = ? AND f_code=?",
                                    args=(lookup_target, place.country_iso, 'ADM2'),
                                    result=Result.EXACT_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? AND f_code=?",
                                    args=(self.create_wildcard(lookup_target), place.country_iso, 'ADM2'),
                                    result=Result.PARTIAL_MATCH))

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        # self.logger.debug(f'get adm2 id nm={lookup_target} res={row_list}')

        if len(row_list) > 0:
            row = row_list[0]
            place.admin2_id = row[Entry.ADM2]

    def get_admin1_name(self, place: Place) -> str:
        """Search for Admin1 entry"""
        lookup_target = place.admin1_id
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin1_id = ? AND country = ?  AND f_code = ? ",
                  args=(lookup_target, place.country_iso, 'ADM1'),
                  result=Result.EXACT_MATCH)
        ]
        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            place.admin1_name = row[Entry.NAME]
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

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            place.admin2_name = row[Entry.NAME]
            # self.logger.debug(f'adm2 nm = {place.admin2_name}')
            return place.admin2_name
        else:
            return ''

    def select_country(self, place: Place):
        """Search for Admin1 entry"""
        lookup_target = place.country_iso
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="country = ? AND f_code = ? ",
                  args=(place.country_iso, 'ADM0'),
                  result=Result.EXACT_MATCH)]

        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)
        # self.build_result_list(place.georow_list, place.event_year)

    def lookup_geoid(self, place: Place) -> None:
        """Search for GEOID"""
        query_list = [
            Query(where="geoid = ? ",
                  args=(place.target,),
                  result=Result.EXACT_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)
        if len(place.georow_list) == 0:
            place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

    def lookup_main_dbid(self, place: Place) -> None:
        """Search for DB ID"""
        query_list = [
            Query(where="id = ? ",
                  args=(place.target,),
                  result=Result.EXACT_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)

    def lookup_admin_dbid(self, place: Place) -> None:
        """Search for DB ID"""
        query_list = [
            Query(where="id = ? ",
                  args=(place.target,),
                  result=Result.EXACT_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

    def get_country_name(self, iso: str) -> str:
        """ return country name for specified ISO code """
        if len(iso) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="country = ? AND f_code = ? ",
                  args=(iso, 'ADM0'),
                  result=Result.EXACT_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            res = row_list[0][Entry.NAME]
        return res

    def get_country_iso(self, place: Place) -> str:
        """ Return ISO code for specified country"""
        lookup_target = place.country_name
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND f_code = ? ",
                  args=(lookup_target, 'ADM0'),
                  result=Result.EXACT_MATCH),
            Query(where="name LIKE ?  AND f_code = ? ",
                  args=(self.create_wildcard(lookup_target), 'ADM0'),
                  result=Result.PARTIAL_MATCH)]

        row_list, result_code = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            res = row_list[0][Entry.ISO]
            if len(row_list) == 1:
                place.country_name = row_list[0][Entry.NAME]
        else:
            res = ''

        return res

    def copy_georow_to_place(self, row, place: Place):
        # Copy data from DB row into Place
        # self.logger.debug(row)
        place.admin1_id = ''
        place.admin2_id = ''
        place.city1 = ''

        place.country_iso = row[Entry.ISO]
        place.country_name = self.get_country_name(row[Entry.ISO])
        place.lat = row[Entry.LAT]
        place.lon = row[Entry.LON]
        place.feature = row[Entry.FEAT]
        place.geoid = row[Entry.ID]

        if place.feature == 'ADM0':
            self.place_type = Place.PlaceType.COUNTRY
            pass
        elif place.feature == 'ADM1':
            place.admin1_id = row[Entry.ADM1]
            self.place_type = Place.PlaceType.ADMIN1
        elif place.feature == 'ADM2':
            place.admin1_id = row[Entry.ADM1]
            place.admin2_id = row[Entry.ADM2]
            self.place_type = Place.PlaceType.ADMIN2
        else:
            place.admin1_id = row[Entry.ADM1]
            place.admin2_id = row[Entry.ADM2]
            place.city1 = row[Entry.NAME]
            self.place_type = Place.PlaceType.CITY

        place.admin1_name = self.get_admin1_name(place)
        place.admin2_name = self.get_admin2_name(place)

        if place.admin2_name is None:
            place.admin2_name = ''
        if place.admin1_name is None:
            place.admin1_name = ''
        if place.city1 is None:
            place.city1 = ''

    def clear_geoname_data(self):
        # Delete all the geoname data
        for tbl in ['geodata', 'admin']:
            # noinspection SqlWithoutWhere
            self.db.delete_table(tbl)

    def create_geoid_index(self):
        # Create indices
        self.db.create_index(create_table_sql='CREATE INDEX geoid_idx ON geodata(geoid)')
        self.db.create_index(create_table_sql='CREATE INDEX admgeoid_idx ON admin(geoid)')

    def create_indices(self):
        # Create indices
        self.db.create_index(create_table_sql='CREATE INDEX name_idx ON geodata(name)')
        self.db.create_index(create_table_sql='CREATE INDEX country_idx ON geodata(country)')
        self.db.create_index(create_table_sql='CREATE INDEX admin1_idx ON geodata(admin1_id)')
        # self.db.create_index(create_table_sql='CREATE INDEX geoid_idx ON geodata(geoid)')

        self.db.create_index(create_table_sql='CREATE INDEX admname_idx ON admin(name)')
        self.db.create_index(create_table_sql='CREATE INDEX admcountry_idx ON admin(country)')
        self.db.create_index(create_table_sql='CREATE INDEX admadmin1_idx ON admin(admin1_id)')

    @staticmethod
    def make_georow(name: str, iso: str, adm1: str, adm2: str, lat: float, lon: float, feat: str, geoid: str) -> ():
        # Return a dummy geo-row
        res = (name, iso, adm1, adm2, lat, lon, feat, geoid)
        return res

    def get_row_count(self) -> int:
        return self.db.get_row_count()

    @staticmethod
    def create_wildcard(lookup_target):
        # Create SQL wildcard pattern (convert * to %).  Add % on end
        pattern = re.sub(r"b\Srg", "b_rg", lookup_target)  # Convert berg, burg, borg to b_rg
        pattern = re.sub(r"gr\Sy", "gr_y", pattern)  # Convert gray,grey to gr_y
        pattern = re.sub(r"\*", "%", pattern)
        pattern = pattern + '%'
        return re.sub("%%", "%", pattern)
