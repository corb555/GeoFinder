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
import argparse
import copy
import glob
import os
import re
import sys
import time
import webbrowser
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from typing import Dict

from geodata import Normalize, GeoUtil, Loc
from geodata import  __version__ as geodata_version

from geodata.Geodata import ResultFlags, Geodata
from tk_helper import TKHelper

from geofinder import AppLayout
from geofinder import __version__
from geofinder.util import CachedDictionary, Config, IniHandler
from geofinder.ancestry import Gedcom, GrampsXml
from geofinder.util_menu import UtilFeatureFrame, UtilLayout

MISSING_FILES = 'Missing Files.  Please select Config and correct errors in Errors Tab'
file_types = 'GEDCOM / Gramps XML'

GEOID_TOKEN = 1
PREFIX_TOKEN = 2
temp_suffix = 'tmp'


class GeoFinder:
    """
    Read in a GEDCOM or Gramps genealogy file and verify that the spelling of each place is correct.
    If place is found, add the latitude and longitude to the output  file.
    If place can't be found, allow the user to correct it.  If match is found, apply the change to
    all matching entries.
    Also allow the user to mark an item to skip if a resolution cant be found.
    Skiplist is a list of locations the user has flagged to skip.  These items will be ignored
    Global replace list is list of fixes that have been found.  These are applied to any new similar matches.

    Main classes for Application:

    #GeoFinder - The main GUI

    #Packages:
    #Geodata
        GeoData - The geonames data model routines
        GeodataFile - routines to read/write geoname data sources
        Loc - holds all info for a single location
        GeoDB - Database insert/lookup routines.
    #Ancestry:
        GEDCOM - routines to read and write GEDCOM files
        GrampsXML - routines to read and write GrampsXML files
    #Util: -  the frames for the Config button

    """

    def __init__(self):
        print('GeoFinder v{}'.format(__version__.__version__))
        print('Python {}.{}'.format(sys.version_info[0], sys.version_info[1]))

        if sys.version_info < (3, 6, 0):
            raise Exception("GeoFinder Requires Python 3.6 or higher.")
        val = ''
        print(f'GeoFinder Requires Python 3.6 or higher {val}')
        
        print(f'Geodata v{geodata_version.__version__}')

        self.save_enabled = False  # Only allow SAVE when we have an item that was matched in geonames
        self.user_selected_list = False  # Indicates whether user selected a list entry or text edit entry
        self.update_counter = 0
        self.matched_count = 0
        self.review_count = 0
        self.skip_count = 0
        self.ancestry_file_handler = None
        self.place = None
        self.skiplist = None
        self.global_replace = None
        self.geodata = None
        self.out_suffix = 'unknown_suffix'
        self.out_diag_file = None
        self.in_diag_file = None
        self.enable_spell_checker = False

        # get command line arguments
        self.get_command_line_arguments()

        # Create App window and configure  window buttons and widgets
        self.w: AppLayout.AppLayout = AppLayout.AppLayout(self)
        self.w.create_initialization_widgets()

        # Get our base directory path from INI file.  Create INI if it doesnt exist
        home_path = str(Path.home())
        self.directory = Path(os.path.join(home_path, str(GeoUtil.get_directory_name())))
        self.ini_handler = IniHandler.IniHandler(base_path=home_path, ini_name='geofinder.ini')
        self.directory = self.ini_handler.get_directory_from_ini("GeoFinder", GeoUtil.get_directory_name())

        self.cache_dir = GeoUtil.get_cache_directory(self.directory)
        self.logger.info(f'Cache directory {self.cache_dir}')

        # Set up configuration  class
        self.cfg = Config.Config(self.directory)
        self.util = UtilLayout.UtilLayout(root=self.w.root, directory=self.directory, cache_dir=self.cache_dir)

        if not os.path.exists(self.cache_dir):
            # Create directories for GeoFinder
            if messagebox.askyesno('Geoname Data Cache Folder not found',
                                   f'Create Geoname Cache folder?\n\n{self.cache_dir} '):
                err = self.cfg.create_directories()
                if not os.path.exists(self.cache_dir):
                    messagebox.showwarning('Geoname Data Cache Folder not found',
                                           f'Unable to create folder\n\n{self.cache_dir} ')
                    self.shutdown()
                else:
                    self.logger.debug(f'Created {self.cache_dir}')
                    messagebox.showinfo('Geoname Data Cache Folder created',
                                        f'Created folder\n\n{self.cache_dir} ')
            else:
                self.shutdown()

        # Ensure GeoFinder directory structure is valid
        if self.cfg.valid_directories():
            # Directories are valid.  See if  required Geonames files are present
            err = self.check_configuration()
            if err:
                # Missing files
                self.logger.warning('Missing files')
                self.w.status.text = "Click Config to set up Geo Finder"
                TKHelper.set_preferred_button(self.w.config_button, self.w.initialization_buttons, "Preferred.TButton")
                self.w.load_button.config(state="disabled")
            else:
                # No config errors
                # Read config settings (Ancestry file path)
                err = self.cfg.read()
                if err:
                    self.logger.warning('error reading {} config.pkl'.format(self.cache_dir))

                self.w.original_entry.text = self.cfg.get("gedcom_path")
                TKHelper.enable_buttons(self.w.initialization_buttons)
                if os.path.exists(self.cfg.get("gedcom_path")):
                    #  file is valid.  Prompt user to click Open for  file
                    self.w.status.text = f"Click Open to load {file_types} file"
                    TKHelper.set_preferred_button(self.w.load_button, self.w.initialization_buttons, "Preferred.TButton")
                else:
                    # No file.  prompt user to select a  file - GEDCOM file name isn't valid
                    self.w.status.text = f"Choose a {file_types} file"
                    self.w.load_button.config(state="disabled")
                    TKHelper.set_preferred_button(self.w.choose_button, self.w.initialization_buttons, "Preferred.TButton")
        else:
            # Missing directories
            self.logger.warning('Directories not found: {} '.format(self.cache_dir))
            self.w.status.text = "Click Config to set up Geo Finder"
            self.w.load_button.config(state="disabled")
            TKHelper.set_preferred_button(self.w.config_button, self.w.initialization_buttons, "Preferred.TButton")

        # Flag to indicate whether we are in startup or in Window loop.  Determines how window idle is called
        self.starting = False

        self.w.title.text = f'GEO FINDER v{__version__.__version__}'
        self.w.root.mainloop()  # ENTER MAIN LOOP and Wait for user to click on load button

    def load_data_files(self) -> bool:
        """
        Load in data files required for GeoFinder:
        Load global_replace dictionary, Geodata files and geonames
        #Returns:
            Error - True if error occurred
        """
        # Read in Skiplist, Replace list
        self.skiplist = CachedDictionary.CachedDictionary(self.cache_dir, "skiplist.pkl")
        self.skiplist.read()
        self.global_replace = CachedDictionary.CachedDictionary(self.cache_dir, "global_replace.pkl")
        self.global_replace.read()
        dict_copy = copy.copy(self.global_replace.dict)

        # Convert all global_replace items to lowercase
        for ky in dict_copy:
            val = self.global_replace.dict.pop(ky)
            new_key = Normalize.normalize(text=ky, remove_commas=False)
            self.global_replace.dict[new_key] = val

        # Read in dictionary listing Geoname features we should include
        self.feature_code_list_cd = CachedDictionary.CachedDictionary(self.cache_dir, "feature_list.pkl")
        self.feature_code_list_cd.read()
        feature_code_list_dct: Dict[str, str] = self.feature_code_list_cd.dict
        if len(feature_code_list_dct) < 3:
            self.logger.warning('Feature list is empty.')
            feature_code_list_dct.clear()
            feature_list = UtilFeatureFrame.default
            for feat in feature_list:
                feature_code_list_dct[feat] = ''
            self.feature_code_list_cd.write()

        # Read in dictionary listing countries (ISO2) we should include
        self.supported_countries_cd = CachedDictionary.CachedDictionary(self.cache_dir, "country_list.pkl")
        self.supported_countries_cd.read()
        supported_countries_dct: Dict[str, str] = self.supported_countries_cd.dict

        # Read in dictionary listing languages (ISO2) we should include
        self.languages_list_cd = CachedDictionary.CachedDictionary(self.cache_dir, "languages_list.pkl")
        self.languages_list_cd.read()
        languages_list_dct: Dict[str, str] = self.languages_list_cd.dict

        # Initialize geo data
        self.geodata = Geodata(directory_name=self.directory, progress_bar=self.w.prog,
                                       enable_spell_checker=self.enable_spell_checker,
                                       show_message=True, exit_on_error=True,
                                       languages_list_dct=languages_list_dct,
                                       feature_code_list_dct=feature_code_list_dct,
                                       supported_countries_dct=supported_countries_dct)

        # If the list of supported countries is unusually short, display note to user
        num = self.display_country_note()
        self.logger.info('{} countries will be loaded'.format(num))

        # open Geoname Gazeteer DB - city names, lat/long, etc.
        error = self.geodata.open()
        if error:
            TKHelper.fatal_error(MISSING_FILES)

        self.w.root.update()
        self.w.prog.update_progress(100, " ")
        return error

    def load_handler(self):
        """
        The User pressed the LOAD button to load an Ancestry file. Switch app display to the Review Widgets layout
        Load in file name and call handle_place_entry()
        """
        self.w.original_entry.text = ""
        self.w.remove_initialization_widgets()  # Remove old widgets
        self.w.create_review_widgets()  # Switch display from Initial widgets to main review widgets

        self.load_data_files()

        ged_path = self.cfg.get("gedcom_path")  # Get saved config setting for  file

        # Load appropriate handler based on file type (Gramps XML or GEDCOM)
        if ged_path is not None:
            if '.ged' in ged_path:
                # GEDCOM
                self.out_suffix = "import.ged"
                self.ancestry_file_handler = Gedcom.Gedcom(in_path=ged_path, out_suffix=temp_suffix, cache_d=self.cache_dir,
                                                           progress=None)  # Routines to open and parse GEDCOM file
            elif '.gramps' in ged_path:
                # GRAMPS
                self.out_suffix = "import.gramps"
                # self.out_suffix = "csv"
                self.ancestry_file_handler = GrampsXml.GrampsXml(in_path=ged_path, out_suffix=temp_suffix, cache_d=self.cache_dir,
                                                                 progress=None, geodata=self.geodata)  # Routines to open and parse Gramps file
        else:
            self.out_suffix = 'unk.new.ged'
            messagebox.showwarning(f'UNKNOWN File type. Not .gramps and not .ged. \n\n{ged_path}')

        self.out_diag_file = open(ged_path + '.output.txt', 'wt')
        self.in_diag_file = open(ged_path + '.input.txt', 'wt')
        miss_diag_fname = ged_path + '.miss.txt'
        self.geodata.open_diag_file(miss_diag_fname)

        if self.ancestry_file_handler.error:
            TKHelper.fatal_error(f"File {ged_path} not found.")

        self.w.root.update()

        self.place: Loc.Loc = Loc.Loc()  # Create an object to store info for the current Place

        # Add  filename to Title
        path_parts = os.path.split(ged_path)  # Extract filename from full path
        self.w.title.text = f'GEO FINDER v{__version__.__version__} - {path_parts[1]}'

        # Read  file, find each place entry and handle it.
        self.w.user_entry.text = "Scanning to previous position..."
        self.process_place_entries()

    def process_place_entries(self):
        """
        Handle PLACE entries in users file.  Replace it, skip it, or have user correct it.
        """
        self.w.original_entry.text = ""

        if self.w.prog.shutdown_requested:
            self.periodic_update("Shutting down...")
        else:
            self.periodic_update("Scanning")
        self.clear_result_list(self.place)

        while True:
            # Keep reading place entries until we need User review or reach End Of File
            self.update_counter += 1  # Counter is used to periodically update
            # Update statistics
            self.update_statistics()

            # Find the next PLACE entry in  file
            # Process it and keep looping until we need user review
            self.place.clear()
            town_entry, eof, rec_id = self.ancestry_file_handler.get_next_place()
            self.place.updated_entry = town_entry
            self.place.id = rec_id
            town_entry = Normalize.normalize(text=town_entry, remove_commas=False)

            if eof:
                self.end_of_file_shutdown()

            # See if we already have a fix (Global Replace) or Skip (ignore).
            # Otherwise see if we can find it or have user handle it
            replacement_geoid = self.get_replacement(self.global_replace, town_entry, self.place)

            if replacement_geoid is not None:
                # There is already a global change that we can apply to this entry.
                self.matched_count += 1

                if self.place.result_type == GeoUtil.Result.STRONG_MATCH:
                    # REPLACE - Output the updated place to ancestry file
                    self.write_updated_place(self.place, town_entry)

                    # Display status to user
                    if self.w.prog.shutdown_requested:
                        self.periodic_update("Creating Import...")
                    else:
                        self.periodic_update("Applying change")
                elif self.place.result_type == GeoUtil.Result.DELETE:
                    # DELETE - Don't write out this place
                    continue
                else:
                    # ERROR - We previously found an update, but the GEOID for replacement can no longer be found
                    self.logger.warning(f'***ERROR looking up GEOID=[{replacement_geoid}] for [{town_entry}] ')
                    self.place.event_year = int(self.ancestry_file_handler.event_year)  # Set place date to event date (geo names change over time)
                    self.w.original_entry.text = f'** DATABASE ERROR FOR GEOID=[{replacement_geoid}] for [{town_entry}]'
                    self.w.user_entry.text = f'{town_entry}'
                    self.geodata.find_matches(town_entry, self.place, self.w.prog.shutdown_requested)
                    break
                continue
            elif self.skiplist.get(town_entry) is not None:
                # SKIP - User marked place as SKIP - Write out as-is and go to next error
                self.skip_count += 1
                self.periodic_update("Skipping")
                self.ancestry_file_handler.write_asis(town_entry)
                continue
            else:
                # FOUND a PLACE entry that we don't already have a global replace or skip for
                # See if it is in the place database
                self.place.event_year = int(self.ancestry_file_handler.event_year)  # Set place date to event date (geo names change over time)
                self.geodata.find_matches(town_entry, self.place, self.w.prog.shutdown_requested)

                if self.place.result_type in GeoUtil.successful_match:
                    # STRONG MATCH
                    if self.place.result_type == GeoUtil.Result.STRONG_MATCH:
                        # FOUND STRONG MATCH - no user verification needed
                        self.matched_count += 1

                        # Write out line without user verification
                        if self.w.prog.shutdown_requested:
                            self.periodic_update("Creating Import...")
                        else:
                            self.periodic_update("Scanning")

                        # Add to global replace list - Use '@' for tokenizing.  Save GEOID_TOKEN and PREFIX_TOKEN
                        res = '@' + self.place.geoid + '@' + self.place.prefix

                        self.global_replace.set(Normalize.normalize(text=town_entry, remove_commas=False), res)
                        self.logger.debug(f'Found Strong Match for {town_entry} res= [{res}] Setting DICT')
                        # Periodically flush dictionary to disk.  (We flush on exit as well)
                        if self.update_counter % 200 == 1:
                            self.global_replace.write()

                        self.write_updated_place(self.place, town_entry)
                        continue
                    else:
                        # WEAK MATCH OR MULTIPLE MATCHES
                        if self.w.prog.shutdown_requested:
                            # User requested shutdown - so no user interaction.  Write this item out as-is
                            self.review_count += 1
                            self.periodic_update("Creating Import...")
                            self.w.original_entry.text = " "
                            self.ancestry_file_handler.write_asis(town_entry)
                            continue
                        else:
                            # USER REVIEW - Have user review the match
                            self.logger.debug(f'user review for {town_entry} res= [{self.place.result_type}] ')

                            self.w.status.configure(style="Good.TLabel")
                            self.w.original_entry.text = self.place.original_entry  # Display place
                            self.w.user_entry.text = self.place.updated_entry  # Display place
                            # Break out of loop and have user review the match
                            break
                else:
                    # NO MATCH FOUND
                    if self.w.prog.shutdown_requested:
                        # User requested shutdown.  Write this item out as-is
                        self.review_count += 1
                        self.periodic_update("Creating Import...")
                        self.w.original_entry.text = " "
                        self.ancestry_file_handler.write_asis(town_entry)
                        continue
                    else:
                        # USER REVIEW - Have user review entry
                        # self.logger.debug(f'User2 review for {town_entry}. status ={self.place.status}')
                        self.w.status.configure(style="Good.TLabel")
                        self.w.original_entry.text = self.place.original_entry  # Display place
                        self.w.user_entry.text = self.place.original_entry  # Display place
                        # Break out of loop and have user review the item
                        break

        # Have user review the result
        self.display_result(self.place)

    def get_list_selection(self):
        """
        Get the item the user selected in list (tree)
        #Returns:
            Prefix, name, DBID
        """
        item = self.w.tree.selection()
        name = (self.w.tree.item(item, "text"))
        values = self.w.tree.item(item)['values']
        if values:
            prefix = (values[0])
            dbid = (values[1])
        else:
            prefix = ''
            dbid = ''
        return prefix, name, dbid

    def get_user_selection(self):
        flags =   ResultFlags(limited=False, filtered=False)

        # User selected item from listbox - get listbox selection
        pref, town_entry, dbid = self.get_list_selection()
        self.place.target = str(dbid)
        # self.logger.debug(f'selected pref=[{pref}] [{town_entry}] id={dbid} id={self.place.geoid}')

        # Update the user edit widget with the List selection item
        self.w.user_entry.text = town_entry

        # Since we are verifying users choice, Get exact match by geoid
        self.geodata.find_geoid(self.place.geoid, self.place)
        self.place.prefix = pref
        # self.logger.debug(f'id={self.place.geoid} res={self.place.result_type} {self.place.georow_list}')

    def doubleclick_handler(self, _):
        """ User double clicked on result in list.  Save the result to ancestry file. """
        self.get_user_selection()
        self.display_result(self.place)
        self.save_handler()

    def verify_handler(self):
        """
        The User clicked Verify button.  Verify if the users new Place entry has a match in geonames data.
        """
        # Do we verify item from the listbox or from the text edit field?
        if self.user_selected_list:
            # User selected an item in the result list
            self.get_user_selection()
        else:
            # User typed in text entry window - get edit field value and look it up
            town_entry: str = self.w.user_entry.text
            if len(town_entry) > 0:
                self.geodata.find_matches(town_entry, self.place, self.w.prog.shutdown_requested)
            else:
                # User entry is blank - prompt to delete this entry
                self.place.clear()
                self.place.result_type = GeoUtil.Result.DELETE
                self.logger.debug('Blank: DELETE')
                self.geodata.process_resultxxx(self.place, ResultFlags(limited=False, filtered=False))

        self.display_result(self.place)

    def display_result(self, place: Loc.Loc):
        """ Display result details for a town entry  """
        # Enable buttons so user can either click Skip, or edit the item and Click Verify.
        place.set_types_as_string()
        place.status = f'{place.result_type_text}  {self.result_text_list.get(place.result_type)} '

        TKHelper.enable_buttons(self.w.review_buttons)

        # Enable action buttons based on type of result
        if place.result_type == GeoUtil.Result.MULTIPLE_MATCHES or \
                place.result_type == GeoUtil.Result.NO_MATCH or \
                place.result_type == GeoUtil.Result.NO_COUNTRY:
            # Result requires user action
            # Disable the Save & Map button until an item is found.  Set Verify as preferred button
            self.set_save_button_allowed(False)
            TKHelper.set_preferred_button(self.w.verify_button, self.w.review_buttons, "Preferred.TButton")
        elif place.result_type == GeoUtil.Result.NOT_SUPPORTED:
            # Country Not supported - set Skip as preferred button
            TKHelper.set_preferred_button(self.w.skip_button, self.w.review_buttons, "Preferred.TButton")
        else:
            # Found a match  - enable save.  Set Save as preferred button
            self.set_save_button_allowed(True)  # Enable save button
            TKHelper.set_preferred_button(self.w.save_button, self.w.review_buttons, "Preferred.TButton")

        # Display status and color based on success
        self.set_status_text(place.get_status())
        if place.result_type in GeoUtil.successful_match:
            if place.place_type == Loc.PlaceType.CITY:
                self.w.status.configure(style="Good.TLabel")
            else:
                self.w.status.configure(style="GoodCounty.TLabel")
        else:
            self.w.status.configure(style="Error.TLabel")

        # If more than one result, set Verify as preferred button
        # TODO - clean this up so we don't have  multiple mechanisms to set status
        if len(place.georow_list) > 1:
            TKHelper.set_preferred_button(self.w.verify_button, self.w.review_buttons, "Preferred.TButton")
            self.set_save_button_allowed(False)

        if len(place.georow_list) > 0:
            # Display matches in listbox
            self.w.tree.focus()  # Set focus to listbox
            self.display_georow_list(place)
        else:
            # No matches
            self.w.user_entry.focus()  # Set focus to text edit widget
            self.display_one_georow(place.status_detail, place.geoid, score=9999, feat='')

        # Display GEDCOM person and event that this location refers to
        self.w.ged_event_info.text = f'{self.ancestry_file_handler.get_name(self.ancestry_file_handler.id)}: ' \
            f'{self.ancestry_file_handler.event_name} {self.ancestry_file_handler.date}'
        self.w.root.update_idletasks()

    def display_georow_list(self, place: Loc.Loc):
        """ Display list of matches in listbox (tree) """

        # Clear listbox
        self.w.tree.clear_display_list()

        temp_place = copy.copy(place)

        # Get geodata for each item and add to listbox output
        for geo_row in place.georow_list:
            self.geodata.geo_files.geodb.copy_georow_to_place(geo_row, temp_place)
            temp_place.set_place_type()

            self.geodata.geo_files.geodb.set_display_names(temp_place)
            nm = temp_place.get_long_name(self.geodata.geo_files.output_replace_dct)
            valid = self.geodata._valid_year_for_location(event_year=place.event_year, country_iso=temp_place.country_iso,
                                                          admin1=temp_place.admin1_id, pad_years=0)
            if valid:
                # Get prefix
                self.w.tree.list_insert(nm, GeoUtil.capwords(geo_row[GeoUtil.Entry.PREFIX]), geo_row[GeoUtil.Entry.ID],
                                        f'{int(geo_row[GeoUtil.Entry.SCORE]):d}',
                                        geo_row[GeoUtil.Entry.FEAT])
            else:
                self.w.tree.list_insert(nm, "VERIFY DATE", geo_row[GeoUtil.Entry.ID], f'{int(geo_row[GeoUtil.Entry.SCORE]):d}',
                                        geo_row[GeoUtil.Entry.FEAT])

        self.w.root.update_idletasks()

    def skip_handler(self):
        """ User clicked SKIP.  Write out original entry as-is and skip any matches in future  """
        self.skip_count += 1

        # self.logger.debug(f'Skip for {self.w.original_entry.get_text()}  Updating SKIP dict')

        self.skiplist.set(self.w.original_entry.text, " ")
        self.ancestry_file_handler.write_asis(self.w.original_entry.text)

        # Save Skip info for future runs
        self.skiplist.write()

        # Go to next entry
        self.process_place_entries()

    def save_handler(self):
        """ Save the Place.  Add Place to global replace list and replace if we see it again. """
        self.matched_count += 1
        # self.geodata.set_last_iso(self.place.country_iso)

        ky = self.w.original_entry.text
        if self.place.result_type == GeoUtil.Result.DELETE:
            # Put in a blank as replacement
            self.place.geoid = ''
            self.place.prefix = ''

        res = '@' + self.place.geoid + '@' + self.place.prefix
        # self.logger.debug(f'Save [{ky}] :: [{res}]')
        self.global_replace.set(Normalize.normalize(text=ky, remove_commas=False), res)

        # Periodically flush dict to disk
        if self.update_counter % 10 == 1:
            self.global_replace.write()
        # self.logger.debug(f'SAVE SetGblRep for [{ky}] res=[{res}] Updating DICT')

        # Write out corrected item to  output file
        if self.place.result_type != GeoUtil.Result.DELETE:
            self.write_updated_place(self.place, ky)

        # Get next error
        self.w.user_entry.text = ''
        self.process_place_entries()

    def help_handler(self):
        """ Launch browser showing help text from Github GeoFinder project wiki """
        help_base = "https://github.com/corb555/GeoFinder/wiki/User-Guide"
        webbrowser.open(help_base)

    def search_handler(self):
        """ Launch browser with a Google search for this item """
        base = "https://www.google.com/search?q="
        loc = self.w.user_entry.text
        webbrowser.open(f"{base}{loc}")

    def map_handler(self):
        """ Launch browser with a map for this item """
        base = "http://www.openstreetmap.org"
        if self.place.place_type == Loc.PlaceType.COUNTRY or self.place.place_type == Loc.PlaceType.ADMIN1:
            # Zoom wide if user just put in state, country
            zoom = "zoom=7"
        else:
            zoom = "zoom=14"
        loc = f"{base}/?mlat={self.place.lat}&mlon={self.place.lon}&{zoom}#map={self.place.lat}/{self.place.lon}"
        webbrowser.open(loc)

    def quit_handler(self):
        """ User clicked Quit.  Set flag for shutdown.  Process all global replaces and exit """
        self.skip_count += 1

        path = self.cfg.get("gedcom_path")
        if self.w.prog.shutdown_requested:
            # Already in shutdown and user quit again - do immediate shutdown
            self.logger.info('Shutdown')
            self.shutdown()

        self.w.prog.shutdown_requested = True

        if messagebox.askyesno('Generate Import File?', f'All updates saved.\n\nDo you want to generate a file for import'
        f' to Gedcom/Gramps?\n\n', default='no'):
            # Write file for importing back
            messagebox.showinfo("Generate Import File", "Reminder -  make sure the ancestry export file you are working on is up to date before "
                                                        "generating a file to import back!\n\nThe file will take about 10 minutes per 1000 places")

            TKHelper.disable_buttons(button_list=self.w.review_buttons)
            self.w.quit_button.config(state="disabled")
            self.w.prog.full_update = True
            self.w.statistics_text.configure(style="Good.TLabel")

            self.w.user_entry.text = "Creating Import File..."
            self.start_time = time.time()
            # Write out the item we are on
            self.ancestry_file_handler.write_asis(self.w.original_entry.text)

            # We will still continue to go through file, but only handle global replaces
            self.process_place_entries()
        else:
            # Immediate exit
            self.logger.info('Shutdown')
            self.shutdown()

    def config_handler(self):
        # User clicked on Config button - bring up configuration windows
        self.w.remove_initialization_widgets()  # Remove old widgets
        self.w.root.protocol("WM_DELETE_WINDOW", self.shutdown)  # Set up handler for exit button
        # Read config settings (Ancestry file path) - this will create config.pkl if not found
        err = self.cfg.read()
        if err:
            self.logger.warning('error reading {} config.pkl'.format(self.cache_dir))
        self.util.create_util_widgets()  # Create Util/Config widgets

    def filename_handler(self):
        """ Display file open selector dialog """
        fname = filedialog.askopenfilename(initialdir=self.directory,
                                           title=f"Select {file_types} file",
                                           filetypes=[("GEDCOM files", "*.ged"), ("Gramps files", "*.gramps"), ("all files", "*.*")])
        if len(fname) > 1:
            self.cfg.set("gedcom_path", fname)  # Add filename to dict
            self.cfg.write()  # Write out config file
            self.w.status.text = f"Click Open to load {file_types} file"
            self.w.original_entry.text = self.cfg.get("gedcom_path")
            TKHelper.set_preferred_button(self.w.load_button, self.w.initialization_buttons, "Preferred.TButton")

    def event_handler_for_return_key(self, _):
        """ User pressed Return key.  Call Verify data entry """
        self.verify_handler()
        return "break"

    def entry_focus_event_handler(self, _):
        # Track focus so when user presses Verify, we know whether to get text from Entry Box or List box
        # User clicked on data entry widget
        # Note - second param _ is to prevent warning for Event param which isn't used
        self.user_selected_list = False

    def list_focus_event_handler(self, _):
        # Track focus so when user presses Verify, we know whether to get text from Entry Box or List box
        # user clicked on listbox
        self.user_selected_list = True

    def ctl_s_event_handler(self, _):
        """ User pressed Ctrl-S Save accelerator key.  Call Save  """
        if self.save_enabled:
            self.save_handler()
        return "break"

    def clear_result_list(self, place):
        """Clear result list"""
        self.w.tree.clear_display_list()
        place.georow_list.clear()

    def display_one_georow(self, txt, geoid, score, feat):
        """ Display a single result row"""
        self.w.tree.clear_display_list()
        self.w.tree.list_insert(txt, '', geoid, score=score, feature=feat)

    def display_country_note(self) -> int:
        """
        Display warning if only a small number of countries are enabled
        #Returns:
            Number of supported countries
        """
        country_list, supported_countries = self.geodata.geo_files.get_supported_countries()
        self.w.root.update()
        if supported_countries == 0:
            TKHelper.fatal_error("No countries enabled.\n\nUse Config Country Tab to change country list\n")
        return supported_countries

    def write_updated_place(self, place: Loc.Loc, original_entry):
        """
        Write out this updated location and lat/lon to ancestry file output
        If place result_type was DELETE, do not write out location
        Write to diagnostic file as well if enabled
        #Args:
            place: Updated location
            original_entry: Original file entry
        """
        self.geodata.geo_files.geodb.set_display_names(place)
        place.original_entry = place.get_long_name(self.geodata.geo_files.output_replace_dct)
        prefix = GeoUtil.capwords(self.place.prefix)
        if self.diagnostics:
            self.in_diag_file.write(f'{GeoUtil.capwords(original_entry)}\n')

        if place.result_type != GeoUtil.Result.DELETE:
            # self.logger.debug(f'Write Updated - name={place.name} pref=[{place.prefix}]')

            self.ancestry_file_handler.write_updated(prefix + place.prefix_commas + place.original_entry, place)
            self.ancestry_file_handler.write_lat_lon(lat=place.lat, lon=place.lon)
            text = prefix + place.prefix_commas + place.original_entry + '\n'
            # text = str(text.encode('utf-8', errors='replace'))
            if self.diagnostics:
                self.out_diag_file.write(text)
        else:
            # self.logger.debug('zero len, no output')
            if self.diagnostics:
                self.out_diag_file.write('DELETE\n')

    def set_save_button_allowed(self, save_allowed: bool):
        """
        Mark Save Button and Map button as allowed if save_allowed is True
        #Args:
            save_allowed: Bool to indicate whether Save button should be enabled
        """
        if save_allowed:
            # Enable the Save and Map buttons
            self.save_enabled = True
            self.w.save_button.config(state="normal")  # Match - enable  button
            self.w.map_button.config(state="normal")   # Match - enable  button
        else:
            # Disable the Save and Map buttons
            self.save_enabled = False
            self.w.save_button.config(state="disabled")
            self.w.map_button.config(state="disabled")

    def set_status_text(self, txt):
        """ Update status text """
        self.w.status.state(["!readonly"])
        self.w.status.text = txt
        self.w.status.state(["readonly"])

    def end_of_file_shutdown(self):
        """
        Reached End of file - close ancestry file handler, display Completion message to user and
        call shutdown()
        """
        TKHelper.disable_buttons(button_list=self.w.review_buttons)
        # self.start_time = time.time()
        # self.logger.debug(f'COMPLETED time={int((time.time() - self.start_time) / 60)} minutes')
        self.w.status.text = "Done.  Shutting Down..."
        self.w.original_entry.text = " "
        path = self.cfg.get("gedcom_path")
        self.ancestry_file_handler.close()

        self.update_statistics()
        self.w.root.update_idletasks()  # Let GUI update

        if 'ramp' in self.out_suffix:
            # Gramps file is .csv
            messagebox.showinfo("Info", f"Finished.  Created file for Import to Ancestry software:\n\n {path}.csv")
            self.logger.info(f'DONE.  Created output file {path}.csv')
        else:
            messagebox.showinfo("Info", f"Finished.  Created file for Import to Ancestry software:\n\n {path}.{self.out_suffix}")
            self.logger.info(f'DONE.  Created output file {path}{self.out_suffix}')
        self.logger.info('End of  file')
        self.shutdown()

    def shutdown(self):
        """
         Shutdown - write out all data and exit.
         Write out Gbl Replace, skip list, config, ancestry file, out_diag, in_diag
         Close DB
        :return: Does not return
        """
        # self.w.root.update_idletasks()
        if self.geodata:
            self.logger.info(self.get_stats_text)
            self.geodata.geo_files.geodb.close()
            self.geodata.close_diag_file()
        if self.skiplist:
            self.skiplist.write()
        if self.global_replace:
            self.global_replace.write()
        if self.cfg:
            self.cfg.write()
        if self.ancestry_file_handler:
            self.ancestry_file_handler.close()
        if self.out_diag_file:
            self.out_diag_file.close()
        if self.in_diag_file:
            self.in_diag_file.close()

        self.w.root.quit()
        self.logger.info('EXIT')
        # sys.exit()
        os._exit(0)

    def periodic_update(self, msg):
        """
        Periodically display status text to user (display on every N updates)
        Note: does not display when we are in shutdown mode
        #Args:
            msg: message to periodically display
        """
        if self.update_counter % 50 == 0:
            if not self.w.prog.shutdown_requested:
                self.w.status.text = msg
                self.w.status.configure(style="Good.TLabel")
                self.w.original_entry.text = self.place.original_entry  # Display place
            self.w.root.update_idletasks()  # Let GUI update

    def check_configuration(self) -> bool:
        """
        Check if GeoFinder configuration is valid:  valid country list, valid GEODB or geoname files
        #Returns:
            Error - True if error
        """
        file_error = False
        file_list = ['allCountries.txt', 'cities500.txt']

        # Get country list and validate
        countries = CachedDictionary.CachedDictionary(self.cache_dir, 'country_list.pkl')
        self.logger.debug('load country selections list')

        err = countries.read()
        if err:
            file_error = True
            return file_error

        country_dct = countries.dict
        if len(country_dct) == 0:
            self.logger.warning('no countries specified')
            file_error = True

        # Ensure that there is geo DB or there are some geoname data files
        path = os.path.join(self.directory, self.cache_dir, "geodata.db")
        if os.path.exists(path):
            self.logger.info(f'Found {path}')
            file_error = False
            return file_error

        path = os.path.join(self.directory, "*.txt")
        self.logger.info(f'Geoname path {path}')
        count = 0

        country_file_len = 6
        for filepath in glob.glob(path):
            # Ignore the two Admin files
            fname = os.path.basename(filepath)
            if len(fname) == country_file_len or fname in file_list:
                count += 1

        self.logger.debug(f'geoname file count={count}')
        if count == 0:
            # No data files, add error to error dictionary
            self.logger.warning('No Geonames files found')
            file_error = True

        return file_error

    @property
    def done_count(self):
        return self.matched_count + self.skip_count + self.review_count

    @property
    def get_stats_text(self) -> str:
        if self.ancestry_file_handler is not None:
            remaining = self.ancestry_file_handler.place_total - self.done_count
            return f'Matched={self.matched_count}   Skipped={self.skip_count}  Needed Review={self.review_count} ' \
                f'Remaining={remaining} Total={self.ancestry_file_handler.place_total}'
        else:
            return ''

    def update_statistics(self):
        """
        Display completion statistics to user:
        Matched, skipped, needed review, remaining
        """
        if self.ancestry_file_handler.place_total is not None:
            remaining = self.ancestry_file_handler.place_total - self.done_count
        else:
            remaining = 0
        self.w.statistics_text.text = self.get_stats_text

        if self.ancestry_file_handler.place_total > 0:
            self.w.prog.update_progress(100 * self.done_count / self.ancestry_file_handler.place_total, " ")
        else:
            self.w.prog.update_progress(0, " ")

        return self.done_count

    def get_replacement(self, dct, town_entry: str, place: Loc.Loc):
        """
        Check global_replace dictionary to see if we've already found a match for this location.
        Update place structure with prefix and found location
        #Args:
            dct: global replacement dictionary
            town_entry: entry to lookup
            place: Loc structure
        #Returns:
            Return geoid of location if found, else None
            place will be filled out with replacement location
        """
        geoid = None
        replacement = dct.get(town_entry)

        if replacement is not None:
            if len(replacement) > 0:
                # parse replacement entry
                rep_tokens = replacement.split('@')
                geoid = rep_tokens[GEOID_TOKEN]
                if len(geoid) > 0:
                    self.geodata.find_geoid(geoid, place)
                    place.set_place_type()
                else:
                    place.result_type = GeoUtil.Result.DELETE

                # Get prefix if there was one
                if len(rep_tokens) > 2:
                    place.prefix = rep_tokens[PREFIX_TOKEN]
                    place.prefix_commas = ','
                    # place.name = place.prefix + ',' + place.name
                # self.logger.debug(f'Found Replace.  Pref=[{place.prefix}] place={place.name} Res={place.result_type}')

        return geoid

    def get_command_line_arguments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--logging", help="info - Enable quiet logging")
        parser.add_argument("--diagnostics", help="on - Create xx.input.txt and xx.output.txt diagnostics files")
        parser.add_argument("--spellcheck", help="on - Enable spellchecker")

        # read arguments from the command line
        args = parser.parse_args()

        # check for --verbose switch
        if args.logging == 'info':
            self.logger =  GeoUtil.set_info_logging('geofinder Init')
        else:
            self.logger = GeoUtil.set_debug_logging('geofinder Init')

        # check for --diagnostics switch
        if args.diagnostics == 'on':
            self.logger.info(f"--diagnostics files enabled {args.diagnostics}")
            self.diagnostics = True
        else:
            self.diagnostics = False

        # check for --spellcheck switch
        if args.spellcheck == 'on':
            self.logger.info(f"--spellchecking enabled {args.spellcheck}")
            self.enable_spell_checker = True
        else:
            self.enable_spell_checker = False

    result_text_list = {
        GeoUtil.Result.STRONG_MATCH: 'Matched! Click Save to accept:',
        GeoUtil.Result.MULTIPLE_MATCHES: ' Multiple matches.  Select one and click Verify or Double-Click',
        GeoUtil.Result.NO_MATCH: 'Not found.  Edit and click Verify.',
        GeoUtil.Result.NOT_SUPPORTED: ' Country is not supported. Skip or Add Country in Config',
        GeoUtil.Result.NO_COUNTRY: 'No Country found.',
        GeoUtil.Result.PARTIAL_MATCH: 'Partial match.  Click Save to accept:',
        GeoUtil.Result.DELETE: 'Empty.  Click Save to delete entry.',
        GeoUtil.Result.WORD_MATCH: 'Word match. Click Save to accept:',
        GeoUtil.Result.WILDCARD_MATCH: 'Wildcard match. Click Save to accept:',
        GeoUtil.Result.SOUNDEX_MATCH: 'Soundex match. Click Save to accept:',
    }

def lowercase_match_group(matchobj):
    return matchobj.group().lower()

def capwords(text):
    """
    Change text from lowercase to Title Case (but fix the title() apostrophe bug)
    #Args:
        text:
    #Returns:
        Text with Title Case
    """
    if text is not None:
        # Use title(), then fix the title() apostrophe defect where letter after apostrophe is made caps
        text = text.title()

        # Fix handling for contractions not handled correctly by title()
        poss_regex = r"(?<=[a-z])[\']([A-Z])"
        text = re.sub(poss_regex, lowercase_match_group, text)

    return text

def entry():
    GeoFinder()


if __name__ == "__main__":
    entry()
