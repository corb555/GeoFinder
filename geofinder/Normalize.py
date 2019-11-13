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
import re
import unidecode

def normalize_for_scoring(full_title:str, iso:str)->str:
    # Normalize the title we use to determine how close a match we got
    full_title = normalize_for_search(full_title, iso)
    full_title = _remove_noise_words(full_title)
    full_title = re.sub(', ', ',', full_title)
    return full_title

def normalize_for_search(res, iso)->str:
    res = normalize(res=res, remove_commas=False)
    return res

def remove_aliase(input_words, res_words)->(str, str):
    if "middlesex" in input_words and "greater london" in res_words:
        input_words = re.sub('middlesex','', input_words)
        res_words = re.sub('greater london','', res_words)
    return input_words, res_words

def normalize(res:str, remove_commas:bool) -> str:
    """ Strip commas.   strip spaces and normalize spelling for items such as Saint and County and chars: ø ß """

    # Convert UT8 to ascii
    res = unidecode.unidecode(res)
    res = str(res).lower()

    # remove most punctuation
    if remove_commas:
        res = re.sub(r"[^a-zA-Z0-9 $.*']+", " ", res)
    else:
        res = re.sub(r"[^a-zA-Z0-9 $.*,']+", " ", res)

    res = _phrase_normalize(res)
    return res.strip(' ')

def _phrase_normalize(res) -> str:
    """ Strip spaces and normalize spelling for items such as Saint and County """
    # Replacement patterns to clean up entries
    res = re.sub('r.k. |r k ', 'rooms katholieke ',res)
    res = re.sub('saints |sainte |sint |saint |sankt |st. ', 'st ', res)  # Normalize Saint to St
    res = re.sub(r' co\.', ' county', res)  # Normalize County
    res = re.sub(r'united states of america', 'usa', res)  # Normalize to USA
    res = re.sub(r'united states', 'usa', res)  # Normalize to USA
    res = re.sub(r'town of ', '', res)  # Normalize - remove town of
    res = re.sub(r'city of ', '', res)  # Normalize - remove city of

    if 'amt' not in res:
        res = re.sub(r'^mt ', 'mount ', res)

    res = re.sub('  +', ' ', res)  # Strip multiple space
    res = re.sub('county of ([^,]+)', r'\g<1> county', res)  # Normalize 'Township of X' to 'X Township'
    res = re.sub('township of ([^,]+)', r'\g<1> township', res)  # Normalize 'Township of X' to 'X Township'
    res = re.sub('cathedral of ([^,]+)', r'\g<1> cathedral', res)  # Normalize 'Township of X' to 'X Township'
    return res

def _remove_noise_words(res):
    # Calculate score with noise word removal (or normalization)
    # inp = re.sub('shire', '', inp)

    # Clean up odd case for Normandy American cemetery having only English spelling of Normandy in France
    res = re.sub(r"normandy american ", 'normandie american ', res)

    res = re.sub(r'nouveau brunswick', ' ', res)

    res = re.sub(r'city of ', ' ', res)
    res = re.sub(r'citta metropolitana di ', ' ', res)
    res = re.sub(r'town of ', ' ', res)

    res = re.sub(r"politischer bezirk ", ' ', res)

    res = re.sub(r'erry', 'ury', res)
    res = re.sub(r'ery', 'ury', res)

    res = re.sub(r'borg', 'burg', res)
    res = re.sub(r'bourg', 'burg', res)
    res = re.sub(r'urgh', 'urg', res)

    res = re.sub(r'mound', 'mund', res)
    res = re.sub(r'ourne', 'orn', res)
    res = re.sub(r'ney', 'ny', res)

    res = re.sub(r' de ', ' ', res)
    res = re.sub(r' di ', ' ', res)
    res = re.sub(r' du ', ' ', res)
    res = re.sub(r' of ', ' ', res)

    """
    res = re.sub(r' county', ' ', res)
    res = re.sub(r' stadt', ' ', res)
    res = re.sub(r' departement', ' ', res)
    res = re.sub(r'regierungsbezirk ', ' ', res)
    res = re.sub(r' departement', ' ', res)
    res = re.sub(r'gemeente ', ' ', res)
    res = re.sub(r'provincia ', ' ', res)
    res = re.sub(r'provincie ', ' ', res)
    """

    return res

def admin1_normalize(res, iso):
    #res = re.sub(r"'", '', res)  # Normalize hyphens
    if iso == 'de':
        res = re.sub(r'bayern', 'bavaria', res)

    if iso == 'fr':
        res = re.sub(r'normandy', 'normandie', res)
        res = re.sub(r'brittany', 'bretagne', res)

        res = re.sub(r'burgundy', 'bourgogne franche comte', res)
        res = re.sub(r'franche comte', 'bourgogne franche comte', res)
        res = re.sub(r'aquitaine', 'nouvelle aquitaine', res)
        res = re.sub(r'limousin', 'nouvelle aquitaine', res)
        res = re.sub(r'poitou charentes', 'nouvelle aquitaine', res)
        res = re.sub(r'alsace', 'grand est', res)
        res = re.sub(r'champagne ardenne', 'grand est', res)
        res = re.sub(r'lorraine', 'grand est', res)
        res = re.sub(r'languedoc roussillon', 'occitanie', res)
        res = re.sub(r'midi pyrenees', 'occitanie', res)
        res = re.sub(r'nord pas de calais', 'hauts de france', res)
        res = re.sub(r'picardy', 'hauts de france', res)
        res = re.sub(r'auvergne', 'auvergne rhone alpes', res)
        res = re.sub(r'rhone alpes', 'auvergne rhone alpes', res)

    return res

def admin2_normalize(res, iso)->(str, bool):
    """
    Some English counties have had Shire removed from name, try doing that
    :param res:
    :return: (result, modified)
    result - new string
    modified - True if modified
    """
    mod = False
    #if 'shire' in res:
    #    res = re.sub('shire', '', res)
    #   mod = True

    if iso == 'gb':
        #res = re.sub(r'middlesex', ' ', res)
        res = re.sub(r'breconshire', 'sir powys', res)
        mod = True

    return res, mod

def country_normalize(res)->(str,bool):
    """
    normalize local language Country name to standardized English country name for lookups
    :param res:
    :return: (result, modified)
    result - new string
    modified - True if modified
    """
    res = re.sub(r'\.', '', res)  # remove .

    natural_names = {
    'norge': 'norway',
    'sverige': 'sweden',
    'osterreich' : 'austria',
    'belgie' : 'belgium',
    'brasil' : 'brazil',
    'danmark' : 'denmark',
    'magyarorszag' : 'hungary',
    'italia' : 'italy',
    'espana' : 'spain',
    'deutschland' : 'germany',
    'prussia' : 'germany',
    'suisse' : 'switzerland',
    'schweiz' : 'switzerland',

    }
    if natural_names.get(res):
        res = natural_names.get(res)
        return res, True
    else:
        return res, False
