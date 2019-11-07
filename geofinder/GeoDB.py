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
import os
import re
import sys
import time
from tkinter import messagebox

from geofinder import DB, Loc, GeoKeys, MatchScore, Country
from geofinder.GeoKeys import Query, Result, Entry, get_soundex


class GeoDB:
    """
    geoname data database.  Add items, look up items, create tables, indices
    """

    def __init__(self, db_path, version):
        self.logger = logging.getLogger(__name__)
        self.start = 0
        self.match = MatchScore.MatchScore()

        self.db_path = db_path
        # See if DB exists
        if os.path.exists(db_path):
            db_exists = True
        else:
            db_exists = False

        self.db = DB.DB(db_path)
        if self.db.err:
            self.logger.error(f"Error! cannot open database {db_path}.")
            raise ValueError('Cannot open database')

        # If DB exists
        if db_exists:
            # Run sanity test on DB
            res = self.db.db_test('main.geodata')

            if res:
                self.logger.warning(f'DB error for {db_path}')
                if messagebox.askyesno('Error',
                                       f'Geoname database is empty or corrupt:\n\n {db_path} \n\nDo you want to delete it and rebuild?'):
                    messagebox.showinfo('', 'Deleting Geoname database')
                    self.db.conn.close()
                    os.remove(db_path)
                sys.exit()
        else:
            # DB didnt exist.  Create tables.
            self.create_tables()
            if version:
                self.insert_version(version)

        self.db.set_speed_pragmas()
        self.db.set_params(order_str='', limit_str='LIMIT 105')
        self.geoid_main_dict = {}  # Key is GEOID, Value is DB ID for entry
        self.geoid_admin_dict = {}  # Key is GEOID, Value is DB ID for entry
        self.place_type = ''

    def delete_dbZZZ(self):
        self.logger.info('Deleting geoname DB')

    def lookup_place(self, place: Loc.Loc) -> []:
        """
        Lookup a place in our geoname.org dictionary and update place with Geo_result with lat, long, District, etc
        The dictionary geo_result entry contains: Lat, Long, districtID (County or State or Province ID)
        There can be multiple entries if a city name isnt unique in a country
        """
        result_place: Loc = Loc.Loc()
        self.start = time.time()
        place.result_type = Result.STRONG_MATCH

        if place.country_iso != '' and place.country_name == '':
            place.country_name = self.get_country_name(place.country_iso)

        # Lookup Place based on Place Type
        if place.place_type == Loc.PlaceType.ADMIN1:
            self.select_admin1(place)
        elif place.place_type == Loc.PlaceType.ADMIN2:
            if place.admin1_id == '':
                self.get_admin1_id(place=place)
            self.select_admin2(place)
            if len(place.georow_list) == 0:
                # Try search with some text replacements
                place.admin2_name, modified = GeoKeys.admin2_normalize(place.admin2_name)
                if modified:
                    self.select_admin2(place)
        elif place.place_type == Loc.PlaceType.COUNTRY:
            self.select_country(place)
        elif place.place_type == Loc.PlaceType.ADVANCED_SEARCH:
            self.advanced_search(place)
        else:
            # Lookup as City
            if place.admin2_id == '':
                self.get_admin2_id(place=place)
            self.select_city(place)

        # nm = place.original_entry
        # self.logger.debug(f'Search results for {place.target} pref[{place.prefix}]')
        min_score = 9999

        # Add search quality score to each entry
        for idx, rw in enumerate(place.georow_list):
            self.copy_georow_to_place(row=rw, place=result_place)

            if len(place.prefix) > 0 and result_place.prefix == '':
                result_place.prefix = ' '
                result_place.prefix_commas = ','
            else:
                result_place.prefix = ''

            score = self.match.match_score(inp_place=place, res_place=result_place)
            if score < min_score:
                min_score = score

            # Convert row tuple to list and extend so we can assign score
            update = list(rw)
            update.append(1)
            update[GeoKeys.Entry.SCORE] = score
            place.georow_list[idx] = tuple(update)  # Convert back from list to tuple

            # Remove items in prefix that are in result
            tk_list = result_place.original_entry.split(",")
            if place.place_type != Loc.PlaceType.ADVANCED_SEARCH:
                for item in tk_list:
                    place.prefix = re.sub(item.strip(' ').lower(), '', place.prefix)

        if place.result_type == Result.STRONG_MATCH and len(place.prefix) > 0:
            place.result_type = Result.PARTIAL_MATCH

        if place.result_type == Result.STRONG_MATCH and min_score > 10:
            place.result_type = Result.PARTIAL_MATCH

    def select_city(self, place: Loc):
        """
        Search for  entry - try the most exact match first, then less exact matches
        """
        lookup_target = place.target
        if len(lookup_target) == 0:
            return
        pattern = self.create_wildcard(lookup_target)
        quick_pattern = self.create_quick_wildcard(lookup_target)

        sdx = get_soundex(lookup_target)
        #self.logger.debug(f'CITY lkp targ=[{lookup_target}] adm1 id=[{place.admin1_id}]'
        #                  f' adm2 id=[{place.admin2_id}] iso=[{place.country_iso}] patt =[{pattern}] sdx={sdx} pref={place.prefix}')

        query_list = []

        if len(place.country_iso) == 0:
            # No country present - try lookup by name.
            query_list.append(Query(where="name = ?",
                                    args=(lookup_target,),
                                    result=Result.PARTIAL_MATCH))
            # lookup by wildcard name
            query_list.append(Query(where="name LIKE ?",
                                    args=(quick_pattern,),
                                    result=Result.WILDCARD_MATCH))
            # lookup by soundex
            query_list.append(Query(where="sdx = ?",
                                    args=(sdx,),
                                    result=Result.SOUNDEX_MATCH))

            place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)
            # self.logger.debug(place.georow_list)
            return

        # Build query list - try each query in order until a match is found
        # Start with the most exact match depending on the data provided.
        if len(place.admin1_name) > 0:
            # lookup by name, ADMIN1, country
            query_list.append(Query(where="name = ? AND country = ? AND admin1_id = ?",
                                    args=(lookup_target, place.country_iso, place.admin1_id),
                                    result=Result.STRONG_MATCH))

            # lookup by wildcard name, ADMIN1, country
            query_list.append(Query(where="name LIKE ? AND country = ? AND admin1_id = ?",
                                    args=(pattern, place.country_iso, place.admin1_id),
                                    result=Result.WILDCARD_MATCH))
        else:
            # lookup by wildcard  name, country
            query_list.append(Query(where="name LIKE ? AND country = ?",
                                    args=(pattern, place.country_iso),
                                    result=Result.WILDCARD_MATCH))

        # Lookup by name, country
        query_list.append(Query(where="name = ? AND country = ?",
                                args=(lookup_target, place.country_iso),
                                result=Result.PARTIAL_MATCH))

        if len(place.admin1_name) > 0:
            # lookup by Soundex name, country and admin1
            query_list.append(Query(where="sdx = ? AND admin1_id = ? AND country = ?",
                                    args=(sdx, place.admin1_id, place.country_iso),
                                    result=Result.SOUNDEX_MATCH))
        else:
            # lookup by Soundex name, country
            query_list.append(Query(where="sdx = ? AND country = ?",
                                    args=(sdx, place.country_iso),
                                    result=Result.SOUNDEX_MATCH))

        # Try each query in list
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata',
                                                                          query_list=query_list)

    def select_admin2(self, place: Loc):
        """Search for Admin2 entry"""
        lookup_target = place.admin2_name
        if len(lookup_target) == 0:
            return
        place.target = lookup_target
        # sdx = get_soundex(lookup_target)

        # Try Admin query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND admin1_id = ? AND f_code=?",
                  args=(lookup_target, place.country_iso, place.admin1_id, 'ADM2'),
                  result=Result.STRONG_MATCH),
            Query(where="name = ? AND country = ? AND f_code=?",
                  args=(lookup_target, place.country_iso, 'ADM2'),
                  result=Result.PARTIAL_MATCH),
            Query(where="name LIKE ? AND country = ? AND f_code=?",
                  args=(self.create_wildcard(lookup_target), place.country_iso, 'ADM2'),
                  result=Result.PARTIAL_MATCH),
            Query(where="name = ?  AND f_code=?",
                  args=(lookup_target, 'ADM2'),
                  result=Result.PARTIAL_MATCH),
            Query(where="name LIKE ? AND country = ? AND f_code=?",
                  args=(self.create_county_wildcard(lookup_target), place.country_iso, 'ADM2'),
                  result=Result.WILDCARD_MATCH)
        ]

        # self.logger.debug(f'Admin2 lookup=[{lookup_target}] country=[{place.country_iso}]')
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)
        if place.result_type == GeoKeys.Result.WILDCARD_MATCH:
            # Found as Admin2 without shire
            place.original_entry = re.sub('shire', '', place.original_entry)

        if len(place.georow_list) == 0:
            # Try city rather than County match.
            save_admin2 = place.admin2_name
            place.city1 = place.admin2_name
            place.admin2_name = ''
            # self.logger.debug(f'Try admin2 as city: [{place.target}]')

            self.select_city(place)

            if len(place.georow_list) == 0:
                #  not found.  restore admin
                place.admin2_name = save_admin2
                place.city1 = ''
            else:
                # Found match as a City
                place.place_type = Loc.PlaceType.CITY
                match_adm1 = self.get_admin1_name_direct(lookup_target=place.georow_list[0][Entry.ADM1], iso=place.country_iso)
                # self.logger.debug(f'pl_iso [{place.country_iso}] pl_adm1 {place.admin1_name} match_adm1=[{match_adm1}] ')
                if place.admin1_name != match_adm1:
                    place.prefix = place.admin1_name.title()
                    place.admin1_name = ''
                return

    def select_admin1(self, place: Loc):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name

        pattern = self.create_wildcard(lookup_target)
        if len(lookup_target) == 0:
            return
        sdx = get_soundex(lookup_target)

        # self.logger.debug(f'sel adm1 patt={pattern} iso={place.country_iso}')

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND f_code = ? ",
                  args=(lookup_target, place.country_iso, 'ADM1'),
                  result=Result.STRONG_MATCH),
            Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                  args=(pattern, place.country_iso, 'ADM1'),
                  result=Result.WILDCARD_MATCH),
            Query(where="sdx = ? AND country = ? AND f_code=?",
                  args=(sdx, place.country_iso, 'ADM1'),
                  result=Result.SOUNDEX_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

    def select_country(self, place: Loc):
        """Search for Admin1 entry"""
        lookup_target = place.country_iso
        if len(lookup_target) == 0:
            return
        sdx = get_soundex(lookup_target)

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="country = ? AND f_code = ? ",
                  args=(place.country_iso, 'ADM0'),
                  result=Result.STRONG_MATCH),
            Query(where="sdx = ?  AND f_code=?",
                  args=(sdx, 'ADM0'),
                  result=Result.SOUNDEX_MATCH)
        ]

        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)
        # self.build_result_list(place.georow_list, place.event_year)

    def get_admin1_id(self, place: Loc):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND country = ? AND f_code = ? ",
                  args=(lookup_target, place.country_iso, 'ADM1'),
                  result=Result.STRONG_MATCH),
            Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                  args=(self.create_wildcard(lookup_target), place.country_iso, 'ADM1'),
                  result=Result.WILDCARD_MATCH),
            Query(where="name = ?  AND f_code = ?",
                  args=(lookup_target, 'ADM1'),
                  result=Result.SOUNDEX_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            place.admin1_id = row_list[0][Entry.ADM1]
            # Fill in Country ISO
            if place.country_iso == '':
                place.country_iso = row_list[0][Entry.ISO]

    def get_admin2_id(self, place: Loc):
        """Search for Admin1 entry"""
        lookup_target = place.admin2_name
        if len(lookup_target) == 0:
            return

        # Try each query until we find a match - each query gets less exact
        query_list = []
        if len(place.admin1_id) > 0:
            query_list.append(Query(where="name = ? AND country = ? AND admin1_id=? AND f_code=?",
                                    args=(lookup_target, place.country_iso, place.admin1_id, 'ADM2'),
                                    result=Result.STRONG_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? and admin1_id = ? AND f_code=?",
                                    args=(self.create_wildcard(lookup_target), place.country_iso, place.admin1_id, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? and admin1_id = ? AND f_code=?",
                                    args=(self.create_county_wildcard(lookup_target), place.country_iso, place.admin1_id, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))
        else:
            query_list.append(Query(where="name = ? AND country = ? AND f_code=?",
                                    args=(lookup_target, place.country_iso, 'ADM2'),
                                    result=Result.STRONG_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? AND f_code=?",
                                    args=(self.create_wildcard(lookup_target), place.country_iso, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? AND f_code=?",
                                    args=(self.create_county_wildcard(lookup_target), place.country_iso, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            place.admin2_id = row[Entry.ADM2]

    def get_admin1_alt_name(self, place: Loc) -> (str, str):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_id
        if len(lookup_target) == 0:
            return '', ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin1_id = ? AND country = ?  AND f_code = ? ",
                  args=(lookup_target, place.country_iso, 'ADM1'),
                  result=Result.STRONG_MATCH)
        ]
        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            admin1_name, lang = self.get_alt_name(row[Entry.ID])
            return admin1_name, lang
        else:
            return '', ''

    def get_admin1_name(self, place: Loc) -> str:
        """Search for Admin1 entry"""
        lookup_target = place.admin1_id
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin1_id = ? AND country = ?  AND f_code = ? ",
                  args=(lookup_target, place.country_iso, 'ADM1'),
                  result=Result.STRONG_MATCH)
        ]
        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            place.admin1_name = row[Entry.NAME]
            return place.admin1_name
        else:
            return ''

    def get_admin1_name_direct(self, lookup_target, iso) -> str:
        """Search for Admin1 entry"""
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin1_id = ? AND country = ?  AND f_code = ? ",
                  args=(lookup_target, iso, 'ADM1'),
                  result=Result.STRONG_MATCH)
        ]
        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            return row[Entry.NAME]
        else:
            return ''

    def get_admin2_name_direct(self, admin1_id, admin2_id, iso) -> str:
        """Search for Admin2 entry"""
        lookup_target = admin2_id
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin2_id = ? AND country = ? AND admin1_id = ?",
                  args=(lookup_target, iso, admin1_id),
                  result=Result.STRONG_MATCH),
            Query(where="admin2_id = ? AND country = ?",
                  args=(lookup_target, iso),
                  result=Result.PARTIAL_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            return row[Entry.NAME]
        else:
            return ''

    def get_admin2_name(self, place: Loc) -> str:
        """Search for Admin1 entry"""
        lookup_target = place.admin2_id
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="admin2_id = ? AND country = ? AND admin1_id = ?",
                  args=(lookup_target, place.country_iso, place.admin1_id),
                  result=Result.STRONG_MATCH),
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

    def lookup_geoid(self, place: Loc) -> None:
        """Search for GEOID"""
        result_place: Loc = Loc.Loc()

        query_list = [
            Query(where="geoid = ? ",
                  args=(place.target,),
                  result=Result.STRONG_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)
        if len(place.georow_list) == 0:
            place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)
        else:
            place.georow_list = place.georow_list[:1]
            place.result_type = GeoKeys.Result.STRONG_MATCH

        # Add search quality score to each entry
        for idx, rw in enumerate(place.georow_list):
            self.copy_georow_to_place(row=rw, place=result_place)
            update = list(rw)
            update.append(1)  # Extend list row and assign score
            result_place.prefix = ''
            res_nm = result_place.format_full_nm(None)
            score = 0.0

            # Remove items in prefix that are in result
            tk_list = res_nm.split(",")
            for item in tk_list:
                place.prefix = re.sub(item.strip(' ').lower(), '', place.prefix)

            update[GeoKeys.Entry.SCORE] = int(score * 100)
            place.georow_list[idx] = tuple(update)

    def lookup_main_dbid(self, place: Loc) -> None:
        """Search for DB ID"""
        query_list = [
            Query(where="id = ? ",
                  args=(place.target,),
                  result=Result.STRONG_MATCH)
        ]
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)

    def lookup_admin_dbid(self, place: Loc) -> None:
        """Search for DB ID"""
        query_list = [
            Query(where="id = ? ",
                  args=(place.target,),
                  result=Result.STRONG_MATCH)
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
                  result=Result.STRONG_MATCH)]

        row_list, res = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            res = row_list[0][Entry.NAME]
            if iso == 'us':
                res = 'United States'
        else:
            res = ''
        return res

    def get_country_iso(self, place: Loc) -> str:
        """ Return ISO code for specified country"""
        lookup_target, modified = GeoKeys.country_normalize(place.country_name)
        if len(lookup_target) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="name = ? AND f_code = ? ",
                  args=(lookup_target, 'ADM0'),
                  result=Result.STRONG_MATCH),
            # Query(where="name LIKE ?  AND f_code = ? ",
            #      args=(self.create_wildcard(lookup_target), 'ADM0'),
            #      result=Result.PARTIAL_MATCH)  #,
            # Query(where="sdx = ?  AND f_code = ? ",
            #      args=(GeoKeys.get_soundex (lookup_target), 'ADM0'),
            #      result=Result.PARTIAL_MATCH)
        ]

        row_list, result_code = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            res = row_list[0][Entry.ISO]
            if len(row_list) == 1:
                place.country_name = row_list[0][Entry.NAME]
        else:
            res = ''

        return res


    def advanced_search(self, place: Loc):
        """
        Advanced search - support parameters for ISO and Feature class
        """
        lookup_target = place.target
        if len(lookup_target) == 0:
            return
        pattern = self.create_wildcard(lookup_target)
        feature_pattern = self.create_wildcard(place.feature)
        self.logger.debug(f'Advanced Search. Targ=[{pattern}] feature=[{feature_pattern}]'
                          f'  iso=[{place.country_iso}] ')

        if len(place.feature) > 0:
            query_list = [
                Query(where="name LIKE ? AND country LIKE ? AND f_code LIKE ?",
                      args=(pattern, place.country_iso, feature_pattern),
                      result=Result.PARTIAL_MATCH)]
        else:
            query_list = [
                Query(where="name LIKE ? AND country LIKE ?",
                      args=(pattern, place.country_iso),
                      result=Result.PARTIAL_MATCH)]

        # Search main DB
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)

        # self.logger.debug(f'main Result {place.georow_list}')

        # Search admin DB
        admin_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)
        place.georow_list.extend(admin_list)
        # self.logger.debug(f'admin Result {place.georow_list}')

    def copy_georow_to_place(self, row, place: Loc):
        # Copy data from DB row into Place
        # self.logger.debug(row)
        place.admin1_id = ''
        place.admin2_id = ''
        place.city1 = ''

        place.country_iso = str(row[Entry.ISO])
        place.country_name = str(self.get_country_name(row[Entry.ISO]))
        place.lat = row[Entry.LAT]
        place.lon = row[Entry.LON]
        place.feature = str(row[Entry.FEAT])
        place.geoid = str(row[Entry.ID])

        if place.feature == 'ADM0':
            self.place_type = Loc.PlaceType.COUNTRY
            pass
        elif place.feature == 'ADM1':
            place.admin1_id = row[Entry.ADM1]
            self.place_type = Loc.PlaceType.ADMIN1
        elif place.feature == 'ADM2':
            place.admin1_id = row[Entry.ADM1]
            place.admin2_id = row[Entry.ADM2]
            self.place_type = Loc.PlaceType.ADMIN2
        else:
            place.admin1_id = row[Entry.ADM1]
            place.admin2_id = row[Entry.ADM2]
            place.city1 = row[Entry.NAME]
            self.place_type = Loc.PlaceType.CITY

        place.admin1_name = str(self.get_admin1_name(place))
        place.admin2_name = str(self.get_admin2_name(place))
        if place.admin2_name is None:
            place.admin2_name = ''
        if place.admin1_name is None:
            place.admin1_name = ''

        place.city1 = str(place.city1)
        if place.city1 is None:
            place.city1 = ''

    def clear_geoname_data(self):
        # Delete all the geoname data
        for tbl in ['geodata', 'admin']:
            # noinspection SqlWithoutWhere
            self.db.delete_table(tbl)

    # Streams_nocase_idx ON Streams(Name 

    def create_geoid_index(self):
        # Create indices
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS geoid_idx ON geodata(geoid )')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS admgeoid_idx ON admin(geoid  )')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS altnamegeoid_idx ON altname(geoid  )')

    def create_indices(self):
        # Create indices
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS name_idx ON geodata(name, country )')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS admin1_idx ON geodata(admin1_id )')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS sdx_idx ON geodata(sdx )')

        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_name_idx ON admin(name, country )')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_admin1_idx ON admin(admin1_id, f_code)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_admin2_idx ON admin(admin1_id, admin2_id)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_country_idx ON admin(country, f_code)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_sdx_idx ON admin(sdx )')

    @staticmethod
    def make_georow(name: str, iso: str, adm1: str, adm2: str, lat: float, lon: float, feat: str, geoid: str, sdx: str) -> ():
        # Return a dummy geo-row
        res = (name, iso, adm1, adm2, lat, lon, feat, geoid, sdx)
        return res

    def get_row_count(self) -> int:
        return self.db.get_row_count()

    @staticmethod
    def create_wildcard(pattern):
        # Create SQL wildcard pattern (convert * to %).  Add % on end
        if '*' in pattern:
            return re.sub(r"\*", "%", pattern)
        else:
            return f'%{pattern}%'

    @staticmethod
    def create_quick_wildcard(pattern):
        # Create SQL wildcard pattern (convert * to %).  Add % on end
        if '*' in pattern:
            return re.sub(r"\*", "%", pattern)
        else:
            return f'{pattern}%'

    @staticmethod
    def create_county_wildcard(pattern):
        # Try pattern with 'shire' removed
        pattern = re.sub(r"shire", "", pattern)
        # Create SQL wildcard pattern (convert * to %).  Add % on end
        if '*' in pattern:
            return re.sub(r"\*", "%", pattern)
        else:
            return f'{pattern}'

    def close(self):
        self.db.set_analyze_pragma()
        self.logger.info('Closing Database')
        self.db.conn.close()

    def set_display_names(self, temp_place):
        place_lang = Country.Country.get_lang(temp_place.country_iso)
        res, lang = self.get_alt_name(temp_place.geoid)
        if res != '' and (lang == place_lang or lang == 'ut8'):
            temp_place.city1 = res

        res, lang = self.get_admin1_alt_name(temp_place)
        if res != '' and (lang == place_lang or lang == 'ut8'):
            temp_place.admin1_name = res

    def get_alt_name(self, geoid) -> (str, str):
        # retrieve alternate name
        query_list = [
            Query(where="geoid = ?",
                  args=(geoid,),
                  result=Result.STRONG_MATCH)]
        select = 'name, lang'
        row_list, res = self.db.process_query(select_string=select, from_tbl='main.altname', query_list=query_list)
        if len(row_list) > 0:
            return row_list[0][0], row_list[0][1]
        else:
            return '', ''

    def insert(self, geo_row: (), feat_code: str):
        # We split the data into 2  tables, 1) Admin: ADM0/ADM1/ADM2,  and 2) city data
        if feat_code == 'ADM1' or feat_code == 'ADM0' or feat_code == 'ADM2':
            sql = ''' INSERT OR IGNORE INTO admin(name,country, admin1_id,admin2_id,lat,lon,f_code, geoid, sdx)
                      VALUES(?,?,?,?,?,?,?,?,?) '''
            row_id = self.db.execute(sql, geo_row)
            # Add name to dictionary.  Used by AlternateNames for fast lookup during DB build
            self.geoid_admin_dict[geo_row[Entry.ID]] = row_id
        else:
            sql = ''' INSERT OR IGNORE INTO geodata(name, country, admin1_id, admin2_id, lat, lon, f_code, geoid, sdx)
                      VALUES(?,?,?,?,?,?,?,?,?) '''
            row_id = self.db.execute(sql, geo_row)
            # Add name to dictionary.  Used by AlternateNames for fast lookup during DB build
            self.geoid_main_dict[geo_row[Entry.ID]] = row_id

        return row_id

    def insert_alternate_name(self, alternate_name: str, geoid: str, lang: str):
        # We split the data into 2  tables, 1) Admin: ADM0/ADM1/ADM2,  and 2) city data
        row = (alternate_name, lang, geoid)
        sql = ''' INSERT OR IGNORE INTO altname(name,lang, geoid)
                  VALUES(?,?,?) '''
        row_id = self.db.execute(sql, row)

    def insert_version(self, db_version: int):
        self.db.begin()

        sql = ''' INSERT OR IGNORE INTO version(version)
                  VALUES(?) '''
        args = (db_version,)
        row_id = self.db.execute(sql, args)
        self.db.commit()

    def get_db_version(self) -> int:
        # If version table does not exist, this is V1
        if self.db.table_exists('version'):
            # query version ID
            query_list = [
                Query(where="version like ?",
                      args=('%',),
                      result=Result.STRONG_MATCH)]
            select_str = '*'
            row_list, res = self.db.process_query(select_string=select_str, from_tbl='main.version', query_list=query_list)
            if len(row_list) > 0:
                ver = int(row_list[0][1])
                self.logger.debug(f'Database Version = {ver}')
                return ver

        # No version table, so this is V1
        self.logger.debug('No version table.  Version is 1')
        return 1

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
                geoid      text,
                sdx     text
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
                geoid      text,
                sdx     text
                                    );"""

        # name, country, admin1_id, admin2_id, lat, lon, f_code, geoid
        sql_alt_name_table = """CREATE TABLE IF NOT EXISTS altname    (
                id           integer primary key autoincrement not null,
                name     text,
                lang     text,
                geoid      text
                                    );"""

        # name, country, admin1_id, admin2_id, lat, lon, f_code, geoid
        sql_version_table = """CREATE TABLE IF NOT EXISTS version    (
                id           integer primary key autoincrement not null,
                version     integer
                                    );"""

        for tbl in [sql_geodata_table, sql_admin_table, sql_version_table, sql_alt_name_table]:
            self.db.create_table(tbl)
