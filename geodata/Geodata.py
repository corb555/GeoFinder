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
import collections
import copy
import logging
from operator import itemgetter

from geodata import GeoUtil, GeodataFiles, Loc, MatchScore


class Geodata:
    """
    Provide a place lookup gazeteer based on datafiles from geonames.org read in by GeodataFiles.py
    """

    def __init__(self, directory_name: str, progress_bar, enable_spell_checker,
                 show_message, exit_on_error):
        """
        Provide a place lookup gazeteer based on datafiles from geonames.org read in by GeodataFiles.py
        The lookup returns whether a place exists and its lat/long.
        :param directory_name:
        :param progress_bar: tkhelper progress bar or None
        :param enable_spell_checker: If True then use SpellChecker (CURRENTLY NOT SUPPORTED)
        :param show_message - show TKInter message dialog on error
        :param exit_on_error - exit on significant error
        """
        self.logger = logging.getLogger(__name__)
        self.status = "geoname file error"
        self.directory: str = directory_name
        self.progress_bar = progress_bar  # progress_bar
        self.geo_files = GeodataFiles.GeodataFiles(self.directory, progress_bar=self.progress_bar,
                                                   enable_spell_checker=enable_spell_checker,
                                                   show_message=show_message, exit_on_error=exit_on_error)
        self.save_place: Loc = Loc.Loc()
        self.match = MatchScore.MatchScore()
        self.miss_diag_file = None

    def find_location(self, location: str, place: Loc, plain_search) -> GeoUtil.Result:
        """
        Find a location in the geoname database.  On successful match, place.georow_list will contain
        list of georows that matched the name.  Each georow can be copied to a Loc structure by
        calling geodb.copy_georow_to_place

        :param location: comma separated name of location to find, e.g. 'Los Angeles, California, USA'
        :param place: Loc structure
        :param plain_search: If True then don't do wildcard searches
        :return: GeoUtil.Result code.
        """

        """
        Search Mechanism
        1) place.parse_place: Parse the location into <prefix>, city, admin2, admin1, country.  Scan from right and fill in Country and Admin1 only
           if those items are found in DB
        2) geodb.lookup_place: look up in the place dictionary: a) as parsed, b) then with Prefix as city, then Admin2  as city, then
            c) try City as Admin2.  Each DB lookup tries key lookup, and wildcard and Soundex.
            All matches are returned.
        3) Process place - Update place with -- lat, lon, district, city, country_iso, result code
        Geofinder then calls geodata.build_list which removes duplicates and ranks the items
        """
        if plain_search:
            # Don't do wildcard searches
            self.geo_files.geodb.db.use_wildcards = False

        place.parse_place(place_name=location, geo_files=self.geo_files)
        self.logger.debug(f"    ==== PARSE: [{location}]\n    Pref=[{place.prefix}] City=[{place.city1}] Adm2=[{place.admin2_name}]"
                          f" Adm1 [{place.admin1_name}] adm1_id [{place.admin1_id}] Ctry [{place.country_name}]"
                          f" type_id={place.place_type}")

        # Successful find of Admin1 will also fill in country_iso
        # Use ISO to fill in country name if missing
        if place.country_name == '' and place.country_iso != '':
            place.country_name = self.geo_files.geodb.get_country_name(place.country_iso)

        # Add comma if prefix present
        if len(place.prefix) > 0:
            prfx = place.prefix + ','
        else:
            prfx = ''

        # Create full entry text
        place.updated_entry = GeoUtil.capwords(prfx) + place.get_long_name(self.geo_files.output_replace_dct)

        flags = ResultFlags(limited=False, filtered=False)
        result_list = []  # We will do different search types and append all results into result_list

        # self.logger.debug(f'== FIND LOCATION City=[{place.city1}] Adm2=[{place.admin2_name}]\
        # Adm1=[{place.admin1_name}] Pref=[{place.prefix}] Cntry=[{place.country_name}] iso=[{place.country_iso}]  Type={place.place_type} ')

        # Save a shallow copy of place so we can restore fields
        self.save_place = copy.copy(place)

        if place.place_type == Loc.PlaceType.ADVANCED_SEARCH:
            self.advanced_search(place, result_list)
            return place.result_type

        self.is_country_valid(place)

        if place.result_type == GeoUtil.Result.NOT_SUPPORTED:
            # The country in this entry is not supported
            self.process_result(place=place, flags=flags)
            return place.result_type

        # 1) Try lookup as determined by standard parsing:  city, county, state/province, country
        place.standard_parse = True
        self.logger.debug(f'  1) Standard, based on parsing.  pref [{place.prefix}] type={place.place_type}')

        self.geo_files.geodb.lookup_place(place=place)
        if place.georow_list:
            result_list.extend(place.georow_list)

        # Restore items
        place.city1 = self.save_place.city1
        place.admin2_name = self.save_place.admin2_name
        place.prefix = self.save_place.prefix
        place.extra = self.save_place.extra

        # Try alternatives since parsing can be wrong
        # 2)  a) Try Prefix as city, b) Try Admin2  as city
        place.standard_parse = False
        for ty in [Loc.PlaceType.PREFIX, Loc.PlaceType.ADMIN2]:
            self.lookup_by_type(place, result_list, ty, self.save_place)

        # 3) Try city as Admin2
        self.logger.debug(f'  3) Lkp w Cit as Adm2. Target={place.city1}  pref [{place.prefix}] ')
        self.lookup_as_admin2(place=place, result_list=result_list, save_place=self.save_place)

        #  Move result list into place georow list
        place.georow_list.clear()
        place.georow_list.extend(result_list)

        if len(place.georow_list) > 0:
            # Copy geodata to place record
            self.process_result(place=place, flags=flags)
            flags = self.build_result_list(place)

        if len(place.georow_list) == 0:
            # NO MATCH
            self.logger.debug(f'Not found.')
            # place = self.save_place
            if place.result_type != GeoUtil.Result.NO_COUNTRY and place.result_type != GeoUtil.Result.NOT_SUPPORTED:
                place.result_type = GeoUtil.Result.NO_MATCH
        elif len(place.georow_list) > 1:
            self.logger.debug(f'Success!  {len(place.georow_list)} matches')
            place.result_type = GeoUtil.Result.MULTIPLE_MATCHES

        # Process the results
        self.process_result(place=place, flags=flags)
        # self.logger.debug(f'Status={place.status}')
        return place.result_type

    def lookup_by_type(self, place: Loc, result_list, typ, save_place: Loc):
        typ_name = ''
        if typ == Loc.PlaceType.CITY:
            # Try City as city (do as-is)
            typ_name = 'City'
            pass
        elif typ == Loc.PlaceType.ADMIN2:
            # Try ADMIN2 as city
            if place.admin2_name != '':
                place.prefix += ' ' + place.city1
                place.city1 = place.admin2_name
                place.admin2_name = ''
                typ_name = 'Admin2'
        elif typ == Loc.PlaceType.PREFIX:
            # Try Prefix as City
            if place.prefix != '':
                place.city1 = place.prefix
                place.prefix = save_place.city1
                typ_name = 'Prefix'
        elif typ == Loc.PlaceType.ADVANCED_SEARCH:
            # Advanced Search
            self.geo_files.geodb.lookup_place(place=place)
            result_list.extend(place.georow_list)
            return
        else:
            self.logger.warning(f'Unknown TYPE {typ}')

        if typ_name != '':
            self.logger.debug(f'2) Lookup by {typ_name} Target={place.city1}  pref [{place.prefix}] ')

            place.target = place.city1
            place.place_type = Loc.PlaceType.CITY

            self.geo_files.geodb.lookup_place(place=place)
            result_list.extend(place.georow_list)
            # self.calculate_prefixes_for_rows(place=place)

            # Restore items
            place.city1 = save_place.city1
            place.admin2_name = save_place.admin2_name
            place.prefix = save_place.prefix
            place.extra = save_place.extra

    def process_result(self, place: Loc, flags) -> None:
        """
        Copy geodata to place record and put together status text
        :param place:
        :param flags:
        :return:
        """
        # self.logger.debug(f'**PROCESS RESULT:  Res={place.result_type}  Targ={place.target} Georow_list={place.georow_list}')
        if place.result_type == GeoUtil.Result.NOT_SUPPORTED:
            place.place_type = Loc.PlaceType.COUNTRY

        if place.result_type in GeoUtil.successful_match and len(place.georow_list) > 0:
            self.geo_files.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)
        elif len(place.georow_list) > 0:
            # self.logger.debug(f'***RESULT={place.result_type} Setting to Partial')
            place.result_type = GeoUtil.Result.PARTIAL_MATCH

        place.prefix = place.prefix.strip(' ')
        place.set_place_type_text()

    def build_result_list(self, place: Loc):
        # Create a sorted version of result_list without any duplicates (same name, similar lat/lon)
        # In case of duplicate, keep the one with best match score
        # Add flag if we hit the lookup limit
        # Discard location names that didnt exist at time of event (update result flag if this occurs)
        date_filtered = False  # Flag to indicate whether we dropped locations due to event date
        event_year = place.event_year

        if len(place.georow_list) > 100:
            limited_flag = True
        else:
            limited_flag = False

        # sort list by LON/LAT and score so we can remove dups
        list_copy = sorted(place.georow_list, key=itemgetter(GeoUtil.Entry.LON, GeoUtil.Entry.LAT, GeoUtil.Entry.SCORE))
        place.georow_list.clear()
        distance_cutoff = 0.5  # Value to determine if two lat/longs are similar

        # Create a dummy 'previous' row so first comparison works
        prev_geo_row = self.geo_files.geodb.make_georow(name='q', iso='q', adm1='q', adm2='q', lat=900, lon=900, feat='q', geoid='q', sdx='q')
        idx = 0
        geoid_dict = {}

        # Create new list without dupes (adjacent items with same name and close lat/lon)
        # Find if two items with same name are similar lat/lon (within Box Distance of 0.5 degrees)
        for geo_row in list_copy:
            if self.valid_year_for_location(event_year, geo_row[GeoUtil.Entry.ISO], geo_row[GeoUtil.Entry.ADM1], 60) is False:
                # Skip location if location name  didnt exist at the time of event WITH 60 years padding
                continue

            if self.valid_year_for_location(event_year, geo_row[GeoUtil.Entry.ISO], geo_row[GeoUtil.Entry.ADM1], 0) is False:
                # Flag if location name  didnt exist at the time of event
                date_filtered = True

            new_row = list(geo_row)
            geo_row = tuple(new_row)
            # self.logger.debug(f'{geo_row[GeoKeys.Entry.NAME]},{geo_row[GeoKeys.Entry.FEAT]} '
            #                  f'{geo_row[GeoKeys.Entry.SCORE]:.1f} {geo_row[GeoKeys.Entry.ADM2]}, '
            #                  f'{geo_row[GeoKeys.Entry.ADM1]} {geo_row[GeoKeys.Entry.ISO]}')
            if geoid_dict.get(geo_row[GeoUtil.Entry.ID]):
                # We already have an entry for this geoid.  Replace if this one has better score
                row_idx = geoid_dict.get(geo_row[GeoUtil.Entry.ID])
                other_row = place.georow_list[row_idx]
                if geo_row[GeoUtil.Entry.SCORE] < other_row[GeoUtil.Entry.SCORE]:
                    # Same GEOID but this has better score so replace other entry.  Otherwise leave previous entry
                    place.georow_list[row_idx] = geo_row
                    self.logger.debug(f'Better score {geo_row[GeoUtil.Entry.SCORE]} < {other_row[GeoUtil.Entry.SCORE]} {geo_row[GeoUtil.Entry.NAME]}')
            elif geo_row[GeoUtil.Entry.NAME] != prev_geo_row[GeoUtil.Entry.NAME]:
                # Name is different.  Add this item
                place.georow_list.append(geo_row)
                geoid_dict[geo_row[GeoUtil.Entry.ID]] = idx
                idx += 1
            elif abs(float(prev_geo_row[GeoUtil.Entry.LAT]) - float(geo_row[GeoUtil.Entry.LAT])) + \
                    abs(float(prev_geo_row[GeoUtil.Entry.LON]) - float(geo_row[GeoUtil.Entry.LON])) > distance_cutoff:
                # Lat/lon is different from previous item. Add this one
                place.georow_list.append(geo_row)
                geoid_dict[geo_row[GeoUtil.Entry.ID]] = idx
                idx += 1
            elif geo_row[GeoUtil.Entry.SCORE] < prev_geo_row[GeoUtil.Entry.SCORE]:
                # Same Lat/lon but this has better score so replace previous entry.  Otherwise leave previous entry
                place.georow_list[idx - 1] = geo_row
                geoid_dict[geo_row[GeoUtil.Entry.ID]] = idx - 1
                # self.logger.debug(f'Use. {geo_row[GeoUtil.Entry.SCORE]}  < {prev_geo_row[GeoUtil.Entry.SCORE]} {geo_row[GeoUtil.Entry.NAME]}')
            # else:
            # self.logger.debug(f'Ignore. {geo_row[GeoUtil.Entry.SCORE]} NOT < {prev_geo_row[GeoUtil.Entry.SCORE]} {geo_row[GeoUtil.Entry.NAME]}')

            prev_geo_row = geo_row

        min_score = 9999
        new_list = sorted(place.georow_list, key=itemgetter(GeoUtil.Entry.SCORE, GeoUtil.Entry.ADM1))
        place.georow_list.clear()
        min_match = ''
        sec_match = ''
        gap_threshold2 = 0

        for rw, geo_row in enumerate(new_list):
            score = geo_row[GeoUtil.Entry.SCORE]
            admin1_name = self.geo_files.geodb.get_admin1_name_direct(geo_row[GeoUtil.Entry.ADM1], geo_row[GeoUtil.Entry.ISO])
            admin2_name = self.geo_files.geodb.get_admin2_name_direct(geo_row[GeoUtil.Entry.ADM1],
                                                                      geo_row[GeoUtil.Entry.ADM2], geo_row[GeoUtil.Entry.ISO])

            if rw == 1:
                sec_match = f'Score={score:.1f} {geo_row[GeoUtil.Entry.NAME]}, {admin2_name},' \
                    f' {admin1_name}, {geo_row[GeoUtil.Entry.ISO]}'

            if score < min_score:
                min_score = score
                min_match = f'Score={score:.1f} {geo_row[GeoUtil.Entry.NAME]}, {admin2_name},' \
                    f' {admin1_name}, {geo_row[GeoUtil.Entry.ISO]}'

            self.logger.debug(f'Score {score:.1f}  {geo_row[GeoUtil.Entry.NAME]}, {geo_row[GeoUtil.Entry.ADM2]},'
                              f' {geo_row[GeoUtil.Entry.ADM1]}')

            gap_threshold2 = MatchScore.EXCELLENT / 2 + abs(min_score) * .4

            # Range to display when there is a strong match
            if min_score <= MatchScore.EXCELLENT and score > min_score + gap_threshold2:
                self.logger.debug(f'Min score <7 and gap > {gap_threshold2}. min={min_score} curr={score}')
                break

            # Range to display when there is a weak match
            gap_threshold = MatchScore.EXCELLENT / 2 + abs(min_score) * .8
            if score > min_score + gap_threshold:
                self.logger.debug(f'Score gap greater than {gap_threshold:.1f}. min={min_score:.1f} curr={score:.1f}')
                break

            place.georow_list.append(geo_row)

        self.logger.debug(f'min={min_score:.1f}, gap2={gap_threshold2:.1f}')

        if min_score <= MatchScore.EXCELLENT and len(place.georow_list) == 1:
            place.result_type = GeoUtil.Result.STRONG_MATCH
        else:
            # Log item that we couldnt match
            if self.miss_diag_file:
                self.miss_diag_file.write(f'{place.original_entry}\n   MIN {min_match}\n   2ND {sec_match}\n\n')

        return ResultFlags(limited=limited_flag, filtered=date_filtered)

    def find_first_match(self, location: str, place: Loc):
        """
        Find the first match for this location in the geoname dictionary.
        First parse the location into <prefix>, city, <district2>, district1, country.
        Then look it up in the place db
        Update place with -- lat, lon, district, city, country_iso, result code
        """
        place.parse_place(place_name=location, geo_files=self.geo_files)
        place.country_name = self.geo_files.geodb.get_country_name(place.country_iso)

        place.country_iso = place.country_iso

        # Lookup location
        self.geo_files.geodb.lookup_place(place=place)

        # Clear to a single entry
        if len(place.georow_list) > 1:
            row = copy.copy(place.georow_list[0])
            place.georow_list.clear()
            place.georow_list.append(row)
            place.result_type = GeoUtil.Result.STRONG_MATCH

        self.process_result(place=place, flags=ResultFlags(limited=False, filtered=False))

    def find_geoid(self, geoid: str, place: Loc):
        place.target = geoid
        place.georow_list.clear()
        self.geo_files.geodb.get_geoid(place=place)
        if len(place.georow_list) > 0:
            # Copy geo row to Place
            self.geo_files.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)
            place.original_entry = place.get_long_name(None)
            place.result_type = GeoUtil.Result.STRONG_MATCH
        else:
            place.result_type = GeoUtil.Result.NO_MATCH

    def lookup_geoid(self, place: Loc):
        flags = ResultFlags(limited=False, filtered=False)
        self.geo_files.geodb.get_geoid(place)
        self.process_result(place=place, flags=flags)

    def search_city(self, place: Loc):
        place.target = place.city1
        place.prefix = f' {place.admin2_name.title()}'
        self.logger.debug(f' Try city [{place.target}] as city')
        self.geo_files.geodb.lookup_place(place=place)

    def lookup_as_admin2(self, place: Loc, result_list, save_place: Loc):
        # Try City as ADMIN2
        place.extra = place.admin2_name
        place.target = place.city1
        place.admin2_name = place.city1
        place.city1 = ''
        place.place_type = Loc.PlaceType.ADMIN2
        self.logger.debug(f'  Try admin2  [{place.target}] as city [{place.get_five_part_title()}]')
        self.geo_files.geodb.lookup_place(place=place)
        result_list.extend(place.georow_list)

        # Restore items
        place.city1 = save_place.city1
        place.admin2_name = save_place.admin2_name
        place.admin1_name = save_place.admin1_name
        place.prefix = save_place.prefix

    def advanced_search(self, place, result_list):
        # Lookup location with advanced search params
        self.logger.debug('Advanced Search')
        self.lookup_by_type(place, result_list, place.place_type, self.save_place)
        place.georow_list.clear()
        place.georow_list.extend(result_list)

        if len(place.georow_list) > 0:
            # Build list - sort and remove duplicates
            # self.logger.debug(f'Match {place.georow_list}')
            flags = ResultFlags(limited=False, filtered=False)
            self.process_result(place=place, flags=flags)
            self.build_result_list(place)

    def read(self) -> bool:
        """ Read in geo name files which contain place names and their lat/lon.
            Return True if error
        """
        err = self.geo_files.read()
        if err:
            return True

    def read_geonames(self):
        self.progress("Reading Geoname files...", 70)
        return self.geo_files.read_geoname()

    def progress(self, msg: str, percent: int):
        if self.progress_bar is not None:
            self.progress_bar.update_progress(percent, msg)
        else:
            self.logger.debug(msg)

    def is_country_valid(self, place: Loc) -> bool:
        # See if COUNTRY is present and is in the supported country list
        if place.country_iso == '':
            place.result_type = GeoUtil.Result.NO_COUNTRY
            is_valid = False
        elif place.country_iso not in self.geo_files.supported_countries_dct:
            self.logger.debug(f'[{place.country_iso}] not supported')
            place.result_type = GeoUtil.Result.NOT_SUPPORTED
            place.place_type = Loc.PlaceType.COUNTRY
            place.target = place.country_name
            is_valid = False
        else:
            is_valid = True

        return is_valid

    @staticmethod
    def valid_year_for_location(event_year: int, iso: str, admin1: str, padding: int) -> bool:
        # See if this location name was valid at the time of the event
        # Try looking up start year by state/province
        place_year = admin1_name_start_year.get(f'{iso}.{admin1.lower()}')
        if place_year is None:
            # Try looking up start year by country
            place_year = country_name_start_year.get(iso)
        if place_year is None:
            place_year = -1

        if event_year + padding < place_year and event_year != 0:
            # self.logger.debug(f'Invalid year:  incorporation={place_year}  event={event_year} loc={admin1},{iso} pad={padding}')
            return False
        else:
            return True

    @staticmethod
    def get_priority(feature):
        # Returns 0-100 for feature priority.  Lowest is best
        f_prior = feature_priority.get(feature)
        if f_prior is None:
            f_prior = feature_priority.get('DEFAULT')
        # print(f'Geodata Feat [{feature}] raw ={f_prior}')

        return 100.0 - float(f_prior)

    def open_diag_file(self, miss_diag_fname: str):
        # Open diagnostic file
        self.miss_diag_file = open(miss_diag_fname, 'wt')

    def close_diag_file(self):
        # Close diagnostic file
        if self.miss_diag_file:
            self.miss_diag_file.close()


# Default geonames.org feature types to load
default = ["ADM1", "ADM2", "ADM3", "ADM4", "ADMF", "CH", "CSTL", "CMTY", "EST ", "HSP",
           "HSTS", "ISL", "MSQE", "MSTY", "MT", "MUS", "PAL", "PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4",
           "PPLC", "PPLG", "PPLH", "PPLL", "PPLQ", "PPLX", "PRK", "PRN", "PRSH", "RUIN", "RLG", "STG", "SQR", "SYG", "VAL"]

# If there are 2 identical entries, we only add the one with higher feature priority.  Highest value is for large city or capital
# These scores are also part of the match ranking score
# Note: PP1M, P1HK, P10K do not exist in Geonames and are created by geofinder
feature_priority = {'PP1M': 90, 'ADM1': 88, 'PPLA': 88, 'PPLC': 88, 'PP1K': 75, 'PPLA2': 85, 'P10K': 81, 'P1HK': 85,
                    'PPL': 50, 'PPLA3': 65, 'ADMF': 65, 'PPLA4': 63, 'ADMX': 60, 'PAL': 40, 'ISL': 50,
                    'ADM2': 73, 'PPLG': 68, 'MILB': 40, 'NVB': 65, 'PPLF': 63, 'ADM0': 85, 'PPLL': 50, 'PPLQ': 55, 'PPLR': 55,
                    'CH': 40, 'MSQE': 40, 'SYG': 40, 'CMTY': 40, 'CSTL': 40, 'EST': 40, 'PPLS': 50, 'PPLW': 50, 'PPLX': 75, 'BTL': 20,
                    'HSTS': 40, 'PRK': 40, 'HSP': 0, 'VAL': 0, 'MT': 0, 'ADM3': 30, 'ADM4': 0, 'DEFAULT': 0, }

ResultFlags = collections.namedtuple('ResultFlags', 'limited filtered')

# Starting year this country name was valid
country_name_start_year = {
    'cu': -1,
}

# Starting year this state/province modern names were valid
# https://en.wikipedia.org/wiki/List_of_North_American_settlements_by_year_of_foundation
admin1_name_start_year = {
    'us.al': 1711,
    'us.ak': 1774,
    'us.az': 1775,
    'us.ar': 1686,
    'us.ca': 1769,
    'us.co': 1871,
    'us.ct': 1633,
    'us.de': 1638,
    'us.dc': 1650,
    'us.fl': 1565,
    'us.ga': 1566,
    'us.hi': -1,
    'us.id': 1862,
    'us.il': 1703,
    'us.in': 1715,
    'us.ia': 1785,
    'us.ks': 1870,
    'us.ky': 1775,
    'us.la': 1699,
    'us.me': 1604,
    'us.md': 1633,
    'us.ma': 1620,
    'us.mi': 1784,
    'us.mn': 1820,
    'us.ms': 1699,
    'us.mo': 1765,
    'us.mt': 1877,
    'us.ne': 1854,
    'us.nv': 1905,
    'us.nh': 1638,
    'us.nj': 1624,
    'us.nm': 1598,
    'us.ny': 1614,
    'us.nc': 1653,
    'us.nd': 1871,
    'us.oh': 1785,
    'us.ok': 1889,
    'us.or': 1811,
    'us.pa': 1682,
    'us.ri': 1636,
    'us.sc': 1663,
    'us.sd': 1865,
    'us.tn': 1739,
    'us.tx': 1685,
    'us.ut': 1847,
    'us.vt': 1650,
    'us.va': 1607,
    'us.wa': 1825,
    'us.wv': 1788,
    'us.wi': 1685,
    'us.wy': 1867,
    'ca.01': 1795,
    'ca.02': 1789,
    'ca.03': 1733,
    'ca.04': 1766,
    'ca.05': 1583,
    'ca.07': 1604,
    'ca.08': 1673,
    'ca.09': 1764,
    'ca.10': 1541,
    'ca.11': 1862,
    'ca.12': 1700,
    'ca.13': 1700,
    'ca.14': 1700
}
