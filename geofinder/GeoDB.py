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
import copy
import logging
import os
import re
import sys
import time
from tkinter import messagebox

from geofinder import DB, Loc, GeoKeys, Geodata
from geofinder.GeoKeys import Query, Result, Entry, get_soundex


class GeoDB:
    """
    geoname data database.  Add items, look up items, create tables, indices
    """

    def __init__(self, database):
        self.logger = logging.getLogger(__name__)
        self.start = 0

        self.database = database
        # See if DB exists
        if os.path.exists(database):
            db_exists = True
        else:
            db_exists = False

        self.db = DB.DB(database)
        if self.db.err:
            self.logger.error(f"Error! cannot open database {database}.")
            raise ValueError('Cannot open database')

        # If DB exists
        if db_exists:
            # Run sanity test on DB
            res = self.db.db_test('main.geodata')

            if res:
                self.logger.debug(f'DB error for {database}')
                if messagebox.askyesno('Error',
                                       f'Geoname database is empty or corrupt:\n\n {database} \n\nDo you want to delete it and rebuild?'):
                    messagebox.showinfo('', 'Deleting Geoname database')
                    self.db.conn.close()
                    os.remove(database)

                sys.exit()
        else:
            # DB didnt exist.  Create tables.
            self.create_tables()

        self.db.set_speed_pragmas()
        self.db.set_params(select_str='name, country, admin1_id, admin2_id, lat, lon, f_code, geoid, sdx', order_str='', limit_str='LIMIT 160')
        self.geoid_main_dict = {}  # Key is GEOID, Value is DB ID for entry
        self.geoid_admin_dict = {}  # Key is GEOID, Value is DB ID for entry
        self.place_type = ''

    def lookup_place(self, place: Loc.Loc) -> []:
        """
        Lookup a place in our geoname.org dictionary and update place with Geo_result with lat, long, District, etc
        The dictionary geo_result entry contains: Lat, Long, districtID (County or State or Province ID)
        There can be multiple entries if a city name isnt unique in a country
        """
        if any(str.isdigit(c) for c in place.target):
            # Don't lookup items with digits
            return

        result_place: Loc = Loc.Loc()
        self.start = time.time()
        place.result_type = Result.STRONG_MATCH

        # Lookup Place based on Place Type
        if place.place_type == Loc.PlaceType.ADMIN1:
            self.select_admin1(place)
        elif place.place_type == Loc.PlaceType.ADMIN2:
            self.get_admin1_id(place=place)
            self.select_admin2(place)
        elif place.place_type == Loc.PlaceType.COUNTRY:
            self.select_country(place)
        elif place.place_type == Loc.PlaceType.FILTER:
            self.advanced_search(place)
        else:
            self.get_admin1_id(place=place)
            self.get_admin2_id(place=place)
            self.select_city(place)

        nm = place.name

        # Add search quality score to each entry
        for idx, rw in enumerate(place.georow_list):
            self.copy_georow_to_place(row=rw, place=result_place)
            update = list(rw)
            update.append(1)  # Extend list row and assign score
            result_place.prefix = ''
            res_nm = result_place.format_full_nm(None)
            # todo - move feature priority into scoring routine
            score = self.match_score(inp=nm, res=res_nm,
                                     feat=Geodata.Geodata.get_priority(rw[GeoKeys.Entry.FEAT]))

            # Remove items in prefix that are in result
            tk_list = res_nm.split(",")
            for item in tk_list:
                place.prefix = re.sub(item.strip(' ').lower(), '', place.prefix)

            update[GeoKeys.Entry.SCORE] = score
            place.georow_list[idx] = tuple(update)

        if place.result_type == Result.STRONG_MATCH and len(place.prefix) > 0:
            place.result_type = Result.PARTIAL_MATCH

    def match_score(self, inp, res, feat)->int:
        inp = GeoKeys.semi_normalize(inp)
        res = GeoKeys.semi_normalize(res)
        res = re.sub(r"'", ' ', res)  # Normalize
        res = re.sub(r"normandy american ", 'normandie american ', res)  # Odd case for Normandy American cemetery having only english spelling

        score1 : int = self.match_score_calc(inp, res)

        # Calculate score with noise word removal
        #inp = re.sub('shire', '', inp)

        res = re.sub(r' county', ' ', res)
        res = re.sub(r' stadt', ' ', res)
        res = re.sub(r' departement', ' ', res)
        res = re.sub(r'regierungsbezirk ', ' ', res)
        res = re.sub(r' departement', ' ', res)
        res = re.sub(r'gemeente ', ' ', res)
        res = re.sub(r'provincia ', ' ', res)
        res = re.sub(r'provincie ', ' ', res)
        res = re.sub(r'nouveau brunswick ', ' ', res)



        res = re.sub(r' de ', ' ', res)
        res = re.sub(r' du ', ' ', res)
        res = re.sub(r' of ', ' ', res)

        res = re.sub(r"politischer bezirk ", ' ', res)  # Normalize
        score2 : int = self.match_score_calc(inp, res)

        return  min(score1, score2)
        #return int ( (sc - float(Geodata.Geodata.get_priority(feat)) * 0.1) * 100)

    def match_score_calc(self, inp, res)->int:
        # Return a score 0-100 reflecting the difference between the user input and the result:
        # The percent of characters in inp that were NOT matched by a word in result
        # Lower score is better match.  0 is perfect match, 100 is no match

        original_inp_tokens = inp.split(',')
        result_tokens = res.split(" ")
        out = result_tokens[0]
        l2 = len(result_tokens[0])

        # Percent of each input token that was not matched.  Averaged over number of tokens
        lst = sorted(result_tokens, key=len, reverse=True)
        for idx, result_tok in enumerate(lst):
            if len(result_tok) > 2:
                inp = re.sub(result_tok.strip(','), '', inp)

        in_score = 0
        inp_tokens = inp.split(',')

        for idx, tk in enumerate(inp_tokens):
            # Tokens to the right end have slightly higher weighting
            weight = (1.0 + idx * .005)
            if len(original_inp_tokens[idx].strip(' ')) > 0:
                in_score += int(100.0 * len(inp_tokens[idx].strip(' ')) / len(original_inp_tokens[idx].strip(' ')) * weight)

        # Average over number of tokens
        in_score = in_score / len(inp_tokens)

        # Output score (percent of first token in output that was not matched)
        result_tokens = res.split(",")
        out = result_tokens[0]

        for tok in original_inp_tokens:
            inp_words = tok.split(" ")
            for in_tok in inp_words:
                ll = len(in_tok)
                if ll > 2:
                    targ = in_tok.strip(',')
                    targ = targ.strip(' ')

                    out = re.sub(targ, '', out)
                    #self.logger.debug(f'in tok [{targ}] out=[{out}]')

        lll = len(out.strip(' '))
        if l2 > 0:
            out_score = (int((0.06 * 100.0) * lll / l2))
        else:
            out_score = 0

        score = in_score + out_score
        self.logger.debug(f'Sc={score}  [{original_inp_tokens[0]}] DB [{res}]  InS={in_score:.1f} InRem [{inp}] '
                          f'OutS={out_score:.1f} OutRem [{out}]  ')
        return score

        """
        res:float = float(Levenshtein.distance(str(GeoKeys.normalize(inp)), str(GeoKeys.normalize(result))))
        if len(inp) > 0:
            return int(100*res / float(len(inp)))
        else:
            if len(result) > 0:
                return 100
            else:
                return 0
        """

    def advanced_search(self, place: Loc):
        """
        Advanced search - support parameters for ISO and Feature class
        """
        lookup_target = place.target
        if len(lookup_target) == 0:
            return
        pattern = self.create_wildcard(lookup_target)
        iso_pattern = self.create_wildcard(place.country_iso)
        feature_pattern = self.create_wildcard(place.feature)
        self.logger.debug(f'CITY FILTER lookup. Targ=[{pattern}] feature=[{feature_pattern}]'
                          f'  iso=[{iso_pattern}] ')

        query_list = []
        query_list.append(Query(where="name LIKE ? AND country LIKE ? AND f_code LIKE ?",
                                args=(pattern, iso_pattern, feature_pattern),
                                result=Result.PARTIAL_MATCH))

        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)
        admin_list, place.result_type = self.db.process_query_list(from_tbl='main.admin', query_list=query_list)
        place.georow_list.extend(admin_list)

    def select_city(self, place: Loc):
        """
        Search for  entry - try the most exact match first, then less exact matches
        """
        lookup_target = place.target
        if len(lookup_target) == 0:
            return
        pattern = self.create_wildcard(lookup_target)
        sdx = get_soundex(lookup_target)
        self.logger.debug(f'CITY lookup. Targ=[{lookup_target}] adm1 id=[{place.admin1_id}]'
                          f' adm2 id=[{place.admin2_id}] iso=[{place.country_iso}] patt =[{pattern}] sdx={sdx}')

        query_list = []

        if len(place.country_iso) == 0:
            # No country present - try lookup by name.
            query_list.append(Query(where="name = ?",
                                    args=(lookup_target,),
                                    result=Result.PARTIAL_MATCH))
            # lookup by wildcard name, admin1
            query_list.append(Query(where="name LIKE ?",
                                    args=(pattern,),
                                    result=Result.WILDCARD_MATCH))
            #query_list.append(Query(where="name LIKE ?",
            #                        args=(pattern + ' historical',),
            #                        result=Result.WILDCARD_MATCH))
            query_list.append(Query(where="sdx = ?",
                                    args=(sdx,),
                                    result=Result.SOUNDEX_MATCH))
            place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)
            # self.logger.debug(place.georow_list)
            return

        # Build query list - try each query in order until a match is found
        # Start with the most exact match depending on the data provided.
        query_list.append(Query(where="name = ? AND country = ?",
                                args=(lookup_target, place.country_iso),
                                result=Result.PARTIAL_MATCH))

        if len(place.admin1_name) > 0:
            if len(place.admin2_name) > 0:
                # lookup by name, admin1, admin2
                query_list.append(Query(where="name = ? AND country = ? AND admin1_id = ? AND admin2_id = ?",
                                        args=(lookup_target, place.country_iso, place.admin1_id, place.admin2_id),
                                        result=Result.STRONG_MATCH))

            # lookup by name, admin1
            query_list.append(Query(where="name = ? AND country = ? AND admin1_id = ?",
                                    args=(lookup_target, place.country_iso, place.admin1_id),
                                    result=Result.STRONG_MATCH))

            # lookup by wildcard name, admin1
            query_list.append(Query(where="name LIKE ? AND country = ? AND admin1_id = ?",
                                    args=(pattern, place.country_iso, place.admin1_id),
                                    result=Result.PARTIAL_MATCH))
        elif len(place.admin2_name) == 0:
            # lookup by name
            # admin1 and admin2 werent entered, so a match here is an exact match
            query_list.append(Query(where="name = ? AND country = ?",
                                    args=(lookup_target, place.country_iso),
                                    result=Result.STRONG_MATCH))
        elif len(place.admin2_name) > 0:
            # lookup by name
            # admin1 wasnt entered, so a match here is an exact match
            query_list.append(Query(where="name = ? AND admin2_id=? AND country = ?",
                                    args=(lookup_target, place.admin2_id, place.country_iso),
                                    result=Result.STRONG_MATCH))
        else:
            # lookup by name (partial match since user specified admin)
            query_list.append(Query(where="name = ? AND country = ?",
                                    args=(lookup_target, place.country_iso),
                                    result=Result.PARTIAL_MATCH))

        # append lookup by wildcard (partial match since user specified admin)
        query_list.append(Query(where="name LIKE ? AND country = ?",
                                args=(pattern, place.country_iso),
                                result=Result.WILDCARD_MATCH))

        # lookup by wildcard with % added (partial match since user specified admin)
        query_list.append(Query(where="name LIKE ? AND country = ?",
                                args=('%' + pattern, place.country_iso),
                                result=Result.WILDCARD_MATCH))

        # lookup by Soundex (partial match)
        if len(place.admin1_name) > 0:
            query_list.append(Query(where="sdx = ? AND admin1_id = ? AND country = ?",
                                    args=(sdx, place.admin1_id, place.country_iso),
                                    result=Result.SOUNDEX_MATCH))
        else:
            query_list.append(Query(where="sdx = ? AND country = ?",
                                    args=(sdx, place.country_iso),
                                    result=Result.SOUNDEX_MATCH))

        # Try each query in list until we find a match
        place.georow_list, place.result_type = self.db.process_query_list(from_tbl='main.geodata', query_list=query_list)
        # self.logger.debug(place.georow_list)

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
            place.name = re.sub('shire', '', place.name)

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

        """
        # if nothing found, Try admin1 as city instead
        if len(place.georow_list) == 0:
            save_admin1 = place.admin1_name
            place.city1 = place.admin1_name
            place.target = place.city1
            place.admin1_name = ''
            self.logger.debug(f'Try admin1: [{place.target}]')

            self.select_city(place)

            if len(place.georow_list) == 0:
                # still not found.  restore admin1
                place.admin1_name = save_admin1
                place.city1 = ''
            else:
                place.place_type = Loc.PlaceType.CITY
        """

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
            # todo - move feature priority into scoring routine
            score = 0.0

            # Remove items in prefix that are in result
            tk_list = res_nm.split(",")
            for item in tk_list:
                place.prefix = re.sub(item.strip(' ').lower(), '', place.prefix)

            update[GeoKeys.Entry.SCORE] = int(score*100)
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
        return res

    def get_country_iso(self, place: Loc) -> str:
        """ Return ISO code for specified country"""
        lookup_target = place.country_name
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

    def copy_georow_to_place(self, row, place: Loc):
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
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS geoid_idx ON geodata(geoid)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS admgeoid_idx ON admin(geoid)')

    def create_indices(self):
        # Create indices
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS name_idx ON geodata(name)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS country_idx ON geodata(country)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS admin1_idx ON geodata(admin1_id)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS sdx_idx ON geodata(sdx)')

        # self.db.create_index(create_table_sql='CREATE INDEX geoid_idx ON geodata(geoid)')

        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_name_idx ON admin(name)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_country_idx ON admin(country)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_admin1_idx ON admin(admin1_id)')
        self.db.create_index(create_table_sql='CREATE INDEX IF NOT EXISTS adm_sdx_idx ON admin(sdx)')

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
    def create_county_wildcard(pattern):
        # Try pattern with 'shire' removed
        pattern = re.sub(r"shire", "", pattern)
        # Create SQL wildcard pattern (convert * to %).  Add % on end
        if '*' in pattern:
            return re.sub(r"\*", "%", pattern)
        else:
            return f'{pattern}'

    def close(self):
        self.logger.info('Closing Database')
        self.db.conn.close()

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

        for tbl in [sql_geodata_table, sql_admin_table]:
            self.db.create_table(tbl)
