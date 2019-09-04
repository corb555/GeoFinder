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
import copy
import glob
import logging
import os
import sys
import webbrowser
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox

from geofinder import Geodata, GeoKeys, Config, Gedcom, Loc, AppLayout, UtilLayout
from geofinder.CachedDictionary import CachedDictionary
from geofinder.Geodata import ResultFlags
from geofinder.TKHelper import TKHelper
from geofinder import __version__

MISSING_FILES = 'Missing Files.  Please run geoutil and correct errors in Errors Tab'

GEOID_TOKEN = 1
PREFIX_TOKEN = 2


class GeoFinder:
    """
    Read in a GEDCOM genealogy file and verify that the spelling of each place is correct.
    If place is found, add the latitude and longitude to the output GEDCOM file.
    If place can't be found, allow the user to correct it.  If it is corrected, apply the change to
    all matching entries.
    Also allow the user to mark an item to skip if a resolution cant be found.
    Skiplist is a list of locations the user has flagged to skip.  These items will be ignored
    Global replace list is list of fixes the user has found.  Apply these to any new similar matches.
    Accepted list is a list of matches that the user has accepted.
        
    Uses gazetteer files from geoname.org as the reference source.  Uses English modern place names,
    plus some county aliases.

    Main classes:

    GeoFinder - The main GUI
    GeoData - The geonames data model routines
    GeoDB -  Database insert/lookup routines
    GEDCOM - routines to read and write GEDCOM files
    GeodataFile - routines to read/write geoname data sources
    AppLayout - routines to create the app windows and widgets
    Loc - holds all info for a single location

    """

    def __init__(self):
        print ('Python {}.{}'.format(sys.version_info[0], sys.version_info[1]))
        if sys.version_info < (3, 6, 0):
            raise Exception("Must be using Python 3.6 or higher.")

        print(f'GeoFinder v{__version__.__version__}')
        self.shutdown_requested: bool = False  # Flag to indicate user requested shutdown
        self.save_enabled = False  # Only allow SAVE when we have an item that was matched in geonames
        self.user_selected_list = False  # Indicates whether user selected a list entry or text edit entry
        self.err_count = 0
        self.odd = False
        self.ancestry_file = None
        self.place = None
        self.skiplist = None
        self.global_replace = None
        self.user_accepted = None
        self.geodata = None

        self.logger = self.setup_logging('geofinder Init')

        # Save our base directory and cache directory
        self.directory: str = os.path.join(str(Path.home()), GeoKeys.get_directory_name())
        self.cache_dir = GeoKeys.get_cache_directory(self.directory)

        # Create App window and configure  window buttons and widgets
        self.w: AppLayout.AppLayout = AppLayout.AppLayout(self)
        self.util = UtilLayout.UtilLayout(root=self.w.root, directory=self.directory, cache_dir=self.cache_dir)
        self.w.create_initialization_widgets()
        self.w.config_button.config(state="normal")

        # Set up configuration  class
        self.cfg = Config.Config()

        # Ensure GeoFinder directory structure is valid
        if self.cfg.valid_directories():
            # Directories are valid.  See if  required Geonames files are present
            err = self.check_configuration()
            if err:
                # Missing files
                self.logger.warning(f'Missing files')
                self.w.status.set_text("Click Config to set up Geo Finder")
                TKHelper.set_preferred_button(self.w.config_button, self.w.initialization_buttons, "Preferred.TButton")
                self.w.load_button.config(state="disabled")
            else:
                # No config errors
                # Read config settings (GEDCOM file path)
                err = self.cfg.read()
                if err:
                    self.logger.warning(f'error reading {self.cache_dir} config.pkl')

                self.w.original_entry.set_text(self.cfg.get("gedcom_path"))
                TKHelper.enable_buttons(self.w.initialization_buttons)
                if os.path.exists(self.cfg.get("gedcom_path")):
                    # GEDCOM file is valid.  Prompt user to click Open for GEDCOM file
                    self.w.status.set_text("Click Open to load GEDCOM file")
                    TKHelper.set_preferred_button(self.w.load_button, self.w.initialization_buttons, "Preferred.TButton")
                else:
                    # No file.  prompt user to select a GEDCOM file - GEDCOM file name isn't valid
                    self.w.status.set_text("Choose a GEDCOM file")
                    self.w.load_button.config(state="disabled")
                    TKHelper.set_preferred_button(self.w.choose_button, self.w.initialization_buttons, "Preferred.TButton")
        else:
            # Missing directories
            self.logger.warning(f'Directories not found: {self.cache_dir} ')
            self.w.status.set_text("Click Config to set up Geo Finder")
            self.w.load_button.config(state="disabled")
            TKHelper.set_preferred_button(self.w.config_button, self.w.initialization_buttons, "Preferred.TButton")

            # Create directories for GeoFinder
            self.cfg.create_directories()

        # Flag to indicate whether we are in startup or in Window loop.  Determines how window idle is called
        self.startup = False
        self.w.root.mainloop()  # ENTER MAIN LOOP and Wait for user to click on load button

    def load_data(self):
        # Read in Skiplist, Replace list and  Already Accepted list
        self.skiplist = CachedDictionary(self.cache_dir, "skiplist.pkl")
        self.skiplist.read()
        self.global_replace = CachedDictionary(self.cache_dir, "global_replace.pkl")
        self.global_replace.read()
        self.user_accepted = CachedDictionary(self.cache_dir, "accepted.pkl")  # List of items that have been accepted
        self.user_accepted.read()

        # Initialize geodata
        self.geodata = Geodata.Geodata(directory_name=self.directory, progress_bar=self.w.prog)
        error = self.geodata.read()
        if error:
            TKHelper.fatal_error(MISSING_FILES)

        # If the list of supported countries is unusually short, display note to user
        num = self.display_country_note()
        self.logger.info(f'{num} countries will be loaded')

        # Read in Geoname Gazeteer file - city names, lat/long, etc.
        error = self.geodata.read_geonames()
        if error:
            TKHelper.fatal_error(MISSING_FILES)
        self.logger.debug(f'Geoname dictionary has {self.geodata.geo_files.geodb.get_row_count()} entries')
        self.w.root.update()
        self.w.prog.update_progress(100, " ")

    def load_handler(self):
        """
        User pressed LOAD button to load a GEDCOM file. Switch app display to the Review Widgets
        Load in file name and
        loop through GEDCOM file and find every PLACE entry and verify the entry against the geoname data
        """
        self.w.original_entry.set_text("")
        self.w.remove_initialization_widgets()  # Remove old widgets
        self.w.create_review_widgets()  # Switch display from Initial widgets to main review widgets

        self.load_data()

        ged_path = self.cfg.get("gedcom_path")  # Get saved config setting for GEDCOM file
        if ged_path is not None:
            out_suffix =  "new.ged"
        else:
            out_suffix = 'unk.new.ged'

        # Initialize routines to read/write GEDCOM file
        if self.ancestry_file is None:
            self.ancestry_file = Gedcom.Gedcom(in_path=ged_path, out_suffix=out_suffix, cache_dir=self.cache_dir,
                                               progress=self.w.prog)  # Routines to open and parse GEDCOM file
        if self.ancestry_file.error:
            TKHelper.fatal_error(f"GEDCOM file {ged_path} not found.")

        self.w.root.update()

        self.place: Loc.Loc = Loc.Loc()  # Create an object to store info for the current Place

        # Add GEDCOM filename to Title
        path_parts = os.path.split(ged_path)  # Extract filename from full path
        self.w.title.set_text(f'GEO FINDER - {path_parts[1]}')

        # Read GEDCOM file, find each place entry and handle it.
        self.handle_place_entry()

    def get_replacement(self, dict, town_entry:str, place):
        geoid = None
        replacement = dict.get(town_entry)

        if replacement is not None:
            if len(replacement) > 0:
                # parse replacement entry
                rep_tokens = replacement.split('@')
                geoid = rep_tokens[GEOID_TOKEN]
                if len(geoid) > 0:
                    self.geodata.find_geoid(geoid, place)
                else:
                    place.result_type = GeoKeys.Result.DELETE

                # Get prefix if there was one
                if len(rep_tokens) > 2:
                    place.prefix = rep_tokens[PREFIX_TOKEN]

        return geoid

    def handle_place_entry(self):
        """ Get next PLACE  in users GEDCOM File.  Replace it, skip it, or have user correct it. """
        self.w.original_entry.set_text("")
        if self.shutdown_requested:
            self.periodic_update("Shutting down...")
        else:
            self.periodic_update("Scanning")
        self.clear_detail_text(self.place)

        while True:
            self.err_count += 1  # Counter is used to periodically update
            # Find the next PLACE entry in GEDCOM file
            # Process it and keep looping until we need user input
            self.place.clear()
            town_entry, eof = self.ancestry_file.get_next_place()

            if eof:
                self.end_of_file_shutdown()

            # When we find an error, see if we already have a fix (Global Replace) or Skip (ignore).
            # Otherwise have user handle it
            geoid = self.get_replacement(self.global_replace, town_entry, self.place)

            if geoid is not None:
                # There is a global change that we can apply to this line.

                if self.place.result_type == GeoKeys.Result.EXACT_MATCH:
                    # Output place to GEDCOM file
                    self.file_output_place(self.place)

                    # Display status to user
                    if self.shutdown_requested:
                        self.periodic_update("Shutting down...")
                    else:
                        self.periodic_update("Applying change")
                elif self.place.result_type == GeoKeys.Result.DELETE:
                    continue
                else:
                    self.logger.debug(f'Error looking up GEOID=[{geoid}] for [{town_entry}] ')
                    self.place.event_year = int(self.ancestry_file.event_year)  # Set place date to event date (geo names change over time)
                    self.geodata.find_location(town_entry, self.place)
                    break

                continue
            elif self.get_replacement(self.user_accepted, town_entry, self.place) is not None:
                # There is an accepted  change that we can use for this line.  Get the replacement text
                if self.place.result_type == GeoKeys.Result.EXACT_MATCH:
                    # Output place to GEDCOM file
                    self.file_output_place(self.place)

                    # Display status to user
                    if self.shutdown_requested:
                        self.periodic_update("Shutting down...")
                    else:
                        self.periodic_update("Applying change")
                else:
                    self.logger.debug(f'Error looking up GEOID {town_entry}')
                    self.place.event_year = int(self.ancestry_file.event_year)  # Set place date to event date (geo names change over time)
                    self.geodata.find_location(town_entry, self.place)
                    self.w.original_entry.set_text(self.place.name)  # Display place
                    self.w.user_entry.set_text(self.place.name)  # Display place
                    break

                continue
            elif self.shutdown_requested:
                # User requested shutdown.  Finish up going thru file, then shut down
                self.periodic_update("Shutting Down...")
                self.w.original_entry.set_text(" ")
                self.ancestry_file.write(town_entry)
                continue
            elif self.skiplist.get(town_entry) is not None:
                # item is in skiplist - Write out as-is and go to next error
                # self.logger.debug(f'Found Skip for {town_entry}')
                self.periodic_update("Skipping")
                self.ancestry_file.write(town_entry)
                continue
            else:
                # Found a new PLACE entry
                # See if it is in our place database
                # self.place.parse_place(place_name=town_entry, geo_files=self.geodata.geo_files)
                self.place.event_year = int(self.ancestry_file.event_year)  # Set place date to event date (geo names change over time)
                self.geodata.find_location(town_entry, self.place)

                if self.place.result_type in GeoKeys.successful_match:
                    # Found a match
                    if self.place.result_type == GeoKeys.Result.EXACT_MATCH:
                        # Exact match
                        # Write out line without user verification
                        if self.shutdown_requested:
                            self.periodic_update("Shutting down...")
                        else:
                            self.periodic_update("Scanning")

                        # Add to global replace list - Use '@' for tokenizing.  Save GEOID_TOKEN and PREFIX_TOKEN
                        res = '@' + self.place.geoid + '@' + self.place.prefix

                        self.global_replace.set(town_entry, res)
                        self.logger.debug(f'Found Exact Match for {town_entry} res= [{res}] Setting DICT')
                        # Periodically flush dictionary to disk.  (We flush on exit as well)
                        if self.err_count % 4 == 1:
                            self.global_replace.write()

                        self.file_output_place(self.place)
                        continue
                    else:
                        # Have user review the match
                        self.w.status.configure(style="Good.TLabel")
                        self.w.original_entry.set_text(self.place.name)  # Display place
                        self.w.user_entry.set_text(self.place.name)  # Display place
                        break
                else:
                    self.logger.debug(f'User2 review for {town_entry}')

                    self.w.status.configure(style="Good.TLabel")
                    self.w.original_entry.set_text(self.place.name)  # Display place
                    self.w.user_entry.set_text(self.place.name)  # Display place
                    # Have user review the match
                    break

        # Have user review the result
        self.display_result(self.place)

    def get_list_selection(self):
        # Get the item the user selected in list (tree)
        loc = (self.w.tree.item(self.w.tree.selection(), "text"))
        prefix = (self.w.tree.item(self.w.tree.selection())['values'][0])
        return prefix, loc

    def verify_handler(self):
        """ The User clicked verify.  Verify if the users new Place entry has a match in geonames data.  """
        # Do we verify item from listbox or from text edit field?
        if self.user_selected_list:
            # User selected item from listbox - get listbox selection
            pref, town_entry = self.get_list_selection()
            self.logger.debug(f'first match {town_entry}')

            # Update the user edit widget with the List selection item
            # self.w.user_entry.set_text(town_entry)

            # Since we are verifying users choice, Get first match.  don't try partial match
            self.geodata.find_first_match(town_entry, self.place)
            self.place.prefix = pref
        else:
            # User typed in text entry window - get edit field value and look it up
            town_entry: str = self.w.user_entry.get()
            if len(town_entry) > 0:
                self.geodata.find_location(town_entry, self.place)
            else:
                # User entry is blank - prompt to delete this entry
                self.place.clear()
                self.place.result_type = GeoKeys.Result.DELETE
                self.logger.debug('Blank: DELETE')
                self.geodata.process_result(self.place, '', ResultFlags(limited=False, filtered=False))

        self.display_result(self.place)

    def display_result(self, place):
        """ Display result details for an item  """
        # Enable buttons so user can either click Skip, or edit the item and Click Verify.
        TKHelper.enable_buttons(self.w.review_buttons)
        nm = place.format_full_name()
        self.logger.debug(f'disp result [{place.prefix}][{place.prefix_commas}][{nm}] res=[{place.result_type}]')

        # Enable action buttons based on type of result
        if place.result_type == GeoKeys.Result.MULTIPLE_MATCHES or \
                place.result_type == GeoKeys.Result.NO_MATCH or \
                place.result_type == GeoKeys.Result.NO_COUNTRY:
            # Disable the Save & Map button until user clicks Verify and item is found
            self.set_save_allowed(False)
            TKHelper.set_preferred_button(self.w.verify_button, self.w.review_buttons, "Preferred.TButton")
        else:
            # Found a match or Not supported - enable save and verify
            self.set_save_allowed(True)  # Enable save button
            TKHelper.set_preferred_button(self.w.save_button, self.w.review_buttons, "Preferred.TButton")

        # Display status and color based on success
        self.set_status_text(place.get_status())
        if place.result_type in GeoKeys.successful_match:
            if place.place_type == Loc.PlaceType.CITY:
                self.w.status.configure(style="Good.TLabel")
            else:
                self.w.status.configure(style="GoodCounty.TLabel")
        else:
            self.w.status.configure(style="Error.TLabel")

        if len(place.georow_list) > 0:
            # Display matches in listbox
            self.w.tree.focus()  # Set focus to listbox
            self.display_georow_list(place)
        else:
            # No matches
            self.w.user_entry.focus()  # Set focus to text edit widget
            self.display_one_georow(place.status_detail)

        # Display GEDCOM person and event that this location refers to
        self.w.ged_event_info.set_text(f'{self.ancestry_file.get_name(self.ancestry_file.id)}: {self.ancestry_file.event_name} {self.ancestry_file.date}')
        self.w.root.update_idletasks()

    def list_insert(self, text, prefix):
        # Tags to alternate colors in lists
        self.odd = not self.odd
        if self.odd:
            tag = ('odd',)
        else:
            tag = ('even',)
        self.w.tree.insert('', "end", "", text=text, values=(prefix,), tags=tag)

    def clear_display_list(self):
        self.odd = False
        for row in self.w.tree.get_children():
            self.w.tree.delete(row)

    def display_georow_list(self, place: Loc.Loc):
        """ Display list of matches in listbox (tree) """

        # Clear listbox
        self.clear_display_list()

        temp_place = copy.copy(place)

        # Get geodata for each item and add to listbox output
        for geo_row in place.georow_list:
            self.geodata.geo_files.geodb.copy_georow_to_place(geo_row, temp_place)
            nm = temp_place.format_full_name()
            valid = self.geodata.validate_year_for_location(event_year=place.event_year, iso=temp_place.country_iso,
                                                            admin1=temp_place.admin1_id, padding= 0)
            if valid:
                self.list_insert(nm, temp_place.prefix)
            else:
                self.list_insert(nm, "INVALID DATE")

        self.w.root.update_idletasks()

    def skip_handler(self):
        """ Write out original entry as-is and skip any matches in future  """
        self.logger.debug(f'Skip for {self.w.original_entry.get_text()}  Updating SKIP dict')

        self.skiplist.set(self.w.original_entry.get_text(), " ")
        self.ancestry_file.write(self.w.original_entry.get_text())

        # Save Skip info for future runs
        self.skiplist.write()

        # Go to next entry
        self.handle_place_entry()

    def save_handler(self):
        """ Save the Place.  Add Place to global replace list and replace if we see it again. """
        ky = self.w.original_entry.get_text()
        if self.place.result_type == GeoKeys.Result.DELETE:
            # Put in a blank as replacement
            self.place.geoid = ''
            self.place.prefix = ''

        res = '@' + self.place.geoid + '@' + self.place.prefix
        self.logger.debug(f'Save [{ky}] :: [{res}]')

        # Add item to global replace list if user made a change.  This will be cached to disk.
        if self.w.original_entry.get_text() != self.w.user_entry.get_text():
            # User made a change - save it
            self.global_replace.set(ky, res)
            # Periodically flush dict to disk
            if self.err_count % 3 == 1:
                self.global_replace.write()
            self.logger.debug(f'SAVE SetGblRep for [{ky}] res=[{res}] Updating DICT')
        else:
            # User accepted the item as is.  Add to accept list
            self.logger.debug(f'SAVE Accept for [{ky}] res=[{res}] Updating DICT')

            self.user_accepted.set(ky, res)
            self.user_accepted.write()

        # Write out corrected item to GEDCOM output file
        if self.place.result_type != GeoKeys.Result.DELETE:
            self.file_output_place(self.place)

        # Get next error
        self.w.user_entry.set_text('')
        self.handle_place_entry()

    @staticmethod
    def help_handler():
        """ Bring up browser with help text """
        help_base = "https://github.com/corb555/GeoFinder/wiki/User-Guide"
        webbrowser.open(help_base)

    def search_handler(self):
        """ Bring up browser with Google search with this item """
        base = "https://www.google.com/search?q="
        loc = self.w.user_entry.get_text()
        webbrowser.open(f"{base}{loc}")

    def map_handler(self):
        """ Bring up browser with map for this item """
        base = "http://www.openstreetmap.org"
        if self.place.place_type == Loc.PlaceType.COUNTRY or self.place.place_type == Loc.PlaceType.ADMIN1:
            # Zoom wide if user just put in state, country
            zoom = "zoom=7"
        else:
            zoom = "zoom=14"
        loc = f"{base}/?mlat={self.place.lat}&mlon={self.place.lon}&{zoom}#map={self.place.lat}/{self.place.lon}"
        webbrowser.open(loc)

    def quit_handler(self):
        """ Set flag for shutdown.  Process all global replaces and exit """
        if messagebox.askyesno(' ', '   Exit?'):
            TKHelper.disable_buttons(button_list=self.w.review_buttons)
            self.w.quit_button.config(state="disabled")
            self.w.prog.startup = True

            self.w.user_entry.set_text(" ")
            self.w.status.set_text("Quitting...")
            # Write out the item we are on
            self.ancestry_file.write(self.w.original_entry.get_text())
            self.shutdown_requested = True

            # We will still continue to go through file, but only handle global replaces
            self.handle_place_entry()

    def config_handler(self):
        # User clicked on Config button - bring up configuration windows
        self.w.remove_initialization_widgets()  # Remove old widgets
        self.util.create_util_widgets()         # Create Util/Config widgets

    def filename_handler(self):
        """ Display file open selector dialog """
        fname = filedialog.askopenfilename(initialdir=self.directory,
                                           title="Select GEDCOM file",
                                           filetypes=(("GEDCOM files", "*.ged"), ("all files", "*.*")))
        if len(fname) > 1:
            self.cfg.set("gedcom_path", fname)  # Add filename to dict
            self.cfg.write()  # Write out config file
            self.w.status.set_text("Click Open to load GEDCOM file")
            self.w.original_entry.set_text(self.cfg.get("gedcom_path"))
            TKHelper.set_preferred_button(self.w.load_button, self.w.initialization_buttons, "Preferred.TButton")

    def return_key_event_handler(self, _):
        """ User pressed Return accelerator key.  Call Verify data entry """
        self.verify_handler()
        return "break"

    def entry_focus_event_handler(self, _):
        # Track focus so when user presses Verify, we know whether to get text from Entry Box or List box
        # User clicked on data entry widget
        # Note - second param of _ is to prevent warning for Event param which isnt used
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

    def clear_detail_text(self, place):
        self.odd = False
        self.clear_display_list()
        place.georow_list.clear()

    def display_one_georow(self, txt):
        self.logger.debug(f'DISP ONE ROW {txt}')
        self.clear_display_list()
        # self.w.scrollbar.grid_remove()  # Just one item, so hide scrollbar
        self.list_insert(txt, '')

    def display_country_note(self) -> int:
        """ display warning if only a small number of countries are enabled """
        country_list, supported_countries = self.geodata.geo_files.get_supported_countries()
        self.w.root.update()
        if supported_countries == 0:
            TKHelper.fatal_error("No countries enabled.\n\nUse Config Country Tab to change country list\n")

        if supported_countries < 20:
            messagebox.showinfo("Info", f"Loading geocode data for the following ISO country codes:"
            f"\n\n{country_list}\n\nUse Config Country Tab to change country list\n")
        return supported_countries

    @staticmethod
    def setup_logging(msg):
        logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)
        logger.info(msg)
        return logger

    def file_output_place(self, place: Loc.Loc):
        # Write out location and lat/lon to gedcom file
        nm = place.format_full_name()
        # self.logger.debug(f'ged write [{place.prefix}][{place.prefix_commas}][{nm}]')
        if place.result_type != GeoKeys.Result.DELETE:
            self.ancestry_file.output_place(place.prefix + place.prefix_commas + nm)
            self.ancestry_file.write_lat_lon(lat=place.lat, lon=place.lon)
        else:
            self.logger.debug('zero len, no output')

    def shutdown(self):
        """ Shutdown - write out Gbl Replace and skip file and exit """
        self.w.root.update_idletasks()
        if self.skiplist:
            self.skiplist.write()
        if self.global_replace:
            self.global_replace.write()
        if self.user_accepted:
            self.user_accepted.write()
        if self.cfg:
            self.cfg.write()
        if self.ancestry_file :
            self.ancestry_file.close()
        self.w.root.quit()
        sys.exit()

    def set_save_allowed(self, save_allowed: bool):
        if save_allowed:
            # Enable the Save and Map buttons
            self.save_enabled = True
            self.w.save_button.config(state="normal")  # Match - enable  button
            self.w.map_button.config(state="normal")  # Match - enable  button
        else:
            # Disable the Save and Map buttons
            self.save_enabled = False
            self.w.save_button.config(state="disabled")
            self.w.map_button.config(state="disabled")

    def set_status_text(self, txt):
        # status text is readonly
        self.w.status.state(["!readonly"])
        self.w.status.set_text(txt)
        self.w.status.state(["readonly"])

    def end_of_file_shutdown(self):
        # End of file reached
        TKHelper.disable_buttons(button_list=self.w.review_buttons)
        self.w.status.set_text("Done.  Shutting Down...")
        self.w.original_entry.set_text(" ")
        path = self.cfg.get("gedcom_path")
        messagebox.showinfo("Info", f"Finished GEDCOM file.\n\nWriting results to\n {path}.new.ged")
        self.logger.info('End of GEDCOM file')
        self.shutdown()

    def periodic_update(self, msg):
        # Display status to user
        if self.err_count % 30 == 0:
            self.w.status.set_text(msg)
            self.w.status.configure(style="Good.TLabel")
            self.w.original_entry.set_text(self.place.name)  # Display place
            self.w.root.update_idletasks()  # Let GUI update

    def check_configuration(self):
        file_error = False
        file_list = ['allCountries.txt', 'cities500.txt']

        # Get country list and validate
        countries = CachedDictionary(self.cache_dir, 'country_list.pkl')
        self.logger.debug('load country selections list')

        countries.read()
        country_dct = countries.dict
        if len(country_dct) == 0:
            self.logger.warning('no countries specified')
            file_error = True

        # Ensure that there are some geoname data files
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


def entry():
    GeoFinder()


if __name__ == "__main__":
    entry()
