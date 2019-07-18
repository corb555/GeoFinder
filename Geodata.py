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

import GeoKeys
import GeodataFiles
import Place


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

    def find_first_match(self, location: st, place: Place.Place):
        """
        Find the first match for this location in the geoname dictionary.
        First parse the location into <prefix>, city, <district2>, district1, country.
        Then look it up in the place db
        Update place with -- lat, lon, district, city, country_iso, result code
        """
        # todo add unit test
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

    def find_location(self, location: str, place: Place.Place):
        """
        Find a location in the geoname dictionary.
        First parse the location into <prefix>, city, <district2>, district1, country.
        Then look it up in the place dictionary
        Update place with -- lat, lon, district, city, country_iso, result code
        """
        place.parse_place(place_name=location, geo_files=self.geo_files)

        if self.country_is_valid(place):
            #place.country_name = self.geo_files.country.get_name(place.country_iso)
            self.logger.debug(f'Find LOCATION Type=[{Place.place_type_name_dict[place.place_type]}] City=[{place.city1}] Adm2=[{place.admin2_name}]\
    Adm1=[{place.admin1_name}] Prefix=[{place.prefix}] cname=[{place.country_name}] iso=[{place.country_iso}]')
            # Lookup location
            self.geo_files.geodb.lookup_place(place=place)
        else:
            place.target = place.country_name

        # Process the results
        self.process_result(place=place, targ_name=place.target)

    def process_result(self, place: Place.Place, targ_name) -> None:
        # Copy geodata to place record and Put together status text
        self.logger.debug(f'**PROCESS RESULT:  Type={place.type_text}.  Geoid_list={place.georow_list}')
        if place.result_type in GeoKeys.successful_match:
            self.geo_files.geodb.get_geodata(row=place.georow_list[0], place=place)

        self.set_place_type(place=place)
        place._status = f'{place.type_text} "{st.capwords(targ_name)}" {result_text_list.get(place.result_type)} '

    def set_place_type(self, place: Place.Place):
        if place.result_type == GeoKeys.Result.NO_COUNTRY:
            place.type_text = 'Country'
        if place.place_type == Place.PlaceType.CITY:
            place.type_text = GeoKeys.type_names.get(place.feature)
            if place.type_text is None:
                place.type_text = 'City/Place'
        elif place.place_type == Place.PlaceType.ADMIN1:
            place.type_text = self.get_district1_type(place.country_iso)
        else:
            place.type_text = Place.place_type_name_dict[place.place_type]
        # self.logger.debug(f'Set Type feat={place.feature} Type={place.type_text}')

    @staticmethod
    def get_district1_type(iso) -> str:
        # Return the local country term for Admin1 district
        if iso in ["al", "ie"]:
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

    def read(self) -> bool:
        """ Read in geo name files which contain place names and their lat/lon.
            Return True if error
        """
        #err: bool = self.geo_files.country.read()
        #if err:
        #    self.status = "country country_iso list error"
        #    return True

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

result_text_list = {
    GeoKeys.Result.EXACT_MATCH: 'matched! Click Save to accept:',
    GeoKeys.Result.MULTIPLE_MATCHES: 'had multiple matches.  Select one and click Verify.',
    GeoKeys.Result.NO_MATCH: 'not found.  Edit and click Verify.',
    GeoKeys.Result.NOT_SUPPORTED: ' is not supported.',
    GeoKeys.Result.NO_COUNTRY: 'No Country found.',
    GeoKeys.Result.PARTIAL_MATCH: 'partial match.  Click Save to accept:'
}


