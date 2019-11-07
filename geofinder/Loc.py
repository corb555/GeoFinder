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
import argparse
import logging
import re
from typing import List, Tuple

from geofinder import GeoKeys
from geofinder.ArgumentParserNoExit import ArgumentParserNoExit

default_country = 'nederland'


# What type of entity is this place?
class PlaceType:
    COUNTRY = 0
    ADMIN1 = 1
    ADMIN2 = 2
    CITY = 3
    PREFIX = 4
    ADVANCED_SEARCH = 5


place_type_name_dict = {
    PlaceType.COUNTRY: 'Country',
    PlaceType.ADMIN1: 'STATE/PROVINCE',
    PlaceType.ADMIN2: 'COUNTY',
    PlaceType.CITY: ' ',
    PlaceType.ADVANCED_SEARCH: ' '
}


class Loc:
    """
    Holds the details about a Location: Name, county, state/province, country, lat/long as well as lookup result details
    Parses a name into Loc items (county, state, etc)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.clear()
        self.event_year: int = 0

    def clear(self):
        # Place geo info
        self.original_entry: str = ""
        self.formatted_name: str = ''
        self.lat: float = float('NaN')  # Latitude
        self.lon: float = float('NaN')  # Longitude
        self.country_iso: str = ""  # Country ISO code
        self.country_name: str = ''
        self.city1: str = ""  # City or entity name
        self.admin1_name: str = ""  # Admin1 (State/province/etc)
        self.admin2_name: str = ""  # Admin2 (county)
        self.admin1_id: str = ""  # Admin1 Geoname ID
        self.admin2_id = ""  # Admin2 Geoname ID
        self.prefix: str = ""  # Prefix (entries before city)
        self.extra: str = ''  # Extra tokens that dont get put in prefix
        self.feature: str = ''  # Geoname feature code
        self.place_type: int = PlaceType.COUNTRY  # Is this a Country , Admin1 ,admin2 or city?
        self.target: str = ''  # Target for lookup
        self.geoid: str = ''
        self.prefix_commas: str = ''
        self.id = ''
        self.enclosed_by = ''
        self.standard_parse = True

        # Lookup result info
        self.status: str = ""
        self.status_detail: str = ""
        self.result_type: int = GeoKeys.Result.NO_MATCH  # Result type of lookup
        self.result_type_text: str = ''  # Text version of result type
        self.georow_list: List[Tuple] = [()]  # List of items that matched this location

        self.georow_list.clear()

    def filter(self, place_name, geo_files):
        # Advanced search parameters
        # Separate out arguments
        tokens = place_name.split(",")
        args = []
        for tkn in tokens:
            if '--' in tkn:
                args.append(tkn.strip(' '))

        # Parse options in place name
        parser = ArgumentParserNoExit(description="Parses command.")
        parser.add_argument("-f", "--feature", help=argparse.SUPPRESS)
        parser.add_argument("-i", "--iso", help=argparse.SUPPRESS)
        parser.add_argument("-c", "--country", help=argparse.SUPPRESS)
        try:
            options = parser.parse_args(args)
            self.city1 = GeoKeys.search_normalize(tokens[0], self.country_iso)
            self.target = self.city1
            if options.iso:
                self.country_iso = options.iso.lower()
            if options.country:
                self.country_iso = options.country.lower()
            if options.feature:
                self.feature = options.feature.upper()
            self.place_type = PlaceType.ADVANCED_SEARCH
        except Exception as e:
            self.logger.debug(e)
        self.logger.debug(f'ADV SEARCH: targ={self.city1} iso={self.country_iso} feat={self.feature} typ={self.place_type}')

    def parse_place(self, place_name: str, geo_files):
        """
        Given a comma separated place name, parse into its city, AdminID, country_iso and type of entity (city, country etc)
        Expected format: prefix,city,admin2,admin1,country
        self.status has Result status code
        """
        self.clear()
        self.original_entry = place_name

        # Convert open-brace and open-paren to comma.  close brace/paren will be stripped by normalize()
        res = re.sub('\[', ',', place_name)
        res = re.sub('\(', ',', res)

        tokens = res.split(",")
        token_count = len(tokens)
        self.place_type = PlaceType.CITY

        # Parse City, Admin2, Admin2, Country scanning from the right.  When there are more tokens, we capture more fields
        # Place type is the leftmost item we found - either City, Admin2, Admin2, or Country
        # self.logger.debug(f'***** PLACE [{place_name}] *****')

        if '--' in place_name:
            # Pull out filter flags if present
            self.logger.debug('filter')
            self.filter(place_name, geo_files)
            return
        elif token_count > 0:
            #  COUNTRY - right-most token should be country
            #  Format: Country
            self.place_type = PlaceType.COUNTRY
            self.country_name = GeoKeys.search_normalize(tokens[-1], "")
            self.target = self.country_name

            # Validate country
            self.country_iso = geo_files.geodb.get_country_iso(self)  # Get Country country_iso
            if self.country_iso != '':
                # self.logger.debug(f'Found country. iso = [{self.country_iso}]')
                pass
            else:
                # Last token is not COUNTRY.
                # Append blank to token list so we now have xx,admin1, blank_country
                tokens.append('')
                token_count = len(tokens)
                self.result_type = GeoKeys.Result.NO_COUNTRY
                self.country_iso = ''
                self.country_name = ''

        if token_count > 1:
            #  Format: Admin1, Country.
            #  Admin1 is 2nd to last token
            self.admin1_name = GeoKeys.search_normalize(tokens[-2], self.country_iso)
            self.admin1_name = GeoKeys.admin1_normalize(self.admin1_name, self.country_iso)

            if len(self.admin1_name) > 0:
                self.place_type = PlaceType.ADMIN1
                self.target = self.admin1_name
                # Lookup Admin1
                geo_files.geodb.get_admin1_id(self)
                if self.admin1_id != '':
                    # self.logger.debug(f'Found admin1 {self.admin1_name}')
                    pass
                else:
                    # Last token is not Admin1 - append blank
                    self.admin1_name = ''
                    # Append blank token for admin1 position
                    tokens.append('')
                    token_count = len(tokens)

        if token_count == 3 and self.admin1_name == '' and self.country_name == '':
            # Just one valid token, so take as city
            self.city1 = GeoKeys.search_normalize(tokens[-3], self.country_iso)
            if len(self.city1) > 0:
                self.place_type = PlaceType.CITY
                self.target = self.city1
        elif token_count > 2:
            #  Format: Admin2, Admin1, Country
            #  Admin2 is 3rd to last.  Note -  if Admin2 isnt found, it will look it up as city
            self.admin2_name = GeoKeys.search_normalize(tokens[-3], self.country_iso)
            if len(self.admin2_name) > 0:
                self.place_type = PlaceType.ADMIN2
                self.target = self.admin2_name

        if token_count > 3:
            # Format: Prefix, City, Admin2, Admin1, Country
            # City is 4th to last token
            # Other tokens go into Prefix
            self.city1 = GeoKeys.search_normalize(tokens[-4], self.country_iso)
            if len(self.city1) > 0:
                self.place_type = PlaceType.CITY
                self.target = self.city1

            # Assign remaining tokens (if any) to prefix.  Zero'th token to 4th from end.
            for item in tokens[0:-4]:
                if len(self.prefix) > 0:
                    self.prefix += ' '
                self.prefix += str(item.strip(' '))

        # Special case for New York, New York which normally refers to the City, not county
        if self.admin2_name == 'new york' and self.place_type == PlaceType.ADMIN2:
            self.admin2_name = 'new york city'
            self.target = self.admin2_name

        self.prefix = self.prefix.strip(',')

        self.logger.debug(f"    ======= PARSE: {place_name} City [{self.city1}] Adm2 [{self.admin2_name}]"
                          f" Adm1 [{self.admin1_name}] adm1_id [{self.admin1_id}] Cntry [{self.country_name}] Pref=[{self.prefix}]"
                          f" type_id={self.place_type}")
        return

    def get_status(self) -> str:
        self.logger.debug(f'status=[{self.status}]')
        return self.status

    def safe_strings(self):
        self.city1 = str(self.city1)
        self.admin1_name = str(self.admin1_name)
        self.admin2_name = str(self.admin2_name)
        self.prefix = str(self.prefix)

    def format_full_nm(self, replace_dct):
        """ Take the parts of a Place and build fullname.  e.g. pref, city,adm2,adm1,country name """
        self.set_place_type()

        if self.admin1_name is None:
            self.admin1_name = ''
        if self.admin2_name is None:
            self.admin2_name = ''

        if self.place_type == PlaceType.COUNTRY:
            nm = f"{self.country_name}"
        elif self.place_type == PlaceType.ADMIN1:
            nm = f"{self.admin1_name}, {self.country_name}"
        elif self.place_type == PlaceType.ADMIN2:
            nm = f"{self.admin2_name}, {self.admin1_name}, {self.country_name}"
        else:
            nm = f"{self.city1}, {self.admin2_name}, {self.admin1_name}, {str(self.country_name)}"

        if self.prefix in nm:
            self.prefix = ''

        if len(self.prefix) > 0:
            self.prefix_commas = ', '
        else:
            self.prefix_commas = ''

        nm = GeoKeys.capwords(nm)

        # Perform any text replacements user entered into Output Tab
        if replace_dct:
            for key in replace_dct:
                nm = re.sub(key, replace_dct[key], nm)

        return nm

    def get_five_part_title(self):
        # Returns a five part title string and tokenized version:
        #     prefix,city,county,state,country

        # Force type to City to generate four part title (then we add prefix for five parts)
        save_type = self.place_type
        self.place_type = PlaceType.CITY

        # Normalize country name
        save_country = self.country_name
        self.country_name, modified = GeoKeys.country_normalize(self.country_name)

        if len(self.extra) > 0:
            full_title = self.prefix + ' ' + self.extra + ',' + self.format_full_nm(None)
        else:
            full_title = self.prefix + ',' + self.format_full_nm(None)

        # Restore values to original
        self.place_type = save_type
        self.country_name = save_country

        return full_title

    def feature_to_type(self):
        # Set place type based on DB response feature code
        if self.feature == 'ADM0':
            self.place_type = PlaceType.COUNTRY
        elif self.feature == 'ADM1':
            self.place_type = PlaceType.ADMIN1
        elif self.feature == 'ADM2':
            self.place_type = PlaceType.ADMIN2
        else:
            self.place_type = PlaceType.CITY
        if len(self.prefix) > 0:
            self.place_type = PlaceType.PREFIX
        return self.place_type

    def set_place_type(self):
        # Set place type based on parsing results
        self.place_type = PlaceType.CITY
        if len(str(self.country_name)) > 0:
            self.place_type = PlaceType.COUNTRY
        if len(self.admin1_name) > 0:
            self.place_type = PlaceType.ADMIN1
        if len(self.admin2_name) > 0:
            self.place_type = PlaceType.ADMIN2
        if len(self.city1) > 0:
            self.place_type = PlaceType.CITY

    def remove_old_fields(self):
        if self.place_type == PlaceType.COUNTRY:
            self.prefix = ''
            self.city1 = ''
            self.admin2_name = ''
            self.admin1_name = ''
        elif self.place_type == PlaceType.ADMIN1:
            self.prefix = ''
            self.city1 = ''
            self.admin2_name = ''
        elif self.place_type == PlaceType.ADMIN2:
            self.prefix = ''
            self.city1 = ''
        elif self.place_type == PlaceType.CITY:
            self.prefix = ''

    def set_place_type_text(self):
        if self.result_type == GeoKeys.Result.NO_COUNTRY:
            self.result_type_text = 'Country'
        elif self.place_type == PlaceType.COUNTRY:
            self.result_type_text = 'Country'
        elif self.place_type == PlaceType.ADMIN1:
            self.result_type_text = self.get_district1_type(self.country_iso)
        elif self.place_type == PlaceType.ADMIN2:
            self.result_type_text = 'County'
        elif self.place_type == PlaceType.CITY:
            self.result_type_text = self.get_type_name(self.feature)
        elif self.place_type == PlaceType.PREFIX:
            self.result_type_text = 'Place'

    @staticmethod
    def get_district1_type(iso) -> str:
        # Return the local country term for Admin1 district
        if iso in ["al", "no"]:
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

    @staticmethod
    def get_type_name(feature):
        nm = type_name.get(feature)
        if nm is None:
            nm = ''
        return nm


type_name = {"ADM0": 'Country', "ADM1": 'City', "ADM2": 'City', "ADM3": 'City', "ADM4": 'City', "ADMF": 'City',
             "CH": 'Church', "CSTL": 'Castle', "CMTY": 'Cemetery', "EST": 'Estate', "HSP": 'Hospital',
             "HSTS": 'Historic', "ISL": 'Island', "MSQE": 'Mosque', "MSTY": 'Monastery', "MT": 'Mountain', "MUS": 'Museum', "PAL": 'Palace',
             "PPL": 'City', "PPLA": 'City', "PPLA2": 'City', "PPLA3": 'City', "PPLA4": 'City',
             "PPLC": 'City', "PPLG": 'City', "PPLH": 'City', "PPLL": 'Village', "PPLQ": 'City', "PPLX": 'City',
             "PRK": 'Park', "PRN": 'Prison', "PRSH": 'Parish', "RUIN": 'Ruin',
             "RLG": 'Religious', "STG": '', "SQR": 'Square', "SYG": 'Synagogue', "VAL": 'Valley', "PP1M": 'City', "PP1K": 'City'}
