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
    """ Calculate how close two placenames are lexically """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def match_score(self, inp_place, res_place) -> int:
        if '*' in inp_place.original_entry:
            # if it was a wildcard search it's hard to rank.  just set to 40
            score = 40
        else:
            score: int = self.match_score_calc(inp_place, res_place)

        return score

    def match_score_calc(self, inp_place: Loc.Loc, res_place: Loc.Loc) -> int:
        # Return a score 0-100 reflecting the difference between the user input and the result:
        # The percent of characters in inp that were NOT matched by a word in result
        # Lower score is better match.  0 is perfect match, 100 is no match
        inp_len = [0] * 5
        num_inp_tokens = 1

        # Create  full name from inp_place and normalize
        # Set type to CITY so we get full four part name from format_full_name
        save_inp_type = inp_place.place_type
        inp_place.place_type = Loc.PlaceType.CITY

        inp = inp_place.prefix + ',' + inp_place.format_full_nm(None)
        inp = GeoKeys.search_normalize(inp, inp_place.country_iso)
        inp = GeoKeys.remove_noise_words(inp)
        inp_tokens = inp.split(',')
        inp_tokens[-1], modified = GeoKeys.country_normalize(inp_tokens[-1])

        # Create full name from result_place and normalize
        save_res_type = res_place.place_type
        res_place.place_type = Loc.PlaceType.CITY

        pref = " "
        res_place.original_entry = pref + ',' + res_place.format_full_nm(None)
        res = GeoKeys.search_normalize(res_place.original_entry, res_place.country_iso)
        res = GeoKeys.remove_noise_words(res)
        res_tokens = res.split(',')
        res_tokens[-1], modified = GeoKeys.country_normalize(res_tokens[-1])

        # remove spaces and Store length of original input tokens
        for it, tk in enumerate(inp_tokens):
            inp_tokens[it] = inp_tokens[it].strip(' ')
            tmp = re.sub(' ', '', inp_tokens[it])
            inp_len[it] = len(tmp)

        # Create a list of all the words in result and save len
        res_word_list = ', '.join(map(str, res_tokens))
        orig_res_len = len(res_word_list)

        # Create a list of all the words in input
        input_word_list = ', '.join(inp_tokens)

        # Find any matching sequences in input list that are in result and remove from input and result
        res_word_list, input_word_list = self.remove_matching_sequences(res_word_list, input_word_list)

        # For each input token calculate percent of new size vs original size
        inp_tokens2 = input_word_list.split(',')
        in_score = 0

        # Each token in place hierarchy gets a different weighting
        #        Pref, city,cty,state,country
        weight = [0.1, 1.0, 0.4, 0.6, 0.9]
        score_diags = ''

        # Calculate percent of unmatched characters in each token of input, then apply weighting
        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                tmp = re.sub(' ', '', inp_tokens2[idx])
                unmatched_percent = int(100.0 * len(tmp) / inp_len[idx])
                in_score += unmatched_percent * weight[idx]
                score_diags += f'  {idx}) [{tk}]{inp_len[idx]} {unmatched_percent}% * {weight[idx]} '
                num_inp_tokens += 1.0 * weight[idx]
                # self.logger.debug(f'{idx} [{inp_tokens2[idx]}:{inp_tokens[idx]}] rawscr={sc}% orig_len={inp_len[idx]} wgt={weight[idx]}')

        # Average over number of tokens, e.g. average percent of tokens unmatched
        in_score = in_score / num_inp_tokens

        # Calculate percent of result text that was unmatched
        new_len = len(res_word_list.strip(' '))
        if orig_res_len > 0:
            out_score = int(100.0 * new_len / orig_res_len)
        else:
            out_score = 0

        if len(inp_place.prefix) > 0:
            # The prefix isnt used for search or match.   Apply a penalty if the search had an unused prefix
            # Penalty is based on size of prefix
            pref_score = len(inp_place.prefix) + len(inp_place.extra)
        else:
            pref_score = 0

        if inp_place.standard_parse == False:
            # Calculate parse penalty.  If Tokens were not in hierarchical order,  give penalty
            parse_penalty = 3
        else:
            parse_penalty = 0

        # Feature score is to ensure "important" places (large city, etc) get somewhat higher rank.
        feature_score = Geodata.Geodata.get_priority(res_place.feature)

        # Add up input score, weighted output score, prefix score, feature and parse penalty
        score = in_score + 0.2 * out_score + pref_score + feature_score + parse_penalty

        self.logger.debug(f'SC {score:.1f} [{res_place.original_entry}]  out={out_score * 0.2:.1f} in={in_score:.1f} {pref_score}\n {score_diags}')
        inp_place.place_type = save_inp_type

        return int(score)

    def remove_matching_seq(self, out: str, inp: str, depth:int)->(str, str):
        # Find largest matching sequence.  Remove it in inp and out.  Then call recursively
        s = SequenceMatcher(None, out, inp)
        match = s.find_longest_match(0, len(out), 0, len(inp))
        if match.size > 1 :
            item = out[match.a:match.a + match.size]
            inp = re.sub(item, '', inp)
            out = re.sub(item, '', out)
            if depth > 0:
                # Call recursively to get next largest match and remove it
                out, inp = self.remove_matching_seq(out, inp, depth - 1)
        return out, inp

    def remove_matching_sequences(self, out: str, inp: str)->(str, str):
        # Prepare strings for input to remove_matching_seq
        # Swap all commas in inp string so we don't match them and remove them
        inp = re.sub(',', '@', inp)
        out, inp = self.remove_matching_seq(out, inp, 15)
        # Restore commas in inp
        inp = re.sub('@', ',', inp)
        return out, inp