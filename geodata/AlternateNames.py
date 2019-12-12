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
from geodata import GeodataFiles, Loc, GeoUtil, GeoDB, FileReader

ALT_GEOID = 1
ALT_LANG = 2
ALT_NAME = 3


class AlternateNames(FileReader.FileReader):
    """
    Read in Alternate names V2 file and add appropriate entries to geoname DB altnames table
    Each row in file contains a geoname ID, an alternative name for that entity, and the language
    If the lang is in lang_list and the ID is ALREADY in our geonames dictionary, we add this as an alternative name
    FileReader calls handle_line every time it reads a line
    """

    def __init__(self, directory: str, filename: str, progress_bar, geo_files: GeodataFiles, lang_list):
        """
        Read in geonames alternate names file and add to geodata database in alt_names table
        :param directory: base directory for alternate names file
        :param filename: filename of geonames alternate_namesV2.txt file
        :param progress_bar: tkhelper progress bar or None
        :param geo_files: GeodataFiles
        :param lang_list: List of ISO languages we want to support, e.g. ['fr', 'es']
        """
        super().__init__(directory, filename, progress_bar)
        self.sub_dir = GeoUtil.get_cache_directory(directory)
        self.geo_files: GeodataFiles.GeodataFiles = geo_files
        self.lang_list = lang_list
        self.loc = Loc.Loc()

    def read(self) -> bool:
        """
        Read file into database
        :return: True if error
        """
        self.geo_files.geodb.db.begin()
        # Read in file.  This will call handle_line for each line in file
        res = super().read()
        self.geo_files.geodb.db.commit()
        return res

    def handle_line(self, line_num, row):
        """
        For each line in file, add item to alternate name DB if we support that language
        Also add to main DB if lang is not English and item is not an ADM item
        :param line_num:  file line number
        :param row: line in file to be handled
        :return: None
        """
        alt_tokens = row.split('\t')
        if len(alt_tokens) != 10:
            self.logger.debug(f'Incorrect number of tokens: {alt_tokens} line {line_num}')
            return

        self.loc.georow_list = []

        # Alternate names are in multiple languages.  Only add if item is in requested lang list
        if alt_tokens[ALT_LANG] in self.lang_list:
            # Only Add this alias if  DB already has an entry (since geoname DB is filtered based on feature)

            # See if item has an entry with same GEOID in Main DB
            dbid = self.geo_files.geodb.geoid_main_dict.get(alt_tokens[ALT_GEOID])
            if dbid is not None:
                self.loc.target = dbid
                # Retrieve entry
                self.geo_files.geodb.lookup_main_dbid(place=self.loc)
            else:
                # See if item has an entry with same GEOID in Admin DB
                dbid = self.geo_files.geodb.geoid_admin_dict.get(alt_tokens[ALT_GEOID])
                if dbid is not None:
                    self.loc.target = dbid
                    # Retrieve entry
                    self.geo_files.geodb.lookup_admin_dbid(place=self.loc)

            if len(self.loc.georow_list) > 0:
                # Create an entry in the alternate name DB  with this name and soundex

                # Convert row to list. modify name and soundex and add to alternate name DB
                # Update the name in the new row with the alternate name
                update = list(self.loc.georow_list[0])

                # Make sure this entry has a different name from existing entry
                if update[ALT_NAME] != alt_tokens[ALT_NAME]:
                    self.geo_files.update_geo_row_name(geo_row=update, name=alt_tokens[ALT_NAME])
                    new_row = tuple(update)  # Convert back to tuple

                    if alt_tokens[ALT_LANG] != 'en' or 'ADM' not in update[GeoDB.Entry.FEAT]:
                        #  Add to main DB if not English or not ADM1/ADM2
                        self.geo_files.geodb.insert(geo_row=new_row, feat_code=update[GeoDB.Entry.FEAT])
                        self.count += 1

                    # Add name to altnames table
                    if alt_tokens[ALT_LANG] != 'en':
                        self.geo_files.geodb.insert_alternate_name(alt_tokens[ALT_NAME],
                                                                   alt_tokens[ALT_GEOID], alt_tokens[ALT_LANG])

    def cancel(self):
        """
        User requested cancel of database build
        Abort DB build.  Clear out partial DB
        :return: None
        """
        self.geo_files.geodb.db.commit()
        self.geo_files.geodb.clear_geoname_data()
