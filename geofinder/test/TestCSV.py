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
import os
import unittest
from pathlib import Path

from geofinder import Geodata, Loc, GrampsXml, GrampsCsv


#             ('12 Privet Drive,Dover, ,England,United Kingdom', "PPL", 'P0006', 'gb'),
class RowEntry:
    NAME = 0
    FEAT = 1
    PLACE_ID = 2
    ISO = 3


class TestCSV(unittest.TestCase):
    geodata = None
    ancestry = None
    logger = None
    csv = None

    @classmethod
    def setUpClass(cls):
        TestCSV.logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)

        # Load test data
        directory = os.path.join(str(Path.home()), "geoname_test")
        csv_path = os.path.join(directory, "test")
        TestCSV.geodata = Geodata.Geodata(directory_name=directory, progress_bar=None)
        error: bool = TestCSV.geodata.read()
        if error:
            TestCSV.logger.error("Missing geodata support Files.")
            raise ValueError('Cannot open database')

        # Read in Geoname Gazeteer file - city names, lat/long, etc.
        error = TestCSV.geodata.read_geonames()

        if error:
            TestCSV.logger.info("Missing geoname Files.")
            TestCSV.logger.info('Requires ca.txt, gb.txt, de.txt from geonames.org in folder username/geoname_test')
            raise ValueError('Cannot open database')

        TestCSV.csv = GrampsCsv.GrampsCsv(in_path=csv_path, geodata=TestCSV.geodata)

        TestCSV.ancestry = GrampsXml.GrampsXml(in_path=csv_path, out_suffix='', cache_d=None,
                                               progress=None, geodata=TestCSV.geodata)  # Routines

        # Set up CSV Data
        csv_data = [
            #('Portugal', 'ADM0', 'P0001', 'po'),
             #('Scotland,United Kingdom', 'ADM1','P0002','gb'),
             #('Kent,England,United Kingdom', 'ADM2','P0003','gb'),
            #('Canterbury,Kent,England,United Kingdom', "PPL", 'P0004', 'gb'),
            #('St Eustace,Canterbury,Kent,England,United Kingdom', "PPL", 'P0005', 'gb'),
            #('Dover, ,England,United Kingdom', "PPL", 'P0006', 'gb'),
            ('12 Privet Drive, Dover, ,England,United Kingdom', "PPL", 'P0006', 'gb'),
            #('Edinburgh, ,Scotland,United Kingdom', "PPL", 'P0007', 'gb'),
            #("St James's Palace, ,England,United Kingdom", "PPL", 'P0008', 'gb'),
        ]

        place = Loc.Loc()

        for row in csv_data:
            place.clear()
            place.name = row[RowEntry.NAME]
            place.feature = row[RowEntry.FEAT]
            place.parse_place(place_name=place.name, geo_files=TestCSV.geodata.geo_files)
            # Lookup record
            TestCSV.geodata.find_first_match(place.name, place)
            place.id = row[RowEntry.PLACE_ID]
            TestCSV.csv.set_CSV_place_type(place)
            #TestCSV.geodata.set_place_type_text(place)
            #place.name = TestCSV.ancestry.get_csv_name(place).title()

            TestCSV.csv.create_csv_node(place)

        TestCSV.csv.complete_csv()

    def setUp(self) -> None:
        self.place: Loc.Loc = Loc.Loc()

    def run_key_test(self, title: str, entry: str):
        print("*****TEST: {}".format(title))
        place = Loc.Loc()
        place.parse_place(entry, TestCSV.geodata.geo_files )
        self.geodata.find_first_match(place.name, place)
        place.name = place.format_full_nm(None)
        TestCSV.csv.set_CSV_place_type(place)
        place.id = TestCSV.csv.get_csv_key(place)

        TestCSV.logger.debug(f'type={place.place_type}')

        TestCSV.geodata.set_place_type_text(place)
        #place_name = TestCSV.ancestry_file_handler.get_csv_name(place).title()
        return place.id

    # ===== TEST RESULT CODES

    def test_key01(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "Dover,Kent,England,United Kingdom")
        self.assertEqual("DOVER_G5_ENG_GB", key, title)
    
    def test_key02(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "Kent,England,United Kingdom")
        self.assertEqual("G5_ENG_GB", key, title)

    def test_key03(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "England,United Kingdom")
        self.assertEqual("ENG_GB", key, title)

    def test_key04(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "United Kingdom")
        self.assertEqual("GB", key, title)

    def test_key05(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "Scotland,United Kingdom")
        self.assertEqual("SCT_GB", key, title)

    def test_key06(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "Dover,xyz,England,United Kingdom")
        self.assertEqual("DOVER_G5_ENG_GB", key, title)

    def test_key07(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "Dover, ,England,United Kingdom")
        self.assertEqual("DOVER_G5_ENG_GB", key, title)

    def test_key08(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "Marks Square,Dover,,England,United Kingdom")
        self.assertEqual("MARKS SQUARE_DOVER_G5_ENG_GB", key, title)

    def test_key09(self):
        title = "City.  Good.  upper lowercase"
        key = self.run_key_test(title, "St. Andrews,Charlotte County,new brunswick,Canada")
        self.assertEqual("ST ANDREWS_1302_04_CA", key, title)


if __name__ == '__main__':
    unittest.main()
