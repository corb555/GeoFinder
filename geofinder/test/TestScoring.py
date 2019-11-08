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

from geofinder import Loc, MatchScore, Geodata


class TestScoring(unittest.TestCase):
    scoring = None
    logger = None
    geodata = None

    @classmethod
    def setUpClass(cls):
        TestScoring.logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)
        TestScoring.logger.debug('Scoring')
        TestScoring.scoring = MatchScore.MatchScore()

        # Load test data
        directory = os.path.join(str(Path.home()), "geoname_test")
        TestScoring.geodata = Geodata.Geodata(directory_name=directory, progress_bar=None)
        error: bool = TestScoring.geodata.read()
        if error:
            TestScoring.logger.error("Missing geodata support Files.")
            raise ValueError('Cannot open database')

        # Read in Geoname Gazeteer file - city names, lat/long, etc.
        start_time = time.time()
        error = TestScoring.geodata.read_geonames()
        end_time = time.time()

    def setUp(self) -> None:
        TestScoring.in_place: Loc.Loc = Loc.Loc()
        TestScoring.out_place: Loc.Loc = Loc.Loc()

    def run_test1(self, title: str, inp, out):
        print("*****TEST: WORD {}".format(title))
        out, inp = TestScoring.scoring.remove_matching_sequences(out, inp)
        return out, inp

    def run_test2(self, title: str, inp, out):
        print("*****TEST: CHAR {}".format(title))
        out, inp = TestScoring.scoring.remove_matching_sequences(out, inp)
        return out, inp

    def run_test3(self, title: str, inp, res, feat):
        print("*****TEST:SCORE {}".format(title))
        in_place = Loc.Loc()
        in_place.original_entry = inp
        in_place.parse_place(inp,geo_files=TestScoring.geodata.geo_files)
        if in_place.country_name == '' and in_place.country_iso != '':
            in_place.country_name = TestScoring.geodata.geo_files.geodb.get_country_name(in_place.country_iso)

        res_place = Loc.Loc()
        res_place.original_entry = res
        res_place.parse_place(place_name=  res, geo_files=TestScoring.geodata.geo_files)
        res_place.feature = feat
        if res_place.country_name == '' and res_place.country_iso != '':
            res_place.country_name = TestScoring.geodata.geo_files.geodb.get_country_name(res_place.country_iso)

        score = TestScoring.scoring.match_score(in_place, res_place)
        return scr

    # ===== TEST SCORING
    PERFECT = -10
    VERY_STRONG = 5
    STRONG = 13
    GOOD = 23
    POOR = 38
    VERY_POOR = 70
    NO_MATCH = 100


    def test_scr22(self):
        title = "score1"
        score = self.run_test3(title, "chelsea,,england", "winchelsea, east sussex, england, united kingdom", 'PP1M')
        self.assertLess(score, TestScoring.STRONG, title)
        self.assertGreater(score, TestScoring.VERY_STRONG, title)

    def test_scr23(self):
        title = "score1"
        score = self.run_test3(title, "chelsea,,england", "chelsea, greater london, england, united kingdom", 'PP1M')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)

    def test_scr21(self):
        title = "score1"
        score = self.run_test3(title, "sonderburg", "sonderburg,sonderborg kommune,region syddanmark, denmark", 'PP1M')
        self.assertLess(score, TestScoring.GOOD, title)
        self.assertGreater(score, TestScoring.STRONG, title)

    def test_scr01(self):
        title = "score1"
        score = self.run_test3(title, "Paris, France", "Paris, France", 'PP1M')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)

    def test_scr02(self):
        title = "score2"
        score = self.run_test3(title, "London, England", "London, England, United Kingdom", 'PP1M')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)

    def test_scr72(self):
        title = "score72"
        score = self.run_test3(title, "London, England, United Kingdom", "London, England, United Kingdom", 'PP1M')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)

    def test_scr73(self):
        title = "score72"
        score = self.run_test3(title, "London, England, United Kingdom", "London, England, United Kingdom", 'HSP')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)

    def test_scr82(self):
        title = "score82"
        score = self.run_test3(title, "Domfront, Normandy", "Domfront-En-Champagne, Sarthe, Pays De La Loire, France", 'PP1M')
        self.assertLess(score, TestScoring.POOR, title)
        self.assertGreater(score, TestScoring.GOOD, title)

    def test_scr84(self):
        title = "score84"
        score = self.run_test3(title, "Domfront, Normandy", "Domfront, Department De L'Orne, Normandie, France", 'PP1M')
        self.assertLess(score, TestScoring.STRONG, title)
        self.assertGreater(score, TestScoring.VERY_STRONG, title)
        
    def test_scr83(self):
        title = "score83"
        score = self.run_test3(title, "St Quentin, Aisne, Picardy, France", "St Quentin, Departement De L'Aisne, Hauts De France, France", 'PP1M')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)

    def test_scr85(self):
        title = "score85"
        score = self.run_test3(title, "Old Bond Street, London, Middlesex, England",
                             " , London, Greater London, England, United Kingdom", 'PP1M')
        self.assertLess(score, TestScoring.STRONG, title)
        self.assertGreater(score, TestScoring.VERY_STRONG, title)

    def test_scr86(self):
        title = "score86"
        score = self.run_test3(title, "Old Bond Street, London, Middlesex, England",
                             " , Museum Of London, Greater London, England, United Kingdom", 'PPL')
        self.assertLess(score, TestScoring.GOOD, title)
        self.assertGreater(score, TestScoring.STRONG, title)

    def test_scr61(self):
        title = "score61"
        score = self.run_test3(title, "zxq, xyzzy",
                             " , London, Greater London, England, United Kingdom", ' ')
        self.assertLess(score, TestScoring.NO_MATCH, title)
        self.assertGreater(score, TestScoring.VERY_POOR, title)

    def test_scr62(self):
        title = "score62"
        score = self.run_test3(title, "France",
                             "France", 'ADM0')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)
    
    def test_scr03(self):
        title = "score3"
        score = self.run_test3(title, "St. Margaret, Westminster, London, England", "London,England,United Kingdom", 'PPL')
        self.assertLess(score, TestScoring.POOR, title)
        self.assertGreater(score, TestScoring.GOOD, title)

    def test_scr04(self):
        title = "score4"
        score = self.run_test3(title, "St. Margaret, Westminster, London, England", "Westminster Cathedral, Greater London, England", 'PPL')
        self.assertLess(score, TestScoring.STRONG, title)
        self.assertGreater(score, TestScoring.VERY_STRONG, title)

    def test_scr05(self):
        title = "score5"
        score = self.run_test3(title, "Canada", "Canada", 'ADM0')
        self.assertLess(score, TestScoring.VERY_STRONG, title)
        self.assertGreater(score, TestScoring.PERFECT, title)

    # St Margaret, Westminster Cathedral, Greater London, England, United Kingdom

    # ===== TEST INPUT WORD REMOVAL

    def test_in01(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "France", "Paris, France")
        self.assertEqual('', inp, title)

    def test_in02(self):
        title = "Input word2"
        out, inp = self.run_test1(title, "Westchester County, New York, USA", "Westchester, New York, USA")
        self.assertEqual('County,,', inp, title)

    def test_in03(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "Frunce", "Paris, France")
        self.assertEqual('u', inp, title)

    def test_in04(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "London,England,", "London,England,United Kingdom")
        self.assertEqual(',,', inp, title)

    def test_in05(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "St. Margaret, Westminster, London, England", "London,England,United Kingdom")
        self.assertEqual('St. Margaret, Westmsr, ,', inp, title)

    def test_in06(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "St. Margaret, Westminster, London, England", "Westminster Cathedral, Greater London, England")
        self.assertEqual('St. Marg, ,,', inp, title)

    # ===== TEST OUTPUT WORD REMOVAL

    def test_out01(self):
        title = "output word1"
        out, inp = self.run_test1(title, "France", "Paris, France")
        self.assertEqual('Paris,', out, title)

    def test_out02(self):
        title = "output word2"
        out, inp = self.run_test1(title, "Westchester County, New York, USA", "Westchester, New York, USA")
        self.assertEqual(',,', out, title)

    def test_out03(self):
        title = "output word1"
        out, inp = self.run_test1(title, "Frunce", "Paris, France")
        self.assertEqual('Paris, a', out, title)

    # ===== TEST total REMOVAL
    def test_tot01(self):
        title = "total word1"
        out, inp = self.run_test1(title, "France", "Paris, France")
        out, inp = self.run_test2(title, inp, out)
        self.assertEqual('', inp, title)

    def test_tot02(self):
        title = "total word1"
        out, inp = self.run_test1(title, "Frunce", "Paris, France")
        out, inp = self.run_test2(title, inp, out)
        self.assertEqual('u', inp, title)

    def test_tot03(self):
        title = "total word2"
        out, inp = self.run_test1(title, "Westchester County, New York, USA", "Westchester, New York, USA")
        out, inp = self.run_test2(title, inp, out)
        self.assertEqual('County,,', inp, title)

    # ===== TEST INPUT CHAR REMOVAL
    def test_char01(self):
        title = "Input word1"
        out, inp = self.run_test2(title, "France", "Paris, France")
        self.assertEqual('', inp, title)

    def test_char02(self):
        title = "Input word2"
        out, inp = self.run_test2(title, "Westchester County, New York, USA", "Westchester, New York, USA")
        self.assertEqual('County,,', inp, title)

    def test_char03(self):
        title = "Input word3"
        out, inp = self.run_test2(title, "Frunce", "Paris, France")
        self.assertEqual('u', inp, title)
    """
    """


if __name__ == '__main__':
    unittest.main()
