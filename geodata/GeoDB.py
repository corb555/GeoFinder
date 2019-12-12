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

from geodata import GeoUtil, Loc, Country, MatchScore, Normalize
from geodata.GeoUtil import Query, Result, Entry, get_soundex
from util import SpellCheck
from sqlhelper import DB


class GeoDB:
    """
    geoname data database.  Add items to DB, look up items, create tables, indices
    """

    def __init__(self, db_path, version, spellcheck: [SpellCheck.SpellCheck, None],
                 show_message, exit_on_error):
        """
        geoname data database init - open database if present otherwise create with specified version number
        :param db_path: full path to database file
        :param version:
        :param spellcheck:
        """
        self.logger = logging.getLogger(__name__)
        self.start = 0
        self.match = MatchScore.MatchScore()
        self.select_str = 'name, country, admin1_id, admin2_id, lat, lon, f_code, geoid, sdx'
        self.spellcheck = spellcheck
        self.use_wildcards = True
        self.total_time = 0
        self.total_lookups = 0

        self.db_path = db_path
        # See if DB exists
        if os.path.exists(db_path):
            db_exists = True
        else:
            db_exists = False

        self.db = DB.DB(db_filename=db_path, show_message=True, exit_on_error=True)
        if self.db.err:
            self.logger.error(f"Error! cannot open database {db_path}.")
            raise ValueError('Cannot open database')

        # If DB exists
        if db_exists:
            # Run sanity test on DB
            res = self.db.test_database('main.geodata', where='name = ? AND country = ?', args=('ba', 'fr'))

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
        self.db_limit = 105
        self.db.order_string = ''
        self.db.limit_string = f'LIMIT {self.db_limit}'
        self.geoid_main_dict = {}  # Key is GEOID, Value is DB ID for entry
        self.geoid_admin_dict = {}  # Key is GEOID, Value is DB ID for entry
        self.place_type = ''

    def lookup_place(self, place: Loc) -> []:
        """
        Lookup a place in our geoname.org dictionary and update place with Geo_result with lat, long, District, etc
        The dictionary geo_result entry contains: Lat, Long, districtID (County or State or Province ID)
        There can be multiple entries if a city name isnt unique in a country
        """
        self.start = time.time()
        place.result_type = Result.STRONG_MATCH
        # place.admin2_name, modified = GeoKeys.admin2_normalize(place.admin2_name, place.country_iso)

        if place.country_iso != '' and place.country_name == '':
            place.country_name = self.get_country_name(place.country_iso)

        target_feature = place.place_type

        # Lookup Place based on Place Type
        if place.place_type == Loc.PlaceType.ADMIN1:
            lookup_type = 'ADMIN1'
            self.wide_search_admin1(place)
        elif place.place_type == Loc.PlaceType.ADMIN2:
            lookup_type = 'ADMIN1'
            if place.admin1_id == '':
                self.wide_search_admin1_id(place=place)
            self.wide_search_admin2(place)
        elif place.place_type == Loc.PlaceType.COUNTRY:
            lookup_type = 'COUNTRY'
            self.wide_search_country(place)
        elif place.place_type == Loc.PlaceType.ADVANCED_SEARCH:
            self.advanced_search(place)
            lookup_type = 'ADVANCED'
        else:
            # Lookup as City
            lookup_type = 'CITY'
            if place.admin2_id == '':
                self.wide_search_admin2_id(place=place)
            self.wide_search_city(place)

        if place.georow_list:
            self.assign_scores(place, target_feature)
            self.logger.debug(f'LOOKUP: {len(place.georow_list)} matches for {lookup_type}  targ={place.target} nm=[{place.get_five_part_title()}]\n')
        else:
            self.logger.debug(f'LOOKUP. No match:for {lookup_type}  targ={place.target} nm=[{place.get_five_part_title()}]\n')
            place.georow_list = []

    def wide_search_city(self, place: Loc):
        """
        Search for  entry - try the most exact match first, then less exact matches
        """
        lookup_target = place.target
        if len(lookup_target) == 0:
            return

        if self.spellcheck:
            pattern = self.spellcheck.fix_spelling(lookup_target)
        else:
            pattern = lookup_target
        pattern = self.create_wildcard(pattern)

        sdx = get_soundex(lookup_target)
        # self.logger.debug(f'CITY lkp targ=[{lookup_target}] adm1 id=[{place.admin1_id}]'
        #                  f' adm2 id=[{place.admin2_id}] iso=[{place.country_iso}] patt =[{pattern}] sdx={sdx} pref={place.prefix}')

        query_list = []

        if len(place.country_iso) == 0:
            # NO COUNTRY - try lookup by name.
            if lookup_target in pattern:
                query_list.append(Query(where="name = ?",
                                        args=(lookup_target,),
                                        result=Result.PARTIAL_MATCH))
            # lookup by wildcard name
            if '%' in pattern:
                query_list.clear()
                query_list.append(Query(where="name LIKE ?",
                                        args=(pattern,),
                                        result=Result.WILDCARD_MATCH))
            else:
                query_list.append(Query(where="name LIKE ?",
                                        args=(pattern,),
                                        result=Result.WORD_MATCH))

            # lookup by soundex
            query_list.append(Query(where="sdx = ?",
                                    args=(sdx,),
                                    result=Result.SOUNDEX_MATCH))

            place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str,
                                                                           from_tbl='main.geodata',
                                                                           query_list=query_list)
            # self.logger.debug(place.georow_list)
            return

        # Build query list
        # Start with the most exact match depending on the data provided.
        if len(place.admin1_name) > 0:
            # lookup by name, ADMIN1, country
            if lookup_target in pattern:
                query_list.append(Query(
                    where="name = ? AND country = ? AND admin1_id = ?",
                    args=(lookup_target, place.country_iso, place.admin1_id),
                    result=Result.STRONG_MATCH))

            # lookup by wildcard name, ADMIN1, country
            if '%' in pattern:
                query_list.clear()

                query_list.append(Query(
                    where="name LIKE ? AND country = ? AND admin1_id = ?",
                    args=(pattern, place.country_iso, place.admin1_id),
                    result=Result.WILDCARD_MATCH))
            else:
                query_list.append(Query(
                    where="name LIKE ? AND country = ? AND admin1_id = ?",
                    args=(pattern, place.country_iso, place.admin1_id),
                    result=Result.WORD_MATCH))
        else:
            # lookup by wildcard  name, country
            if '%' in pattern:
                query_list.clear()

                query_list.append(Query(where="name LIKE ? AND country = ?",
                                        args=(pattern, place.country_iso),
                                        result=Result.WILDCARD_MATCH))
            else:
                query_list.append(Query(where="name LIKE ? AND country = ?",
                                        args=(pattern, place.country_iso),
                                        result=Result.WORD_MATCH))

        # Lookup by name, country
        query_list.append(Query(where="name = ? AND country = ?",
                                args=(lookup_target, place.country_iso),
                                result=Result.PARTIAL_MATCH))

        # lookup by Soundex name, country
        query_list.append(Query(where="sdx = ? AND country = ?",
                                args=(sdx, place.country_iso),
                                result=Result.SOUNDEX_MATCH))

        # Try each query in list
        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.geodata',
                                                                       query_list=query_list)

    def wide_search_admin2(self, place: Loc):
        """

        :param place:
        :return:
        """
        query_list = []
        """Search for Admin2 entry"""
        lookup_target = place.admin2_name
        if len(lookup_target) == 0:
            return
        place.target = lookup_target
        if self.spellcheck:
            pattern = self.spellcheck.fix_spelling(lookup_target)
        else:
            pattern = lookup_target
        pattern = self.create_wildcard(pattern)

        # Try Admin queries and find best match
        query_list.append(Query(where="name = ? AND country = ? AND admin1_id = ? AND f_code=?",
                                args=(lookup_target, place.country_iso, place.admin1_id, 'ADM2'),
                                result=Result.STRONG_MATCH))
        query_list.append(Query(where="name = ? AND country = ? AND f_code=?",
                                args=(lookup_target, place.country_iso, 'ADM2'),
                                result=Result.PARTIAL_MATCH))
        query_list.append(Query(where="name LIKE ? AND country = ? AND f_code=?",
                                args=(lookup_target, place.country_iso, 'ADM2'),
                                result=Result.PARTIAL_MATCH))
        query_list.append(Query(where="name = ?  AND f_code=?",
                                args=(lookup_target, 'ADM2'),
                                result=Result.PARTIAL_MATCH))
        if '%' in pattern:
            query_list.clear()

            query_list.append(Query(where="name LIKE ? AND country = ? AND f_code=?",
                                    args=(pattern, place.country_iso, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))
        else:
            query_list.append(Query(
                where="name LIKE ? AND country = ? AND admin1_id = ?",
                args=(pattern, place.country_iso, place.admin1_id),
                result=Result.WORD_MATCH))

        # self.logger.debug(f'Admin2 lookup=[{lookup_target}] country=[{place.country_iso}]')
        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

        if len(place.georow_list) == 0:
            # Try city rather than County match.
            save_admin2 = place.admin2_name
            place.city1 = place.admin2_name
            place.admin2_name = ''
            # self.logger.debug(f'Try admin2 as city: [{place.target}]')

            self.wide_search_city(place)

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

    def wide_search_admin1(self, place: Loc):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name

        if self.spellcheck:
            pattern = self.spellcheck.fix_spelling(lookup_target)
        else:
            pattern = lookup_target
        pattern = self.create_wildcard(pattern)

        if len(lookup_target) == 0:
            return
        sdx = get_soundex(lookup_target)

        # self.logger.debug(f'sel adm1 patt={pattern} iso={place.country_iso}')

        # Try each query until we find a match - each query gets less exact
        query_list = []
        query_list.append(Query(where="name = ? AND country = ? AND f_code = ? ",
                                args=(lookup_target, place.country_iso, 'ADM1'),
                                result=Result.STRONG_MATCH))
        if '%' in pattern:
            query_list.clear()

            query_list.append(Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                                    args=(pattern, place.country_iso, 'ADM1'),
                                    result=Result.WILDCARD_MATCH))
        else:
            query_list.append(Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                                    args=(pattern, place.country_iso, 'ADM1'),
                                    result=Result.WORD_MATCH))

        query_list.append(Query(where="sdx = ? AND country = ? AND f_code=?",
                                args=(sdx, place.country_iso, 'ADM1'),
                                result=Result.SOUNDEX_MATCH))

        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

    def wide_search_country(self, place: Loc):
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

        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)
        # self.build_result_list(place.georow_list, place.event_year)

    def wide_search_admin1_id(self, place: Loc):
        """Search for Admin1 entry"""
        lookup_target = place.admin1_name
        pattern = self.create_wildcard(lookup_target)
        if len(lookup_target) == 0:
            return

        query_list = []

        # Try each query then calculate best match - each query gets less exact
        if place.country_iso == '':
            query_list.append(Query(where="name = ?  AND f_code = ? ",
                                    args=(lookup_target, 'ADM1'),
                                    result=Result.STRONG_MATCH))

            if '%' in pattern:
                query_list.clear()

                query_list.append(Query(where="name LIKE ? AND f_code = ?",
                                        args=(pattern, 'ADM1'),
                                        result=Result.WILDCARD_MATCH))
            else:
                query_list.append(Query(where="name LIKE ? AND f_code = ?",
                                        args=(lookup_target, 'ADM1'),
                                        result=Result.WORD_MATCH))
        else:
            query_list.append(Query(where="name = ? AND country = ? AND f_code = ? ",
                                    args=(lookup_target, place.country_iso, 'ADM1'),
                                    result=Result.STRONG_MATCH))

            if '%' in pattern:
                query_list.clear()
                query_list.append(Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                                        args=(pattern, place.country_iso, 'ADM1'),
                                        result=Result.WILDCARD_MATCH))
            else:
                query_list.append(Query(where="name LIKE ? AND country = ?  AND f_code = ?",
                                        args=(lookup_target, place.country_iso, 'ADM1'),
                                        result=Result.WORD_MATCH))

        query_list.append(Query(where="name = ?  AND f_code = ?",
                                args=(lookup_target, 'ADM1'),
                                result=Result.SOUNDEX_MATCH))

        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

        self.assign_scores(place, 'ADM1')

        if place.result_type == Result.STRONG_MATCH:
            place.admin1_id = place.georow_list[0][Entry.ADM1]
            # Fill in Country ISO
            if place.country_iso == '':
                place.country_iso = place.georow_list[0][Entry.ISO]

    def wide_search_admin2_id(self, place: Loc):
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
                                    args=(lookup_target, place.country_iso, place.admin1_id, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? and admin1_id = ? AND f_code=?",
                                    args=(self.create_county_wildcard(lookup_target), place.country_iso, place.admin1_id, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))
        else:
            query_list.append(Query(where="name = ? AND country = ? AND f_code=?",
                                    args=(lookup_target, place.country_iso, 'ADM2'),
                                    result=Result.STRONG_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? AND f_code=?",
                                    args=(lookup_target, place.country_iso, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))
            query_list.append(Query(where="name LIKE ? AND country = ? AND f_code=?",
                                    args=(self.create_county_wildcard(lookup_target), place.country_iso, 'ADM2'),
                                    result=Result.WILDCARD_MATCH))

        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

        self.assign_scores(place, 'ADM2')

        if place.result_type == Result.STRONG_MATCH:
            row = place.georow_list[0]
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
        row_list, res = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

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
        row_list, res = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

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
        row_list, res = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

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

        row_list, res = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

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

        row_list, res = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            row = row_list[0]
            place.admin2_name = row[Entry.NAME]
            # self.logger.debug(f'adm2 nm = {place.admin2_name}')
            return place.admin2_name
        else:
            return ''

    def get_geoid(self, place: Loc) -> None:
        """Search for GEOID"""
        result_place: Loc = Loc.Loc()

        query_list = [
            Query(where="geoid = ? ",
                  args=(place.target,),
                  result=Result.STRONG_MATCH)
        ]
        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str,
                                                                       from_tbl='main.geodata', query_list=query_list)
        if len(place.georow_list) == 0:
            place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str,
                                                                           from_tbl='main.admin', query_list=query_list)
        else:
            place.georow_list = place.georow_list[:1]
            place.result_type = GeoUtil.Result.STRONG_MATCH

        # Add search quality score to each entry
        for idx, rw in enumerate(place.georow_list):
            self.copy_georow_to_place(row=rw, place=result_place)
            update = list(rw)
            update.append(1)  # Extend list row and assign score
            result_place.prefix = ''
            res_nm = result_place.get_long_name(None)
            score = 0.0

            # Remove any words from Prefix that are in result
            for item in res_nm.split(","):
                for word in item.split(' '):
                    if word in place.prefix and '*' not in word:
                        place.prefix = re.sub(word, '', place.prefix, 1)

            update[GeoUtil.Entry.SCORE] = int(score * 100)
            place.georow_list[idx] = tuple(update)

    def lookup_main_dbid(self, place: Loc) -> None:
        """Search for DB ID"""
        query_list = [
            Query(where="id = ? ",
                  args=(place.target,),
                  result=Result.STRONG_MATCH)
        ]
        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str,
                                                                       from_tbl='main.geodata', query_list=query_list)

    def lookup_admin_dbid(self, place: Loc) -> None:
        """Search for DB ID"""
        query_list = [
            Query(where="id = ? ",
                  args=(place.target,),
                  result=Result.STRONG_MATCH)
        ]
        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

    def get_country_name(self, iso: str) -> str:
        """ return country name for specified ISO code """
        if len(iso) == 0:
            return ''

        # Try each query until we find a match - each query gets less exact
        query_list = [
            Query(where="country = ? AND f_code = ? ",
                  args=(iso, 'ADM0'),
                  result=Result.STRONG_MATCH)]

        row_list, res = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

        if len(row_list) > 0:
            res = row_list[0][Entry.NAME]
            if iso == 'us':
                res = 'United States'
        else:
            res = ''
        return res

    def get_country_iso(self, place: Loc) -> str:
        """ Return ISO code for specified country"""
        lookup_target, modified = Normalize.country_normalize(place.country_name)
        if len(lookup_target) == 0:
            return ''
        query_list = []

        # Add queries - each query gets less exact
        query_list.append(Query(where="name = ? AND f_code = ? ",
                                args=(lookup_target, 'ADM0'),
                                result=Result.STRONG_MATCH))

        if self.spellcheck:
            pattern = self.spellcheck.fix_spelling(lookup_target)
            query_list.append(Query(where="name LIKE ?  AND f_code = ? ",
                                    args=(pattern, 'ADM0'),
                                    result=Result.WILDCARD_MATCH))

        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)

        self.assign_scores(place, 'ADM0')

        if place.result_type == Result.STRONG_MATCH:
            res = place.georow_list[0][Entry.ISO]
            # if len(row_list) == 1:
            place.country_name = place.georow_list[0][Entry.NAME]
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
        place.georow_list, place.result_type = self.process_query_list(select_string=self.select_str,
                                                                       from_tbl='main.geodata',
                                                                       query_list=query_list)

        # self.logger.debug(f'main Result {place.georow_list}')

        # Search admin DB
        admin_list, place.result_type = self.process_query_list(select_string=self.select_str, from_tbl='main.admin', query_list=query_list)
        place.georow_list.extend(admin_list)
        # self.logger.debug(f'admin Result {place.georow_list}')

    def copy_georow_to_place(self, row, place: Loc):
        """

        :param row:
        :param place:
        """
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
        place.prefix = row[Entry.PREFIX]

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
        """

        """
        # Delete all the geoname data
        for tbl in ['geodata', 'admin']:
            # noinspection SqlWithoutWhere
            self.db.delete_table(tbl)

    # Streams_nocase_idx ON Streams(Name

    def create_geoid_index(self):
        """

        """
        # Create indices
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS geoid_idx ON geodata(geoid)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS admgeoid_idx ON admin(geoid)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS altnamegeoid_idx ON altname(geoid)')

    def create_indices(self):
        """

        """
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
        """

        :param name:
        :param iso:
        :param adm1:
        :param adm2:
        :param lat:
        :param lon:
        :param feat:
        :param geoid:
        :param sdx:
        :return:
        """
        # Return a dummy geo-row
        res = (name, iso, adm1, adm2, lat, lon, feat, geoid, sdx)
        return res

    def get_row_count(self) -> int:
        """

        :return:
        """
        return self.db.get_row_count()

    @staticmethod
    def create_wildcard(pattern):
        """

        :param pattern:
        :return:
        """
        # Create SQL wildcard pattern (convert * to %).  Add % on end
        if '*' in pattern:
            return re.sub(r"\*", "%", pattern)
        else:
            return f'%{pattern}%'

    @staticmethod
    def create_county_wildcard(pattern):
        """

        :param pattern:
        :return:
        """
        # Try pattern with 'shire' removed
        pattern = re.sub(r"shire", "", pattern)
        # Create SQL wildcard pattern (convert * to %).  Add % on end
        if '*' in pattern:
            return re.sub(r"\*", "%", pattern)
        else:
            return f'{pattern}'

    def close(self):
        """

        """
        self.db.set_analyze_pragma()
        self.logger.info('Closing Database')
        self.db.conn.close()

    def set_display_names(self, temp_place):
        """

        :param temp_place:
        """
        place_lang = Country.Country.get_lang(temp_place.country_iso)
        res, lang = self.get_alt_name(temp_place.geoid)
        if res != '' and (lang == place_lang or lang == 'ut8'):
            temp_place.city1 = res

        res, lang = self.get_admin1_alt_name(temp_place)
        if res != '' and (lang == place_lang or lang == 'ut8'):
            temp_place.admin1_name = res

    def get_alt_name(self, geoid) -> (str, str):
        """

        :param geoid:
        :return:
        """
        # retrieve alternate name
        query_list = [
            Query(where="geoid = ?",
                  args=(geoid,),
                  result=Result.STRONG_MATCH)]
        select = 'name, lang'
        row_list, res = self.process_query_list(select_string=select, from_tbl='main.altname', query_list=query_list)
        if len(row_list) > 0:
            return row_list[0][0], row_list[0][1]
        else:
            return '', ''

    def insert(self, geo_row: (), feat_code: str):
        """

        :param geo_row:
        :param feat_code:
        :return:
        """
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

        # Add item to Spell Check dictionary
        if self.spellcheck:
            self.spellcheck.insert(geo_row[Entry.NAME], geo_row[Entry.ISO])

        return row_id

    def insert_alternate_name(self, alternate_name: str, geoid: str, lang: str):
        """

        :param alternate_name:
        :param geoid:
        :param lang:
        """
        # We split the data into 2  tables, 1) Admin: ADM0/ADM1/ADM2,  and 2) city data
        row = (alternate_name, lang, geoid)
        sql = ''' INSERT OR IGNORE INTO altname(name,lang, geoid)
                  VALUES(?,?,?) '''
        self.db.execute(sql, row)

    def insert_version(self, db_version: int):
        """

        :param db_version:
        """
        self.db.begin()

        sql = ''' INSERT OR IGNORE INTO version(version)
                  VALUES(?) '''
        args = (db_version,)
        self.db.execute(sql, args)
        self.db.commit()

    def get_db_version(self) -> int:
        """

        :return:
        """
        # If version table does not exist, this is V1
        if self.db.table_exists('version'):
            # query version ID
            query_list = [
                Query(where="version like ?",
                      args=('%',),
                      result=Result.STRONG_MATCH)]
            select_str = '*'
            row_list, res = self.process_query_list(select_string=select_str, from_tbl='main.version', query_list=query_list)
            if len(row_list) > 0:
                ver = int(row_list[0][1])
                self.logger.debug(f'Database Version = {ver}')
                return ver

        # No version table, so this is V1
        self.logger.debug('No version table.  Version is 1')
        return 1

    def process_query_list(self, select_string, from_tbl: str, query_list: [Query]):
        """

        :param select_string:
        :param from_tbl:
        :param query_list:
        :return:
        """
        # Perform each SQL query in the list
        row_list = []
        result_type = Result.NO_MATCH
        for query in query_list:
            # During shutdown, wildcards are turned off since there is no UI to verify results
            if self.use_wildcards is False and (query.result == Result.WILDCARD_MATCH or query.result == Result.SOUNDEX_MATCH):
                continue
            start = time.time()
            if query.result == Result.WORD_MATCH:
                result_list = self.word_match(select_string, query.where, from_tbl,
                                              query.args)
            else:
                result_list = self.db.select(select_string, query.where, from_tbl,
                                             query.args)
            if row_list:
                row_list.extend(result_list)
            else:
                row_list = result_list

            if len(row_list) > 0:
                result_type = query.result

            elapsed = time.time() - start
            self.total_time += elapsed
            self.total_lookups += 1
            if elapsed > .005:
                self.logger.debug(f'Time={elapsed:.6f} TOT={self.total_time:.1f} '
                                  f'len {len(row_list)} from {from_tbl} '
                                  f'where {query.where} val={query.args} ')
            if len(row_list) > 50:
                break

        return row_list, result_type

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
        results = []  # the entire merged list of result rows
        res_flags = []  # list of flags, matching results list, 'True' to keep
        for word in words:
            # redo tuple for each word; select_string still has LIKE
            n_args = (f'%{word.strip()}%', *args[1:])
            result = self.db.select(select_string, where, from_tbl, n_args)
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

    @staticmethod
    def prefix_cleanup(pref, result):
        """

        :param pref:
        :param result:
        :return:
        """
        new_prfx = pref.lower()

        # Remove result words  from prefix
        for item in re.split(r'\W+', result.lower()):
            if len(item) > 1:
                new_prfx = re.sub(item, '', new_prfx, count=1)

        return new_prfx

    def assign_scores(self, place, target_feature):
        """

        :param place:
        :param target_feature:
        """
        result_place: Loc = Loc.Loc()

        min_score = 9999
        original_prefix = place.prefix + ' ' + place.extra + ' ' + place.target

        # Remove redundant terms in prefix by converting it to dictionary (then back to list)
        # prefix_list = list(dict.fromkeys(original_prefix.split(' ')))
        # original_prefix = ' '.join(list(prefix_list))

        # Add search quality score and prefix to each entry
        for idx, rw in enumerate(place.georow_list):
            self.copy_georow_to_place(row=rw, place=result_place)
            result_place.set_place_type()
            result_place.original_entry = result_place.get_long_name(None)

            if len(place.prefix) > 0 and result_place.prefix == '':
                result_place.prefix = ' '
                result_place.prefix_commas = ','
            else:
                result_place.prefix = ''

            # Remove items in prefix that are in result
            if place.place_type != Loc.PlaceType.ADVANCED_SEARCH:
                nm = place.get_long_name(None)
                place.prefix = self.prefix_cleanup(original_prefix, nm)
                new_prfx = place.prefix

                if len(new_prfx) > 0:
                    new_prfx += ', '
            else:
                place.updated_entry = place.get_long_name(None)

            score = self.match.match_score(target_place=place, result_place=result_place)
            if result_place.feature == target_feature:
                score -= 10

            min_score = min(min_score, score)

            # Convert row tuple to list and extend so we can assign score
            update = list(rw)
            update.append(1)
            update[GeoUtil.Entry.SCORE] = score
            update[GeoUtil.Entry.PREFIX] = place.prefix
            place.georow_list[idx] = tuple(update)  # Convert back from list to tuple

        if min_score < MatchScore.EXCELLENT + 2:
            place.result_type = GeoUtil.Result.STRONG_MATCH

    def create_tables(self):
        """

        """
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
