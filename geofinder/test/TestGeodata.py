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

from geofinder import Geodata, GeoKeys, Place

halifax_lat = 44.71314


class TestGeodata(unittest.TestCase):
    geodata = None

    """
    Test case - multiple st andrews:
    6155128	St. Andrews	St. Andrews		46.38341	-62.84866	P	PPLL	CA		09			0
    6155129	St. Andrews	St. Andrews		45.55614	-61.88909	P	PPL	    CA		07			0
    6155132	St. Andrews	St. Andrews		50.0714	    -96.98393	P	PPLL	CA		03			0
    6137411	St. Andrews	St. Andrews		45.0737	    -67.05312	P	PPL	    CA		04	        1302
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

    # ===== TEST RESULT CODES
    def test_res_code01(self):
        test = "City.  Good.  upper lowercase"
        lat: float = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(GeoKeys.Result.EXACT_MATCH, self.place.result_type, test)

    def test_res_code02(self):
        test = "City - multiple matches"
        lat: float = self.run_test(test, "Alberton,, Ontario, Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_res_code03(self):
        test = "County - Good.  wrong Province"
        lat: float = self.run_test(test, "Halifax County, Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code11(self):
        test = "City and county  Good."
        lat: float = self.run_test(test, "baldwin mills,estrie,,canada")
        self.assertEqual(GeoKeys.Result.EXACT_MATCH, self.place.result_type, test)

    def test_res_code04(self):
        test = "city - Good. wrong Province"
        lat: float = self.run_test(test, "Halifax, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code05(self):
        test = "multiple county - not unique"
        lat: float = self.run_test(test, "St Andrews,,,Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_res_code06(self):
        test = "City - good. wrong province"
        lat: float = self.run_test(test, "Natuashish, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code07(self):
        test = "City - good. wrong county"
        lat: float = self.run_test(test, "Natuashish, Alberta, ,Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code08(self):
        test = "City - Bad"
        lat: float = self.run_test(test, "Alberton, ,,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_res_code09(self):
        test = "State - Bad"
        lat: float = self.run_test(test, "skdfjd,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_res_code10(self):
        test = "Country - blank"
        lat: float = self.run_test(test, '')
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    # Country
    def test_res_code_country01(self):
        test = "Country - bad"
        lat: float = self.run_test(test, "squid")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_res_code_country02(self):
        test = "No Country - Natuashish"
        lat: float = self.run_test(test, "Natuashish,, ")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_res_code_country03(self):
        test = "No Country - Berlin"
        lat: float = self.run_test(test, "Berlin,,, ")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_res_code_country04(self):
        test = "Country - not supported"
        lat: float = self.run_test(test, "Tokyo,,,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, test)

    def test_res_code_country05(self):
        test = "Country - not supported"
        lat: float = self.run_test(test, "Tokyo,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, test)

    # =====  TEST PLACE TYPE CODES
    def test_place_code01(self):
        test = "Country  verify place type"
        lat: float = self.run_test(test, "Germany")
        self.assertEqual(Place.PlaceType.COUNTRY, self.place.place_type, test)

    def test_place_code02(self):
        test = "State - Bad.  verify place type"
        lat: float = self.run_test(test, "skdfjd,Germany")
        self.assertEqual(Place.PlaceType.ADMIN1, self.place.place_type, test)

    def test_place_code03(self):
        test = "State - Bad.  verify place type.  with prefix"
        lat: float = self.run_test(test, "abc,,,Alberta,Canada")
        self.assertEqual(Place.PlaceType.ADMIN1, self.place.place_type, test)

    def test_place_code04(self):
        test = "County  prioritize city.  verify place type "
        lat: float = self.run_test(test, "Halifax, Nova Scotia, Canada")
        self.assertEqual(Place.PlaceType.CITY, self.place.place_type, test)

    def test_place_code24(self):
        test = "County  prioritize city.  verify place type "
        lat: float = self.run_test(test, "Halifax County, Nova Scotia, Canada")
        self.assertEqual(Place.PlaceType.ADMIN2, self.place.place_type, test)

    def test_place_code05(self):
        test = "County prioritize city verify place type with prefix "
        lat: float = self.run_test(test, "abc,,Halifax, Nova Scotia, Canada")
        self.assertEqual(Place.PlaceType.CITY, self.place.place_type, test)

    def test_place_code25(self):
        test = "County prioritize city verify place type with prefix "
        lat: float = self.run_test(test, "abc,,Halifax County, Nova Scotia, Canada")
        self.assertEqual(Place.PlaceType.ADMIN2, self.place.place_type, test)

    def test_place_code06(self):
        test = "City  verify place type"
        lat: float = self.run_test(test, "Halifax, , Nova Scotia, Canada")
        self.assertEqual(Place.PlaceType.CITY, self.place.place_type, test)

    def test_place_code07(self):
        test = "City  verify place type with prefix"
        lat: float = self.run_test(test, "abc,,Halifax, , Nova Scotia, Canada")
        self.assertEqual(Place.PlaceType.CITY, self.place.place_type, test)

    # ===== TEST PERMUTATIONS for Exact lookups (non wildcard)

    # Country -------------
    def test_country01(self):
        test = "Country -  good"
        lat: float = self.run_test(test, "Canada")
        self.assertEqual('canada', self.place.country_name, test)

    def test_country02(self):
        test = "Country -  bad"
        lat: float = self.run_test(test, "xyzzy")
        self.assertEqual('', self.place.country_iso, test)

    def test_country03(self):
        test = "Country - Good"
        lat: float = self.run_test(test, "Canada")
        self.assertEqual(60.0, lat, test)

    # Province -------------
    def test_province01(self):
        test = "Province - Good"
        lat: float = self.run_test(test, "Alberta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_province02(self):
        test = "Province - Good with prefix"
        lat: float = self.run_test(test, "abcde, , ,Alberta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_province03(self):
        test = "Province - Partial "
        lat: float = self.run_test(test, "new brunswick,Canada")
        self.assertEqual(46.5001, lat, test)

    def test_province04(self):
        test = "Province - bad name"
        lat: float = self.run_test(test, "xyzzy,Canada")
        self.assertEqual('', self.place.admin1_id, test)

    # County ---------------
    def test_county01(self):
        test = "County - good"
        lat: float = self.run_test(test, "Albert County, New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county02(self):
        test = "County - good with prefix"
        lat: float = self.run_test(test, "abcd, ,Albert County, New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county03(self):
        test = "County - Abbreviated good"
        lat: float = self.run_test(test, "Albert Co., New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county04(self):
        test = "County - good.  prioritize Halifax city vs County"
        lat: float = self.run_test(test, "Halifax, Nova Scotia, Canada")
        self.assertEqual(44.71314, lat, test)

    def test_county24(self):
        test = "County - good.  prioritize Halifax city vs County"
        lat: float = self.run_test(test, "Halifax County, Nova Scotia, Canada")
        self.assertEqual(44.86685, lat, test)

    # City -------------------
    def test_city01(self):
        test = "City - good. upper lowercase"
        lat: float = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_city02(self):
        test = "City - good, no county"
        lat: float = self.run_test(test, "Albanel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_city03(self):
        test = "City - Good name, Saint"
        lat: float = self.run_test(test, "Saint Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city04(self):
        test = "City - Good name, St "
        lat: float = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city05(self):
        test = "City - Good name, edberg "
        lat: float = self.run_test(test, "Edberg,,,Canada")
        self.assertEqual(52.78343, lat, test)

    def test_city06(self):
        test = "City - Good name, edburg with U "
        lat: float = self.run_test(test, "Edburg,,,Canada")
        self.assertEqual(52.78343, lat, test)

    def test_city07(self):
        test = "City - Good name, gray creek "
        lat: float = self.run_test(test, "gray creek,,,Canada")
        self.assertEqual(49.63333, lat, test)

    def test_city08(self):
        test = "City - Good name, grey creek with E "
        lat: float = self.run_test(test, "grey creek,,,Canada")
        self.assertEqual(49.63333, lat, test)

    def test_city09(self):
        test = "City - Good name, St. "
        lat: float = self.run_test(test, "St. Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city10(self):
        test = "City - Good name, St. with county and province"
        lat: float = self.run_test(test, "St. Andrews,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_city11(self):
        test = "City - Good , Alberton PEI vs Alberton Ontario"
        lat: float = self.run_test(test, "Alberton,,Prince Edward Island, Canada")
        self.assertEqual(46.81685, lat, test)

    def test_city12(self):
        test = "City - Good , Alberton Ontario vs Alberton PEI"
        lat: float = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual(48.58318, lat, test)

    def test_city13(self):
        test = "City - Good , Halifax, Nova Scotia"
        lat: float = self.run_test(test, "Halifax,, Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, test)

    def test_city14(self):
        test = "City - Good - with prefix"
        lat: float = self.run_test(test, "Oak Street, Halifax, ,Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, test)

    def test_city15(self):
        test = "City - Good - with prefix and wrong county"
        lat: float = self.run_test(test, "Oak Street, Halifax, aaa, Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, test)

    def test_city16(self):
        test = "City -  Good - no county"
        lat: float = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city17(self):
        test = "County - no County"
        lat: float = self.run_test(test, "Albanel, ,Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_city18(self):
        test = "County - Wrong county"
        lat: float = self.run_test(test, "Albanel, Zxzzy, Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_city19(self):
        test = "City - good - Wrong Province"
        lat: float = self.run_test(test, "Halifax, Alberta, Canada")
        self.assertAlmostEqual(-63.71541, float(self.place.lon))

    def test_city20(self):
        test = "City - Good "
        lat: float = self.run_test(test, "Natuashish,,, Canada")
        self.assertEqual(55.91564, lat, test)

    def test_city21(self):
        test = "City - Good "
        lat: float = self.run_test(test, "Natuashish")
        self.assertEqual(55.91564, lat, test)

    def test_city22(self):
        test = "City -  wrong county but single match"
        lat: float = self.run_test(test, "Agassiz,, british columbia, Canada")
        self.assertEqual(49.23298, lat, test)

    def test_city23(self):
        test = "City - good. No Country"
        lat: float = self.run_test(test, "Albanel,,Quebec")
        self.assertEqual(48.88324, lat, test)

    def test_city24(self):
        test = "City - good. city,country"
        lat: float = self.run_test(test, "Natuashish,canada")
        self.assertEqual(55.91564, lat, test)

    def test_city25(self):
        test = "City - from AlternateNames"
        lat: float = self.run_test(test, "Pic du port, canada")
        self.assertEqual(52.28333, lat, test)

    # ===== TEST WILDCARDS
    def test_wildcard01(self):
        test = "Country - wildcard country"
        lat: float = self.run_test(test, "C*da")
        self.assertEqual('canada', self.place.country_name, test)

    def test_wildcard02(self):
        test = "Province - wildcard province"
        lat: float = self.run_test(test, "Al*ta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_wildcard03(self):
        test = "City - good - wildcard city, full county and province"
        lat: float = self.run_test(test, "St. Andr,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_wildcard04(self):
        test = "City - good - wildcard city, no county"
        lat: float = self.run_test(test, "Alb*el,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_wildcard05(self):
        test = "City - good - wildcard city, no county, wild province"
        lat: float = self.run_test(test, "Alb*el,, Queb*, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_wildcard06(self):
        test = "City - good - wildcard city, no county, wild province, wild country"
        lat: float = self.run_test(test, "Alb*el,, Queb*, Can*a")
        self.assertEqual(48.88324, lat, test)

    def test_wildcard07(self):
        test = "City - Wildcard - 300+ matches"
        lat: float = self.run_test(test, "b*,,, CanAda")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    # ===== TEST ADMIN ID

    def test_admin_id01(self):
        test = "Admin2 ID - good "
        lat: float = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual('3559', self.place.admin2_id, test)

    def test_admin_id02(self):
        test = "Admin2 ID - good, no province "
        lat: float = self.run_test(test, "Alberton,Rainy River District, , Canada")
        self.assertEqual('3559', self.place.admin2_id, test)

    def test_admin_id03(self):
        test = "Admin1 ID - good "
        lat: float = self.run_test(test, "Nova Scotia,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_admin_id04(self):
        test = "Admin1 ID - good - abbreviated "
        lat: float = self.run_test(test, "Baden, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_admin_id05(self):
        test = "Admin1 ID - good.  With non-ASCII"
        lat: float = self.run_test(test, "Baden-Württemberg Region, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_admin_id06(self):
        test = "Admin1 ID - good - abbreviated "
        lat: float = self.run_test(test, "Nova,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_admin_id07(self):
        test = "Admin1 ID - good - abbreviated, non-ASCII "
        lat: float = self.run_test(test, "Baden-Württemberg, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    # ===== TEST PARSING
    def test_parse01(self):
        test = "***** Test Parse admin1"
        print(test)
        self.place.parse_place(place_name="aaa,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("alberta", self.place.admin1_name, test)

    def test_parse02(self):
        test = "***** Test Parse admin2"
        print(test)
        self.place.parse_place(place_name="aaa,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("alberta's rockies", self.place.admin2_name, test)

    def test_parse03(self):
        test = "***** Test Parse city with punctuation"
        print(test)
        self.place.parse_place(place_name="aaa,Banff!@#^&()_+-=;:<>/?,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("banff", self.place.city1, test)

    def test_parse04(self):
        test = "***** Test Parse prefix"
        print(test)
        self.place.parse_place(place_name="pref,   abcde,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("pref abcde", self.place.prefix + self.place.prefix_commas, test)

    # =====  TEST Name formatting
    def test_place_name01(self):
        test = "Country  verify place name"
        lat: float = self.run_test(test, "Germany")
        nm = self.place.format_full_name()
        self.assertEqual("Germany", self.place.prefix + self.place.prefix_commas + nm, test)

    def test_place_name03(self):
        test = "State - Bad.  verify place name.  with prefix"
        lat: float = self.run_test(test, "abc,,,Alberta,Canada")
        nm = self.place.format_full_name()
        self.assertEqual("abc, , ,  Alberta, Canada", self.place.prefix + self.place.prefix_commas + nm, test)

    def test_place_name04(self):
        test = "County  verify place name "
        lat: float = self.run_test(test, "Halifax, Nova Scotia, Canada")
        nm = self.place.format_full_name()
        self.assertEqual("Halifax, , Nova Scotia, Canada", self.place.prefix + self.place.prefix_commas + nm, test)

    def test_place_name05(self):
        test = "County  verify place name with prefix. prioritize city "
        lat: float = self.run_test(test, "abc,,Halifax, Nova Scotia, Canada")
        nm = self.place.format_full_name()
        self.assertEqual("abc, Halifax, , Nova Scotia, Canada", self.place.prefix + self.place.prefix_commas + nm, test)

    def test_place_name25(self):
        test = "County  verify place name with prefix "
        lat: float = self.run_test(test, "abc,,Halifax County, Nova Scotia, Canada")
        nm = self.place.format_full_name()
        self.assertEqual("abc, , Halifax County, Nova Scotia, Canada", self.place.prefix + self.place.prefix_commas + nm, test)

    def test_place_name06(self):
        test = "City  verify place name"
        lat: float = self.run_test(test, "Halifax, , Nova Scotia, Canada")
        nm = self.place.format_full_name()
        self.assertEqual("Halifax, , Nova Scotia, Canada", self.place.prefix + self.place.prefix_commas + nm, test)

    def test_place_name07(self):
        test = "City  verify place name with prefix"
        lat: float = self.run_test(test, "abc,,Halifax, , Nova Scotia, Canada")
        nm = self.place.format_full_name()
        self.assertEqual("abc , Halifax, , Nova Scotia, Canada", self.place.prefix + self.place.prefix_commas + nm, test)

    def test_place_name08(self):
        test = "province  verify place name with country"
        lat: float = self.run_test(test, "Alberta")
        nm = self.place.format_full_name()
        self.assertEqual(" Alberta, Canada", self.place.prefix + self.place.prefix_commas + nm, test)

    # ======= TEST Event Year
    def test_eventyear01(self):
        test = "City - good - after start"
        self.place.event_year = 1541
        lat: float = self.run_test(test, "Albanel,, Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_eventyear02(self):
        test = "City - good - before start"
        self.place.event_year = 1540
        lat: float = self.run_test(test, "Albanel,, Quebec, Canada")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_eventyear03(self):
        test = "City - not in list"
        self.place.event_year = 1541
        lat: float = self.run_test(test, "Stuttgart,,,Germany")
        self.assertEqual(48.78232, lat, test)

    # ====== TEST find first match, find geoid
    def test_findfirst01(self):
        test = "City - find first"
        entry = "Berlin,,,Germany"

        print("*****TEST: {}".format(test))
        TestGeodata.geodata.find_first_match(entry, self.place)
        lat = float(self.place.lat)

        self.assertEqual(54.03573, lat, test)

    def test_findgeoid01(self):
        test = "City - find first"
        entry = "Berlin,,,Germany"

        print("*****TEST: {}".format(test))
        TestGeodata.geodata.find_geoid('8133394', self.place)
        lat = float(self.place.lat)

        self.assertEqual(43.69655, lat, test)


if __name__ == '__main__':
    unittest.main()
