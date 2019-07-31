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
import string as st
from typing import List, Tuple

from geofinder import GeoKeys


class Place:
    """
    Holds the details about a Place: Name, county, state/province, country, lat/long as well as lookup result details
    Parses a name into Place items (county, state, etc)
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

        # Lookup result info
        self.status: str = ""
        self.status_detail: str = ""
        self.result_type: int = GeoKeys.Result.NO_MATCH  # Result type of lookup
        self.result_type_text: str = ''  # Text version of result type
        self.georow_list: List[Tuple] = [()]  # List of items that matched this location

        self.georow_list.clear()

    def parse_place(self, place_name: str, geo_files):
        """
        Given a comma separated place name, parse into its city, AdminID, country_iso and type of entity (city, country etc)
        Expected format: prefix,city,admin2,admin1,country
        Place.status has Result status code
        """
        self.clear()
        self.name = place_name

        tokens = place_name.split(",")
        token_count = len(tokens)
        self.place_type = PlaceType.CITY

        # Parse City, Admin2, Admin2, Country scanning from the right.  When there are more tokens, we capture more fields
        # Place type is the leftmost item we found - either City, Admin2, Admin2, or Country

        #  COUNTRY - right-most token should be country
        if token_count > 0:
            #  Format: Country
            self.place_type = PlaceType.COUNTRY
            self.country_name = GeoKeys.normalize(tokens[-1])

            # Validate country
            self.country_iso = geo_files.geodb.get_country_iso(self)  # Get Country country_iso
            if self.country_iso is '':
                # Not found.  See if rightmost token is actually Admin1 (state/province).  Look up admin1 and derive its country
                save_admin1 = self.admin1_name
                self.admin1_name = GeoKeys.normalize(self.country_name)

                # Lookup last token as admin1.  This will fill in country ISO if admin1 is found
                geo_files.geodb.get_admin1_id(self)
                self.admin1_name = save_admin1  # Restore Admin1

                if self.country_iso is not None:
                    # We found the country.  Append it to token list so we now have xx,admin1, country
                    tokens.append(geo_files.geodb.get_country_name(self.country_iso))
                    self.country_name = tokens[-1].strip(' ').lower()
                    token_count = len(tokens)
                else:
                    # No country found for this
                    # Append blank to token list so we now have xx,admin1, blank_country
                    self.logger.debug(f'didnt find last tkn as adm1 {self.admin1_name}')
                    tokens.append('')
                    self.country_name = ''
                    token_count = len(tokens)
                    self.result_type = GeoKeys.Result.NO_COUNTRY
                    self.country_iso = ''

            self.target = self.country_name

        if token_count > 1:
            #  Format: Admin1, Country.
            #  Admin1 is 2nd to last token
            self.admin1_name = GeoKeys.normalize(tokens[-2])
            if len(self.admin1_name) > 0:
                self.place_type = PlaceType.ADMIN1
                self.target = self.admin1_name

        if token_count > 2:
            #  Format: Admin2, Admin1, Country
            #  Admin2 is 3rd to last.  Note -  if Admin2 isnt found, it will look it up as city
            self.admin2_name = GeoKeys.normalize(tokens[-3])
            if len(self.admin2_name) > 0:
                self.place_type = PlaceType.ADMIN2
                if self.admin2_name == 'london':
                    # Change to Greater London
                    self.admin2_name = 'greater london'
                self.target = self.admin2_name
            # else:
            #    self.place_type = PlaceType.CITY

        if token_count > 3:
            # Format: Prefix, City, Admin2, Admin1, Country
            # City is 4th to last token
            # Other tokens go into Prefix
            self.city1 = GeoKeys.normalize(tokens[-4])
            if len(self.city1) > 0:
                self.place_type = PlaceType.CITY
                self.target = self.city1

            # Assign remaining tokens (if any) to prefix
            for item in tokens[0:-4]:
                if len(self.prefix) > 0:
                    self.prefix += ' '
                self.prefix += item.strip(' ')

            # self.prefix.strip(' ')

        # Special case for New York, New York which normally refers to the City, not county
        if self.admin2_name == 'new york' and self.place_type == PlaceType.ADMIN2:
            self.admin2_name = 'new york city'
            self.target = self.admin2_name

        self.logger.debug(f"*** PARSE  #={token_count} City [{self.city1}] Adm2 [{self.admin2_name}]"
                          f"  Adm1 [{self.admin1_name}] Cntry [{self.country_name}] Pref=[{self.prefix}] Com=[{self.prefix_commas}]"
                          f" Typ={place_type_name_dict[self.place_type]}")
        return

    def set_place_type(self):
        self.place_type = PlaceType.CITY
        if len(self.country_name) > 0:
            self.place_type = PlaceType.COUNTRY
        if len(self.admin1_name) > 0:
            self.place_type = PlaceType.ADMIN1
        if len(self.admin2_name) > 0:
            self.place_type = PlaceType.ADMIN2
        if len(self.city1) > 0:
            self.place_type = PlaceType.CITY

    def get_status(self) -> str:
        return self.status

    def format_full_name(self):
        """ Take the parts of a Place and build fullname.  e.g. pref, city,adm2,adm1,country name """
        self.set_place_type()
        self.prefix = self.prefix.strip(',')

        if self.admin1_name is None:
            self.admin1_name = ''
        if self.admin2_name is None:
            self.admin2_name = ''

        if self.place_type == PlaceType.COUNTRY:
            nm = f"{st.capwords(self.country_name)}"
            self.prefix_commas = ', , , , '
        elif self.place_type == PlaceType.ADMIN1:
            nm = f" {st.capwords(self.admin1_name)}, {st.capwords(self.country_name)}"
            self.prefix_commas = ', , , '
        elif self.place_type == PlaceType.ADMIN2:
            nm = f"{st.capwords(self.admin2_name)}," \
                f" {st.capwords(self.admin1_name)}, {st.capwords(self.country_name)}"
            self.prefix_commas = ', , '
        else:
            nm = f"{st.capwords(self.city1)}, {st.capwords(self.admin2_name)}, " \
                f"{st.capwords(self.admin1_name)}, {st.capwords(str(self.country_name))}"
            self.prefix_commas = ', '

        if len(self.prefix) == 0:
            self.prefix_commas = ''
        # self.logger.debug(f' [{self.prefix}][{self.prefix_commas}][{nm}]')
        return nm


# What type of entity is this place?
class PlaceType:
    COUNTRY = 0
    ADMIN1 = 1
    ADMIN2 = 2
    CITY = 3


place_type_name_dict = {
    PlaceType.COUNTRY: 'Country',
    PlaceType.ADMIN1: 'STATE/PROVINCE',
    PlaceType.ADMIN2: 'COUNTY',
    PlaceType.CITY: ' '
}
