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

    """
    6155128	St. Andrews	St. Andrews		46.38341	-62.84866	P	PPLL	CA		09				0
    6155129	St. Andrews	St. Andrews		45.55614	-61.88909	P	PPL	    CA		07				0
    6155132	St. Andrews	St. Andrews		50.0714	    -96.98393	P	PPLL	CA		03				0
    6137411	Saint Andrews	Saint Andrews		45.0737	-67.05312	P	PPL	CA		04	1302
    """

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

    # TEST RESULT CODES
    def test_good_name38(self):
        test = "City.  Good.  upper lowercase"
        lat: float = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(GeoKeys.Result.EXACT_MATCH, self.place.result_type, test)

    def test_dup_name07(self):
        test = "City - multiple matches"
        lat: float = self.run_test(test, "Alberton,, Ontario, Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_good_name15(self):
        test = "County - Good.  wrong Province"
        lat: float = self.run_test(test, "Halifax County, Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_good_name25(self):
        test = "city - Good. wrong Province"
        lat: float = self.run_test(test, "Halifax, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_bad_county03(self):
        test = "multiple county - not unique"
        lat: float = self.run_test(test, "St Andrews,,,Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_good_name27(self):
        test = "City - good. wrong province"
        lat: float = self.run_test(test, "Natuashish, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_good_name28(self):
        test = "City - good. wrong county"
        lat: float = self.run_test(test, "Natuashish, Alberta, ,Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_bad_name37(self):
        test = "City - Bad"
        lat: float = self.run_test(test, "Alberton, ,,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_wrong_country1(self):
        test = "Country - blank"
        lat: float = self.run_test(test, '')
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    # Country

    def test_bad_country03(self):
        test = "Country - bad"
        lat: float = self.run_test(test, "squid")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_no_country56(self):
        test = "No Country - Natuashish"
        lat: float = self.run_test(test, "Natuashish,, ")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_no_country57(self):
        test = "No Country - Berlin"
        lat: float = self.run_test(test, "Berlin,,, ")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_bad_country04(self):
        test = "Country - not supported"
        lat: float = self.run_test(test, "Tokyo,,,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, test)

    # TEST LOOKUP PERMUTATIONS

    # COUNTRY -------------
    def test_good_country29(self):
        test = "Country -  good"
        lat: float = self.run_test(test, "Canada")
        self.assertEqual('canada', self.place.country_name, test)

    def test_good_country67(self):
        test = "Country -  bad"
        lat: float = self.run_test(test, "xyzzy")
        self.assertEqual('', self.place.country_iso, test)

    # PROVINCE -------------
    def test_county_alias02(self):
        test = "Province - Good"
        lat: float = self.run_test(test, "Alberta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_good_name36(self):
        test = "Province - Partial "
        lat: float = self.run_test(test, "new brunswick,Canada")
        self.assertEqual(46.5001, lat, test)

    def test_good_name46(self):
        test = "Province - bad name"
        lat: float = self.run_test(test, "xyzzy,Canada")
        self.assertEqual('', self.place.admin1_id, test)

    # COUNTY ---------------
    def test_county45(self):
        test = "County - good"
        lat: float = self.run_test(test, "County of Athabasca , Alberta, Canada")
        self.assertEqual(54.73298, lat, test)

    def test_county_alias04(self):
        test = "County - good"
        lat: float = self.run_test(test, "Albert County, New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county_alias05(self):
        test = "County - Abbreviated good"
        lat: float = self.run_test(test, "Albert Co., New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_good_name14(self):
        test = "County - good.  Halifax city vs County"
        lat: float = self.run_test(test, "Halifax, Nova Scotia, Canada")
        self.assertEqual(44.86685, lat, test)

    # CITY -------------------

    def test_good_name02(self):
        test = "City - good. upper lowercase"
        lat: float = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_good_name03(self):
        test = "City - good, no county"
        lat: float = self.run_test(test, "Albanel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_good_name06(self):
        test = "City - Good name, Saint"
        lat: float = self.run_test(test, "Saint Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_good_name04(self):
        test = "City - Good name, St "
        lat: float = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_good_name05(self):
        test = "City - Good name, St. "
        lat: float = self.run_test(test, "St. Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_good_name35(self):
        test = "City - Good name, St. with county and province"
        lat: float = self.run_test(test, "St. Andrews,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_good_name08(self):
        test = "City - Good , Alberton PEI vs Alberton Ontario"
        lat: float = self.run_test(test, "Alberton,,Prince Edward Island, Canada")
        self.assertEqual(46.81685, lat, test)

    def test_dup_name09(self):
        test = "City - Good , Alberton Ontario vs Alberton PEI"
        lat: float = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual(48.58318, lat, test)

    def test_good_name10(self):
        test = "City - Good , Halifax, Nova Scotia"
        lat: float = self.run_test(test, "Halifax,, Nova Scotia, Canada")
        self.assertEqual(44.646, lat, test)

    def test_good_name11(self):
        test = "City - Good - with prefix"
        lat: float = self.run_test(test, "Oak Street, Halifax, ,Nova Scotia, Canada")
        self.assertEqual(44.646, lat, test)

    def test_good_name12(self):
        test = "City - Good - with prefix and wrong county"
        lat: float = self.run_test(test, "Oak Street, Halifax, aaa, Nova Scotia, Canada")
        self.assertEqual(44.646, lat, test)

    def test_good_name13(self):
        test = "City -  Good - no county"
        lat: float = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_county_alias01(self):
        test = "County - no County"
        lat: float = self.run_test(test, "Albanel, ,Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_county_alias03(self):
        test = "County - Wrong county"
        lat: float = self.run_test(test, "Albanel, Zxzzy, Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_wrong_province26(self):
        test = "City - good - Wrong Province"
        lat: float = self.run_test(test, "Halifax, Alberta, Canada")
        self.assertAlmostEqual(-63.71541, float(self.place.lon))

    def test_good_name16(self):
        test = "City - Good "
        lat: float = self.run_test(test, "Natuashish, ,, Canada")
        self.assertEqual(55.91564, lat, test)

    def test_good_county02(self):
        test = "City -  wrong county but single match"
        lat: float = self.run_test(test, "Agassiz,, british columbia, Canada")
        self.assertEqual(49.23298, lat, test)

    def test_good_name72(self):
        test = "City - good. No Country"
        lat: float = self.run_test(test, "Albanel,,Quebec")
        self.assertEqual(48.88324, lat, test)

    # WILDCARD ----------------
    def test_wild_country29(self):
        test = "Country - wildcard country"
        lat: float = self.run_test(test, "C*da")
        self.assertEqual('canada', self.place.country_name, test)

    def test_county_alias73(self):
        test = "Province - wildcard province"
        lat: float = self.run_test(test, "Al*ta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_good_name37(self):
        test = "City - good - wildcard city, full county and province"
        lat: float = self.run_test(test, "St. Andr,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_good_wildcard01(self):
        test = "City - good - wildcard city, no county"
        lat: float = self.run_test(test, "Alb*el,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_good_wildcard81(self):
        test = "City - good - wildcard city, no county, wild province"
        lat: float = self.run_test(test, "Alb*el,, Queb*, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_good_wildcard82(self):
        test = "City - good - wildcard city, no county, wild province, wild country"
        lat: float = self.run_test(test, "Alb*el,, Queb*, Can*a")
        self.assertEqual(48.88324, lat, test)

    def test_good_name55(self):
        test = "City - Wildcard - 300+ matches"
        lat: float = self.run_test(test, "er,,, CanAda")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    # TEST ADMIN ID

    def test_good_county03(self):
        test = "Admin2 ID - good "
        lat: float = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual('3559', self.place.admin2_id, test)

    def test_good_admin01(self):
        test = "Admin1 ID - good "
        lat: float = self.run_test(test, "Nova Scotia,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_good_admin02(self):
        test = "Admin1 ID - good - abbreviated "
        lat: float = self.run_test(test, "Baden, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_good_admin03(self):
        test = "Admin1 ID - good.  With non-ASCII"
        lat: float = self.run_test(test, "Baden-Württemberg Region, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_partial_admin0(self):
        test = "Admin1 ID - good - abbreviated "
        lat: float = self.run_test(test, "Nova,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_partial_admin1(self):
        test = "Admin1 ID - good - abbreviated, non-ASCII "
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
