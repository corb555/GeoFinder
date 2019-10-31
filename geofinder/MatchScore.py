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

from geofinder import GeoKeys, Geodata

class MatchScore:
    """ Calculate how close two placenames are lexically """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def match_score(self, inp_place, res_place, iso) -> int:
        score: int = self.match_score_calc(inp_place, res_place)
        feature_score = Geodata.Geodata.get_priority(res_place.feature)
        if len(inp_place.prefix) > 0:
            pref_score = 1 + len(inp_place.prefix)/8
        else:
            pref_score = 0
        return score + feature_score + pref_score

    def match_score_calc(self, inp_place, res_place) -> int:
        # Return a score 0-100 reflecting the difference between the user input and the result:
        # The percent of characters in inp that were NOT matched by a word in result
        # Lower score is better match.  0 is perfect match, 100 is no match
        inp_len = [0] * 8
        res_len = [0] * 8
        inp = GeoKeys.search_normalize(inp_place.name, inp_place.country_iso)
        inp = GeoKeys.remove_noise_words(inp)
        inp_tokens = inp.split(',')
        num_inp_tokens = len(inp_tokens)

        res = GeoKeys.search_normalize(res_place.name, res_place.country_iso)
        res = GeoKeys.remove_noise_words(res)
        res_tokens = res.split(',')

        # Counties are frequently wrong.  Minimize impact
        if len(res_tokens) > 2 and len(inp_tokens) > 2:
            # See if result county is in user request.  If it is not, just keep 2 chars
            if res_tokens[-3].strip(' ') not in inp:
                res_tokens[-3] = res_tokens[-3][:8]
                inp_tokens[-3] = inp_tokens[-3][:8]  # Just keep the first 2 chars of county name

        # Countries are frequently left out.  Minimize impact
        if len(res_tokens) > 0:
            # See if result country is in user request.  If it is not, delete it
            if res_tokens[-1].strip(' ') not in inp:
                res_tokens[-1] = ''

        # Store length of original tokens
        for it, tk in enumerate(inp_tokens):
            inp_tokens[it] = inp_tokens[it].strip(' ')
            inp_len[it] = len(tk)

        res = ', '.join(map(str, res_tokens))
        orig_res_len = len(res)

        # Create a list of all the words in input
        inp2 = ', '.join(inp_tokens)

        res, inp2 = self.remove_matching_words(res, inp2)
        res, inp2 = self.remove_matching_characters(res, inp2)
        #self.logger.debug(f' In [{inp}] Res [{res}]')

        # For each input token calculate percent of new size vs original size
        inp_tokens = inp2.split(',')
        in_score = 0

        # Each item in place hierarchy gets a different weighting
        weight = [1.0, 1.005, 0.5, 1.015, 1.02, 1.035]

        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                sc = int(100.0 * len(inp_tokens[idx]) / inp_len[idx])
                in_score += sc * weight[idx]
                #self.logger.debug(f'{idx} [{inp_tokens[idx]}] scr={sc} wgt={weight[idx]}')

        # Average over number of tokens, e.g. average percent of tokens unmatched
        in_score = in_score / num_inp_tokens

        # Output score (percent of first token in output that was not matched)
        new_len = len(res.strip(' '))
        if orig_res_len > 0:
            out_score = (int((0.11 * 100.0) * new_len / orig_res_len))
            if new_len > 0:
                out_score += 1
        else:
            out_score = 0

        score = in_score + out_score
        #self.logger.debug(f'Sc={score}  Match [{res_place.name}]  InScr={in_score:.1f} InRem [{inp}] '
        #                  f'OutScr={out_score:.1f} OutRem [{res}]  ')
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