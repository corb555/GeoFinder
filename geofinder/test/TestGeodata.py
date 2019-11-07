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

halifax_lat = 44.646
bruce_cty_lat = 44.50009
albanel_lat = 48.91492


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
            raise ValueError('Missing ca.txt, gb.txt, de.txt from geonames.org')

    def setUp(self) -> None:
        self.place: Loc.Loc = Loc.Loc()

    def run_test(self, title: str, entry: str):
        #if title not in ['903']:
        #    return 99.9, 'XX'

        print("*****TEST: {}".format(title))
        TestGeodata.geodata.find_location(entry, self.place, False)
        flags = TestGeodata.geodata.build_result_list(self.place)
        # If multiple matches, truncate to first match
        lat = self.place.lat
        if len(self.place.georow_list) > 0:
            lat = self.place.georow_list[0][GeoKeys.Entry.LAT]
            self.place.georow_list = self.place.georow_list[:1]
            TestGeodata.geodata.process_result(place=self.place, flags=flags)

            nm = f'{self.place.format_full_nm(TestGeodata.geodata.geo_files.output_replace_dct)}'
            print(f'Found pre=[{self.place.prefix}{self.place.prefix_commas}] Nam=[{nm}]')
            return float(lat), self.place.prefix+self.place.prefix_commas+nm
        else:
            return float(lat), 'NO MATCH'


    # ===== TEST RESULT CODES


    def test_res_code01(self):
        title = "City.  Good.  upper lowercase"
        lat, name = self.run_test(title, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(GeoKeys.Result.STRONG_MATCH, self.place.result_type, title)

    def test_res_code02(self):
        title = "City - multiple matches"
        lat, name = self.run_test(title, "Alberton,, Ontario, Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, title)

    def test_res_code03(self):
        title = "County - Good.  wrong Province"
        lat, name = self.run_test(title, "Halifax County, Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, title)

    def test_res_code11(self):
        title = "City and county  Good."
        lat, name = self.run_test(title, "baldwin mills,estrie,,canada")
        self.assertEqual(GeoKeys.Result.STRONG_MATCH, self.place.result_type, title)

    def test_res_code04(self):
        title = "city - Good. wrong Province"
        lat, name = self.run_test(title, "Halifax, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, title)

    def test_res_code05(self):
        title = "multiple county - not unique"
        lat, name = self.run_test(title, "St Andrews,,,Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, title)

    def test_res_code06(self):
        title = "City - good. wrong province"
        lat, name = self.run_test(title, "Natuashish, ,Alberta, Canada")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, title)

    def test_res_code07(self):
        title = "City - good. wrong county"
        lat, name = self.run_test(title, "Natuashish, Alberta, ,Canada")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, title)

    def test_res_code08(self):
        title = "City - Bad"
        lat, name = self.run_test(title, "Alberton, ,,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, title)

    def test_res_code09(self):
        title = "State - Bad"
        lat, name = self.run_test(title, "skdfjd,Germany")
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, title)

    def test_res_code10(self):
        title = "Country - blank"
        lat, name = self.run_test(title, '')
        self.assertEqual(GeoKeys.Result.NO_MATCH, self.place.result_type, title)

    # Country
    def test_res_code_country01(self):
        title = "Country - bad"
        lat, name = self.run_test(title, "squid")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, title)

    def test_res_code_country02(self):
        title = "No Country - Natuashish"
        lat, name = self.run_test(title, "Natuashish,, ")
        self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, title)

    def test_res_code_country03(self):
        title = "No Country - Berlin"
        lat, name = self.run_test(title, "Berlin,,, ")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, title)

    def test_res_code_country04(self):
        title = "Country - not supported"
        lat, name = self.run_test(title, "Tokyo,,,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, title)

    def test_res_code_country05(self):
        title = "Country - not supported"
        lat, name = self.run_test(title, "Tokyo,Japan")
        self.assertEqual(GeoKeys.Result.NOT_SUPPORTED, self.place.result_type, title)

    # =====  TEST PLACE TYPES
    def test_place_code01(self):
        title = "Country  verify place type"
        lat, name = self.run_test(title, "Germany")
        self.assertEqual(Loc.PlaceType.COUNTRY, self.place.place_type, title)

    def test_place_code03(self):
        title = "State - Bad.  verify place type.  with prefix"
        lat, name = self.run_test(title, "abc,,,Alberta,Canada")
        self.assertEqual(Loc.PlaceType.ADMIN1, self.place.place_type, title)

    def test_place_code04(self):
        title = "County  prioritize city.  verify place type "
        lat, name = self.run_test(title, "Halifax, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.CITY, self.place.place_type, title)

    def test_place_code24(self):
        title = "County  prioritize city.  verify place type "
        lat, name = self.run_test(title, "Halifax County, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.ADMIN2, self.place.place_type, title)

    def test_place_code05(self):
        title = "County prioritize city verify place type with prefix "
        lat, name = self.run_test(title, "abc,,Halifax, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.CITY, self.place.place_type, title)

    def test_place_code25(self):
        title = "County prioritize city verify place type with prefix "
        lat, name = self.run_test(title, "abc,,Halifax County, Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.ADMIN2, self.place.place_type, title)

    def test_place_code06(self):
        title = "City  verify place type"
        lat, name = self.run_test(title, "Halifax, , Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.CITY, self.place.place_type, title)

    def test_place_code07(self):
        title = "City  verify place type with prefix"
        lat, name = self.run_test(title, "abc,,Halifax, , Nova Scotia, Canada")
        self.assertEqual(Loc.PlaceType.CITY, self.place.place_type, title)


    # ===== TEST PERMUTATIONS for Exact lookups (non wildcard)

    # Country -------------
    def test_country01(self):
        title = "Country -  good"
        lat, name = self.run_test(title, "Canada")
        self.assertEqual('canada', self.place.country_name, title)

    def test_country02(self):
        title = "Country -  bad"
        lat, name = self.run_test(title, "abflab")
        self.assertEqual('', self.place.country_iso, title)

    def test_country03(self):
        title = "Country - Good"
        lat, name = self.run_test(title, "Canada")
        self.assertEqual(60.0, lat, title)

    # Province ------------- Verify lookup returns correct place (latitude)
    def test_province01(self):
        title = "Province - Good"
        lat, name = self.run_test(title, "Alberta, Canada")
        self.assertEqual(52.28333, lat, title)

    def test_province02(self):
        title = "Province - Good with prefix"
        lat, name = self.run_test(title, "abcde, , ,Alberta, Canada")
        self.assertEqual(52.28333, lat, title)

    def test_province03(self):
        title = "Province - Partial "
        lat, name = self.run_test(title, "new brunswick,Canada")
        self.assertEqual(46.5001, lat, title)

    def test_province04(self):
        title = "Province - bad name"
        lat, name = self.run_test(title, "notaplace,Canada")
        self.assertEqual('', self.place.admin1_id, title)

    # County ---------------Verify lookup returns correct place (latitude)
    def test_county01(self):
        title = "County - good Bruce County"
        lat, name = self.run_test(title, "Bruce County, Ontario, Canada")
        self.assertEqual(bruce_cty_lat, lat, title)

    def test_county02(self):
        title = "County - good with prefix Bruce County"
        lat, name = self.run_test(title, "abcd, ,Bruce County, Ontario, Canada")
        self.assertEqual(bruce_cty_lat, lat, title)

    def test_county03(self):
        title = "County - Abbreviated good Bruce Co."
        lat, name = self.run_test(title, "Bruce Co., Ontario, Canada")
        self.assertEqual(bruce_cty_lat, lat, title)

    def test_county04(self):
        title = "County - good.  prioritize Halifax city vs County"
        lat, name = self.run_test(title, "Halifax, Nova Scotia, Canada")
        self.assertEqual(44.646, lat, title)

    def test_county24(self):
        title = "County - good.  prioritize Halifax city vs County"
        lat, name = self.run_test(title, "Halifax County, Nova Scotia, Canada")
        self.assertEqual(44.86685, lat, title)

    # City - Verify lookup returns correct place (latitude) -------------------
    def test_city01(self):
        title = "City - good. upper lowercase"
        lat, name = self.run_test(title, "AlbAnel,, Quebec, CanAda")
        self.assertEqual(48.91492, lat, title)

    def test_city02(self):
        title = "City - good, no county"
        lat, name = self.run_test(title, "Albanel,, Quebec, CanAda")
        self.assertEqual(48.91492, lat, title)

    def test_city03(self):
        title = "City - Good name, Saint"
        lat, name = self.run_test(title, "Saint Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, title)

    def test_city04(self):
        title = "City - Good name, St "
        lat, name = self.run_test(title, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, title)

    def test_city05(self):
        title = "City - Good name, edberg "
        lat, name = self.run_test(title, "Edberg,,Alberta,Canada")
        self.assertEqual(52.78565, lat, title)

    def test_city07(self):
        title = "City - Good name, gray gull island "
        lat, name = self.run_test(title, "gray gull island,,newfoundland and labrador,Canada")
        self.assertEqual(47.5166, lat, title)

    def test_city08(self):
        title = "City - Good name, grey gull island with E "
        lat, name = self.run_test(title, "grey gull island,,newfoundland and labrador,Canada")
        self.assertEqual(47.5166, lat, title)

    def test_city09(self):
        title = "City - Good name, St. "
        lat, name = self.run_test(title, "St. Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, title)

    def test_city10(self):
        title = "City - Good name, St. with county and province"
        lat, name = self.run_test(title, "St. Andrews,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, title)

    def test_city11(self):
        title = "City - Good , Alberton PEI vs Alberton Ontario"
        lat, name = self.run_test(title, "Alberton,,Prince Edward Island, Canada")
        self.assertEqual(46.81685, lat, title)

    def test_city12(self):
        title = "City - Good , Alberton Ontario vs Alberton PEI"
        lat, name = self.run_test(title, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual(48.58318, lat, title)

    def test_city13(self):
        title = "City - Good , Halifax, Nova Scotia"
        lat, name = self.run_test(title, "Halifax,, Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, title)

    def test_city14(self):
        title = "City - Good - with prefix"
        lat, name = self.run_test(title, "Oak Street, Halifax, ,Nova Scotia, Canada")
        self.assertEqual(halifax_lat, lat, title)

    def test_city15(self):
        title = "City - Good - with prefix and wrong county"
        lat, name = self.run_test(title, "Oak Street, Halifax, aaa, Nova Scotia, Canada")
        self.assertEqual(44.646, lat, title)

    def test_city16(self):
        title = "City -  Good - no county"
        lat, name = self.run_test(title, "St Andrews,,Nova Scotia,Canada")
        self.assertEqual(45.55614, lat, title)

    def test_city17(self):
        title = "County - no County"
        lat, name = self.run_test(title, "Albanel, ,Quebec, Canada")
        self.assertEqual(albanel_lat, lat, title)

    def test_city18(self):
        title = "County - Wrong county"
        lat, name = self.run_test(title, "Albanel, Zxzzy, Quebec, Canada")
        self.assertEqual(albanel_lat, lat, title)

    def test_city19(self):
        title = "City - good - Halifax ALBERTA Province"
        lat, name = self.run_test(title, "Halifax Coulee, Alberta, Canada")
        self.assertEqual(-113.78523, float(self.place.lon))

    def test_city20(self):
        title = "City - Good "
        lat, name = self.run_test(title, "Natuashish,,, Canada")
        self.assertEqual(55.91564, lat, title)

    def test_city21(self):
        title = "City - Good "
        lat, name = self.run_test(title, "Natuashish")
        self.assertEqual(55.91564, lat, title)

    def test_city22(self):
        title = "City -  wrong county but single match"
        lat, name = self.run_test(title, "Agassiz,, british columbia, Canada")
        self.assertEqual(49.23298, lat, title)

    def test_city23(self):
        title = "City - good. No Country"
        lat, name = self.run_test(title, "Albanel,,Quebec")
        self.assertEqual(albanel_lat, lat, title)

    def test_city24(self):
        title = "City - good. city,country"
        lat, name = self.run_test(title, "Natuashish,canada")
        self.assertEqual(55.91564, lat, title)

    # def test_city25(self):
    #   title = "City - from AlternateNames"
    #   lat, name = self.run_test(title, "Pic du port, canada")
    #   self.assertEqual(52.28333, lat, title)

    def test_city26(self):
        title = "City - Edensor, Derbyshire "
        lat, name = self.run_test(title, "Edensor, Derbyshire ")
        self.assertEqual(53.22662, lat, title)

    def test_city27(self):
        title = "City - Somersetshire, England "
        lat, name = self.run_test(title, "Somersetshire, England")
        self.assertEqual(51.08333, lat, title)

    def test_city28(self):
        title = "City - Lower Grosvenor Street, London, England "
        lat, name = self.run_test(title, "Lower Grosvenor Street, London, England")
        self.assertEqual(51.50853, lat, title)

    def test_city29(self):
        title = "City - Lower Grosvenor Street, London, London, England"
        lat, name = self.run_test(title, "Lower Grosvenor Street, London, London, England")
        self.assertEqual(51.50853, lat, title)

    def test_city30(self):
        title = "City - Old Bond Street, London, Middlesex, England"
        lat, name = self.run_test(title, "Old Bond Street, London, Middlesex, England")
        self.assertEqual(51.53174, lat, title)

    def test_city31(self):
        title = "City - St. Margaret, Westminster, London, England"
        lat, name = self.run_test(title, "St. Margaret, Westminster, London, England")
        self.assertEqual(GeoKeys.Result.MULTIPLE_MATCHES, self.place.result_type, title)

    def test_city32(self):
        title = "City - Amsterdam, Zuiderkerk"
        lat, name = self.run_test(title, "Amsterdam, Zuiderkerk")
        self.assertEqual(52.37027, lat, title)

    def test_city33(self):
        title = "City - Amsterdam, Spiegelplein 9"
        lat, name = self.run_test(title, "Amsterdam, Spiegelplein 9")
        self.assertEqual(52.37403, lat, title)

    def test_city34(self):
        title = "City - Rooms-Katholieke begraafplaats ‘Buitenveldert’, Amsterdam"
        lat, name = self.run_test(title, "Rooms-Katholieke begraafplaats ‘Buitenveldert’, Amsterdam")
        self.assertEqual(52.31926, lat, title)

    # ===== TEST WILDCARDS Verify lookup returns correct place (latitude)
    def test_wildcard02(self):
        title = "Province - wildcard province"
        lat, name = self.run_test(title, "Al*ta, Canada")
        self.assertEqual(52.28333, lat, title)

    def test_wildcard03(self):
        title = "City - good - wildcard city, full county and province"
        lat, name = self.run_test(title, "St. Andr,Charlotte County,new brunswick,Canada")
        self.assertEqual(45.0737, lat, title)

    def test_wildcard04(self):
        title = "City - good - wildcard city, no county"
        lat, name = self.run_test(title, "Alb*el,, Quebec, CanAda")
        self.assertEqual(51.36681, lat, title)

    def test_wildcard05(self):
        title = "City - good - wildcard city, no county, wild province"
        lat, name = self.run_test(title, "Alb*el,, Queb*, CanAda")
        self.assertEqual(51.36681, lat, title)

    def test_wildcard06(self):
        title = "City - good - wildcard city, no county, wild province, wild country"
        lat, name = self.run_test(title, "Alb*el,, Queb*, Canada")
        self.assertEqual(51.36681, lat, title)

    #def test_wildcard07(self):
    #    title = "City - Wildcard - 300+ matches"
    #    lat, name = self.run_test(title, "b*,,, CanAda")
    #    self.assertEqual(GeoKeys.Result.PARTIAL_MATCH, self.place.result_type, title)

    # ===== TEST ADMIN ID Verify lookup returns correct place (ID)

    def test_admin_id01(self):
        title = "Admin2 ID - good "
        lat, name = self.run_test(title, "Alberton,Rainy River District,Ontario, Canada")
        self.assertEqual('3559', self.place.admin2_id, title)

    def test_admin_id02(self):
        title = "Admin2 ID - good, no province "
        lat, name = self.run_test(title, "Alberton,Rainy River District, , Canada")
        self.assertEqual('3559', self.place.admin2_id, title)

    def test_admin_id03(self):
        title = "Admin1 ID - good "
        lat, name = self.run_test(title, "Nova Scotia,Canada")
        self.assertEqual('07', self.place.admin1_id, title)

    def test_admin_id04(self):
        title = "Admin1 ID - good - abbreviated "
        lat, name = self.run_test(title, "Baden, Germany")
        self.assertEqual('01', self.place.admin1_id, title)

    def test_admin_id05(self):
        title = "Admin1 ID - good.  With non-ASCII"
        lat, name = self.run_test(title, "Baden-Württemberg Region, Germany")
        self.assertEqual('01', self.place.admin1_id, title)

    def test_admin_id06(self):
        title = "Admin1 ID - good - abbreviated "
        lat, name = self.run_test(title, "Nova,Canada")
        self.assertEqual('07', self.place.admin1_id, title)

    def test_admin_id07(self):
        title = "Admin1 ID - good - abbreviated, non-ASCII "
        lat, name = self.run_test(title, "Baden-Württemberg, Germany")
        self.assertEqual('01', self.place.admin1_id, title)


    # ===== TEST PARSING Verify lookup returns correct place (name)
    def test_parse01(self):
        title = "***** Test Parse admin1"
        print(title)
        self.place.parse_place(place_name="aaa,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("alberta", self.place.admin1_name, title)

    def test_parse02(self):
        title = "***** Test Parse admin2"
        print(title)
        self.place.parse_place(place_name="aaa,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("alberta's rockies", self.place.admin2_name, title)

    def test_parse03(self):
        title = "***** Test Parse city with punctuation"
        print(title)
        self.place.parse_place(place_name="aaa,Banff!@#^&)_+-=;:<>/?,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("banff", self.place.city1, title)

    def test_parse04(self):
        title = "***** Test Parse prefix"
        print(title)
        self.place.parse_place(place_name="pref,   abcde,Banff,Alberta's Rockies,Alberta,Canada", geo_files=TestGeodata.geodata.geo_files)
        self.assertEqual("pref abcde", self.place.prefix + self.place.prefix_commas, title)

    # =====  TEST Verify Name formatting

    def test_place_name01(self):
        title = "Country  verify place name"
        lat, name = self.run_test(title, "Germany")
        self.assertEqual("Germany", name, title)

    def test_place_name03(self):
        title = "111"
        lat, name = self.run_test(title, "Alberta,Canada")
        self.assertEqual("Alberta, Canada", name, title)

    def test_place_name04(self):
        title = "555"
        lat, name = self.run_test(title, "Halifax, Nova Scotia, Canada")
        self.assertEqual("Halifax, , Nova Scotia, Canada", name, title)

    def test_place_name05(self):
        title = "County  verify place name with prefix. prioritize city "
        lat, name = self.run_test(title, "abc,,Halifax, Nova Scotia, Canada")
        self.assertEqual("Abc, Halifax, , Nova Scotia, Canada", name, title)

    def test_place_name06(self):
        title = "City  verify place name"
        lat, name = self.run_test(title, "Halifax, , Nova Scotia, Canada")
        self.assertEqual("Halifax, , Nova Scotia, Canada", name, title)

    def test_place_name07(self):
        title = "City  verify place name with prefix"
        lat, name = self.run_test(title, "abc,Halifax, , Nova Scotia, Canada")
        self.assertEqual("Abc, Halifax, , Nova Scotia, Canada", name, title)

    def test_place_name08(self):
        title = "province  verify place name with country"
        lat, name = self.run_test(title, "Alberta")
        self.assertEqual("Alberta, Canada", name, title)

    def test_place_name09(self):
        title = "City - Edensor, Derbyshire "
        lat, name = self.run_test(title, "Edensor, Derbyshire ")
        self.assertEqual("Edensor, Derbyshire, England, United Kingdom", name, title)

    def test_place_name10(self):
        title = "City - Somersetshire, England "
        lat, name = self.run_test(title, "Somersetshire, England")
        self.assertEqual("Somersetshire, Somerset, England, United Kingdom", name, title)

    def test_place_name11(self):
        title = "City - Lower Grosvenor Street, London, England "
        lat, name = self.run_test(title, "Lower Grosvenor Street, London, England")
        self.assertEqual("Lower Grosvenor Street, London, Greater London, England, United Kingdom", name, title)

    def test_place_name12(self):
        title = "City - Lower Grosvenor Street, London, London, England"
        lat, name = self.run_test(title, "Lower Grosvenor Street, London, London, England")
        self.assertEqual("Lower Grosvenor Street, London, Greater London, England, United Kingdom", name, title)

    def test_place_name13(self):
        title = "City - Old Bond Street, London, Middlesex, England"
        lat, name = self.run_test(title, "Old Bond Street, London, Middlesex, England")
        self.assertEqual("Old Bond Street, Middlesex, Greater London, England, United Kingdom", name, title)

    def test_place_name14(self):
        title = "name" #""City - St. Margaret, Westminster, London, England"
        lat, name = self.run_test(title, "St. Margaret, Westminster, London, England")
        self.assertEqual("St Margaret, London, Greater London, England, United Kingdom", name, title)

    def test_place_name15(self):
        title = "City - Amsterdam, Zuiderkerk"
        lat, name = self.run_test(title, "Amsterdam, Zuiderkerk")
        self.assertEqual("Zuiderkerk,  Amsterdam,  Noord Holland, Netherlands", name, title)

    def test_place_name16(self):
        title = "City - Amsterdam, Spiegelplein 9"
        lat, name = self.run_test(title, "Amsterdam, Spiegelplein 9")
        self.assertEqual("Spiegelplein 9, Amsterdam,  Amsterdam,  Noord Holland, Netherlands", name, title)

    def test_place_name17(self):
        title = "City - Rooms-Katholieke begraafplaats ‘Buitenveldert’, Amsterdam"
        lat, name = self.run_test(title, "Rooms-Katholieke begraafplaats ‘Buitenveldert’, Amsterdam, netherlands")
        self.assertEqual("Rooms Katholieke Begraafplaats 'Buitenveldert', Amsterdam Duivendrecht,  Ouder Amstel,  Noord Holland, Netherlands",
                         name, title)

    def test_place_name18(self):
        title = "City - Troyes, Aube,  , France"
        lat, name = self.run_test(title, "Troyes, Aube,  , France")
        self.assertEqual("Troyes, Departement De L'Aube, Grand Est, France",
                         name, title)

    def test_place_name19(self):
        title = "City - Hoxa ,Ronaldsay, orkney, scotland"
        lat, name = self.run_test(title, "Hoxa ,Ronaldsay, orkney, scotland")
        self.assertEqual("Hoxa, Orkney, Orkney Islands, Scotland, United Kingdom",
                         name, title)

    def test_place_name20(self):
        title = "City - Paris, France"
        lat, name = self.run_test(title, "Paris, France")
        self.assertEqual("Paris, Paris, Ile De France, France",
                         name, title)

    def test_place_name21(self):
        title = "City - Oak Street, Toronto, Ontario, Canada"
        lat, name = self.run_test(title, "Oak Street, Toronto, Ontario, Canada")
        self.assertEqual("Oak Street, Toronto, , Ontario, Canada",
                         name, title)

    def test_place_name22(self):
        title = "City - Evreux, Eure, Normandy, France"
        lat, name = self.run_test(title, "Evreux, Eure, Normandy, France")
        self.assertEqual("Evreux, Departement De L'Eure, Normandie, France",
                         name, title)

    def test_place_name23(self):
        title = "City - St. Janskathedraal, 's Hertogenbosch"
        lat, name = self.run_test(title, "St. Janskathedraal, 's Hertogenbosch")
        self.assertEqual("St Janskathedraal, 'S Hertogenbosch,  'S Hertogenbosch,  Noord Brabant, Netherlands",
                         name, title)

    def test_place_name24(self):
        title = "City - Cambridge, cambridgeshire , England"
        lat, name = self.run_test(title, "Cambridge, cambridgeshire , England")
        self.assertEqual("Cambridge, Cambridgeshire, England, United Kingdom",
                         name, title)

    def test_place_name25(self):
        title = "City soundex - Parus, France"
        lat, name = self.run_test(title, "Parus, Ile De France, France")
        self.assertEqual("Parus, Paris, Paris, Ile De France, France",
                         name, title)

    def test_place_name26(self):
        title = "City soundex - Taronto, Canada"
        lat, name = self.run_test(title, "Taronto, Ontario, Canada")
        self.assertEqual("Taronto, Toronto, , Ontario, Canada",
                         name, title)

    def test_place_name27(self):
        title = "County  verify place name with prefix "
        lat, name = self.run_test(title, "abc,,Halifax County, Nova Scotia, Canada")
        self.assertEqual("Abc, Halifax County, Nova Scotia, Canada", name, title)

    def test_place_name29(self):
        title = "County  verify not found "
        lat, name = self.run_test(title, "khjdfh,Halifax , Nova Scotia, Canada")
        self.assertEqual("Khjdfh, Halifax, , Nova Scotia, Canada", name, title)
    
    def test_place_name28(self):
        title = "Advanced search - albanel,--country=ca"
        lat, name = self.run_test(title, "albanel,--country=CA")
        self.assertEqual("Country Ca, Albanel, Saguenay Lac St Jean, Quebec, Canada", name, title)

    def test_place_name291(self):
        title = "903"
        lat, name = self.run_test(title, "Germany")
        self.assertEqual("Germany", name, title)

    def test_place_name129(self):
        title = "County  verify not found "
        lat, name = self.run_test(title, "Nova Scotia, Canada")
        self.assertEqual("Nova Scotia, Canada", name, title)

    # al*,--country=ca, --f_code=CH
    # Blois, Loir-et-Cher, Orleanais/Centre, France

    # ======= TEST Event Year handling
    def test_eventyear01(self):
        title = "City - good - and after city start"
        self.place.event_year = 1541
        lat, name = self.run_test(title, "Albanel,, Quebec, Canada")
        self.assertEqual(albanel_lat, lat, title)

    def test_eventyear02(self):
        title = "City - good - but before city start"
        self.place.event_year = 1540
        lat, name = self.run_test(title, "Albanel,, Quebec, Canada")
        self.assertEqual(GeoKeys.Result.STRONG_MATCH, self.place.result_type, title)

    def test_eventyear03(self):
        title = "name"
        self.place.event_year = 1541
        lat, name = self.run_test(title, "Stuttgart,,,Germany")
        self.assertEqual(48.78232, lat, title)
    

    # ====== TEST find first match, find geoid
    def test_findfirst01(self):
        title = "City - find first"
        entry = "Berlin,,,Germany"

        print("*****TEST: {}".format(title))
        TestGeodata.geodata.find_first_match(entry, self.place)
        lat = float(self.place.lat)

        self.assertEqual(47.73834, lat, title)

    def test_findgeoid01(self):
        title = "City - find first"
        entry = "Berlin,,,Germany"

        print("*****TEST: {}".format(title))
        TestGeodata.geodata.find_geoid('8133394', self.place)
        lat = float(self.place.lat)

        self.assertEqual(43.69655, lat, title)


if __name__ == '__main__':
    unittest.main()
