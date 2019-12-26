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
import copy
import logging
import re

from geodata import GeoUtil, Geodata, Loc, Normalize

class Score:
    VERY_GOOD = 19
    GOOD = 40
    POOR = 60
    VERY_POOR = 120


class MatchScore:
    """
    Calculate a heuristic score for how well a result place name matches a target place name. The score is based on percent
    of characters that didnt match plus other items - described in match_score()
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Weighting for each input term match - prefix, city, adm2, adm1, country
        self.token_weight = [0.0, 1.0, 0.6, 0.8, 0.9, 0, 0, 0]

        # Weighting for each part of score
        self.wildcard_penalty = -41.0
        self.first_token_match_bonus = 40.0
        self.wrong_order_penalty = -3.0
        self.prefix_weight = 1.9

        self.feature_weight = 0.12
        self.result_weight = 0.17  # weight for match score of Result name
        self.input_weight = 1.0 - self.result_weight - self.feature_weight  # Weight for match score of user input name

        # Out weight + Feature weight must be less than 1.0.
        if self.result_weight + self.feature_weight > 1.0:
            self.logger.error('Out weight + Feature weight must be less than 1.0')

        self.in_score = 99.0
        self.out_score = 99.0

    def match_score(self, target_place: Loc, result_place: Loc) -> float:
        """
            Calculate a heuristic score for how well a result place name matches a target place name.  The score is based on
            percent of characters that didnt match in input and output (plus other items described below).
            Mismatch score is 0-100% reflecting the percent mismatch between the user input and the result.  This is then
            adjusted by Feature type (large city gives best score) plus other items to give a final heuristic where
            -10 is perfect match of a large city and 100 is no match.

            A) Heuristic:
            1) Create 5 part title (prefix, city, county, state/province, country)
            2) Normalize text - Normalize.normalize_for_scoring()
            3) Remove sequences over 3 chars that match in target and result
            4) Calculate inscore - percent of characters in input that didn't match output.  Weighted by term (county is lower weight)
                    Exact match of city term gets a bonus
            5) Calculate outscore - percent of characters in output that didn't match input

            B) Score components (All are weighted except Prefix and Parse):
            in_score - percent of characters in input that didnt match output
            out_score - percent of characters in output that didnt match input
            feature_score - Geodata.feature_priority().  adjustment based on Feature type.  More important features (larger city)
            get lower result
            wildcard_penalty - score is raised by 41 if it includes a wildcard
            prefix_penalty -  score is raised by length of Prefix
            parse_penalty - score is raised by 3 if lookup was done with terms out of order

            C) A standard text difference, such as Levenstein, was not used because those treat both strings as equal,
            whereas this treats the User text as more important than DB result text and also weights each token.  A user's
            text might commonly be something like: Paris, France and a DB result of Paris, Paris, Ile De France, France.
            The Levenstein distance would be large, but with this heuristic, the middle terms can have lower weights, and
            having all the input matched can be weighted higher than mismatches on the county and province.  This heuristic gives
            a score of -9 for Paris, France.

        # Args:
            target_place:  Loc  with users entry.
            result_place:  Loc with DB result.
        # Returns:
            score
        """
        target_tkn_len = [0] * 20

        # Create full RESULT title (prefix,city,county,state,country)
        result_place.prefix = ' '
        result_words = result_place.get_five_part_title()
        result_words = Normalize.normalize_for_scoring(result_words, result_place.country_iso)
        result_place.original_entry = copy.copy(result_words)
        res_tokens = result_words.split(',')

        # Create full TARGET  title (prefix,city,county,state,country)
        # Clean up prefix - remove any words that are in city, admin1 or admin2 from Prefix
        target_place.clean_prefix()
        target_words = target_place.get_five_part_title()
        target_words = Normalize.normalize_for_scoring(target_words, target_place.country_iso)
        target_tokens = target_words.split(',')

        target_words, result_words = Normalize.remove_aliase(target_words, result_words)

        # Store length of original tokens in target.  This is used for percent unmatched calculation
        for it, tk in enumerate(target_tokens):
            target_tokens[it] = target_tokens[it].strip(' ')
            target_tkn_len[it] = len(target_tokens[it])

        # Remove sequences that match in target  and result
        result_words, target_words = GeoUtil.remove_matching_sequences(text1=result_words, text2=target_words, min_len=3)

        # Calculate score for input match
        self.in_score = self._calculate_input_score(target_tkn_len, target_tokens, target_words, res_tokens)

        # Calculate score for output match
        self.out_score = self._calculate_output_score(result_words, result_place.original_entry)

        if not target_place.standard_parse:
            # If Tokens were not in hierarchical order, give penalty
            parse_penalty = self.wrong_order_penalty
        else:
            parse_penalty = 0.0

        if '*' in target_place.original_entry:
            # if it was a wildcard search it's hard to rank - add a penalty
            wildcard_penalty = self.wildcard_penalty
        else:
            wildcard_penalty = 0.0

        # Prefix penalty for length of prefix
        if target_tkn_len[0] > 0:
            prefix_penalty = 3 + target_tkn_len[0]
        else:
            prefix_penalty = 0

        # Feature score is to ensure "important" places get higher rank (large city, etc)
        feature_score = Geodata.Geodata.feature_priority(result_place.feature)

        # Add up scores - Each item is appx 0-100 and weighted
        score: float = self.in_score * self.input_weight + self.out_score * self.result_weight + feature_score * self.feature_weight + \
                       wildcard_penalty + prefix_penalty * self.prefix_weight + parse_penalty

        #self.logger.debug(f'SCORE {score:.1f} res=[{result_place.original_entry}] pref=[{target_place.prefix}]\n'
        #                  f'inp=[{",".join(target_tokens)}]  outSc={self.out_score * self.out_weight:.1f}% '
        #                  f'inSc={self.in_score * self.in_weight:.1f}% feat={feature_score * self.feature_weight:.1f} {result_place.feature}  '
        #                  f'wild={wildcard_penalty} pref={prefix_penalty * self.prefix_weight:.1f}')
        #self.logger.debug(f'{self.score_diags}\n')

        return score

    def _calculate_input_score(self, inp_len: [], inp_tokens: [], input_words, res_tokens: []) -> float:
        num_inp_tokens = 0.0
        in_score = 0

        # For each input token calculate percent of unmatched size vs original size
        unmatched_input_tokens = input_words.split(',')

        # Each token in place hierarchy gets a different weighting
        #      Prefix, city,county, state, country
        self.score_diags = ''
        unmatched_input_tokens[0] = inp_tokens[0]
        match_bonus = 0

        # Calculate percent of USER INPUT text that was unmatched, then apply weighting
        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                unmatched_percent = int(100.0 * len(unmatched_input_tokens[idx].strip(' ')) / inp_len[idx])
                in_score += unmatched_percent * self.token_weight[idx]
                self.score_diags += f'  {idx}) [{tk}][{unmatched_input_tokens[idx]}] {unmatched_percent}% * {self.token_weight[idx]} '
                # self.logger.debug(f'{idx}) Rem=[{unmatched_input_tokens[idx].strip(" " )}] wgtd={unmatched_percent * self.weight[idx]}')
                num_inp_tokens += 1.0 * self.token_weight[idx]
                # self.logger.debug(f'{idx} [{inp_tokens2[idx]}:{inp_tokens[idx]}] rawscr={sc}% orig_len={inp_len[idx]} wgt={self.weight[idx]}')
                if idx == 1:
                    # If the full first or second token of the result is in input then improve score
                    # Bonus for a full match as against above partial matches
                    if res_tokens[idx] in inp_tokens[idx]:
                        in_score -= self.first_token_match_bonus
                    # If exact match of term, give bonus
                    if inp_tokens[idx] == res_tokens[idx]:
                        if idx == 0:
                            match_bonus -= 9
                        else:
                            match_bonus -= 3

        # Average over number of tokens (with fractional weight).  Gives 0-100% regardless of weighting and number of tokens
        if num_inp_tokens > 0:
            in_score = in_score / num_inp_tokens
        else:
            in_score = 0

        return in_score + match_bonus + 10

    def _calculate_output_score(self, unmatched_result: str, original_result:str) -> float:
        """
        Calculate score for output (DB result).
        :param unmatched_result: The text of the DB result that didnt match the user's input
        :param original_result: The original DB result
        :return: 0=strong match, 100=no match
        """

        # Remove spaces and commas from original and unmatched result
        original_result = re.sub(r'[ ,]', '', original_result)
        unmatched = re.sub(r'[ ,]', '', unmatched_result)

        orig_res_len = len(original_result)
        if orig_res_len > 0:
            # number of chars of DB RESULT text that matched target - scaled from 0 (20 or more matched) to 100 (0 matched)
            out_score_1 = (20.0 - min((orig_res_len - len(unmatched)), 20.0)) * 5.0
            #self.logger.debug(f'matched {orig_res_len - len(unmatched)} [{unmatched}]')

            # Percent of unmatched
            out_score_2 = 100.0 * len(unmatched) / orig_res_len

            out_score = out_score_1 * 0.1 + out_score_2 * 0.9
        else:
            out_score = 0.0

        self.score_diags += f'\noutrem=[{unmatched}]'

        return out_score

    def _adjust_adm_score(self, score, feat):
        return score
