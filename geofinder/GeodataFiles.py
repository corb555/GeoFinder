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
import logging
import os
import time
from collections import namedtuple
from tkinter import messagebox
from typing import Dict

from geofinder import CachedDictionary, Country, GeoDB, GeoUtil, Loc, AlternateNames, UtilFeatureFrame, Normalize


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
        self.required_db_version = 2
        self.db_upgrade_text = 'Adding support for non-English output'
        self.directory: str = directory
        self.progress_bar = progress_bar
        self.line_num = 0
        self.cache_changed: bool = False
        sub_dir = GeoUtil.get_cache_directory(self.directory)
        self.country = None

        # Read in dictionary listing Geoname features we should include
        self.feature_code_list_cd = CachedDictionary.CachedDictionary(sub_dir, "feature_list.pkl")
        self.feature_code_list_cd.read()
        self.feature_code_list_dct: Dict[str, str] = self.feature_code_list_cd.dict
        if len(self.feature_code_list_dct) < 3:
            self.logger.warning('Feature list is empty. Setting defaults')
            self.feature_code_list_dct.clear()
            feature_list = UtilFeatureFrame.default
            for feat in feature_list:
                self.feature_code_list_dct[feat] = ''
            self.feature_code_list_cd.write()

        # Read in dictionary listing countries (ISO2) we should include
        self.supported_countries_cd = CachedDictionary.CachedDictionary(sub_dir, "country_list.pkl")
        self.supported_countries_cd.read()
        self.supported_countries_dct: Dict[str, str] = self.supported_countries_cd.dict

        # Read in dictionary listing languages (ISO2) we should include
        self.languages_list_cd = CachedDictionary.CachedDictionary(sub_dir, "languages_list.pkl")
        self.languages_list_cd.read()
        self.languages_list_dct: Dict[str, str] = self.languages_list_cd.dict
        self.lang_list = []

        for item in self.languages_list_dct:
            self.lang_list.append(item)

        # Read in dictionary listing output text replacements
        self.output_replace_cd = CachedDictionary.CachedDictionary(sub_dir, "output_list.pkl")
        self.output_replace_cd.read()
        self.output_replace_dct: Dict[str, str] = self.output_replace_cd.dict
        self.output_replace_list = []

        for item in self.output_replace_dct:
            self.output_replace_list.append(item)
            self.logger.debug(f'Output replace [{item}]')

        self.entry_place = Loc.Loc()

        # Support for Geonames AlternateNames file.  Adds alternate names for entries
        self.alternate_names = AlternateNames.AlternateNames(directory_name=self.directory,
                                                             geo_files=self, progress_bar=self.progress_bar,
                                                             filename='alternateNamesV2.txt', lang_list=self.lang_list)

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
        cache_dir = GeoUtil.get_cache_directory(self.directory)
        db_path = os.path.join(cache_dir, 'geodata.db')
        self.logger.debug(f'path for geodata.db: {db_path}')
        err_msg = ''

        # Validate Database setup
        if os.path.exists(db_path):
            # See if db is fresh (newer than other files)
            self.logger.debug(f'DB found at {db_path}')
            self.geodb = GeoDB.GeoDB(db_path=db_path, version=self.required_db_version)

            # Make sure DB is correct version
            ver = self.geodb.get_db_version()
            if ver != self.required_db_version:
                err_msg = f'Database version will be upgraded:\n\n{self.db_upgrade_text}\n\n' \
                    f'Upgrading database from V{ver} to V{self.required_db_version}.'
            else:
                # Correct Version.  Make sure DB is not stale
                dir_time = os.path.getmtime(self.directory)
                cache_time = os.path.getmtime(db_path)
                #if cache_time > dir_time:
                if True:
                    self.logger.info(f'DB is up to date')
                    # Ensure DB has reasonable number of records
                    count = self.geodb.get_row_count()
                    self.logger.info(f'Geoname entries = {count:,}')
                    if count < 1000:
                        # Error if DB has under 1000 records
                        err_msg = f'Geoname Database is too small.\n\n {db_path}\n\nRebuilding DB '
                if False:
                    # DB is stale
                    err_msg = f'DB {db_path} is older than geonames.org files.  Rebuilding DB '
                    if not messagebox.askyesno('Stale Database','Database is older than geonames.org files.\n\nRebuild database?'):
                        err_msg = ''
        else:
            err_msg = f'Database not found at\n\n{db_path}.\n\nBuilding DB'

        self.logger.debug(f'{err_msg}')
        if err_msg == '':
            # No DB errors detected
            self.geodb.create_indices()
            self.geodb.create_geoid_index()
            return False

        # DB error detected - rebuild database
        self.logger.debug('message box')
        messagebox.showinfo('Database Error', err_msg)
        self.logger.debug('message box done')

        # DB  error.  Rebuild it from geoname files
        self.logger.debug(err_msg)

        if os.path.exists(db_path):
            self.geodb.close()
            os.remove(db_path)
            self.logger.debug('Database deleted')

        self.geodb = GeoDB.GeoDB(db_path=db_path, version=self.required_db_version)
        self.country = Country.Country(self.progress_bar, geo_files=self, lang_list=self.lang_list)

        # walk thru list of files ending in .txt e.g US.txt, FR.txt, all_countries.txt, etc
        file_count = 0

        # Put in country data
        self.country.read()

        start_time = time.time()

        # Set DB version as -1 for incomplete
        self.geodb.insert_version(-1)

        # Put in geonames file data
        for fname in ['allCountries.txt', 'ca.txt', 'gb.txt', 'de.txt', 'fr.txt', 'nl.txt']:
            # Read all geoname files
            error = self.read_geoname_file(fname)  # Read in info (lat/long) for all places from

            if error:
                self.logger.error(f'Error reading geoname file {fname}')
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
        self.progress("3) Final Step: Creating Indices for Database...", 95)
        self.geodb.create_geoid_index()
        self.geodb.create_indices()
        self.logger.debug(f'Indices done.  Elapsed ={time.time() - start_time}')
        self.geodb.insert_version(self.required_db_version)

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
                self.progress("Building Database from {}".format(file), 2)  # initialize progress bar
                reader = csv.reader(geofile, delimiter='\t')
                self.geodb.db.begin()

                # Map line from csv reader into GeonameData namedtuple
                for line in reader:
                    self.line_num += 1
                    if self.line_num % 20000 == 0:
                        # Periodically update progress
                        prog = self.line_num * bytes_per_line * 100 / fsize
                        self.progress(msg=f"1) Building Database from {file}            {prog:.1f}%", val=prog)
                    try:
                        geoname_row = Geofile_row._make(line)
                    except TypeError:
                        self.logger.error(f'Unable to parse geoname location info in {file}  line {self.line_num}')
                        continue

                    # Only handle line if it's  for a country we follow and its
                    # for a Feature tag we're interested in
                    if geoname_row.iso.lower() in self.supported_countries_dct and \
                            geoname_row.feat_code in self.feature_code_list_dct:
                        self.insert_georow(geoname_row)
                        if geoname_row.name.lower() != Normalize.normalize(geoname_row.name,remove_commas=True):
                            self.geodb.insert_alternate_name(geoname_row.name,
                                                                   geoname_row.id, 'ut8')

                    if self.progress_bar is not None:
                        if self.progress_bar.shutdown_requested:
                            # Abort DB build.  Clear out partial DB
                            self.geodb.clear_geoname_data()

            self.progress("Write Database", 90)
            self.geodb.db.commit()
            self.progress("Database created", 100)
            return False
        else:
            return True

    def update_geo_row_name(self, geo_row, name):
        geo_row[GeoDB.Entry.NAME] = Normalize.normalize(name, remove_commas=True)
        geo_row[GeoDB.Entry.SDX] = GeoUtil.get_soundex(geo_row[GeoDB.Entry.NAME])

    def insert_georow(self, geoname_row):
        # Create Geo_row and inses
        # ('paris', 'fr', '07', '012', 12.345, 45.123, 'PPL', '34124')
        geo_row = [None] * GeoDB.Entry.MAX
        self.update_geo_row_name(geo_row=geo_row, name=geoname_row.name)

        geo_row[GeoDB.Entry.ISO] = geoname_row.iso.lower()
        geo_row[GeoDB.Entry.ADM1] = geoname_row.admin1_id
        geo_row[GeoDB.Entry.ADM2] = geoname_row.admin2_id
        geo_row[GeoDB.Entry.LAT] = geoname_row.lat
        geo_row[GeoDB.Entry.LON] = geoname_row.lon
        geo_row[GeoDB.Entry.FEAT] = geoname_row.feat_code
        geo_row[GeoDB.Entry.ID] = geoname_row.id

        if int(geoname_row.pop) > 1000000 and 'PP' in geoname_row.feat_code:
            geo_row[GeoDB.Entry.FEAT] = 'PP1M'
        elif int(geoname_row.pop) > 100000 and 'PP' in geoname_row.feat_code:
            geo_row[GeoDB.Entry.FEAT] = 'P1HK'
        elif int(geoname_row.pop) > 10000 and 'PP' in geoname_row.feat_code:
            geo_row[GeoDB.Entry.FEAT] = 'P10K'

        #if geoname_row.feat_code == 'PPLQ':
        #    geo_row[GeoDB.Entry.NAME] = re.sub(r' historical', '', geo_row[GeoDB.Entry.NAME])

        self.geodb.insert(geo_row=geo_row, feat_code=geoname_row.feat_code)

        # Also add abbreviations for USA states
        if geo_row[GeoDB.Entry.ISO] == 'us' and geoname_row.feat_code == 'ADM1':
            #geo_row[GeoDB.Entry.NAME] = geo_row[GeoDB.Entry.ADM1].lower()
            self.update_geo_row_name(geo_row=geo_row, name=geo_row[GeoDB.Entry.ADM1])
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

    def close(self):
        if self.geodb:
            self.geodb.close()
