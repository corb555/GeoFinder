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

from geofinder import CachedDictionary, Country, GeoDB, GeoKeys, Place, AlternateNames


class GeodataFiles:
    """
    Read in geonames.org geo data files and place the entries in dictionaries.
    Once that slow conversion is down, cache the dictionaries in Python Pickle files
    Items that have Feature Class matching Adm1 are placed in dictionary with @A in key,
    others are placed in  dictionary with @P in key.
    The dictionary data entry contains: Lat, Long, and districtID (County or State or Province ID)
    The dictionary key is the place name, admin1 (state/province) and country (created by  function make_key)
    Only items whose feature code is in feature_code list are included.

    The files must be downloaded from geonames.org and used according to their usage rules.
    
    geoname_data - Any of the following: gb.TXT (or other country), allCountries.txt, cities500.txt, etc.
                   Some of these files are large and take a long time to process.
    
    The files are large and parsing them is slow.  To speed this up, once the files are read they are output to a Python
    pickle file.  On the next startup the pickle file is read rather than the original geonames files unless the directory has
    been updated.
         
         There is a separate GeoUtil.py utility which allows users to:
             1. set country list config file.  Only entries for those countries will be read.    "country_list.pkl"
             2. set the feature list for features to include
             3. if files or the above are changed, the utility deletes the cache file and we rebuild it here
    """

    def __init__(self, directory: str, progress_bar):  # , geo_district):
        self.logger = logging.getLogger(__name__)
        self.geodb = None
        self.directory: str = directory
        self.progress_bar = progress_bar
        self.line_num = 0
        self.cache_changed: bool = False
        sub_dir = GeoKeys.cache_directory(self.directory)
        self.country = None

        self.feature_code_list_cd = CachedDictionary.CachedDictionary(sub_dir, "feature_list.pkl")
        self.feature_code_list_cd.read()
        self.feature_code_list_dct: Dict[str, str] = self.feature_code_list_cd.dict

        self.supported_countries_cd = CachedDictionary.CachedDictionary(sub_dir, "country_list.pkl")
        self.supported_countries_cd.read()
        self.supported_countries_dct: Dict[str, str] = self.supported_countries_cd.dict

        self.entry_place = Place.Place()
        self.alternate_names = AlternateNames.AlternateNames(directory_name=self.directory,
                                                             geo_files=self,progress_bar=self.progress_bar,
                                                             filename='alternateNamesV2.txt')

    def read(self) -> bool:
        """
        .. module:: read
        :synopsis: Read in geoname data from cache file if available or read each geoname.org file and place in cache file.
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
        # the GeoUtil.py allows user changes to config parameters and then requires rebuild of db
        # if the user loads a new geonames.org file, we also need to rebuild the db

        # Use db if it exists and is newer than the geonames directory
        cache_dir = GeoKeys.cache_directory(self.directory)
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
                if count > 1000:
                    # No error if DB has over 1000 records
                    return False

        # DB  is stale or not available, rebuild it
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
        self.logger.debug(f'geonames files done.  Elapsed ={time.time() - start_time}')

        self.add_admin_aliases()

        start_time = time.time()
        self.alternate_names.read()
        self.logger.debug(f'Alt names done.  Elapsed ={time.time() - start_time}')

        start_time = time.time()
        self.progress("Create Indices", 95)
        self.geodb.create_geoid_index()
        self.geodb.create_indices()
        self.logger.debug(f'Indices done.  Elapsed ={time.time() - start_time}')

        return False

    def add_admin_aliases(self):
        # name='q', iso='q', adm1='q', adm2='q', lat=900, lon=900, feat='q', id='q')
        """
        alias_list = [
            ('brittany','fr', '53', '', 48.16667, -2.83333, 'ADM1','3030293'),
            ('normandy', 'fr', '28', '', 49.19906, 0.49988, 'ADM1', '11071621'),
            ('burgundy', 'fr', '28', '', 47.06981, 5.04822, 'ADM1', '11071619'),
            ('prussia', 'de', '', '', 51.0, 9.0, 'ADM0', 'de'),
            ('North Rhine-Westphalia', 'de', '07', '', 51.21895, 6.76339, 'ADM1', '2861876')
        ] """

        alias_list = [
            ('prussia', 'de', '', '', 51.0, 9.0, 'ADM0', 'de')
        ]

        for geo_row in alias_list:
            self.geodb.insert(geo_row=geo_row, feat_code=geo_row[GeoDB.Entry.FEAT])

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
                        self.insert_line(geoname_row)

            self.progress("Write Database", 90)
            self.geodb.db.commit()
            self.progress("Database created", 100)
            return False
        else:
            return True

    def insert_line(self, geoname_row):
        # Create Geo_row
        # ('paris', 'fr', '07', '012', 12.345, 45.123, 'PPL', '34124')
        geo_row = [None] * 8
        geo_row[GeoDB.Entry.NAME] = GeoKeys.normalize(geoname_row.name)
        geo_row[GeoDB.Entry.ISO] = geoname_row.iso.lower()
        geo_row[GeoDB.Entry.ADM1] = geoname_row.admin1_id
        geo_row[GeoDB.Entry.ADM2] = geoname_row.admin2_id
        geo_row[GeoDB.Entry.LAT] = geoname_row.lat
        geo_row[GeoDB.Entry.LON] = geoname_row.lon
        geo_row[GeoDB.Entry.FEAT] = geoname_row.feat_code
        geo_row[GeoDB.Entry.ID] = geoname_row.id

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
