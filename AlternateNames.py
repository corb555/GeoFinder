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
import typing
from collections import namedtuple, defaultdict

# The tab separated columns in geoname.org file rows are as follows
import GeoKeys
import GeodataFiles
from FileReader import FileReader
from Place import Place

AltNameRow = namedtuple('AltNameRow', 'name lang geo_id')
GeoDict = defaultdict(typing.List)


class AlternateNames(FileReader):
    """
    Read in alternate names file and add appropriate entries to geoname dictionary
    Each row contains a geoname ID, an alternative name for that entity, and the language
    If the lang is english and the ID is in our geonames dictionary, we add this as an alternative name
    FileReader calls handle_line every time it reads a line
    """

    def __init__(self, directory_name: str, filename: str, progress_bar, geo_files: GeodataFiles):
        super().__init__(directory_name, filename, progress_bar)

        self.cache_changed: bool = False
        self.sub_dir = GeoKeys.cache_directory(self.directory)
        self.geo_files: GeodataFiles.GeodataFiles = geo_files

    def handle_line(self, count, line_num, row):
        place = Place()

        lang_list = ['en']  # Languages we want to support for alternate names

        alt_tokens = row.split('\t')
        if len(alt_tokens) != 10:
            self.logger.debug(f'Incorrect number of tokens: {alt_tokens} line {line_num}')
            return
        alt_data = AltNameRow(lang=alt_tokens[2], name=alt_tokens[3], geo_id=alt_tokens[1])
        # Alternate names are in multiple languages.  Only add if item is an 'en' lang
        if alt_data.lang in lang_list:
            # Add this alias to geoname db if there is already an entry (geoname DB is filtered based on feature)
            geo_rowlist = self.geo_files.get_lookup(alt_data.geo_id)
            if geonames_key is not None:
                typ, iso, name, admin1 = GeoKeys.split_key(geonames_key)
                self.geo_files.get_geodata(geo_id=alt_data.geo_id, place=place)
                # create new key by replacing place name and keeping the rest of the key
                new_key = modify_key(geonames_key=geonames_key, new_name=alt_data.name)
                lat: float = float(place.lat)
                lon: float = float(place.lon)
                new_row = GeodataFiles.GeoRow(name=place.name,
                                              lat=lat, lon=lon, admin1_id=place.admin1_id,
                                              admin2_id=place.admin2_id, f_code=place.feature,
                                              geo_id=place.id)
                if new_row is not None:
                    self.geo_files.add_to_geoname_dict(key=new_key, new_row=new_row, geo_id=alt_data.geo_id, iso=iso)
                    count += 1
        return count
