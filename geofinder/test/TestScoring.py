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
import unittest

from geofinder import GeoKeys, Loc, MatchScore


class TestScoring(unittest.TestCase):
    scoring = None
    logger = None

    @classmethod
    def setUpClass(cls):
        TestScoring.logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)
        TestScoring.scoring = MatchScore.MatchScore()

    def setUp(self) -> None:
        TestScoring.in_place: Loc.Loc = Loc.Loc()
        TestScoring.out_place: Loc.Loc = Loc.Loc()

    def run_test1(self, title: str, inp, out):
        print("*****TEST: WORD {}".format(title))
        out, inp = TestScoring.scoring.remove_matching_words(out, inp)
        return out, inp

    def run_test2(self, title: str, inp, out):
        print("*****TEST: CHAR {}".format(title))
        out, inp = TestScoring.scoring.remove_matching_characters(out, inp)
        return out, inp

    def run_test3(self, title: str, inp, out):
        print("*****TEST:SCORE {}".format(title))
        in_place = Loc.Loc()
        in_place.name = inp
        in_place.country_iso = 'gb'

        res_place = Loc.Loc()
        res_place.name = out
        res_place.country_iso = 'gb'
        scr = TestScoring.scoring.match_score_calc( in_place, res_place, in_place.name)
        return scr

    # ===== TEST SCORING

    def test_scr01(self):
        title = "Input word1"
        scr = self.run_test3(title, "Paris, France", "Paris, France")
        self.assertGreater(5, scr, title)

    def test_scr02(self):
        title = "Input word1"
        scr = self.run_test3(title, "London, England,", "London, England, United Kingdom")
        self.assertGreater(7, scr, title)

    # St Margaret, Westminster Cathedral, Greater London, England, United Kingdom

    # ===== TEST INPUT WORD REMOVAL

    def test_in01(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "France", "Paris, France")
        self.assertEqual('', inp, title)

    def test_in02(self):
        title = "Input word2"
        out, inp = self.run_test1(title, "Westchester County, New York, USA", "Westchester, New York, USA")
        self.assertEqual('County,  ,', inp, title)

    def test_in03(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "Frunce", "Paris, France")
        self.assertEqual('Frunce', inp, title)

    def test_in04(self):
        title = "Input word1"
        out, inp = self.run_test1(title, "London,England,", "London,England,United Kingdom")
        self.assertEqual(',', inp, title)


    # ===== TEST OUTPUT WORD REMOVAL

    def test_out01(self):
        title = "output word1"
        out, inp = self.run_test1(title, "France", "Paris, France")
        self.assertEqual('Paris,', out, title)

    def test_out02(self):
        title = "output word2"
        out, inp = self.run_test1(title, "Westchester County, New York, USA", "Westchester, New York, USA")
        self.assertEqual(',  ,', out, title)

    def test_out03(self):
        title = "output word1"
        out, inp = self.run_test1(title, "Frunce", "Paris, France")
        self.assertEqual('Paris, France', out, title)

    # ===== TEST total REMOVAL
    def test_tot01(self):
        title = "total word1"
        out, inp = self.run_test1(title, "France", "Paris, France")
        out, inp = self.run_test2(title, inp, out)
        self.assertEqual('', inp, title)

    def test_tot02(self):
        title = "total word1"
        out, inp = self.run_test1(title, "Frunce", "Paris, France")
        TestScoring.logger.debug  (f'[{inp}] [{out}]')
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



if __name__ == '__main__':
    unittest.main()
