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

    def debug(self, txt):
        self.logger.debug(txt)

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_five_part_title(self, place: Loc.Loc):
        # Returns a five part title string and tokenized version (prefix,city,county,state,country)

        # Force type to City to generate four part title (then we add prefix for five parts)
        save_type = place.place_type
        place.place_type = Loc.PlaceType.CITY

        # Normalize country name
        save_country = place.country_name
        place.country_name, modified = GeoKeys.country_normalize(place.country_name)

        if len(place.extra) > 0:
            full_title = place.prefix + ' ' + place.extra + ',' + place.format_full_nm(None)
        else:
            full_title = place.prefix +  ',' + place.format_full_nm(None)

        full_title = GeoKeys.search_normalize(full_title, place.country_iso)
        full_title = GeoKeys.remove_noise_words(full_title)
        full_title = re.sub(', ', ',', full_title)

        name_tokens = full_title.split(',')

        # Restore values to original
        place.place_type =  save_type
        place.country_name = save_country

        return full_title, name_tokens

    def match_score(self, inp_place: Loc.Loc, res_place: Loc.Loc) -> int:
        # Return a score 0-100 reflecting the difference between the user input and the result:
        # The percent of characters in inp that were NOT matched by a word in result
        # Lower score is better match.  0 is perfect match, 100 is no match
        inp_len = [0] * 5
        num_inp_tokens = 0.0
        in_score = 0

        if '*' in inp_place.original_entry:
            # if it was a wildcard search it's hard to rank.  just set to 40
            return 40

        # Create full place title (prefix,city,county,state,country) from inp_place
        inp_title, inp_tokens = self.get_five_part_title(inp_place)

        # Create full place title (prefix,city,county,state,country) from res_place
        res_place.prefix = ' '
        res_title, res_tokens = self.get_five_part_title(res_place)

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
        #        Pref, city,cty,state,country
        weight = [0.5, 1.0, 0.2, 0.6, 0.9]
        score_diags = ''

        # Calculate percent of input text that was unmatched, then apply weighting
        for idx, tk in enumerate(inp_tokens):
            if inp_len[idx] > 0:
                unmatched_percent = int(100.0 * len(unmatched_input_tokens[idx].strip(' ')) / inp_len[idx])
                in_score += unmatched_percent * weight[idx]
                score_diags += f'  {idx}) [{tk}]{inp_len[idx]} {unmatched_percent}% * {weight[idx]} '
                #self.logger.debug(f'{idx}) Rem=[{unmatched_input_tokens[idx].strip(" " )}] wgtd={unmatched_percent * weight[idx]}')
                num_inp_tokens += 1.0 * weight[idx]
                # self.logger.debug(f'{idx} [{inp_tokens2[idx]}:{inp_tokens[idx]}] rawscr={sc}% orig_len={inp_len[idx]} wgt={weight[idx]}')
                if idx < 2:
                    # If full first or second token of result is in input  then lower score
                    if res_tokens[idx] in inp_tokens[idx]:
                        in_score -= 10
        # Average over number of tokens (with fractional weight).  Gives 0-100% regardless of weighting and number of tokens
        #self.logger.debug(f'raw in={in_score}  numtkn={num_inp_tokens}')
        in_score = in_score / num_inp_tokens

        # Calculate percent of result text that was unmatched
        if orig_res_len > 0:
            out_score = int(100.0 * len(res_word_list.strip(' ')) / orig_res_len)
            #self.logger.debug(f"Out=[{res_word_list.strip(' ')}] orig_len={orig_res_len}")
        else:
            out_score = 0

        if inp_place.standard_parse == False:
            # If Tokens were not in hierarchical order, give penalty
            parse_penalty = 2.0
        else:
            parse_penalty = 0.0

        # Feature score is to ensure "important" places (large city, etc) get somewhat higher rank.
        feature_score = Geodata.Geodata.get_priority(res_place.feature)

        # Add up scores - Each item is 0-100
        out_weight = 0.17
        feature_weight = 0.06
        in_weight = 1.0 - out_weight - feature_weight
        score = in_score * in_weight + out_weight * out_score + feature_score * feature_weight + parse_penalty

        #self.logger.debug(f'SCORE {score:.1f} [{res_title}]  out={out_score * out_weight:.1f} '
        #                  f'in={in_score:.1f} feat={feature_score * feature_weight:.1f} parse={parse_penalty}\n {score_diags}')

        return score

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
        # Swap all commas in inp string so we don't match and remove them
        inp = re.sub(',', '@', inp)
        out, inp = self.remove_matching_seq(out, inp, 15)
        # Restore commas in inp
        inp = re.sub('@', ',', inp)
        return out.strip(' '), inp.strip(' ')