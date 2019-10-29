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
import string as st
from operator import itemgetter

from geofinder import GeodataFiles, GeoKeys, Loc


class Geodata:
    """
    Provide a place lookup gazeteer based on datafiles from geonames.org read in by GeodataFiles.py

    The lookup returns whether a place exists and its lat/long.
    The data files must be downloaded from geonames.org
    First try a key lookup.  If that fails do a partial match
    """

    def __init__(self, directory_name: str, progress_bar):
        self.logger = logging.getLogger(__name__)
        self.status = "geoname file error"
        self.directory: st = directory_name
        self.progress_bar = progress_bar  # progress_bar
        self.geo_files = GeodataFiles.GeodataFiles(self.directory, progress_bar=self.progress_bar)  # , geo_district=self.geo_district)
        self.save_place = None
        self.last_iso = ''

    def update_prefix(self, place):
        temp_place = Loc.Loc()
        tokens = place.name.split(',')

        # Set all the prefix values in the georow_list
        for idx, rw in enumerate(place.georow_list):
            update = list(rw)

            # Put unused fields into prefix
            self.geo_files.geodb.copy_georow_to_place(rw, temp_place)
            temp_place.prefix = ''
            nm = GeoKeys.search_normalize(temp_place.format_full_nm(self.geo_files.output_replace_dct),place.country_iso)
            # self.logger.debug(f'NAME ={nm}')
            place.prefix = ''

            for num,fld in enumerate(tokens[:2]):
                item = GeoKeys.search_normalize(fld,place.country_iso)
                add_item = False
                # self.logger.debug(f'item={item} ')
                if num == 0 and item not in nm:
                    add_item = True

                if num == 1 and item not in nm and len(tokens) == 2:
                    # We only add the second token if there are only 2 tokens
                    add_item = True

                if '*' in item:
                    # Don't add as prefix if item is a wildcard search
                    add_item = False

                if add_item:
                    if len(place.prefix) > 0:
                        place.prefix += ' '
                    place.prefix += item.title()

            if len(place.prefix) > 0:
                place.prefix_commas = ', '
            update[GeoKeys.Entry.PREFIX] = place.prefix
            # self.logger.debug(f'PREFIX={place.prefix} ')

            place.georow_list[idx] = tuple(update)

    def lookup_by_type(self, place, result_list, typ, save_place):
        if typ == Loc.PlaceType.CITY:
            place.target = place.city1
            place.city1 = place.city1
            place.place_type = Loc.PlaceType.CITY
        elif typ == Loc.PlaceType.ADMIN2:
            place.target = place.admin2_name
            place.city1 = place.admin2_name
            place.admin2_name = ''
            place.place_type = Loc.PlaceType.CITY
        elif typ == Loc.PlaceType.ADMIN1:
            place.target = place.admin1_name
            place.city1 = place.admin1_name
            place.admin1_name = ''
            place.place_type = Loc.PlaceType.ADMIN1
        elif typ == Loc.PlaceType.PREFIX:
            place.target = place.prefix
            place.city1 = place.prefix
            place.prefix = ''
            place.place_type = Loc.PlaceType.CITY
        elif typ == Loc.PlaceType.COUNTRY:
            place.target = place.country_name
            place.place_type = Loc.PlaceType.COUNTRY

        self.geo_files.geodb.lookup_place(place=place)
        result_list.extend(place.georow_list)
        self.update_prefix(place=place)

        # Restore items
        place.city1 = save_place.city1
        place.admin2_name = save_place.admin2_name
        place.admin1_name = save_place.admin1_name
        place.prefix = save_place.prefix

    def find_location(self, location: str, place: Loc.Loc):
        """
        Find a location in the geoname dictionary.
        First parse the location into <prefix>, city, <district2>, district1, country.
        Then look it up in the place dictionary
        Update place with -- lat, lon, district, city, country_iso, result code
        """
        place.parse_place(place_name=location, geo_files=self.geo_files)

        flags = ResultFlags(limited=False, filtered=False)
        result_list = []

        #self.logger.debug(f'Find LOCATION City=[{place.city1}] Adm2=[{place.admin2_name}]\
        #Adm1=[{place.admin1_name}] Pref=[{place.prefix}] Cntry=[{place.country_name}] iso=[{place.country_iso}]  Type={place.place_type} ')

        self.save_place = copy.copy(place)

        if place.place_type == Loc.PlaceType.ADVANCED_SEARCH:
            # Lookup location with advanced search params
            self.logger.debug('Advanced Search')
            self.lookup_by_type(place, result_list, place.place_type, self.save_place)
            return

        self.country_is_valid(place)

        # The country in this entry is not supported (not loaded into DB)
        if place.result_type == GeoKeys.Result.NOT_SUPPORTED:
            self.process_result(place=place, targ_name=place.target, flags=flags)
            return

        # Try standard lookup based on simple parse:  city, county, state/province, country
        self.geo_files.geodb.lookup_place(place=place)
        result_list.extend(place.georow_list)
        self.update_prefix(place=place)

        # Simple parse can be wrong, so also try prefix token  as city and admin2 token as city
        for ty in [Loc.PlaceType.PREFIX, Loc.PlaceType.ADMIN2]:
            self.lookup_by_type(place, result_list, ty, self.save_place)

        #self.logger.debug(result_list)

        #  Move result list into place georow list
        place.georow_list.clear()
        place.georow_list.extend(result_list)

        if len(place.georow_list) > 0:
            # Build list - sort and remove duplicates
            #self.logger.debug(f'Match {place.georow_list}')
            self.process_result(place=place, targ_name=place.target, flags=flags)
            flags = self.build_result_list(place)

        if len(place.georow_list) == 0:
            # NO MATCH
            self.logger.debug(f'Not found.')
            # place = self.save_place
            if place.result_type != GeoKeys.Result.NO_COUNTRY and place.result_type != GeoKeys.Result.NOT_SUPPORTED:
                place.result_type = GeoKeys.Result.NO_MATCH
        elif len(place.georow_list) > 1:
            self.logger.debug(f'Success!  {len(place.georow_list)} matches')
            place.result_type = GeoKeys.Result.MULTIPLE_MATCHES

        # Process the results
        self.process_result(place=place, targ_name=place.target, flags=flags)
        self.logger.debug(f'Status={place.status}')

    def lookup_geoid(self, place):
        flags = ResultFlags(limited=False, filtered=False)
        self.geo_files.geodb.lookup_geoid(place)
        self.update_prefix(place=place)
        self.process_result(place,'', flags=flags)

    def search_city(self, place):
        place.target = place.city1
        place.prefix = f' {place.admin2_name.title()}'
        self.logger.debug(f' Try city [{place.target}] as city')
        self.geo_files.geodb.lookup_place(place=place)
        self.update_prefix(place=place)

    def search_admin2(self, place):
        place.target = place.admin2_name
        place.prefix = f' {place.city1.title()}'
        self.logger.debug(f'  Try admin2  [{place.target}] as city')
        self.geo_files.geodb.lookup_place(place=place)
        self.update_prefix(place=place)

    def search_admin1(self, place):
        place.target = place.admin1_name
        # place.prefix = f' {place.city1.title()} {place.admin2_name.title()}'
        self.logger.debug(f'  Try admin1  [{place.target}] as city')
        self.geo_files.geodb.lookup_place(place=place)
        self.update_prefix(place=place)

    def process_result(self, place: Loc.Loc, targ_name, flags) -> None:
        # Copy geodata to place record and Put together status text
        #self.logger.debug(f'**PROCESS RESULT:  Res={place.result_type}  Targ={place.target} Georow_list={place.georow_list}')
        if place.result_type == GeoKeys.Result.NOT_SUPPORTED:
            place.place_type = Loc.PlaceType.COUNTRY

        if place.result_type in GeoKeys.successful_match and len(place.georow_list) > 0:
            self.geo_files.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)
            place.format_full_nm(self.geo_files.output_replace_dct)
        elif len(place.georow_list) > 0:
            self.logger.debug(f'***RESULT={place.result_type} Setting to Partial')
            place.result_type = GeoKeys.Result.PARTIAL_MATCH

        place.prefix = place.prefix.strip(' ')
        self.set_place_type_text(place=place)
        place.status = f'{place.result_type_text}  {result_text_list.get(place.result_type)} '
        if flags.limited:
            place.status += ' First 300 matches shown...'

        if flags.filtered:
            place.status = f'{place.result_type_text}  {result_text_list.get(place.result_type)} '
            place.status += ' ***VERIFY EVENT DATE***'
            place.result_type = GeoKeys.Result.PARTIAL_MATCH

        self.update_prefix(place=place)

    def find_first_match(self, location: st, place: Loc.Loc):
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
        self.update_prefix(place=place)

        # Clear to a single entry
        if len(place.georow_list) > 1:
            row = copy.copy(place.georow_list[0])
            place.georow_list.clear()
            place.georow_list.append(row)
            place.result_type = GeoKeys.Result.STRONG_MATCH

        self.process_result(place=place, targ_name=place.target, flags=ResultFlags(limited=False, filtered=False))

    def find_geoid(self, geoid: str, place: Loc.Loc):
        place.target = geoid
        place.georow_list.clear()
        self.geo_files.geodb.lookup_geoid(place=place)
        if len(place.georow_list) > 0:
            # Copy geo row to Place
            self.geo_files.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)
            place.name = place.format_full_nm(None)
            place.result_type = GeoKeys.Result.STRONG_MATCH
        else:
            place.result_type = GeoKeys.Result.NO_MATCH

    def set_place_type_text(self, place: Loc.Loc):
        if place.result_type == GeoKeys.Result.NO_COUNTRY:
            place.result_type_text = 'Country'
        elif place.place_type == Loc.PlaceType.COUNTRY:
            place.result_type_text = 'Country'
        elif place.place_type == Loc.PlaceType.ADMIN1:
            place.result_type_text = self.get_district1_type(place.country_iso)
        elif place.place_type == Loc.PlaceType.ADMIN2:
            place.result_type_text = 'County'
        elif place.place_type == Loc.PlaceType.CITY:
            place.result_type_text = self.get_type_name(place.feature)
        elif place.place_type == Loc.PlaceType.PREFIX:
            place.result_type_text = 'Place'
        """
        if place.place_type == Loc.PlaceType.CITY:
            place.result_type_text = '' #GeoKeys.type_names.get(place.feature)
            if place.result_type_text is None:
                place.result_type_text = ' '
        elif place.place_type == Loc.PlaceType.ADMIN1:
            place.result_type_text = self.get_district1_type(place.country_iso)
        else:
            place.result_type_text = Loc.place_type_name_dict[place.place_type]
        """

    def set_last_iso(self, iso):
        self.last_iso = iso

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

    def progress(self, msg: st, percent: int):
        if self.progress_bar is not None:
            self.progress_bar.update_progress(percent, msg)
        else:
            self.logger.debug(msg)

    def country_is_valid(self, place: Loc) -> bool:
        # See if COUNTRY is present and is in the supported country list
        if place.country_iso == '':
            place.result_type = GeoKeys.Result.NO_COUNTRY
            is_valid = False
        elif place.country_iso not in self.geo_files.supported_countries_dct:
            self.logger.debug(f'[{place.country_iso}] not supported')
            place.result_type = GeoKeys.Result.NOT_SUPPORTED
            place.place_type = Loc.PlaceType.COUNTRY
            place.target = place.country_name
            is_valid = False
        else:
            is_valid = True

        return is_valid

    def validate_year_for_location(self, event_year: int, iso: str, admin1: str, padding: int) -> bool:
        # See if this location name was valid at the time of the event
        # Try looking up start year by state/province
        event_year += padding
        start_year = admin1_name_start_year.get(f'{iso}.{admin1.lower()}')
        if start_year is None:
            # Try looking up start year by country
            start_year = country_name_start_year.get(iso)
        if start_year is None:
            start_year = -1

        if event_year < start_year and event_year != 0 + padding:
            # self.logger.debug(f'Val year:  loc year={start_year}  event yr={event_year} loc={admin1},{iso}')
            return False
        else:
            return True

    def build_result_list(self, place):
        # Create a sorted version of result_list without any dupes
        # Add flag if we hit the lookup limit
        # Discard location names that didnt exist at time of event and add to result flag
        date_filtered = False  # Flag to indicate whether we dropped locations due to event date
        event_year = place.event_year

        if len(place.georow_list) > 299:
            limited_flag = True
        else:
            limited_flag = False

        # sort list by State/Province id, and County id
        list_copy = sorted(place.georow_list, key=itemgetter(GeoKeys.Entry.ADM1, GeoKeys.Entry.LON))
        place.georow_list.clear()
        distance_cutoff = 0.5  # Value to determine if two lat/longs are similar

        # Create a dummy 'previous' row so first comparison works
        prev_geo_row = self.geo_files.geodb.make_georow(name='q', iso='q', adm1='q', adm2='q', lat=900, lon=900, feat='q', geoid='q', sdx='q')
        idx = 0

        # Create new list without dupes (adjacent items with same name and same lat/lon)
        # Find if two items with same name are similar lat/lon (within Box Distance of 0.5 degrees)
        #self.logger.debug('===== BUILD RESULT =====')
        for geo_row in list_copy:
            if self.validate_year_for_location(event_year, geo_row[GeoKeys.Entry.ISO], geo_row[GeoKeys.Entry.ADM1], 80) is False:
                # Skip location if location name  didnt exist at the time of event WITH 80 years padding
                continue

            if self.validate_year_for_location(event_year, geo_row[GeoKeys.Entry.ISO], geo_row[GeoKeys.Entry.ADM1], 0) is False:
                # Flag if location name  didnt exist at the time of event
                date_filtered = True

            new_row = list(geo_row)
            geo_row = tuple(new_row)
            self.logger.debug(f'{geo_row[GeoKeys.Entry.NAME]},{geo_row[GeoKeys.Entry.FEAT]} '
                              f'{geo_row[GeoKeys.Entry.SCORE]:.1f} {geo_row[GeoKeys.Entry.ADM2]}, '
                              f'{geo_row[GeoKeys.Entry.ADM1]} {geo_row[GeoKeys.Entry.ISO]}')

            if geo_row[GeoKeys.Entry.NAME] != prev_geo_row[GeoKeys.Entry.NAME]:
                # Name is different.  Add previous item
                place.georow_list.append(geo_row)
                idx += 1
            elif abs(float(prev_geo_row[GeoKeys.Entry.LAT]) - float(geo_row[GeoKeys.Entry.LAT])) + \
                    abs(float(prev_geo_row[GeoKeys.Entry.LON]) - float(geo_row[GeoKeys.Entry.LON])) > distance_cutoff:
                # Lat/lon is different from previous item. Add this one
                place.georow_list.append(geo_row)
                idx += 1
            elif self.get_priority(geo_row[GeoKeys.Entry.FEAT]) < self.get_priority(prev_geo_row[GeoKeys.Entry.FEAT]):
                # Same Lat/lon but this has higher feature priority so replace previous entry
                place.georow_list[idx - 1] = geo_row

            prev_geo_row = geo_row

        min_score = 9999
        new_list = sorted(place.georow_list, key=itemgetter(GeoKeys.Entry.SCORE, GeoKeys.Entry.ADM1, GeoKeys.Entry.ADM2))
        place.georow_list.clear()

        for rw, geo_row in enumerate(new_list):
            # if rw==0:
            #   place.prefix = geo_row[GeoKeys.Entry.PREFIX].title()
            #  place.prefix = place.prefix.strip(' ')
            score = geo_row[GeoKeys.Entry.SCORE]
            if score < min_score:
                min_score = score
            #self.logger.debug(f'Score {score:.2f}  {geo_row[GeoKeys.Entry.NAME]}, {geo_row[GeoKeys.Entry.ADM2]}, {geo_row[GeoKeys.Entry.ADM1]}')
            if score > min_score + 15 or score > 88:
                break
            place.georow_list.append(geo_row)

        if min_score < 20 and len(place.georow_list) == 1:
            place.result_type = GeoKeys.Result.STRONG_MATCH

        return ResultFlags(limited=limited_flag, filtered=date_filtered)

    @staticmethod
    def get_priority(feature):
        f_prior = feature_priority.get(feature)
        if f_prior is None:
            f_prior = 1

        return (22.0 - float(f_prior) )/ 6.0

    @staticmethod
    def get_type_name(feature):
        nm = type_name.get(feature)
        if nm is None:
            nm = ''
        return nm

    @staticmethod
    def get_district1_type(iso) -> str:
        # Return the local country term for Admin1 district
        if iso in ["al"]:
            return "County"
        elif iso in ["us", "at", "bm", "br", "de"]:
            return "State"
        elif iso in ["ac", "an", 'ao', 'bb', 'bd']:
            return "Parish"
        elif iso in ["ae"]:
            return "Emirate"
        elif iso in ["bc", "bf", "bh", "bl", "bn"]:
            return "District"
        elif iso in ["gb"]:
            return "Country"
        else:
            return "Province"


default = ["ADM1", "ADM2", "ADM3", "ADM4", "ADMF", "CH", "CSTL", "CMTY", "EST ", "HSP",
           "HSTS", "ISL", "MSQE", "MSTY", "MT", "MUS", "PAL", "PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4",
           "PPLC", "PPLG", "PPLH", "PPLL", "PPLQ", "PPLX", "PRK", "PRN", "PRSH", "RUIN", "RLG", "STG", "SQR", "SYG", "VAL"]

# If there are 2 identical entries, we only add the one with higher feature priority.  Highest value is for large city or capital
feature_priority = {'PP1M':22, 'PP1K':19, 'ADM1': 20, 'PPLA': 20, 'PPL': 18, 'PPLA2': 19, 'PPLA3': 17, 'PPLA4': 16, 'PPLC': 20, 'PPLG': 15,
'ADM2': 19, 'MILB': 13,'NVB': 12, 'PPLF': 11, 'DEFAULT': 3, 'ADM0': 10, 'PPLL': 6, 'PPLQ': 5, 'PPLR': 4, 'PPLS': 3, 'PPLW': 3, 'PPLX': 3, 'BTL': 3,
                    'STLMT': 1, 'CMTY': 4, 'VAL': 1, 'CH': 4, 'MSQE': 4}

result_text_list = {
    GeoKeys.Result.STRONG_MATCH: 'Matched! Click Save to accept:',
    GeoKeys.Result.MULTIPLE_MATCHES: ' Multiple matches.  Select one and click Verify or Double-Click',
    GeoKeys.Result.NO_MATCH: 'Not found.  Edit and click Verify.',
    GeoKeys.Result.NOT_SUPPORTED: ' Country is not supported. Skip or Add Country in Config',
    GeoKeys.Result.NO_COUNTRY: 'No Country found.',
    GeoKeys.Result.PARTIAL_MATCH: 'Partial match.  Click Save to accept:',
    GeoKeys.Result.DELETE: 'Empty.  Click Save to delete entry.',
    GeoKeys.Result.WILDCARD_MATCH: 'Wildcard match. Click Save to accept:',
    GeoKeys.Result.SOUNDEX_MATCH: 'Soundex match. Click Save to accept:',
}

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

type_name = {"ADM0":'Country', "ADM1":'City', "ADM2":'City', "ADM3":'City', "ADM4":'City', "ADMF":'City',
             "CH":'Church', "CSTL":'Castle', "CMTY":'Cemetery', "EST":'Estate', "HSP":'Hospital',
           "HSTS":'Historic', "ISL":'Island', "MSQE":'Mosque', "MSTY":'Monastery', "MT":'Mountain', "MUS":'Museum', "PAL":'Palace',
             "PPL":'City', "PPLA":'City', "PPLA2":'City', "PPLA3":'City', "PPLA4":'City',
           "PPLC":'City', "PPLG":'City', "PPLH":'City', "PPLL":'Village', "PPLQ":'City', "PPLX":'City',
            "PRK":'Park', "PRN":'Prison', "PRSH":'Parish', "RUIN":'Ruin',
            "RLG":'Religious', "STG":'', "SQR":'Square', "SYG":'Synagogue', "VAL":'Valley', "PP1M":'City', "PP1K":'City'}
