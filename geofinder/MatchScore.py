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
import re
from difflib import SequenceMatcher

from geofinder import GeoKeys, Geodata, Loc


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

    def match_score(self, inp_place: Loc.Loc, res_place: Loc.Loc) -> int:
        """
        :param inp_place: Input place structure with users text
        :param res_place: Result place structure with DB result
        :return: score 0-100 reflecting the difference between the user input and the result.  0 is perfect match, 100 is no match
        Score is also adjusted based on Feature type.  More important features (large city) get lower result
        """
        inp_len = [0] * 5
        num_inp_tokens = 0.0
        in_score = 0

        if '*' in inp_place.original_entry:
            # if it was a wildcard search it's hard to rank.  just set to 40
            return 40

        # Create full place title (prefix,city,county,state,country) from input place.
        inp_title = inp_place.get_five_part_title()
        inp_title = GeoKeys.normalize_match_title(inp_title, inp_place.country_iso)
        inp_tokens = inp_title.split(',')

        # Create full place title (prefix,city,county,state,country) from result place
        res_place.prefix = ' '
        res_title = res_place.get_five_part_title()
        res_title = GeoKeys.normalize_match_title(res_title, res_place.country_iso)
        res_tokens = res_title.split(',')

        # Store length of original input tokens.  This is used for percent unmatched calculation
        for it, tk in enumerate(inp_tokens):
            inp_tokens[it] = inp_tokens[it].strip(' ')
            inp_len[it] = len(inp_tokens[it])

        # Create a list of all the words in result and save result len for percent calc
        res_word_list = ', '.join(map(str, res_tokens))
        orig_res_len = len(res_word_list)

        # Create a list of all the words in input
        input_words = ', '.join(map(str, inp_tokens))

        # Remove any matching sequences in input list and result
        res_word_list, input_words = self.remove_matching_sequences(res_word_list, input_words)

        # For each input token calculate percent of new (unmatched) size vs original size
        unmatched_input_tokens = input_words.split(',')

        # Each token in place hierarchy gets a different weighting
        #      Prefix, city,county, state, country
        weight = [0.5, 1.0, 0.2, 0.6, 0.9]
        score_diags = ''

        # Calculate percent of USER INPUT text that was unmatched, then apply weighting
        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                unmatched_percent = int(100.0 * len(unmatched_input_tokens[idx].strip(' ')) / inp_len[idx])
                in_score += unmatched_percent * weight[idx]
                score_diags += f'  {idx}) [{tk}]{inp_len[idx]} {unmatched_percent}% * {weight[idx]} '
                # self.logger.debug(f'{idx}) Rem=[{unmatched_input_tokens[idx].strip(" " )}] wgtd={unmatched_percent * weight[idx]}')
                num_inp_tokens += 1.0 * weight[idx]
                # self.logger.debug(f'{idx} [{inp_tokens2[idx]}:{inp_tokens[idx]}] rawscr={sc}% orig_len={inp_len[idx]} wgt={weight[idx]}')
                if idx < 2:
                    # If the full first or second token of the result is in input then improve score
                    # Bonus for a full match as against above partial matches
                    if res_tokens[idx] in inp_tokens[idx]:
                        in_score -= 10

        # Average over number of tokens (with fractional weight).  Gives 0-100% regardless of weighting and number of tokens
        in_score = in_score / num_inp_tokens
        # self.logger.debug(f'raw in={in_score}  numtkn={num_inp_tokens}')

        # Calculate percent of DB RESULT text that was unmatched
        if orig_res_len > 0:
            out_score = int(100.0 * len(res_word_list.strip(' ')) / orig_res_len)
            # self.logger.debug(f"Out=[{res_word_list.strip(' ')}] orig_len={orig_res_len}")
        else:
            out_score = 0

        if not inp_place.standard_parse:
            # If Tokens were not in hierarchical order, give penalty
            parse_penalty = 2.0
        else:
            parse_penalty = 0.0

        # Feature score is to ensure "important" places  get  higher rank (large city, etc)
        feature_score = Geodata.Geodata.get_priority(res_place.feature)

        # Add up scores - Each item is 0-100 and weighed as below
        out_weight = 0.17
        feature_weight = 0.06
        in_weight = 1.0 - out_weight - feature_weight

        score = in_score * in_weight + out_weight * out_score + feature_score * feature_weight + parse_penalty

        # self.logger.debug(f'SCORE {score:.1f} [{res_title}]  out={out_score * out_weight:.1f} '
        #                  f'in={in_score:.1f} feat={feature_score * feature_weight:.1f} parse={parse_penalty}\n {score_diags}')

        return score

    def _remove_matching_seq(self, text1: str, text2: str, attempts: int) -> (str, str):
        """
        Find largest matching sequence.  Remove it in text1 and text2.
                Private - called by remove_matching_sequences which provides a wrapper
        Call recursively until attempts hits zero or there are no matches longer than 1 char
        :param text1:
        :param text2:
        :param attempts: Number of times to remove largest text sequence
        :return:
        """
        s = SequenceMatcher(None, text1, text2)
        match = s.find_longest_match(0, len(text1), 0, len(text2))
        if match.size > 1:
            # Remove matched sequence from inp and out
            item = text1[match.a:match.a + match.size]
            text2 = re.sub(item, '', text2)
            text1 = re.sub(item, '', text1)
            if attempts > 0:
                # Call recursively to get next largest match and remove it
                text1, text2 = self._remove_matching_seq(text1, text2, attempts - 1)
        return text1, text2

    def remove_matching_sequences(self, text1: str, text2: str) -> (str, str):
        """
        Find largest sequences that match between text1 and 2.  Remove them from text1 and text2.
        :param text1:
        :param text2:
        :return:
        """
        # Prepare strings for input to remove_matching_seq
        # Swap all commas in text1 string to '@'.  This way they will never match comma in text2 string
        # Ensures we don;t remove commas and don't match across tokens
        text2 = re.sub(',', '@', text2)
        text1, text2 = self._remove_matching_seq(text1=text1, text2=text2, attempts=15)
        # Restore commas in inp
        text2 = re.sub('@', ',', text2)
        return text1.strip(' '), text2.strip(' ')
