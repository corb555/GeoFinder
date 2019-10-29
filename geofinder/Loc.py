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
import string as st
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
        self.name: str = ""
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
        self.feature: str = ''  # Geoname feature code
        self.place_type: int = PlaceType.COUNTRY  # Is this a Country , Admin1 ,admin2 or city?
        self.target: str = ''  # Target for lookup
        self.geoid: str = ''
        self.prefix_commas: str = ''
        self.id = ''
        self.enclosed_by = ''

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

    def parse_place(self, place_name: str, geo_files):
        """
        Given a comma separated place name, parse into its city, AdminID, country_iso and type of entity (city, country etc)
        Expected format: prefix,city,admin2,admin1,country
        self.status has Result status code
        """
        self.clear()
        self.name = place_name

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
            self.country_name = re.sub(r'\.', '', self.country_name)  # remove .
            if self.country_name == 'USA':
                self.country_name = 'United States'
            self.target = self.country_name

            # Validate country
            self.country_iso = geo_files.geodb.get_country_iso(self)  # Get Country country_iso
            if self.country_iso != '':
                # self.logger.debug(f'Found country. iso = [{self.country_iso}]')
                pass
            else:
                # Last token is not COUNTRY.
                # self.logger.debug(f'last tkn [{self.admin1_name}] is not a country ')

                # Append blank to token list so we now have xx,admin1, blank_country
                # self.admin1_name = save_admin1  # Restore Admin1 field
                tokens.append('')
                token_count = len(tokens)
                self.result_type = GeoKeys.Result.NO_COUNTRY
                self.country_iso = ''
                self.country_name = ''

        if token_count > 1:
            #  Format: Admin1, Country.
            #  Admin1 is 2nd to last token
            self.admin1_name = GeoKeys.search_normalize(tokens[-2], self.country_iso)
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

        if token_count > 2:
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

            # Assign remaining tokens (if any) to prefix
            for item in tokens[0:-4]:
                if len(self.prefix) > 0:
                    self.prefix += ' '
                self.prefix += str(item.strip(' '))

        # Special case for New York, New York which normally refers to the City, not county
        if self.admin2_name == 'new york' and self.place_type == PlaceType.ADMIN2:
            self.admin2_name = 'new york city'
            self.target = self.admin2_name

        self.logger.debug(f"***** PARSE: {place_name} City [{self.city1}] Adm2 [{self.admin2_name}]"
                          f" Adm1 [{self.admin1_name}] adm1_id [{self.admin1_id}] Cntry [{self.country_name}] Pref=[{self.prefix}]"
                          f" type_id={self.place_type}")
        return

    def get_status(self) -> str:
        self.logger.debug(f'status=[{self.status}]')
        return self.status

    def clean(self):
        self.city1 = str(self.city1)
        self.admin1_name = str(self.admin1_name)
        self.admin2_name = str(self.admin2_name)
        self.prefix = str(self.prefix)

    def format_full_nm(self, replace_dct):
        """ Take the parts of a Place and build fullname.  e.g. pref, city,adm2,adm1,country name """
        self.set_place_type()
        self.prefix = self.prefix.strip(',')

        if self.admin1_name is None:
            self.admin1_name = ''
        if self.admin2_name is None:
            self.admin2_name = ''

        """
        if self.place_type == PlaceType.COUNTRY:
            nm = f"{st.capwords(self.country_name)}"
        elif self.place_type == PlaceType.ADMIN1:
            nm = f"{st.capwords(self.admin1_name)}, {st.capwords(self.country_name)}"
        elif self.place_type == PlaceType.ADMIN2:
            nm = f"{st.capwords(self.admin2_name)}," \
                f" {st.capwords(self.admin1_name)}, {st.capwords(self.country_name)}"
        else:
            nm = f"{st.capwords(self.city1)}, {st.capwords(self.admin2_name)}, " \
                f"{st.capwords(self.admin1_name)}, {st.capwords(str(self.country_name))}"
        """
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

        nm = st.capwords(nm)
        #nm = re.sub("S ", "s ", nm)  # Fix the apostrophe S problem in Titles
        nm = re.sub(r"D.c.", "D.C.", nm)

        self.prefix = st.capwords(self.prefix)


        # Perform any text replacements user entered into Output Tab
        if replace_dct:
            for key in replace_dct:
                nm = re.sub(key, replace_dct[key], nm)

        return nm

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
