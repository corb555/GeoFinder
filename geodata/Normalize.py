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

from geodata import GeodataFiles, GeoUtil, Loc, GeoDB


def normalize_for_scoring(text: str, iso: str) -> str:
    # Normalize the title we use to determine how close a match we got
    text = normalize_for_search(text, iso)
    text = _remove_noise_words(text)
    text = re.sub(', ', ',', text)
    return text


def normalize_for_search(text: str, iso) -> str:
    text = normalize(text=text, remove_commas=False)

    return text


def normalize(text: str, remove_commas: bool) -> str:
    """
    Normalize text - Convert from UTF-8 to lowercase ascii.  Remove most punctuation. Remove commas if parameter set.
    Then call _phrase_normalize() which normalizes common phrases with multiple spellings, such as Saint
    :param text: Text to normalize
    :param remove_commas: True if commas should be removed
    :return: Normalized text
    """

    # Convert UT8 to ascii
    text = unidecode.unidecode(text)
    text = str(text).lower()

    # remove most punctuation
    if remove_commas:
        text = re.sub(r"[^a-zA-Z0-9 $*']+", " ", text)
    else:
        text = re.sub(r"[^a-zA-Z0-9 $*,']+", " ", text)

    text = _phrase_normalize(text)
    return text.strip(' ')


def _phrase_normalize(text: str) -> str:
    """ Strip spaces and normalize spelling for items such as Saint and County """
    # Replacement patterns to clean up entries
    text = re.sub('r.k. |r k ', 'rooms katholieke ', text)
    text = re.sub('saints |sainte |sint |saint |sankt |st. ', 'st ', text)  # Normalize Saint to St
    text = re.sub(r' co\.', ' county', text)  # Normalize County
    text = re.sub(r'united states of america', 'usa', text)  # Normalize to USA
    text = re.sub(r'united states', 'usa', text)  # Normalize to USA
    text = re.sub(r'town of ', '', text)  #  - remove town of
    text = re.sub(r'city of ', '', text)  #  - remove city of
    text = re.sub(r'near ', ' ', text)  #  - remove near


    if 'amt' not in text:
        text = re.sub(r'^mt ', 'mount ', text)

    text = re.sub('  +', ' ', text)  # Strip multiple space
    text = re.sub('county of ([^,]+)', r'\g<1> county', text)  # Normalize 'Township of X' to 'X Township'
    text = re.sub('township of ([^,]+)', r'\g<1> township', text)  # Normalize 'Township of X' to 'X Township'

    text = re.sub('cathedral of ([^,]+)', r'\g<1> cathedral', text)  # Normalize 'Township of X' to 'X Township'
    text = re.sub('palace of ([^,]+)', r'\g<1> palace', text)  # Normalize 'Township of X' to 'X Township'
    text = re.sub('castle of ([^,]+)', r'\g<1> castle', text)  # Normalize 'Township of X' to 'X Township'

    text = re.sub(r',castle', ' castle', text)  # - castle  - remove extra comma
    text = re.sub(r',palace', ' palace', text)  # - palace  - remove extra comma
    text = re.sub(r',cathedral', ' cathedral', text)  # - palace  - remove extra comma

    text = re.sub(r'battle of ', 'battle of ,', text)  #  - battle of - add comma
    text = re.sub(r'k. at ', ' ', text)  #  - killed at  - remove extra comma
    text = re.sub(r'killed ', ' ', text)  #  - killed at  - remove extra comma
    return text


def _remove_noise_words(text: str):
    # Calculate score with noise word removal / normalization
    # inp = re.sub('shire', '', inp)

    # Clean up odd case for Normandy American cemetery having only English spelling of Normandy in France
    text = re.sub(r"normandy american ", 'normandie american ', text)
    text = re.sub(r'nouveau brunswick', ' ', text)
    text = re.sub(r'westphalia', 'westfalen', text)
    text = re.sub(r'city of ', ' ', text)
    text = re.sub(r'citta metropolitana di ', ' ', text)
    text = re.sub(r'town of ', ' ', text)
    text = re.sub(r'kommune', '', text)
    text = re.sub(r"politischer bezirk ", ' ', text)
    text = re.sub(r'erry', 'ury', text)
    text = re.sub(r'ery', 'ury', text)
    text = re.sub(r'borg', 'burg', text)
    text = re.sub(r'bourg', 'burg', text)
    text = re.sub(r'urgh', 'urg', text)
    text = re.sub(r'mound', 'mund', text)
    text = re.sub(r'ourne', 'orn', text)
    text = re.sub(r'ney', 'ny', text)
    text = re.sub(r' de ', ' ', text)
    text = re.sub(r' di ', ' ', text)
    text = re.sub(r' du ', ' ', text)
    text = re.sub(r' of ', ' ', text)
    text = re.sub(r' departement', ' ', text)
    text = re.sub(r'battle of ', 'battle of ,', text)  #  - battle of - add comma
    text = re.sub(r'k. at ', ' ', text)  #  - killed at  - remove extra comma
    text = re.sub(r'killed ', ' ', text)  #  - killed at  - remove extra comma
    text = re.sub(r'royal borough of windsor and maidenhead', 'berkshire', text)

    return text


def remove_aliase(input_words, res_words) -> (str, str):
    if "middlesex" in input_words and "greater london" in res_words:
        input_words = re.sub('middlesex', '', input_words)
        res_words = re.sub('greater london', '', res_words)
    return input_words, res_words


alias_list = {
    'norge': ('norway', '', 'ADM0'),
    'sverige': ('sweden', '', 'ADM0'),
    'osterreich': ('austria', '', 'ADM0'),
    'belgie': ('belgium', '', 'ADM0'),
    'brasil': ('brazil', '', 'ADM0'),
    'danmark': ('denmark', '', 'ADM0'),
    'eire': ('ireland', '', 'ADM0'),
    'magyarorszag': ('hungary', '', 'ADM0'),
    'italia': ('italy', '', 'ADM0'),
    'espana': ('spain', '', 'ADM0'),
    'deutschland': ('germany', '', 'ADM0'),
    'prussia': ('germany', '', 'ADM0'),
    'suisse': ('switzerland', '', 'ADM0'),
    'schweiz': ('switzerland', '', 'ADM0'),

    'bayern': ('bavaria', 'de', 'ADM1'),
    'westphalia': ('westfalen', 'de', 'ADM1'),

    'normandy': ('normandie', 'fr', 'ADM1'),
    'brittany': ('bretagne', 'fr', 'ADM1'),
    'burgundy': ('bourgogne franche comte', 'fr', 'ADM1'),
    'franche comte': ('bourgogne franche comte', 'fr', 'ADM1'),
    'aquitaine': ('nouvelle aquitaine', 'fr', 'ADM1'),
    'limousin': ('nouvelle aquitaine', 'fr', 'ADM1'),
    'poitou charentes': ('nouvelle aquitaine', 'fr', 'ADM1'),
    'alsace': ('grand est', 'fr', 'ADM1'),
    'champagne ardenne': ('grand est', 'fr', 'ADM1'),
    'lorraine': ('grand est', 'fr', 'ADM1'),
    'languedoc roussillon': ('occitanie', 'fr', 'ADM1'),
    'nord pas de calais': ('hauts de france', 'fr', 'ADM1'),
    'picardy': ('hauts de france', 'fr', 'ADM1'),
    'auvergne': ('auvergne rhone alpes', 'fr', 'ADM1'),
    'rhone alpes': ('auvergne rhone alpes', 'fr', 'ADM1'),

    'breconshire': ('sir powys', 'gb', 'ADM2'),
}


def add_aliases(geo_files: GeodataFiles):
    #  Add alias names to DB
    place = Loc.Loc()
    for ky in alias_list:
        row = alias_list.get(ky)
        place.clear()

        # Create Geo_row
        # ('paris', 'fr', '07', '012', '12.345', '45.123', 'PPL')
        geo_row = [None] * GeoDB.Entry.MAX
        geo_row[GeoDB.Entry.FEAT] = row[2]
        geo_row[GeoDB.Entry.ISO] = row[1].lower()
        geo_row[GeoDB.Entry.LAT] = '99.9'
        geo_row[GeoDB.Entry.LON] = '99.9'
        geo_row[GeoDB.Entry.ADM1] = ''
        geo_row[GeoDB.Entry.ADM2] = ''

        geo_files.update_geo_row_name(geo_row=geo_row, name=ky)
        if row[2] == 'ADM1':
            geo_row[GeoDB.Entry.ADM1] = ky
            place.place_type = Loc.PlaceType.ADMIN1
        elif row[2] == 'ADM2':
            geo_row[GeoDB.Entry.ADM2] = ky
            place.place_type = Loc.PlaceType.ADMIN2
        else:
            place.place_type = Loc.PlaceType.COUNTRY
            place.country_name = ky

        place.country_iso = row[1]
        place.admin1_name = geo_row[GeoDB.Entry.ADM1]
        place.admin2_name = geo_row[GeoDB.Entry.ADM2]

        # Lookup main entry and get GEOID
        geo_files.geodb.lookup_place(place)
        if place.result_type in GeoUtil.successful_match and len(place.georow_list) > 0:
            geo_files.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)
            # place.format_full_nm(geodata.geo_files.output_replace_dct)

        geo_row[GeoDB.Entry.ID] = place.geoid

        geo_files.geodb.insert(geo_row=geo_row, feat_code=row[2])


def admin1_normalize(admin1_name: str, iso):
    """ Normalize historic or colloquial Admin1 names to standard """
    if iso == 'de':
        admin1_name = re.sub(r'bayern', 'bavaria', admin1_name)
        admin1_name = re.sub(r'westphalia', 'westfalen', admin1_name)

    if iso == 'fr':
        admin1_name = re.sub(r'normandy', 'normandie', admin1_name)
        admin1_name = re.sub(r'brittany', 'bretagne', admin1_name)

        admin1_name = re.sub(r'burgundy', 'bourgogne franche comte', admin1_name)
        admin1_name = re.sub(r'franche comte', 'bourgogne franche comte', admin1_name)
        admin1_name = re.sub(r'aquitaine', 'nouvelle aquitaine', admin1_name)
        admin1_name = re.sub(r'limousin', 'nouvelle aquitaine', admin1_name)
        admin1_name = re.sub(r'poitou charentes', 'nouvelle aquitaine', admin1_name)
        admin1_name = re.sub(r'alsace', 'grand est', admin1_name)
        admin1_name = re.sub(r'champagne ardenne', 'grand est', admin1_name)
        admin1_name = re.sub(r'lorraine', 'grand est', admin1_name)
        admin1_name = re.sub(r'languedoc roussillon', 'occitanie', admin1_name)
        admin1_name = re.sub(r'midi pyrenees', 'occitanie', admin1_name)
        admin1_name = re.sub(r'nord pas de calais', 'hauts de france', admin1_name)
        admin1_name = re.sub(r'picardy', 'hauts de france', admin1_name)
        admin1_name = re.sub(r'auvergne', 'auvergne rhone alpes', admin1_name)
        admin1_name = re.sub(r'rhone alpes', 'auvergne rhone alpes', admin1_name)

    return admin1_name


def admin2_normalize(admin2_name: str, iso) -> (str, bool):
    """
    Normalize historic or colloquial Admin2 names to standard
    :param admin2_name:
    :return: (result, modified)
    result - new string
    modified - True if modified
    """
    mod = False

    if iso == 'gb':
        # res = re.sub(r'middlesex', ' ', res)
        admin2_name = re.sub(r'breconshire', 'sir powys', admin2_name)
        mod = True

    return admin2_name, mod


def country_normalize(country_name) -> (str, bool):
    """
    normalize local language Country name to standardized English country name for lookups
    :param country_name:
    :return: (result, modified)
    result - new string
    modified - True if modified
    """
    country_name = re.sub(r'\.', '', country_name)  # remove .

    natural_names = {
        'norge': 'norway',
        'sverige': 'sweden',
        'osterreich': 'austria',
        'belgie': 'belgium',
        'brasil': 'brazil',
        'danmark': 'denmark',
        'magyarorszag': 'hungary',
        'italia': 'italy',
        'espana': 'spain',
        'deutschland': 'germany',
        'prussia': 'germany',
        'suisse': 'switzerland',
        'schweiz': 'switzerland',

    }
    if natural_names.get(country_name):
        country_name = natural_names.get(country_name)
        return country_name.strip(' '), True
    else:
        return country_name.strip(' '), False
