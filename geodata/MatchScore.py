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

EXCELLENT = 10
GOOD = 30
POOR = 50
VERY_POOR = 70
TERRIBLE = 90
NO_MATCH = 110


class MatchScore:
    """
    Calculate how close the text of the database result place name is to the users input place name.
    1) Recursively remove the largest text sequence in both to end up with just unmatched text in both
    2) Calculate the percent that didnt match in each comma separated term of user input
    3) Score is based on percent mismatch weighted for each term (City is higher, county is lower)

    A standard text difference, such as Levenstein, was not used because those treat both strings as equal, whereas this
    treats the User text as more important than DB result text and also weights each token.  A user's text might commonly be something
    like: Paris, France and a DB result of Paris, Paris, Ile De France, France.  The Levenstein distance would be large, but
    with this heuristic, the middle terms can have lower weights, and having all the input matched can be weighted higher than mismatches
    on the county and province.

    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Weighting for each token - prefix, city, adm2, adm1, country
        self.token_weight = [0.0, 1.0, 0.6, 0.8, 0.9, 0, 0, 0]

        self.prefix_weight = 1.9
        self.wildcard_penalty = -41.0
        self.first_token_match_bonus = 40.0
        self.wrong_order_penalty = -3.0
        self.feature_weight = 0.12

        # weight for match score of Result name
        self.out_weight = 0.17

        # Weight for match score of user input name
        self.in_weight = 1.0 - self.out_weight - self.feature_weight

        # Out weight + Feature weight must be less than 1.0.
        if self.out_weight + self.feature_weight > 1.0:
            self.logger.error('Out weight + Feature weight must be less than 1.0')
        self.in_score = 99
        self.out_score = 99

    def match_score(self, target_place: Loc, result_place: Loc) -> float:
        """
        :param target_place: Target Location  with users entry
        :param result_place: Result Location  with DB result
        :return: score -10-100 reflecting the difference between the user input and the result.  -10 is perfect match, 100 is no match
        Score is also adjusted based on Feature type.  More important features (large city) get lower result
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

        # Remove any sequences that match in target  and result
        result_words, target_words = GeoUtil.remove_matching_sequences(text1=result_words, text2=target_words, min_len=3)

        # Calculate score for input match
        self.in_score = self.calculate_input_score(target_tkn_len, target_tokens, target_words, res_tokens)

        # Calculate score for output match
        self.out_score = self.calculate_output_score(result_words, result_place.original_entry)

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

        # Feature score is to ensure "important" places  get  higher rank (large city, etc)
        feature_score = Geodata.Geodata.get_priority(result_place.feature)

        # Add up scores - Each item is appx 0-100 and weighted
        score: float = self.in_score * self.in_weight + self.out_score * self.out_weight + feature_score * self.feature_weight + \
                       wildcard_penalty + prefix_penalty * self.prefix_weight + parse_penalty

        #self.logger.debug(f'SCORE {score:.1f} res=[{result_place.original_entry}] pref=[{target_place.prefix}]\n'
        #                  f'inp=[{",".join(target_tokens)}]  outSc={self.out_score * self.out_weight:.1f}% '
        #                  f'inSc={self.in_score * self.in_weight:.1f}% feat={feature_score * self.feature_weight:.1f} {result_place.feature}  '
        #                  f'wild={wildcard_penalty} pref={prefix_penalty * self.prefix_weight:.1f}')
        #self.logger.debug(f'{self.score_diags}\n')

        return score

    def calculate_input_score(self, inp_len: [], inp_tokens: [], input_words, res_tokens: []) -> float:
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

        return in_score + match_bonus

    def calculate_output_score(self, unmatched_result: str, original_result:str) -> float:
        """
        Calculate score for output (DB result).   filtered = [c.lower() for c in text if c.isalnum()]
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
            out_score = 0

        self.score_diags += f'\noutrem=[{unmatched}]'

        return out_score

    def adjust_adm_score(self, score, feat):
        return score
