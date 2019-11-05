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

# The tab separated columns in geoname.org file rows are as follows

from geofinder import GeodataFiles, GeoKeys, GeoDB
from geofinder.FileReader import FileReader
from geofinder.Loc import Loc

ALT_GEOID = 1
ALT_LANG = 2
ALT_NAME = 3


class AlternateNames(FileReader):
    """
    Read in Alternate names file and add appropriate entries to geoname dictionary
    Each row contains a geoname ID, an alternative name for that entity, and the language
    If the lang is in our Config and the ID is in our geonames dictionary, we add this as an alternative name
    FileReader calls handle_line every time it reads a line
    """

    def __init__(self, directory_name: str, filename: str, progress_bar, geo_files: GeodataFiles, lang_list):
        super().__init__(directory_name, filename, progress_bar)
        self.sub_dir = GeoKeys.get_cache_directory(directory_name)
        self.geo_files: GeodataFiles.GeodataFiles = geo_files
        self.lang_list = lang_list
        self.loc = Loc()

    def read(self) -> bool:
        self.geo_files.geodb.db.begin()
        # Read in file.  This will call handle_line for each file line
        res = super().read()
        self.geo_files.geodb.db.commit()
        return res

    def cancel(self):
        # User requested cancel
        # Abort DB build.  Clear out partial DB
        self.geo_files.geodb.db.commit()
        self.geo_files.geodb.clear_geoname_data()

    def handle_line(self, line_num, row):
        # This is called as each line is read
        alt_tokens = row.split('\t')
        if len(alt_tokens) != 10:
            self.logger.debug(f'Incorrect number of tokens: {alt_tokens} line {line_num}')
            return

        self.loc.georow_list = []

        # Alternate names are in multiple languages.  Only add if item is in requested lang list
        if alt_tokens[ALT_LANG] in self.lang_list:
            # Add this alias to geoname db if there is already an entry (geoname DB is filtered based on feature)
            # See if item has an entry with same GEOID in Main DB
            dbid = self.geo_files.geodb.geoid_main_dict.get(alt_tokens[ALT_GEOID])
            if dbid is not None:
                self.loc.target = dbid
                self.geo_files.geodb.lookup_main_dbid(place=self.loc)
            else:
                # See if item has an  entry with same GEOID in Admin DB
                dbid = self.geo_files.geodb.geoid_admin_dict.get(alt_tokens[ALT_GEOID])
                if dbid is not None:
                    self.loc.target = dbid
                    self.geo_files.geodb.lookup_admin_dbid(place=self.loc)

            if len(self.loc.georow_list) > 0:
                # convert to list  and modify name and add to DB and its soundex
                lst = list(self.loc.georow_list[0])
                del lst[-1]
                lst[GeoDB.Entry.NAME] = GeoKeys.normalize(alt_tokens[ALT_NAME])
                lst.append(GeoKeys.get_soundex(alt_tokens[ALT_NAME]))
                new_row = tuple(lst)   # Convert back to tuple
                if alt_tokens[ALT_LANG] != 'en' or 'ADM' not in lst[GeoDB.Entry.FEAT]:
                    # Only add if not English or not ADM1/ADM2
                    self.geo_files.geodb.insert(geo_row=new_row, feat_code=lst[GeoDB.Entry.FEAT])
                    self.count += 1

                # Add name to altnames table
                if alt_tokens[ALT_LANG] != 'en':
                    self.geo_files.geodb.insert_alternate_name(alt_tokens[ALT_NAME],
                                                           alt_tokens[ALT_GEOID], alt_tokens[ALT_LANG])
