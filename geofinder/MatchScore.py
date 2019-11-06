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

        in_pref = inp_place.prefix
        if in_pref == '':
            in_pref = ' '
        save_type = inp_place.place_type
        inp_place.place_type = Loc.PlaceType.CITY

        # Create input full name
        inp = in_pref + ',' + inp_place.format_full_nm(None)
        inp = GeoKeys.search_normalize(inp, inp_place.country_iso)
        inp = GeoKeys.remove_noise_words(inp)
        inp_tokens = inp.split(',')
        inp_tokens[-1], modified = GeoKeys.country_normalize(inp_tokens[-1])

        # Store length of original tokens and strip spaces
        for it, tk in enumerate(inp_tokens):
            inp_tokens[it] = inp_tokens[it].strip(' ')
            tmp = re.sub(' ', '', inp_tokens[it])
            inp_len[it] = len(tmp)

        # Create result full name
        pref = " "
        res_place.original_entry = pref + ',' + res_place.format_full_nm(None)
        res = GeoKeys.search_normalize(res_place.original_entry, res_place.country_iso)
        res = GeoKeys.remove_noise_words(res)
        res_tokens = res.split(',')

        # Normalize country (last token)
        res_tokens[-1], modified = GeoKeys.country_normalize(res_tokens[-1])

        res = ', '.join(map(str, res_tokens))
        orig_res_len = len(res)

        # Create a list of all the words in input
        input_word_list = ', '.join(inp_tokens)

        # Find any words in input list that are in result and remove from input and result
        res, input_word_list = self.remove_matching_words(res, input_word_list)
        res, input_word_list = self.remove_matching_characters(res, input_word_list)

        # For each input token calculate percent of new size vs original size
        inp_tokens2 = input_word_list.split(',')
        in_score = 0

        # Each token in place hierarchy gets a different weighting
        #        Pref, city,cty,state,country
        weight = [0.1, 1.0, 0.4, 0.6, 0.9]
        score_text = ''

        # Calculate percent of unmatched characters in each token of input, then apply weighting
        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                unmatched_percent = int(100.0 * len(inp_tokens2[idx]) / inp_len[idx])
                in_score += unmatched_percent * weight[idx]
                score_text += f'  {idx}) [{tk}] {unmatched_percent}% * {weight[idx]} '
                num_inp_tokens += 1.0 * weight[idx]
                # self.logger.debug(f'{idx} [{inp_tokens2[idx]}:{inp_tokens[idx]}] rawscr={sc}% orig_len={inp_len[idx]} wgt={weight[idx]}')

        # Average over number of tokens, e.g. average percent of tokens unmatched
        in_score = in_score / num_inp_tokens

        # Calculate percent of result that was not matched - not weighted per token
        new_len = len(res.strip(' '))
        if orig_res_len > 0:
            out_score = int(100.0 * new_len / orig_res_len)
            if new_len > 0:
                out_score += 1
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

        #self.logger.debug(f'SC {score:.1f} [{res_place.original_entry}]  out={out_score * 0.2:.1f} in={in_score:.1f} {pref_score} {score_text}')
        inp_place.place_type = save_type

        return int(score)

    def remove_matching_words(self, out: str, inp: str):
        # Remove any WORD in input that is in result, delete it from both input and from result

        inp_words = inp.split(' ')

        lst = sorted(inp_words, key=len, reverse=True)  # Remove longest words first
        for idx, word in enumerate(lst):
            targ = word.strip(',')
            if len(word) > 2 and targ in out:
                # If input word is in result, delete it from input string and result string
                inp = re.sub(targ, '', inp)
                out = re.sub(targ, '', out)
        out = out.strip(' ')
        inp = inp.strip(' ')
        return out, inp

    def remove_matching_characters(self, out: str, inp: str):
        # Strip out any remaining CHARACTERS in inp that match chars at same position in out
        inp2_char_list = list(inp)  # Convert string to list so we can modify
        length = min(len(out), len(inp))
        match_list = []

        for i in range(length):
            idx = len(inp) - i - 1
            if inp[idx] == out[len(out) - i - 1] and inp[idx] != ',':
                match_list.append(idx)

            if inp[i] == out[i] and inp[i] != ',':
                match_list.append(i)

        for i in match_list:
            inp2_char_list[i] = '@'

        inp = re.sub(r'[@| ]', "", ''.join(inp2_char_list))
        return out, inp
