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

from geofinder import Geodata, Loc, Normalize, GeoUtil

EXCELLENT = 10
GOOD = 29
POOR = 49
VERY_POOR = 69
TERRIBLE = 89
NO_MATCH = 109


class MatchScore:
    """
    Calculate how close the database result place name is to the users input place name.
    1) Recursively remove largest text sequence in both to end up with just mismatched text
    2) Calculate the percent that didnt match in each comma separated term of user input
    3) Score is based on percent mismatch weighted for each term (City is higher, county is lower)

    A standard text difference, such as Levenstein, was not used because those treat both strings as equal, whereas this
    treats the User text as more important than DB result and also weights each token

    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Weighting for each token - prefix, city, adm2, adm1, country
        self.token_weight = [0.0, 1.0, 0.3, 0.6, 0.9]
        #self.token_weight = [1.0, 1.0, 1.0, 1.0, 1.0]

        self.prefix_weight = 1.2
        self.wildcard_penalty = 10.0
        self.first_token_match_bonus = 10.0
        self.wrong_order_penalty = 1.0
        self.feature_weight = 0.12

        # weight for match score of Result name
        self.out_weight = 0.17

        # Weight for match score of user input name
        self.in_weight = 1.0 - self.out_weight - self.feature_weight

        # Out weight + Feature weight must be less than 1.0.
        if self.out_weight + self.feature_weight > 1.0:
            self.logger.error('Out weight + Feature weight must be less than 1.0')

    def match_score(self, inp_place: Loc.Loc, res_place: Loc.Loc) -> int:
        """
        :param inp_place: Input place structure with users text
        :param res_place: Result place structure with DB result text
        :return: score 0-100 reflecting the difference between the user input and the result.  0 is perfect match, 100 is no match
        Score is also adjusted based on Feature type.  More important features (large city) get lower result
        """
        inp_len = [0] * 5
        num_inp_tokens = 0.0
        in_score = 0
        res_place.prefix = ' '

        # Create full place title (prefix,city,county,state,country) from input place.
        inp_title = inp_place.get_five_part_title()
        inp_title = Normalize.normalize_for_scoring(inp_title, inp_place.country_iso)
        inp_tokens = inp_title.split(',')
        # Create a list of all the words in input
        input_words = inp_title
        # Store length of original input tokens.  This is used for percent unmatched calculation
        for it, tk in enumerate(inp_tokens):
            inp_tokens[it] = inp_tokens[it].strip(' ')
            inp_len[it] = len(inp_tokens[it])

        # Create full place title (prefix,city,county,state,country) from result place
        res_title = res_place.get_five_part_title()
        res_title = Normalize.normalize_for_scoring(res_title, res_place.country_iso)
        res_place.original_entry = res_title
        res_tokens = res_title.split(',')

        # Create a list of all the words in result
        res_words = res_title
        # save result len for percent calc
        resw = res_words.strip(',')
        resw = resw.strip(' ')
        orig_res_len = len(resw)

        # Remove any sequences that match in input list and result
        res_words, input_words = GeoUtil.remove_matching_sequences(res_words, input_words)

        input_words, res_words = Normalize.remove_aliase(input_words, res_words)

        # For each input token calculate percent of new (unmatched) size vs original size
        unmatched_input_tokens = input_words.split(',')

        # Each token in place hierarchy gets a different weighting
        #      Prefix, city,county, state, country
        score_diags = ''

        # Restore prefix
        unmatched_input_tokens[0] = inp_tokens[0]
        match_bonus = 0

        # Calculate percent of USER INPUT text that was unmatched, then apply weighting
        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                unmatched_percent = int(100.0 * len(unmatched_input_tokens[idx].strip(' ')) / inp_len[idx])
                in_score += unmatched_percent * self.token_weight[idx]
                score_diags += f'  {idx}) [{tk}][{unmatched_input_tokens[idx]}] {unmatched_percent}% * {self.token_weight[idx]} '
                # self.logger.debug(f'{idx}) Rem=[{unmatched_input_tokens[idx].strip(" " )}] wgtd={unmatched_percent * self.weight[idx]}')
                num_inp_tokens += 1.0 * self.token_weight[idx]
                # self.logger.debug(f'{idx} [{inp_tokens2[idx]}:{inp_tokens[idx]}] rawscr={sc}% orig_len={inp_len[idx]} wgt={self.weight[idx]}')
                if idx < 2:
                    # If the full first or second token of the result is in input then improve score
                    # Bonus for a full match as against above partial matches
                    if res_tokens[idx] in inp_tokens[idx]:
                        in_score -= self.first_token_match_bonus
                    # If exact match of term, give bonus
                    if inp_tokens[idx] == res_tokens[idx]:
                        match_bonus -= 4

        # Average over number of tokens (with fractional weight).  Gives 0-100% regardless of weighting and number of tokens
        if num_inp_tokens > 0:
            in_score = in_score / num_inp_tokens
        else:
            in_score = 0
        # self.logger.debug(f'raw in={in_score}  numtkn={num_inp_tokens}')

        # Calculate percent of DB RESULT text that was unmatched
        res = res_words.strip(',')
        res = res.strip(' ')
        if orig_res_len > 0:
            out_score = int(100.0 * len(res) / orig_res_len)
            # self.logger.debug(f"Out=[{res_word_list.strip(' ')}] orig_len={orig_res_len}")
        else:
            out_score = 0

        if not inp_place.standard_parse:
            # If Tokens were not in hierarchical order, give penalty
            parse_penalty = self.wrong_order_penalty
        else:
            parse_penalty = 0.0

        if '*' in inp_place.original_entry:
            # if it was a wildcard search it's hard to rank - add a penalty
            wildcard_penalty = self.wildcard_penalty
        else:
            wildcard_penalty = 0.0

        # Prefix penalty for length of prefix
        if inp_len[0] > 0:
            prefix_penalty = 4 + inp_len[0]
        else:
            prefix_penalty = 0

            # Feature score is to ensure "important" places  get  higher rank (large city, etc)
        feature_score = Geodata.Geodata.get_priority(res_place.feature)

        # Add up scores - Each item is appx 0-100 and weighted
        score:float = in_score * self.in_weight +  out_score * self.out_weight  + match_bonus + \
                      feature_score * self.feature_weight  + wildcard_penalty + prefix_penalty * self.prefix_weight

        #self.logger.debug(f'SCORE {score:.1f} res=[{res_title}]\ninp=[{inp_title}]  outSc={out_score * self.out_weight:.1f}% '
        #                  f'inSc={in_score * self.in_weight:.1f}% feat={feature_score * self.feature_weight:.1f} {res_place.feature}  '
        #                  f'wild={wildcard_penalty} pref={prefix_penalty * self.prefix_weight} outrem=[{res}]')
        #self.logger.debug(f'{score_diags}\n')


        return round(score)

    def adjust_adm_score(self, score, feat):
        return score

        if 'ADM3' in feat or 'ADM4' in feat:
            # Back out original feature score
            score -= Geodata.Geodata.get_priority(feat) * self.feature_weight
            # Add in score for ADMX score
            score += Geodata.Geodata.get_priority('ADMX') * self.feature_weight
        return score




