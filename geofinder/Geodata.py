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
import string as st
from operator import itemgetter

from geofinder import GeodataFiles, GeoKeys, Place


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

    def find_location(self, location: str, place: Place.Place):
        """
        Find a location in the geoname dictionary.
        First parse the location into <prefix>, city, <district2>, district1, country.
        Then look it up in the place dictionary
        Update place with -- lat, lon, district, city, country_iso, result code
        """
        place.parse_place(place_name=location, geo_files=self.geo_files)

        if self.country_is_valid(place):
            self.logger.debug(f'Find LOCATION Type=[{Place.place_type_name_dict[place.place_type]}] City=[{place.city1}] Adm2=[{place.admin2_name}]\
    Adm1=[{place.admin1_name}] Prefix=[{place.prefix}] cname=[{place.country_name}] iso=[{place.country_iso}]')
            # Lookup location
            self.geo_files.geodb.lookup_place(place=place)
        else:
            place.target = place.country_name
            # No country - try city lookup without country
            if len(place.admin1_name) > 0 and place.result_type is not GeoKeys.Result.NOT_SUPPORTED:
                self.geo_files.geodb.lookup_place(place=place)
                if len(place.georow_list) == 0:
                    place.result_type = GeoKeys.Result.NO_COUNTRY
            else:
                self.process_result(place=place, targ_name=place.target)
                return

        if len(place.georow_list) > 0:
            self.build_result_list(place.georow_list, place.event_year)

        if len(place.georow_list) == 0:
            place.result_type = GeoKeys.Result.NO_MATCH
        elif len(place.georow_list) > 1:
            self.logger.debug(f'mult matches {len(place.georow_list)}')
            place.result_type = GeoKeys.Result.MULTIPLE_MATCHES

        # Process the results
        self.process_result(place=place, targ_name=place.target)
        self.logger.debug(f'Status={place.status}')

    def process_result(self, place: Place.Place, targ_name) -> None:
        # Copy geodata to place record and Put together status text
        self.logger.debug(f'**PROCESS RESULT:  Res={place.result_type}  Georow_list={place.georow_list}')
        if place.result_type in GeoKeys.successful_match:
            self.geo_files.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)

        self.set_place_type_text(place=place)
        place.status = f'{place.result_type_text} "{st.capwords(targ_name)}" {result_text_list.get(place.result_type)} '

    def set_place_type_text(self, place: Place.Place):
        if place.result_type == GeoKeys.Result.NO_COUNTRY:
            place.result_type_text = 'Country'
        if place.place_type == Place.PlaceType.CITY:
            place.result_type_text = GeoKeys.type_names.get(place.feature)
            if place.result_type_text is None:
                place.result_type_text = ' '
        elif place.place_type == Place.PlaceType.ADMIN1:
            place.result_type_text = self.get_district1_type(place.country_iso)
        else:
            place.result_type_text = Place.place_type_name_dict[place.place_type]

    def find_first_match(self, location: st, place: Place.Place):
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
            place.result_type = GeoKeys.Result.EXACT_MATCH

        self.process_result(place=place, targ_name=place.target)

    def find_geoid(self, geoid: str, place: Place.Place):
        place.target = geoid
        self.geo_files.geodb.lookup_geoid(place=place)
        if len(place.georow_list) > 0:
            # Copy geo row to Place
            self.geo_files.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)

    @staticmethod
    def get_district1_type(iso) -> str:
        # Return the local country term for Admin1 district
        if iso in ["al", "ie"]:
            return "COUNTY"
        elif iso in ["us", "at", "bm", "br", "de"]:
            return "STATE"
        elif iso in ["ac", "an", 'ao', 'bb', 'bd']:
            return "PARISH"
        elif iso in ["ae"]:
            return "EMIRATE"
        elif iso in ["bc", "bf", "bh", "bl", "bn"]:
            return "DISTRICT"
        elif iso in ["gb"]:
            return "Country"
        else:
            return "PROVINCE"

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

    @staticmethod
    def get_directory_name() -> st:
        return "geoname_data"

    def progress(self, msg: st, percent: int):
        if self.progress_bar is not None:
            self.progress_bar.update_progress(percent, msg)
        else:
            self.logger.debug(msg)

    def country_is_valid(self, place: Place) -> bool:
        # See if COUNTRY is present and is in the supported country list
        if place.country_iso == '':
            place.result_type = GeoKeys.Result.NO_COUNTRY
            is_valid = False
        elif place.country_iso not in self.geo_files.supported_countries_dct:
            place.result_type = GeoKeys.Result.NOT_SUPPORTED
            place.place_type = Place.PlaceType.COUNTRY
            is_valid = False
        else:
            is_valid = True

        return is_valid

    def validate_year_for_location(self, event_year: int, iso: str, admin1: str) -> bool:
        # See if this location name was valid at the time of the event
        # Try looking up start year by state/province
        start_year = admin1_name_start_year.get(f'{iso}.{admin1.lower()}')
        if start_year is None:
            # Try looking up start year by country
            start_year = country_name_start_year.get(iso)
        if start_year is None:
            start_year = -1

        if event_year < start_year and event_year != 0:
            self.logger.debug(f'Val year:  loc year={start_year}  event yr={event_year} loc={admin1},{iso}')
            return False
        else:
            return True

    def build_result_list(self, georow_list, event_year: int):
        # Create a sorted version of result_list without any dupes
        # Add note if we hit the lookup limit
        # Discard location names that didnt exist at time of event
        if len(georow_list) > 299:
            georow_list.append(self.geo_files.geodb.make_georow(name='(plus more...)', iso='US', adm1=' ', adm2=' ', feat='Q0', lat=99.9, lon=99.9,
                                                                geoid='q'))

        # sort list by State/Province id, and County id
        list_copy = sorted(georow_list, key=itemgetter(GeoKeys.Entry.ADM1, GeoKeys.Entry.ADM2))
        georow_list.clear()
        distance_cutoff = 0.5  # Value to determine if two lat/longs are similar

        # Create a dummy 'previous' row so first comparison works
        prev_geo_row = self.geo_files.geodb.make_georow(name='q', iso='q', adm1='q', adm2='q', lat=900, lon=900, feat='q', geoid='q')
        idx = 0
        date_filtered = ''

        # Create new list without dupes (adjacent items with same name and same lat/lon)
        # Find if two items with same name are similar lat/lon (within Box Distance of 0.5 degrees)
        for geo_row in list_copy:
            if self.validate_year_for_location(event_year, geo_row[GeoKeys.Entry.ISO], geo_row[GeoKeys.Entry.ADM1]) is False:
                # Skip location if location name  didnt exist at the time of event
                date_filtered += f'[{geo_row[GeoKeys.Entry.ADM1]}, {geo_row[GeoKeys.Entry.ISO]}] '
                continue

            if geo_row[GeoKeys.Entry.NAME] != prev_geo_row[GeoKeys.Entry.NAME]:
                # Name is different.  Add previous item
                georow_list.append(geo_row)
                idx += 1
            elif abs(float(prev_geo_row[GeoKeys.Entry.LAT]) - float(geo_row[GeoKeys.Entry.LAT])) + \
                    abs(float(prev_geo_row[GeoKeys.Entry.LON]) - float(geo_row[GeoKeys.Entry.LON])) > distance_cutoff:
                # Lat/lon is different from previous item. Add this one
                georow_list.append(geo_row)
                idx += 1
            elif self.get_priority(geo_row[GeoKeys.Entry.FEAT]) > self.get_priority(prev_geo_row[GeoKeys.Entry.FEAT]):
                # Same Lat/lon but this has higher feature priority so replace previous entry
                georow_list[idx - 1] = geo_row

            prev_geo_row = geo_row

    @staticmethod
    def get_priority(feature):
        prior = feature_priority.get(feature)
        if prior is None:
            return 1
        else:
            return prior


# If there are 2 identical entries, we only add the one with higher feature priority.  Highest value is for large city or capital
feature_priority = {'ADM1': 22, 'PPL': 21, 'PPLA': 20, 'PPLA2': 19, 'PPLA3': 18, 'PPLA4': 17, 'PPLC': 16, 'PPLG': 15, 'ADM2': 14, 'MILB': 13,
                    'NVB': 12,
                    'PPLF': 11, 'DEFAULT': 10, 'ADM0': 10, 'PPLL': 10, 'PPLQ': 9, 'PPLR': 8, 'PPLS': 7, 'PPLW': 6, 'PPLX': 5, 'BTL': 4,
                    'PPLCH': 3,
                    'PPLH': 2, 'STLMT': 1, 'CMTY': 1, 'VAL': 1}

result_text_list = {
    GeoKeys.Result.EXACT_MATCH: 'matched! Click Save to accept:',
    GeoKeys.Result.MULTIPLE_MATCHES: 'had multiple matches.  Select one and click Verify.',
    GeoKeys.Result.NO_MATCH: 'not found.  Edit and click Verify.',
    GeoKeys.Result.NOT_SUPPORTED: ' is not supported. Skip or add in GeoUtil.py',
    GeoKeys.Result.NO_COUNTRY: 'No Country found.',
    GeoKeys.Result.PARTIAL_MATCH: 'partial match.  Click Save to accept:'
}

# Starting year this country name was valid
country_name_start_year = {
    'cu': -1,
}

# Starting year this state/province name was valid
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
