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

import csv
import glob
import logging
import os
import time
from collections import namedtuple
from typing import Dict

from geofinder import CachedDictionary, Country, GeoDB, GeoKeys, Loc, AlternateNames


class GeodataFiles:
    """
    Read in geonames.org geo data files, filter them and place the entries in sqlite db.

    The files must be downloaded from geonames.org and used according to their usage rules.
    
    geoname_data - Any of the following: gb.TXT (or other country), allCountries.txt, cities500.txt, etc.

    The geoname file is filtered to only include the countries and feature codes specified in the country_list
    dictionary (stored in a pickle file) and the feature_list dictionary (also from a pickle)
         
     There is a separate UtilMain.py utility which allows users to:
         1. edit country list config file.  Only entries for those countries will be read.    "country_list.pkl"
         2. edit the geoname feature list.  Only those geonames features are included.  "features.pkl"
         3. if files or the above are changed, the utility deletes the DB
    """

    def __init__(self, directory: str, progress_bar):
        self.logger = logging.getLogger(__name__)
        self.geodb = None
        self.directory: str = directory
        self.progress_bar = progress_bar
        self.line_num = 0
        self.cache_changed: bool = False
        sub_dir = GeoKeys.get_cache_directory(self.directory)
        self.country = None

        # Read in dictionary listing Geoname features we should include
        self.feature_code_list_cd = CachedDictionary.CachedDictionary(sub_dir, "feature_list.pkl")
        self.feature_code_list_cd.read()
        self.feature_code_list_dct: Dict[str, str] = self.feature_code_list_cd.dict

        # Read in dictionary listing countries (ISO2) we should include
        self.supported_countries_cd = CachedDictionary.CachedDictionary(sub_dir, "country_list.pkl")
        self.supported_countries_cd.read()
        self.supported_countries_dct: Dict[str, str] = self.supported_countries_cd.dict

        self.entry_place = Loc.Loc()

        # Support for Geonames AlternateNames file.  Adds alternate names for entries
        self.alternate_names = AlternateNames.AlternateNames(directory_name=self.directory,
                                                             geo_files=self, progress_bar=self.progress_bar,
                                                             filename='alternateNamesV2.txt', lang_list=['en'])

    def read(self) -> bool:
        """
        .. module:: read
        :synopsis: Read in dictionary for supported countries and features
        :returns: True if error
        """
        # Read list of Supported countries and features - only these countries/features will be loaded from geoname data
        err = self.feature_code_list_cd.read()
        self.feature_code_list_dct = self.feature_code_list_cd.dict
        if err:
            self.logger.error('Error reading features list')
            return True

        err = self.supported_countries_cd.read()
        self.supported_countries_dct = self.supported_countries_cd.dict
        if err:
            self.logger.error('Error reading  supported countries')
            return True

        self.logger.debug('done loading geodata')

        return False

    def read_geoname(self) -> bool:
        # Read Geoname DB file - this is the db of geoname.org city files and is stored in cache directory under geonames_data
        # The db only contains important fields and only for supported countries
        # This file is much smaller and faster to read than the geoname files
        # If the db doesn't exist, read the geonames.org files and build it.
        # the UtilMain.py allows user changes to config parameters and then requires rebuild of db
        # if the user loads a new geonames.org file, we also need to rebuild the db

        # Use db if it exists and is newer than the geonames directory
        cache_dir = GeoKeys.get_cache_directory(self.directory)
        fullpath = os.path.join(cache_dir, 'geodata.db')
        self.logger.debug(f'read_geo db: {fullpath}')

        if os.path.exists(fullpath):
            # See if db exists and is fresh (newer than other files)
            dir_time = os.path.getmtime(self.directory)
            cache_time = os.path.getmtime(fullpath)
            if cache_time > dir_time:
                self.logger.info(f'db up to date: {fullpath}')
                self.geodb = GeoDB.GeoDB(os.path.join(cache_dir, 'geodata.db'))
                # Ensure DB has reasonable number of records
                count = self.geodb.get_row_count()
                self.logger.info(f'Geoname entries = {count:,}')
                if count > 1000:
                    # No error if DB has over 1000 records
                    return False

        # DB  is stale or not available, rebuild it from geoname files
        self.geodb = GeoDB.GeoDB(os.path.join(cache_dir, 'geodata.db'))
        self.country = Country.Country(self.progress_bar, geodb=self.geodb)

        # walk thru list of files ending in .txt e.g US.txt, FR.txt, all_countries.txt, etc
        self.logger.debug(f'{fullpath} not new.  Building db ')
        file_count = 0

        # Clear out all geo_data data since we are rebuilding
        self.geodb.clear_geoname_data()

        # Put in country data
        self.country.read()

        start_time = time.time()

        # Put in geonames file data
        for fname in glob.glob(os.path.join(self.directory, "*.txt")):
            # Read all geoname files except the  utility files and add to db
            if os.path.basename(fname) not in ["admin2Codes.txt", "admin1CodesASCII.txt",
                                               "alternateNamesV2.txt", "alternateNames.txt"]:
                error = self.read_geoname_file(fname)  # Read in info (lat/long) for all places from

                if error:
                    self.logger.error(f'Error reading geoname file')
                else:
                    file_count += 1

        if file_count == 0:
            self.logger.error(f'No geonames files found in {os.path.join(self.directory, "*.txt")}')
            return True

        # Put in alias names
        self.logger.info(f'geonames files done.  Elapsed ={time.time() - start_time}')

        start_time = time.time()
        self.alternate_names.read()
        self.logger.info(f'Alternate names done.  Elapsed ={time.time() - start_time}')
        self.logger.info(f'Geonames entries = {self.geodb.get_row_count():,}')

        start_time = time.time()
        self.progress("Create Indices", 95)
        self.geodb.create_geoid_index()
        self.geodb.create_indices()
        self.logger.debug(f'Indices done.  Elapsed ={time.time() - start_time}')

        return False

    def read_geoname_file(self, file) -> bool:  # , g_dict
        """Read in geonames files and build lookup structure

        Read a geoname.org places file and create a db of all the places.
        1. The db contains: Name, Lat, Long, district1ID (State or Province ID),
        district2_id, feat_code

        2. Since Geonames supports over 25M entries, the db is filtered to only the countries and feature types we want
        """
        Geofile_row = namedtuple('Geofile_row',
                                 'id name name_asc alt lat lon feat_class feat_code iso iso2 admin1_id'
                                 ' admin2_id admin3_id admin4_id pop elev dem timezone mod')
        self.line_num = 0
        self.progress("Reading {}...".format(file), 0)
        path = os.path.join(self.directory, file)

        if os.path.exists(path):
            fsize = os.path.getsize(path)
            bytes_per_line = 128
            with open(path, 'r', newline="", encoding='utf-8', errors='replace') as geofile:
                self.progress("Loading {}".format(file), 2)  # initialize progress bar
                reader = csv.reader(geofile, delimiter='\t')
                self.geodb.db.begin()

                # Map line from csv reader into GeonameData namedtuple
                for line in reader:
                    self.line_num += 1
                    if self.line_num % 80000 == 0:
                        # Periodically update progress
                        self.progress(msg="Loading {}".format(file), val=self.line_num * bytes_per_line * 100 / fsize)
                    try:
                        geoname_row = Geofile_row._make(line)
                    except TypeError:
                        self.logger.error(f'Unable to read Geoname file {file}.  Line {self.line_num}')
                        continue

                    # Only handle line if it's  for a country we follow and its
                    # for a Feature tag we're interested in
                    if geoname_row.iso.lower() in self.supported_countries_dct and \
                            geoname_row.feat_code in self.feature_code_list_dct:
                        self.insert_georow(geoname_row)

            self.progress("Write Database", 90)
            self.geodb.db.commit()
            self.progress("Database created", 100)
            return False
        else:
            return True

    def insert_georow(self, geoname_row):
        # Create Geo_row and inses
        # ('paris', 'fr', '07', '012', 12.345, 45.123, 'PPL', '34124')
        geo_row = [None] * GeoDB.Entry.MAX
        geo_row[GeoDB.Entry.NAME] = GeoKeys.normalize(geoname_row.name)
        geo_row[GeoDB.Entry.SDX] = GeoKeys.get_soundex(geo_row[GeoDB.Entry.NAME])

        geo_row[GeoDB.Entry.ISO] = geoname_row.iso.lower()
        geo_row[GeoDB.Entry.ADM1] = geoname_row.admin1_id
        geo_row[GeoDB.Entry.ADM2] = geoname_row.admin2_id
        geo_row[GeoDB.Entry.LAT] = geoname_row.lat
        geo_row[GeoDB.Entry.LON] = geoname_row.lon
        geo_row[GeoDB.Entry.FEAT] = geoname_row.feat_code
        geo_row[GeoDB.Entry.ID] = geoname_row.id
        if geoname_row.id == '11594109':
            self.logger.debug(f'Eastminster {geoname_row}')


        self.geodb.insert(geo_row=geo_row, feat_code=geoname_row.feat_code)

    def get_supported_countries(self) -> [str, int]:
        """ Convert list of supported countries into sorted string """
        # todo implement list of names of supported countries
        nm_msg = ""
        for ky in self.supported_countries_dct:
            nm_msg += ky.upper() + ', '
        return nm_msg, len(self.supported_countries_dct)

    def progress(self, msg, val):
        """ Update progress bar if there is one """
        if val > 80:
            self.logger.info(f'{val:.1f}%  {msg}')
        else:
            self.logger.debug(f'{val:.1f}%  {msg}')

        if self.progress_bar is not None:
            self.progress_bar.update_progress(val, msg)
