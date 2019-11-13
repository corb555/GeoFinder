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

from geofinder import Loc, MatchScore, Geodata, GeoUtil


class TestScoring(unittest.TestCase):
    scoring = None
    logger = None
    geodata = None
    test_idx = -1
    delta = 22

    # ===== TEST SCORING
    MatchScore.EXCELLENT = 10
    MatchScore.GOOD = 29
    MatchScore.POOR = 49
    MatchScore.VERY_POOR = 69
    MatchScore.TERRIBLE = 89
    MatchScore.NO_MATCH = 109

    test_values = [
        # Target, Result, Feature, Expected Score
        ("toronto,nova scotia, canada", "toronto,ontario,canada", 'PPL', MatchScore.GOOD),   #0
        ("toronto,ontario,canada", "toronto,ontario,canada", 'PP1M', MatchScore.EXCELLENT), #1

        ("toronto, canada", "toronto, canada", 'PPL', MatchScore.EXCELLENT), #2

        ("chelsea,,england", "winchelsea, east sussex, england, united kingdom", 'PP1M', MatchScore.GOOD), #3
        ("chelsea,,england", "chelsea, greater london, england, united kingdom", 'PP1M', MatchScore.EXCELLENT), #4

        ("sonderburg", "sonderborg kommune,region syddanmark, denmark", 'PP1M', MatchScore.GOOD), #5

        ("Paris, France", "Paris,, France", 'PP1M', MatchScore.EXCELLENT), #6
        ("Paris, France.", "Paris,, France", 'PP1M', MatchScore.EXCELLENT), #7

        ("London, England", "London, England, United Kingdom", 'PP1M', MatchScore.EXCELLENT), #8
        ("London, England, United Kingdom", "London, England, United Kingdom", 'PP1M', MatchScore.EXCELLENT), #9
        ("London, England, United Kingdom", "London, England, United Kingdom", 'HSP', MatchScore.GOOD), #10

        ("Domfront, Normandy", "Domfront-En-Champagne, Sarthe, Pays De La Loire, France", 'PP1M', MatchScore.POOR), #11
        ("Domfront, Normandy", "Domfront, Department De L'Orne, Normandie, France", 'PP1M', MatchScore.GOOD), #12

        ("St Quentin, Aisne, Picardy, France", "St Quentin, Departement De L'Aisne, Hauts De France, France", 'PP1M', MatchScore.EXCELLENT), #13

        ("Old Bond Street, London, Middlesex, England"," , London, Greater London, England, United Kingdom", 'PP1M', MatchScore.GOOD), #14
        ("Old Bond Street, London, Middlesex, England", " , Museum Of London, Greater London, England, United Kingdom", 'PPL', MatchScore.GOOD),#15

        ("zxq, xyzzy", " , London, Greater London, England, United Kingdom", ' ', MatchScore.NO_MATCH),#16

        ("St. Margaret, Westminster, London, England", "London,England,United Kingdom", 'PPL', MatchScore.POOR),#17
        ("St. Margaret, Westminster, London, England", "Westminster Cathedral, Greater London, England", 'PPL', MatchScore.GOOD), #18

        ("Canada", "Canada", 'ADM0', MatchScore.EXCELLENT),#19
        ("France", ",France", 'ADM0', MatchScore.EXCELLENT),  # 20

        ("barton, lancashire, england, united kingdom", "barton, lancashire, england, united kingdom", 'PPLL', MatchScore.EXCELLENT), #21
        ("barton, lancashire, england, united kingdom", "barton, cambridgeshire, england, united kingdom", 'PPLL', MatchScore.GOOD), #22

        ("testerton, norfolk, , england", "norfolk,england, united kingdom","ADM2", MatchScore.GOOD), #23
        ("testerton, norfolk, , england", "testerton, norfolk, england,united kingdom", "PPLL", MatchScore.EXCELLENT), #24

        ("Holborn, Middlesex, England", "Holborn, Greater London, England, United Kingdom", 'PP1M', MatchScore.GOOD),  # 25

    ]

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
        out, inp = GeoUtil.remove_matching_sequences(out, inp)
        return out, inp

    @staticmethod
    def run_test2(title: str, inp, out):
        print("*****TEST: CHAR {}".format(title))
        out, inp = GeoUtil.remove_matching_sequences(out, inp)
        return out, inp

    @staticmethod
    def run_test3(idx)->int:
        TestScoring.test_idx = idx
        title = TestScoring.test_values[idx][0]
        inp = TestScoring.test_values[idx][0]
        res = TestScoring.test_values[idx][1]
        feat = TestScoring.test_values[idx][2]

        in_place = Loc.Loc()
        in_place.original_entry = inp
        in_place.parse_place(place_name=inp, geo_files=TestScoring.geodata.geo_files)
        if in_place.country_name == '' and in_place.country_iso != '':
            in_place.country_name = TestScoring.geodata.geo_files.geodb.get_country_name(in_place.country_iso)

        res_place = Loc.Loc()
        res_place.original_entry = res
        res_place.parse_place(place_name=res, geo_files=TestScoring.geodata.geo_files)
        res_place.feature = feat
        if res_place.country_name == '' and res_place.country_iso != '':
            res_place.country_name = TestScoring.geodata.geo_files.geodb.get_country_name(res_place.country_iso)

        score = TestScoring.scoring.match_score(in_place, res_place)
        print(f'#{idx} {score:.1f} [{in_place.original_entry.title()}] [{res_place.get_five_part_title()}]')
        return score

    def test_score_00(self):
        score = self.run_test3(0)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_01(self):
        score = self.run_test3(1)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_02(self):
        score = self.run_test3(2)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_03(self):
        score = self.run_test3(3)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_04(self):
        score = self.run_test3(4)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_05(self):
        score = self.run_test3(5)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_06(self):
        score = self.run_test3(6)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_07(self):
        score = self.run_test3(7)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_08(self):
        score = self.run_test3(8)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3] - TestScoring.delta,
                           TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_09(self):
        score = self.run_test3(9)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3] - TestScoring.delta,
                           TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_10(self):
        score = self.run_test3(10)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_11(self):
        score = self.run_test3(11)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_12(self):
        score = self.run_test3(12)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_13(self):
        score = self.run_test3(13)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_14(self):
        score = self.run_test3(14)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_15(self):
        score = self.run_test3(15)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_16(self):
        score = self.run_test3(16)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_17(self):
        score = self.run_test3(17)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_18(self):
        score = self.run_test3(18)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_19(self):
        score = self.run_test3(19)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])
    def test_score_20(self):
        score = self.run_test3(20)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_21(self):
        score = self.run_test3(21)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_22(self):
        score = self.run_test3(22)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])


    def test_score_23(self):
        score = self.run_test3(23)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_24(self):
        score = self.run_test3(24)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

    def test_score_25(self):
        score = self.run_test3(25)
        self.assertLess(score, TestScoring.test_values[TestScoring.test_idx][3],
                        TestScoring.test_values[TestScoring.test_idx][0])
        self.assertGreaterEqual(score, TestScoring.test_values[TestScoring.test_idx][3]-TestScoring.delta,
                        TestScoring.test_values[TestScoring.test_idx][0])

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
        self.assertEqual('St. Margaret, ,,', inp, title)

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
