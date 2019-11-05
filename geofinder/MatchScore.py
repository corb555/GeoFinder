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
            score = 40
        else:
            score: int = self.match_score_calc(inp_place, res_place)

        feature_score = Geodata.Geodata.get_priority(res_place.feature)
        return score + feature_score

    def match_score_calc(self, inp_place:Loc.Loc, res_place:Loc.Loc) -> int:
        # Return a score 0-100 reflecting the difference between the user input and the result:
        # The percent of characters in inp that were NOT matched by a word in result
        # Lower score is better match.  0 is perfect match, 100 is no match
        inp_len = [0] * 5
        num_inp_tokens = 1

        in_pref = inp_place.prefix
        if  in_pref == '':
            in_pref = ' '
        save_type = inp_place.place_type
        inp_place.place_type = Loc.PlaceType.CITY
        inp = in_pref + ',' + inp_place.format_full_nm(None)
        inp_place.place_type = save_type

        inp = GeoKeys.search_normalize(inp, inp_place.country_iso)
        inp = GeoKeys.remove_noise_words(inp)
        inp_tokens = inp.split(',')
        inp_tokens[-1], modified = GeoKeys.country_normalize(inp_tokens[-1])

        # Store length of original tokens
        for it, tk in enumerate(inp_tokens):
            inp_tokens[it] = inp_tokens[it].strip(' ')
            tmp = re.sub(' ','', inp_tokens[it])
            inp_len[it] = len(tmp)

        res_pref = res_place.prefix
        #if  res_pref == '':
        #    res_pref = ' '
        save_type = res_place.place_type

        pref = " "
        res_place.original_entry = pref + ',' + res_place.format_full_nm(None)
        res = GeoKeys.search_normalize(res_place.original_entry, res_place.country_iso)
        res = GeoKeys.remove_noise_words(res)
        res_tokens = res.split(',')
        res_tokens[-1], modified = GeoKeys.country_normalize(res_tokens[-1])

        res = ', '.join(map(str, res_tokens))
        orig_res_len = len(res)

        # Create a list of all the words in input
        inp2 = ', '.join(inp_tokens)

        #self.logger.debug(f'Matchscore: Res [{res}] In [{inp2}] ')

        res, inp2 = self.remove_matching_words(res, inp2)
        res, inp2 = self.remove_matching_characters(res, inp2)
        #self.logger.debug(f'Removed: In [{inp2}] Res [{res}]')

        # For each input token calculate percent of new size vs original size
        inp_tokens2 = inp2.split(',')
        in_score = 0

        # Each item in place hierarchy gets a different weighting
        #        Pref, city,cty,state,country
        weight = [0.1, 1.0, 0.4, 0.6, 0.9 ]

        score_text = ''

        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                sc = int(100.0 * len(inp_tokens2[idx]) / inp_len[idx])
                in_score += sc * weight[idx]
                score_text += f'  {idx}) [{tk}] {sc}% * {weight[idx]} '
                num_inp_tokens += 1.0 * weight[idx]
                #self.logger.debug(f'{idx} [{inp_tokens2[idx]}:{inp_tokens[idx]}] rawscr={sc}% orig_len={inp_len[idx]} wgt={weight[idx]}')

        # Average over number of tokens, e.g. average percent of tokens unmatched
        in_score = in_score / num_inp_tokens

        # Output score (percent of output that was not matched)
        new_len = len(res.strip(' '))
        if orig_res_len > 0:
            out_score = int(100.0 * new_len / orig_res_len)
            if new_len > 0:
                out_score += 1
        else:
            out_score = 0


        if len(inp_place.prefix) > 0:
            # prefix penalty
            pref_score = 2 * len(inp_place.prefix) + 2 *len(inp_place.extra)
        else:
            pref_score = 0

        score =  in_score + 0.2 * out_score + pref_score
        if inp_place.standard_parse == False:
            # Tokens were not in correct order, so give penalty
            score += 3

        self.logger.debug(f'SC {score:.1f} [{res_place.original_entry}]  out={out_score*0.2:.1f} in={in_score:.1f} {pref_score} {score_text}')

        return int(score)

    def remove_matching_words(self, out: str, inp: str):
        inp_words = inp.split(' ')

        # If any WORD in input is in result, delete it from input and from result
        lst = sorted(inp_words, key=len, reverse=True)  # Use longest words first
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
            idx = len(inp)-i-1
            if inp[idx] == out[len(out)-i-1] and inp[idx] != ',':
                match_list.append(idx)

            if inp[i] == out[i] and inp[i] != ',':
                match_list.append(i)

        for i in match_list:
            inp2_char_list[i] = '@'

        inp = re.sub(r'[@| ]', "", ''.join(inp2_char_list))
        return out, inp