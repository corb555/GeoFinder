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
import time
import unittest
from pathlib import Path

import GeoKeys
import Geodata
import Place


class TestGeodata(unittest.TestCase):
    geodata = None

    @classmethod
    def setUpClass(cls):
        logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)

        # Load test data
        directory = os.path.join(str(Path.home()), "geoname_test")
        TestGeodata.geodata = Geodata.Geodata(directory_name=directory, progress_bar=None)
        error: bool = TestGeodata.geodata.read()
        if error:
            logger.error("Missing geodata support Files.")
            raise ValueError('Cannot open database')

        # Read in Geoname Gazeteer file - city names, lat/long, etc.
        start_time = time.time()
        error = TestGeodata.geodata.read_geonames()
        end_time = time.time()

        print(f'Elapsed {end_time - start_time}')
        if error:
            logger.info("Missing geoname Files.")
            logger.info('Requires ca.txt and de.txt from geonames.org in folder username/geoname_test')
            raise ValueError('Cannot open database')

    def setUp(self) -> None:
        self.place: Place.Place = Place.Place()

    def run_test(self, title: str, entry: str) -> float:
        print("*****TEST: {}".format(title))
        TestGeodata.geodata.find_location(entry, self.place)
        # if self.place.result_type != GeoKeys.Result.SUCCESS and self.place.result_type != GeoKeys.Result.NOT_SUPPORTED:
        #    TestGeodata.geodata.find_partial_results(self.place)
        return float(self.place.lat)

    """
    Test all Result Types
        
    SUCCESS = 0 xx
    EOF = 1
    NOT_UNIQUE = 2  xx
    NOT_FOUND = 3  xx
    NOT_SUPPORTED = 4 xx
    NO_COUNTRY = 5  xx
    NOT_IDENTICAL = 7 xx
    """

    def test_good_name38(self):
        test = "Test38 Good name, upper lowercase"
        lat: float = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(GeoKeys.Result.EXACT_MATCH, self.place.result_type, test)

    def test_dup_name07(self):
        test = "Test16 Dup name, Alberton  Ontario"
        lat: float = self.run_test(test, "Alberton,, Ontario, Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_good_name15(self):
        test = "Test15 Good county wrong Province, Halifax, Alberta"
        lat: float = self.run_test(test, "Halifax County, Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_good_name25(self):
        test = "Test15 Good city wrong Province, Halifax, Alberta"
        lat: float = self.run_test(test, "Halifax, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_bad_county03(self):
        test = "bad county3 multiple county not unique"
        lat: float = self.run_test(test, "St Andrews,,,Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_bad_name37(self):
        test = "Test37 Bad name, Alberton, ,,Germany "
        lat: float = self.run_test(test, "Alberton, ,,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_wrong_country1(self):
        test = "Test51 wrong country"
        lat: float = self.run_test(test, '')
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_bad_country03(self):
        test = "Test53 bad country: squid"
        lat: float = self.run_test(test, "squid")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_bad_country04(self):
        test = "Test54 bad country: Japan"
        lat: float = self.run_test(test, "Tokyo,,,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, test)

    def test_good_name27(self):
        test = "Test27 Good city wrong province, Natuashish, Alberta"
        lat: float = self.run_test(test, "Natuashish, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_good_name28(self):
        test = "Test28 Good city wrong county, Natuashish, Alberta"
        lat: float = self.run_test(test, "Natuashish, Alberta, ,Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    #  Test County Alias
    def test_county_alias01(self):
        test = "Test1 Test Newfoundland alias"
        lat: float = self.run_test(test, "Albanel, ,Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_wrong_province26(self):
        test = "Test15 Good county wrong Province, Halifax, Alberta"
        lat: float = self.run_test(test, "Halifax, Alberta, Canada")
        self.assertAlmostEqual(-63.71541, float(self.place.lon))

    def test_county_alias02(self):
        test = "Test country alias 2 Test Name,Country"
        lat: float = self.run_test(test, "Alberta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_county_alias03(self):
        test = "Test3 Test Name,extra, county, Country"
        lat: float = self.run_test(test, "Albanel, Zill, Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_county45(self):
        test = "Test3 Test county 45,County of Athabasca, Alberta"
        lat: float = self.run_test(test, "County of Athabasca , Alberta, Canada")
        self.assertEqual(54.73298, lat, test)

    def test_county_alias04(self):
        test = "Test51 Test Albert County"
        lat: float = self.run_test(test, "Albert County, New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county_alias05(self):
        test = "Test52 Test Albert Co."
        lat: float = self.run_test(test, "Albert Co., New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    # Test Good name
    def test_good_name02(self):
        test = "good_name02, upper lowercase"
        lat: float = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_good_name03(self):
        test = "good_name03"
        lat: float = self.run_test(test, "Albanel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_good_wildcard01(self):
        test = "good_wildcard01"
        lat: float = self.run_test(test, "Alb*el,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_good_name55(self):
        test = "Test55 300+ matches"
        lat: float = self.run_test(test, "er,,, CanAda")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_no_country56(self):
        test = "Test56 No Country - Natuashish"
        lat: float = self.run_test(test, "Natuashish,, ")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_no_country57(self):
        test = "Test57 No Country - Berlin"
        lat: float = self.run_test(test, "Berlin,,, ")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_good_name04(self):
        """
        6155128	St. Andrews	St. Andrews		46.38341	-62.84866	P	PPLL	CA		09				0
        6155129	St. Andrews	St. Andrews		45.55614	-61.88909	P	PPL	    CA		07				0
        6155132	St. Andrews	St. Andrews		50.0714	    -96.98393	P	PPLL	CA		03				0
        6137411	Saint Andrews	Saint Andrews		45.0737	-67.05312	P	PPL	CA		04	1302
        """
        test = "Test13 Good name, St Andrews Canada"
        lat: float = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_good_name05(self):
        test = "Test14 Good name, St."
        lat: float = self.run_test(test, "St. Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_good_name37(self):
        test = "Test14 wildcard name, full county and province"
        lat: float = self.run_test(test, "St. Andr,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_good_name35(self):
        test = "Test14 Good name, St."
        lat: float = self.run_test(test, "St. Andrews,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_good_name36(self):
        test = "Test14 Good name, St."
        lat: float = self.run_test(test, "new brunswick,Canada")
        self.assertEqual(46.5001, lat, test)

    def test_good_name06(self):
        test = "Test15 Good name, Saint"
        lat: float = self.run_test(test, "Saint Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_good_name08(self):
        test = "Test17 Good name, Alberton PEI similar lat"
        lat: float = self.run_test(test, "Alberton,,Prince Edward Island, Canada")
        self.assertEqual(46.81685, lat, test)

    def test_dup_name09(self):
        test = "Dup name9, Alberton Ontario similar lat"
        lat: float = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual(48.58318, lat, test)

    def test_good_name10(self):
        test = "Test10 Good name, Halifax, Nova Scotia"
        lat: float = self.run_test(test, "Halifax,, Nova Scotia, Canada")
        self.assertEqual(44.646, lat, test)

    def test_good_name11(self):
        test = "Test11 Good city in 4th position, Oak Street, Halifax, Nova Scotia"
        lat: float = self.run_test(test, "Oak Street, Halifax, ,Nova Scotia, Canada")
        self.assertEqual(44.646, lat, test)

    def test_good_name12(self):
        test = "Test12 Good city in 4th position, Halifax,aaa,"
        lat: float = self.run_test(test, "Oak Street, Halifax, aaa, Nova Scotia, Canada")
        self.assertEqual(44.646, lat, test)

    def test_good_name13(self):
        test = "Test13 Good city in 2nd position, "
        lat: float = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_good_name14(self):
        test = "Test14 County in 3rd, Halifax, Nova Scotia"
        lat: float = self.run_test(test, "Halifax, Nova Scotia, Canada")
        self.assertEqual(44.86685, lat, test)

    def test_good_name16(self):
        test = "Test16 Good city in 4th, Natuashish"
        lat: float = self.run_test(test, "Natuashish, ,, Canada")
        self.assertEqual(55.91564, lat, test)

    def test_good_name17(self):
        test = "Test17 Good city in 3rd, Natuashish"
        lat: float = self.run_test(test, "Natuashish, ,, Canada")
        self.assertEqual(55.91564, lat, test)

    def test_good_country29(self):
        test = "Test52 good country - Canada "
        lat: float = self.run_test(test, "Canada")
        self.assertEqual('canada', self.place.country_name, test)

    def test_good_county02(self):
        test = "Test54 wrong county but single match"
        lat: float = self.run_test(test, "Agassiz,, british columbia, Canada")
        self.assertEqual(49.23298, lat, test)

    def test_good_county03(self):
        test = "good cty 03, Rainy River District,Ontario, Canada"
        lat: float = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual('3559', self.place.admin2_id, test)

    def test_good_admin01(self):
        test = "good admin1"
        lat: float = self.run_test(test, "Nova Scotia,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_good_admin02(self):
        test = "good admin2"
        lat: float = self.run_test(test, "Baden, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_good_admin03(self):
        test = "good admin3"
        lat: float = self.run_test(test, "Baden-Württemberg Region, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_partial_admin0(self):
        test = "partial admin1"
        lat: float = self.run_test(test, "Nova,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_partial_admin1(self):
        test = "partial admin2"
        lat: float = self.run_test(test, "Baden-Württemberg, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    # TEST PARSE_CVS
    def test_get_county_csv02(self):
        test = "***** TEST: 104 Test CSV Parse 2 county alias"
        print(test)
        self.place.parse_place(place_name="aaa,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("alberta", self.place.admin1_name, test)

    def test_get_county_csv03(self):
        test = "***** TEST: 105 Test CSV Parse 2 county alias"
        print(test)
        self.place.parse_place(place_name="aaa,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("alberta's rockies", self.place.admin2_name, test)


if __name__ == '__main__':
    unittest.main()
