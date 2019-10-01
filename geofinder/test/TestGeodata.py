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

from geofinder import Geodata, GeoKeys, Loc

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
            logger.info('Requires ca.txt, gb.txt, de.txt from geonames.org in folder username/geoname_test')
            raise ValueError('Cannot open database')

    def setUp(self) -> None:
        self.place: Loc.Loc = Loc.Loc()

    def run_test(self, title: str, entry: str):
        print("*****TEST: {}".format(title))
        TestGeodata.geodata.find_location(entry, self.place)
        return float(self.place.lat), self.place.prefix + self.place.prefix_commas + self.place.format_full_name()

    # ===== TEST RESULT CODES
    def test_res_code01(self):
        test = "City.  Good.  upper lowercase"
        lat, nm = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(GeoKeys.Result.EXACT_MATCH, self.place.result_type, test)

    def test_res_code02(self):
        test = "City - multiple matches"
        lat, nm = self.run_test(test, "Alberton,, Ontario, Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_res_code03(self):
        test = "County - Good.  wrong Province"
        lat, nm = self.run_test(test, "Halifax County, Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code11(self):
        test = "City and county  Good."
        lat, nm = self.run_test(test, "baldwin mills,estrie,,canada")
        self.assertEqual(GeoKeys.Result.EXACT_MATCH, self.place.result_type, test)

    def test_res_code04(self):
        test = "city - Good. wrong Province"
        lat, nm = self.run_test(test, "Halifax, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code05(self):
        test = "multiple county - not unique"
        lat, nm = self.run_test(test, "St Andrews,,,Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_res_code06(self):
        test = "City - good. wrong province"
        lat, nm = self.run_test(test, "Natuashish, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code07(self):
        test = "City - good. wrong county"
        lat, nm = self.run_test(test, "Natuashish, Alberta, ,Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code08(self):
        test = "City - Bad"
        lat, nm = self.run_test(test, "Alberton, ,,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_res_code09(self):
        test = "State - Bad"
        lat, nm = self.run_test(test, "skdfjd,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, test)

    def test_res_code10(self):
        test = "Country - blank"
        lat, nm = self.run_test(test, '')
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    # Country
    def test_res_code_country01(self):
        test = "Country - bad"
        lat, nm = self.run_test(test, "squid")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_res_code_country02(self):
        test = "No Country - Natuashish"
        lat, nm = self.run_test(test, "Natuashish,, ")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_res_code_country03(self):
        test = "No Country - Berlin"
        lat, nm = self.run_test(test, "Berlin,,, ")
        self.assertEqual(GeoKeys.Result.NO_COUNTRY, self.place.result_type, test)

    def test_res_code_country04(self):
        test = "Country - not supported"
        lat, nm = self.run_test(test, "Tokyo,,,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, test)

    def test_res_code_country05(self):
        test = "Country - not supported"
        lat, nm = self.run_test(test, "Tokyo,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, test)

    # =====  TEST PLACE TYPES
    def test_place_code01(self):
        test = "Country  verify place type"
        lat, nm = self.run_test(test, "Germany")
        self.assertEqual(Loc.PlaceType.COUNTRY, self.place.place_type, test)

    def test_place_code03(self):
        test = "State - Bad.  verify place type.  with prefix"
        lat, nm = self.run_test(test, "abc,,,Alberta,Canada")
        self.assertEqual(Loc.PlaceType.ADMIN1, self.place.place_type, test)

    def test_place_code04(self):
        test = "County  prioritize city.  verify place type "
        lat, nm = self.run_test(test, "Halifax, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.ADMIN2, self.place.place_type, test)

    def test_place_code24(self):
        test = "County  prioritize city.  verify place type "
        lat, nm = self.run_test(test, "Halifax County, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.ADMIN2, self.place.place_type, test)

    def test_place_code05(self):
        test = "County prioritize city verify place type with prefix "
        lat, nm = self.run_test(test, "abc,,Halifax, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.ADMIN2, self.place.place_type, test)

    def test_place_code25(self):
        test = "County prioritize city verify place type with prefix "
        lat, nm = self.run_test(test, "abc,,Halifax County, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.ADMIN2, self.place.place_type, test)

    def test_place_code06(self):
        test = "City  verify place type"
        lat, nm = self.run_test(test, "Halifax, , Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.CITY, self.place.place_type, test)

    def test_place_code07(self):
        test = "City  verify place type with prefix"
        lat, nm = self.run_test(test, "abc,,Halifax, , Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.CITY, self.place.place_type, test)

    # ===== TEST PERMUTATIONS for Exact lookups (non wildcard)

    # Country -------------
    def test_country01(self):
        test = "Country -  good"
        lat, nm = self.run_test(test, "Canada")
        self.assertEqual('canada', self.place.country_name, test)

    def test_country02(self):
        test = "Country -  bad"
        lat, nm = self.run_test(test, "abflab")
        self.assertEqual('', self.place.country_iso, test)

    def test_country03(self):
        test = "Country - Good"
        lat, nm = self.run_test(test, "Canada")
        self.assertEqual(60.0, lat, test)

    # Province ------------- Verify lookup returns correct place (latitude)
    def test_province01(self):
        test = "Province - Good"
        lat, nm = self.run_test(test, "Alberta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_province02(self):
        test = "Province - Good with prefix"
        lat, nm = self.run_test(test, "abcde, , ,Alberta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_province03(self):
        test = "Province - Partial "
        lat, nm = self.run_test(test, "new brunswick,Canada")
        self.assertEqual(46.5001, lat, test)

    def test_province04(self):
        test = "Province - bad name"
        lat, nm = self.run_test(test, "xyzzy,Canada")
        self.assertEqual('', self.place.admin1_id, test)

    # County ---------------Verify lookup returns correct place (latitude)
    def test_county01(self):
        test = "County - good"
        lat, nm = self.run_test(test, "Albert County, New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county02(self):
        test = "County - good with prefix"
        lat, nm = self.run_test(test, "abcd, ,Albert County, New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county03(self):
        test = "County - Abbreviated good"
        lat, nm = self.run_test(test, "Albert Co., New Brunswick, Canada")
        self.assertEqual(45.83346, lat, test)

    def test_county04(self):
        test = "County - good.  prioritize Halifax city vs County"
        lat, nm = self.run_test(test, "Halifax, Nova Scotia, Canada")
        self.assertEqual(44.86685, lat, test)

    def test_county24(self):
        test = "County - good.  prioritize Halifax city vs County"
        lat, nm = self.run_test(test, "Halifax County, Nova Scotia, Canada")
        self.assertEqual(44.86685, lat, test)

    # City - Verify lookup returns correct place (latitude) -------------------
    def test_city01(self):
        test = "City - good. upper lowercase"
        lat, nm = self.run_test(test, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_city02(self):
        test = "City - good, no county"
        lat, nm = self.run_test(test, "Albanel,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_city03(self):
        test = "City - Good name, Saint"
        lat, nm = self.run_test(test, "Saint Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city04(self):
        test = "City - Good name, St "
        lat, nm = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city05(self):
        test = "City - Good name, edberg "
        lat, nm = self.run_test(test, "Edberg,,Alberta,Canada")
        self.assertEqual(52.78343, lat, test)

    def test_city07(self):
        test = "City - Good name, gray gull island "
        lat, nm = self.run_test(test, "gray gull island,,newfoundland and labrador,Canada")
        self.assertEqual(47.5166, lat, test)

    def test_city08(self):
        test = "City - Good name, grey gull island with E "
        lat, nm = self.run_test(test, "grey gull island,,newfoundland and labrador,Canada")
        self.assertEqual(47.5166, lat, test)

    def test_city09(self):
        test = "City - Good name, St. "
        lat, nm = self.run_test(test, "St. Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city10(self):
        test = "City - Good name, St. with county and province"
        lat, nm = self.run_test(test, "St. Andrews,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_city11(self):
        test = "City - Good , Alberton PEI vs Alberton Ontario"
        lat, nm = self.run_test(test, "Alberton,,Prince Edward Island, Canada")
        self.assertEqual(46.81685, lat, test)

    def test_city12(self):
        test = "City - Good , Alberton Ontario vs Alberton PEI"
        lat, nm = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual(48.58318, lat, test)

    def test_city13(self):
        test = "City - Good , Halifax, Nova Scotia"
        lat, nm = self.run_test(test, "Halifax,, Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, test)

    def test_city14(self):
        test = "City - Good - with prefix"
        lat, nm = self.run_test(test, "Oak Street, Halifax, ,Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, test)

    def test_city15(self):
        test = "City - Good - with prefix and wrong county"
        lat, nm = self.run_test(test, "Oak Street, Halifax, aaa, Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, test)

    def test_city16(self):
        test = "City -  Good - no county"
        lat, nm = self.run_test(test, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, test)

    def test_city17(self):
        test = "County - no County"
        lat, nm = self.run_test(test, "Albanel, ,Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_city18(self):
        test = "County - Wrong county"
        lat, nm = self.run_test(test, "Albanel, Zxzzy, Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_city19(self):
        test = "City - good - Wrong Province"
        lat, nm = self.run_test(test, "Halifax, Alberta, Canada")
        self.assertAlmostEqual(-63.71541, float(self.place.lon))

    def test_city20(self):
        test = "City - Good "
        lat, nm = self.run_test(test, "Natuashish,,, Canada")
        self.assertEqual(55.91564, lat, test)

    def test_city21(self):
        test = "City - Good "
        lat, nm = self.run_test(test, "Natuashish")
        self.assertEqual(55.91564, lat, test)

    def test_city22(self):
        test = "City -  wrong county but single match"
        lat, nm = self.run_test(test, "Agassiz,, british columbia, Canada")
        self.assertEqual(49.23298, lat, test)

    def test_city23(self):
        test = "City - good. No Country"
        lat, nm = self.run_test(test, "Albanel,,Quebec")
        self.assertEqual(48.88324, lat, test)

    def test_city24(self):
        test = "City - good. city,country"
        lat, nm = self.run_test(test, "Natuashish,canada")
        self.assertEqual(55.91564, lat, test)

    # def test_city25(self):
    #   test = "City - from AlternateNames"
    #   lat, nm = self.run_test(test, "Pic du port, canada")
    #   self.assertEqual(52.28333, lat, test)

    def test_city26(self):
        test = "City - Edensor, Derbyshire "
        lat, nm = self.run_test(test, "Edensor, Derbyshire ")
        self.assertEqual(53.22662, lat, test)

    def test_city27(self):
        test = "City - Somersetshire, England "
        lat, nm = self.run_test(test, "Somersetshire, England")
        self.assertEqual(51.08333, lat, test)

    def test_city28(self):
        test = "City - Lower Grosvenor Street, London, England "
        lat, nm = self.run_test(test, "Lower Grosvenor Street, London, England")
        self.assertEqual(52.28333, lat, test)

    def test_city29(self):
        test = "City - Lower Grosvenor Street, London, London, England"
        lat, nm = self.run_test(test, "Lower Grosvenor Street, London, London, England")
        self.assertEqual(51.50853, lat, test)

    def test_city30(self):
        test = "City - Old Bond Street, London, Middlesex, England"
        lat, nm = self.run_test(test, "Old Bond Street, London, Middlesex, England")
        self.assertEqual(51.50853, lat, test)

    def test_city31(self):
        test = "City - St. Margaret, Westminster, London, England"
        lat, nm = self.run_test(test, "St. Margaret, Westminster, London, England")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    def test_city32(self):
        test = "City - Amsterdam, Zuiderkerk"
        lat, nm = self.run_test(test, "Amsterdam, Zuiderkerk")
        self.assertEqual(52.37403, lat, test)

    # ===== TEST WILDCARDS Verify lookup returns correct place (latitude)
    def test_wildcard02(self):
        test = "Province - wildcard province"
        lat, nm = self.run_test(test, "Al*ta, Canada")
        self.assertEqual(52.28333, lat, test)

    def test_wildcard03(self):
        test = "City - good - wildcard city, full county and province"
        lat, nm = self.run_test(test, "St. Andr,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, test)

    def test_wildcard04(self):
        test = "City - good - wildcard city, no county"
        lat, nm = self.run_test(test, "Alb*el,, Quebec, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_wildcard05(self):
        test = "City - good - wildcard city, no county, wild province"
        lat, nm = self.run_test(test, "Alb*el,, Queb*, CanAda")
        self.assertEqual(48.88324, lat, test)

    def test_wildcard06(self):
        test = "City - good - wildcard city, no county, wild province, wild country"
        lat, nm = self.run_test(test, "Alb*el,, Queb*, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_wildcard07(self):
        test = "City - Wildcard - 300+ matches"
        lat, nm = self.run_test(test, "b*,,, CanAda")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, test)

    # ===== TEST ADMIN ID Verify lookup returns correct place (ID)

    def test_admin_id01(self):
        test = "Admin2 ID - good "
        lat, nm = self.run_test(test, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual('3559', self.place.admin2_id, test)

    def test_admin_id02(self):
        test = "Admin2 ID - good, no province "
        lat, nm = self.run_test(test, "Alberton,Rainy River District, , Canada")
        self.assertEqual('3559', self.place.admin2_id, test)

    def test_admin_id03(self):
        test = "Admin1 ID - good "
        lat, nm = self.run_test(test, "Nova Scotia,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_admin_id04(self):
        test = "Admin1 ID - good - abbreviated "
        lat, nm = self.run_test(test, "Baden, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_admin_id05(self):
        test = "Admin1 ID - good.  With non-ASCII"
        lat, nm = self.run_test(test, "Baden-Württemberg Region, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    def test_admin_id06(self):
        test = "Admin1 ID - good - abbreviated "
        lat, nm = self.run_test(test, "Nova,Canada")
        self.assertEqual('07', self.place.admin1_id, test)

    def test_admin_id07(self):
        test = "Admin1 ID - good - abbreviated, non-ASCII "
        lat, nm = self.run_test(test, "Baden-Württemberg, Germany")
        self.assertEqual('01', self.place.admin1_id, test)

    # ===== TEST PARSING Verify lookup returns correct place (name)
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
        self.place.parse_place(place_name="aaa,Banff!@#^&)_+-=;:<>/?,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("banff", self.place.city1, test)

    def test_parse04(self):
        test = "***** Test Parse prefix"
        print(test)
        self.place.parse_place(place_name="pref,   abcde,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("pref abcde", self.place.prefix + self.place.prefix_commas, test)

    # =====  TEST verify Name formatting
    def test_place_name01(self):
        test = "Country  verify place name"
        lat, nm = self.run_test(test, "Germany")
        self.assertEqual("Germany", nm, test)

    def test_place_name03(self):
        test = "State - Bad.  verify place name.  with prefix"
        lat, nm = self.run_test(test, "abc,,,Alberta,Canada")
        self.assertEqual("abc,  Alberta, Canada", nm, test)

    def test_place_name04(self):
        test = "County  verify place name "
        lat, nm = self.run_test(test, "Halifax, Nova Scotia, Canada")
        self.assertEqual("Halifax County, Nova Scotia, Canada", nm, test)

    def test_place_name05(self):
        test = "County  verify place name with prefix. prioritize city "
        lat, nm = self.run_test(test, "abc,,Halifax, Nova Scotia, Canada")
        self.assertEqual("abc, Halifax County, Nova Scotia, Canada", nm, test)

    def test_place_name25(self):
        test = "County  verify place name with prefix "
        lat, nm = self.run_test(test, "abc,,Halifax County, Nova Scotia, Canada")
        self.assertEqual("abc, Halifax County, Nova Scotia, Canada", nm, test)

    def test_place_name06(self):
        test = "City  verify place name"
        lat, nm = self.run_test(test, "Halifax, , Nova Scotia, Canada")
        self.assertEqual("Halifax, , Nova Scotia, Canada", nm, test)

    def test_place_name07(self):
        test = "City  verify place name with prefix"
        lat, nm = self.run_test(test, "abc,,Halifax, , Nova Scotia, Canada")
        self.assertEqual("abc , Halifax, , Nova Scotia, Canada", nm, test)

    def test_place_name08(self):
        test = "province  verify place name with country"
        lat, nm = self.run_test(test, "Alberta")
        self.assertEqual(" Alberta, Canada", nm, test)

    def test_place_name09(self):
        test = "City - Edensor, Derbyshire "
        lat, nm = self.run_test(test, "Edensor, Derbyshire ")
        self.assertEqual("Edensor, Derbyshire, England, United Kingdom", nm, test)

    def test_place_name10(self):
        test = "City - Somersetshire, England "
        lat, nm = self.run_test(test, "Somersetshire, England")
        self.assertEqual("Somersetshire, England, United Kingdom", nm, test)

    def test_place_name11(self):
        test = "City - Lower Grosvenor Street, London, England "
        lat, nm = self.run_test(test, "Lower Grosvenor Street, London, England")
        self.assertEqual("Lower Grosvenor Street, London, England, United Kingdom", nm, test)

    def test_place_name12(self):
        test = "City - Lower Grosvenor Street, London, London, England"
        lat, nm = self.run_test(test, "Lower Grosvenor Street, London, London, England")
        self.assertEqual("Lower Grosvenor Street, London, Greater London, England, United Kingdom", nm, test)

    def test_place_name13(self):
        test = "City - Old Bond Street, London, Middlesex, England"
        lat, nm = self.run_test(test, "Old Bond Street, London, Middlesex, England")
        self.assertEqual("Old Bond Street, London, Greater London, England, United Kingdom", nm, test)

    def test_place_name14(self):
        test = "City - St. Margaret, Westminster, London, England"
        lat, nm = self.run_test(test, "St. Margaret, Westminster, London, England")
        self.assertEqual("St. Margaret, Westminster, London, England, United Kingdom", nm, test)

    def test_place_name15(self):
        test = "City - Amsterdam, Zuiderkerk"
        lat, nm = self.run_test(test, "Amsterdam, Zuiderkerk")
        self.assertEqual("Zuiderkerk, Amsterdam, Gemeente Amsterdam, Provincie Noord Holland, Netherlands", nm, test)

    # ======= TEST Event Year handling
    def test_eventyear01(self):
        test = "City - good - and after city start"
        self.place.event_year = 1541
        lat, nm = self.run_test(test, "Albanel,, Quebec, Canada")
        self.assertEqual(48.88324, lat, test)

    def test_eventyear02(self):
        test = "City - good - but before city start"
        self.place.event_year = 1540
        lat, nm = self.run_test(test, "Albanel,, Quebec, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, test)

    def test_eventyear03(self):
        test = "City - not in list"
        self.place.event_year = 1541
        lat, nm = self.run_test(test, "Stuttgart,,,Germany")
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
