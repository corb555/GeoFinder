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
import os
import re
from collections import Counter

from symspellpy.symspellpy import SymSpell, Verbosity

delim = '_'

noise_words = ['died', 'buried', 'executed', 'fatally', 'wounded']


class SpellCheck:
    def __init__(self, progress, directory, countries_dict):
        self.progress = progress
        self.logger = logging.getLogger(__name__)
        self.spelling_update = Counter()
        self.directory = directory
        self.spell_path = os.path.join(self.directory, 'spelling.pkl')
        self.countries_dict = countries_dict
        self.sym_spell = SymSpell()

    def insert(self, name, iso):
        if 'gothland cemetery' not in name and name not in noise_words:
            name_tokens = name.split(' ')
            for word in name_tokens:
                key = f'{word}'
                if len(key) > 2:
                    self.spelling_update[key] += 1

    def write(self):
        # Create blank spelling dictionary
        path = os.path.join(self.directory, 'spelling.tmp')
        fl = open(path, 'w')
        fl.write('the,1\n')
        fl.close()
        success = self.sym_spell.create_dictionary(corpus=path)
        if not success:
            self.logger.error(f"error creating spelling dictionary")

        self.logger.info('Building Spelling Dictionary')

        # Add all words from geonames into spelling dictionary
        for key in self.spelling_update:
            self.sym_spell.create_dictionary_entry(key=key, count=self.spelling_update[key])

        self.logger.info('Writing Spelling Dictionary')
        self.sym_spell.save_pickle(self.spell_path)

    def read(self):
        success = False
        if os.path.exists(self.spell_path):
            self.logger.info(f'Loading Spelling Dictionary from {self.spell_path}')
            success = self.sym_spell.load_pickle(self.spell_path)
        else:
            self.logger.error(f"spelling dictionary not found: {self.spell_path}")

        if not success:
            self.logger.error(f"error loading spelling dictionary from {self.spell_path}")
        else:
            self.sym_spell.delete_dictionary_entry(key='gothland')

        size = len(self.sym_spell.words)
        self.logger.info(f"Spelling Dictionary contains {size} words")

    def lookup(self, input_term):
        #suggestions = [SymSpell.    SuggestItem]
        if '*' in input_term:
            return input_term
        res = ''
        if len(input_term) > 1:
            suggestions = self.sym_spell.lookup(input_term, Verbosity.CLOSEST,
                                           max_edit_distance=2, include_unknown=True)
            for idx, item in enumerate(suggestions):
                if idx > 3:
                    break
                #self.logger.debug(f'{item._term}')
                if item._term[0] == input_term[0]:
                    # Only accept results where first letter matches
                    res += item._term + ' '
            return res
        else:
            return input_term

    def lookup_compound(self, phrase):
        suggestions = self.sym_spell.lookup_compound(phrase=phrase,
                                       max_edit_distance=2, ignore_non_words=False)
        for item in suggestions:
            self.logger.debug(f'{item._term}')
        return suggestions[0]._term

    def fix_spelling(self, text):
        new_text = text
        if  bool(re.search(r'\d', text)):
            # Has digits, just return text, no spellcheck
            pass
        elif 'st ' in text:
            # Spellcheck not handling St properly
            pass
        else:
            if len(text) > 0:
                new_text = self.lookup(text)
                self.logger.debug(f'Spell {text} -> {new_text}')

        return new_text.strip(' ')

        #for word in text.split(' '):
        #    new_text += self.lookup(word) + ' '
