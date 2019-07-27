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
import logging
import os
import sys
import webbrowser
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox

from geofinder import AppLayout, Gedcom, Geodata, GeoKeys, Place
from geofinder.CachedDictionary import CachedDictionary
from geofinder.Config import Config
from geofinder.Widge import Widge

MISSING_FILES = 'Missing Files.  Please run GeoUtil.py and correct errors in Errors Tab'

odd_tag = ('odd',)
even_tag = ('even',)

LOC_TOKEN = 1
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

    geofinder - The main GUI
    GeoData - The geonames data model routines
    GeoDB -  Database insert/lookup routines
    GEDCOM - routines to read and write GEDCOM files
    GeodataFile - routines to read/write geoname data sources
    AppLayout - routines to create the app windows and widgets
    Place - holds all info for a single place
    """

    def __init__(self):
        print('GeoFinder')
        self.shutdown_requested: bool = False  # Flag to indicate user requested shutdown
        self.save_enabled = False  # Only allow SAVE when we have an item that was matched in geonames
        self.user_selected_list = False  # Indicates whether user selected a list entry or text edit entry
        self.err_count = 0
        self.odd = False

        self.logger = self.setup_logging('geofinder Init')
        # Save our base directory and cache directory
        self.directory: str = os.path.join(str(Path.home()), Geodata.Geodata.get_directory_name())
        self.cache_dir = GeoKeys.cache_directory(self.directory)

        # Get configuration settings stored in config pickle file
        self.logger.debug('load config')
        self.cfg = Config()
        err = self.cfg.read(self.cache_dir, "config.pkl")
        if err:
            self.logger.warning(f'error reading {self.cache_dir} config.pkl')

        pathname = self.cfg.get("gedcom_path")  # Get saved config setting for GEDCOM file
        if pathname is not None:
            out_path = pathname + "new.ged"
        else:
            out_path = 'unk.new.ged'
        cdir = self.cache_dir

        # Initialize routines to read/write GEDCOM file
        self.gedcom: Gedcom.Gedcom(in_path=pathname, out_path=out_path, cache_dir=cdir, progress=None) = None
        self.place: Place.Place = Place.Place()  # Create an object to store info for the current Place

        # Create App window and configure  window buttons and widgets
        self.w: AppLayout.AppLayout = AppLayout.AppLayout(self)
        self.w.create_initialization_widgets()

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
            Widge.fatal_error(MISSING_FILES)

        # If the list of supported countries is unusually short, display note to user
        num = self.display_country_note()
        self.logger.info(f'{num} countries will be loaded')

        # Read in Geoname Gazeteer file - city names, lat/long, etc.
        error = self.geodata.read_geonames()
        if error:
            Widge.fatal_error(MISSING_FILES)
        self.logger.info(f'Geoname dictionary has {self.geodata.geo_files.geodb.get_row_count()} entries')
        self.w.root.update()
        self.w.prog.update_progress(100, " ")

        # Prompt user to click Open for GEDCOM file
        Widge.set_text(self.w.original_entry, self.cfg.get("gedcom_path"))
        Widge.enable_buttons(self.w.initialization_buttons)
        if os.path.exists(self.cfg.get("gedcom_path")):
            Widge.set_text(self.w.status, "Click Open to load GEDCOM file")
        else:
            # GEDCOM file name isn't valid - prompt user to select a GEDCOM file
            self.w.load_button.config(state="disabled")
            Widge.set_text(self.w.status, "Choose a GEDCOM file")

        # Flag to indicate whether we are in startup or in Window loop.  Determines how window idle is called
        self.startup = False
        self.w.root.mainloop()  # ENTER MAIN LOOP and Wait for user to click on load button

    def load_handler(self):
        """
        User pressed LOAD button to load a GEDCOM file. Load in file name and
        loop through GEDCOM file and find every PLACE entry and verify the entry against the geoname data
        """
        Widge.set_text(self.w.original_entry, "")
        self.w.create_review_widgets()  # Switch display from Initial widgets to main review widgets

        # Open GEDCOM file
        ged_path = self.cfg.get("gedcom_path")
        self.gedcom = Gedcom.Gedcom(in_path=ged_path, out_path=ged_path + '.new.ged', cache_dir=self.cache_dir,
                                    progress=self.w.prog)  # Routines to open and parse GEDCOM file
        self.w.root.update()
        if self.gedcom.error:
            Widge.fatal_error(f"GEDCOM file {ged_path} not found.")

        # Add GEDCOM filename to Title
        path_parts = os.path.split(ged_path)  # Extract filename from full path
        Widge.set_text(self.w.title, f'geofinder - {path_parts[1]}')

        # Read GEDCOM file, find each place entry and handle it.
        self.handle_place_entry()

    def handle_place_entry(self):
        """ Get next PLACE  in users GEDCOM File.  Replace it, skip it, or have user correct it. """
        Widge.set_text(self.w.original_entry, "")
        if self.shutdown_requested:
            self.periodic_update("Shutting down...")
        else:
            self.periodic_update("Scanning")
        self.clear_detail_text(self.place)

        while True:
            self.err_count += 1    # Counter is used to periodically update status
            # Find the next PLACE entry in GEDCOM file
            # Process it and keep looping until we need user input
            self.place.clear()
            town_entry, eof = self.gedcom.scan_for_tag('PLAC')

            if eof:
                self.end_of_file_shutdown()

            # When we find an error, see if we have a fix (Global Replace) or Skip (ignore).
            # Otherwise have user handle it
            if self.global_replace.get(town_entry) is not None:
                # There is a global change that we can apply to this line.  Get the replacement text
                replacement = self.global_replace.get(town_entry)
                # self.logger.debug(f'Found GblRep {replacement} for {town_entry}')

                # get lat long and write out to gedcom output file
                rep_token = replacement.split('@')
                self.geodata.find_geoid(rep_token[LOC_TOKEN], self.place)

                # Get prefix if there was one
                if len(rep_token) > 2:
                    self.place.prefix = rep_token[PREFIX_TOKEN]

                # Output place to GEDCOM file
                self.gedcom_output_place(self.place)

                # Display status to user
                if self.shutdown_requested:
                    self.periodic_update("Shutting down...")
                else:
                    self.periodic_update("Applying change")

                continue
            elif self.user_accepted.get(town_entry) is not None:
                # There is an accepted  change that we can use for this line.  Get the replacement text
                replacement = self.user_accepted.get(town_entry)
                self.logger.debug(f'Found Accept {replacement} for {town_entry}')

                # get lat long and write out to gedcom output file
                rep_token = replacement.split('@')
                self.geodata.find_geoid(rep_token[LOC_TOKEN], self.place)

                # Get prefix if there was one
                if len(rep_token) > 2:
                    self.place.prefix = rep_token[PREFIX_TOKEN]

                self.gedcom_output_place(self.place)

                # Display status to user
                if self.shutdown_requested:
                    self.periodic_update("Shutting down...")
                else:
                    self.periodic_update("Applying change")

                continue
            elif self.shutdown_requested:
                # User requested shutdown.  Finish up going thru file, then shut down
                self.periodic_update("Shutting Down...")
                Widge.set_text(self.w.original_entry, " ")
                self.gedcom.write(town_entry)
                continue
            elif self.skiplist.get(town_entry) is not None:
                # item is in skiplist - Write out as-is and go to next error
                self.logger.debug(f'Found Skip for {town_entry}')
                self.periodic_update("Skipping")
                self.gedcom.write(town_entry)
                continue
            else:
                # Found a new PLACE entry
                # See if it is in our place database
                # Parse the entry into Prefix, City, Admin2, Admin1, Country
                self.place.parse_place(place_name=town_entry, geo_files=self.geodata.geo_files)
                self.place.event_year = int(self.gedcom.year)  # Set place date to event date (as geo names change over time)
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
                        # Add to global replace list - Use '@' for tokenizing.  Save LOC_TOKEN and PREFIX_TOKEN
                        res = '@' + self.place.geoid + '@' + self.place.prefix

                        self.global_replace.set(town_entry, res)
                        self.logger.debug(f'Found Exact Match for {town_entry} res= {res} Setting DICT')
                        self.global_replace.write()

                        self.gedcom_output_place(self.place)
                        continue
                    else:
                        self.logger.debug(f'User review for {town_entry}')

                        self.w.status.configure(style="Good.TLabel")
                        Widge.set_text(self.w.original_entry, self.place.name)  # Display place
                        break  # Have user review the match
                else:
                    self.logger.debug(f'User2 review for {town_entry}')

                    self.w.status.configure(style="Good.TLabel")
                    Widge.set_text(self.w.original_entry, self.place.name)  # Display place
                    # Have user review the match
                    break

        # Have user review the result
        self.display_result(self.place)

    def get_list_selection(self):
        # Get the item the user selected in list (tree)
        loc = (self.w.tree.item(self.w.tree.selection(), "text"))
        prefix = (self.w.tree.item(self.w.tree.selection())['values'][0])
        return f'{prefix}, {loc}'

    def verify_handler(self):
        """ User clicked verify.  Verify if the users new Place entry has a match in geonames data.  """
        # Do we verify item from listbox or from text edit field?
        if self.user_selected_list:
            # User selected item from listbox - get listbox selection
            town_entry = self.get_list_selection()

            # Update the user edit widget with the List selection item
            Widge.set_text(self.w.user_edit, town_entry)
            # Since we are verifying users choice, Get first match.  don't try partial match
            self.geodata.find_first_match(town_entry, self.place)
        else:
            # User typed in text entry window - get edit field value and look it up
            town_entry: str = self.w.user_edit.get()
            self.geodata.find_location(town_entry, self.place)

        self.display_result(self.place)

    def display_result(self, place):
        """ Display result details for an item  """
        # Enable buttons so user can either click Skip, or edit the item and Click Verify.
        Widge.enable_buttons(self.w.review_buttons)
        Widge.set_text(self.w.user_edit, place.name)

        # Enable action buttons based on type of result
        if place.result_type == GeoKeys.Result.MULTIPLE_MATCHES or \
                place.result_type == GeoKeys.Result.NO_MATCH or \
                place.result_type == GeoKeys.Result.NO_COUNTRY:
            # Disable the Save & Map button until user clicks Verify and item is found
            self.disable_save_button(True)
            self.set_verify_as_preferred(True)
        else:
            # Found a match or Not supported - enable save and verify
            self.disable_save_button(False)  # Enable save button
            self.set_verify_as_preferred(False)  # Make Save button in highlighted style

        # Display status and color based on success
        self.set_status_text(place.get_status())
        if place.result_type in GeoKeys.successful_match:
            if place.place_type == Place.PlaceType.ADMIN1 or place.place_type == Place.PlaceType.ADMIN2:
                self.w.status.configure(style="GoodCounty.TLabel")
            else:
                self.w.status.configure(style="Good.TLabel")
        else:
            self.w.status.configure(style="Error.TLabel")

        if len(place.georow_list) > 0:
            # Display matches in listbox
            self.w.tree.focus()  # Set focus to listbox
            self.display_georow_list(place)
        else:
            # No matches
            self.w.user_edit.focus()  # Set focus to text edit widget
            self.display_one_georow(place.status_detail)

        # Display GEDCOM person and event that this location refers to
        Widge.set_text(self.w.ged_event_info, f'{self.gedcom.get_name(self.gedcom.id)}: {self.gedcom.last_tag_name} {self.gedcom.date}')
        self.w.root.update_idletasks()

    def list_insert(self, text, prefix):
        self.odd = not self.odd
        if self.odd:
            tag = odd_tag
        else:
            tag = even_tag
        self.w.tree.insert('', "end", "", text=text, values=(prefix,), tags=tag)

    def clear_display_list(self):
        self.odd = False
        for row in self.w.tree.get_children():
            self.w.tree.delete(row)

    def display_georow_list(self, place: Place.Place):
        """ Display list of matches in listbox (tree) """

        # Clear listbox
        self.clear_display_list()

        temp_place = copy.copy(place)

        # Get geodata for each item and add to listbox output
        for geo_row in place.georow_list:
            self.geodata.geo_files.geodb.copy_georow_to_place(geo_row, temp_place)
            nm = temp_place.format_full_name()
            self.list_insert(nm, temp_place.prefix)

        self.w.root.update_idletasks()

    def skip_handler(self):
        """ Write out original entry as-is and skip any matches in future  """
        self.logger.debug(f'Skip for {Widge.get_text(self.w.original_entry)}  Updating SKIP dict')

        self.skiplist.set(Widge.get_text(self.w.original_entry), " ")
        self.gedcom.write(Widge.get_text(self.w.original_entry))

        # Save Skip info for future runs
        self.skiplist.write()

        # Go to next entry
        self.handle_place_entry()

    def save_handler(self):
        """ Save the Place.  Add Place to global replace list and replace if we see it again. """
        ky = Widge.get_text(self.w.original_entry)
        res = '@' + self.place.geoid + '@' + self.place.prefix

        # Add item to global replace list if user made a change.  This will be cached to disk.
        if Widge.get_text(self.w.original_entry) != Widge.get_text(self.w.user_edit):
            # User made a change - save it
            self.global_replace.set(ky, res)
            self.global_replace.write()
            self.logger.debug(f'SAVE SetGblRep for {ky} res={res} Updating DICT')
        else:
            # User accepted the item as is.  Add to accept list
            self.user_accepted.set(ky, res)
            self.user_accepted.write()

        # Write out corrected item to GEDCOM output file
        self.gedcom_output_place(self.place)

        # Get next error
        Widge.set_text(self.w.user_edit, '')
        self.handle_place_entry()

    @staticmethod
    def help_handler():
        """ Bring up browser with help text """
        help_base = "https://github.com/corb555/GeoFinder/wiki/User-Guide"
        webbrowser.open(help_base)

    def search_handler(self):
        """ Bring up browser with Google search with this item """
        base = "https://www.google.com/search?q="
        loc = Widge.get_text(self.w.user_edit)
        webbrowser.open(f"{base}{loc}")

    def map_handler(self):
        """ Bring up browser with map for this item """
        base = "http://www.openstreetmap.org"
        if self.place.place_type == Place.PlaceType.COUNTRY or self.place.place_type == Place.PlaceType.ADMIN1:
            # Zoom wide if user just put in state, country
            zoom = "zoom=7"
        else:
            zoom = "zoom=14"
        loc = f"{base}/?mlat={self.place.lat}&mlon={self.place.lon}&{zoom}#map={self.place.lat}/{self.place.lon}"
        webbrowser.open(loc)

    def quit_handler(self):
        """ Set flag for shutdown.  Process all global replaces and exit """
        if messagebox.askyesno(' ', '   Exit?'):
            Widge.disable_buttons(button_list=self.w.review_buttons)
            self.w.quit_button.config(state="disabled")
            self.w.prog.startup = True

            Widge.set_text(self.w.user_edit, " ")
            Widge.set_text(self.w.status, "Quitting...")
            # Write out the item we are on
            self.gedcom.write(Widge.get_text(self.w.original_entry))
            self.shutdown_requested = True

            # We will still continue to go through file, but only handle global replaces
            self.handle_place_entry()

    def filename_handler(self):
        """ Display file open selector dialog """
        fname = filedialog.askopenfilename(initialdir=self.directory,
                                           title="Select GEDCOM file",
                                           filetypes=(("GEDCOM files", "*.ged"), ("all files", "*.*")))
        if len(fname) > 1:
            self.cfg.set("gedcom_path", fname)  # Add filename to dict
            self.cfg.write()  # Write out config file
            self.w.load_button.config(state="normal")
            Widge.set_text(self.w.status, "Click Open to load GEDCOM file")
            Widge.set_text(self.w.original_entry, self.cfg.get("gedcom_path"))

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
        #self.w.scrollbar.grid_remove()  # Just one item, so hide scrollbar
        self.list_insert(txt, '')

    def display_country_note(self) -> int:
        """ display warning if only a small number of countries are enabled """
        countries, num = self.geodata.geo_files.get_supported_countries()
        self.w.root.update()
        if num == 0:
            Widge.fatal_error("No countries enabled.\n\nUse GeoUtil.py Country Tab to change country list\n")

        if num < 20:
            messagebox.showinfo("Info", "{}{}{}".format("Loading geocode data for the following ISO country codes:\n\n",
                                                        countries,
                                                        "\n\nUse GeoUtil.py Country Tab to change country list\n"))
        return num

    @staticmethod
    def setup_logging(msg):
        logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)
        logger.info(msg)
        return logger

    def gedcom_output_place(self, place: Place.Place):
        # Write out location and lat/lon to gedcom file
        nm = place.format_full_name()
        self.logger.debug(f'ged write [{place.prefix}][{place.prefix_commas}][{nm}]')
        self.gedcom.write(place.prefix + place.prefix_commas + nm)
        self.gedcom.write_lat_lon(lat=place.lat, lon=place.lon)

    def shutdown(self):
        """ Shutdown - write out Gbl Replace and skip file and exit """
        self.w.root.update_idletasks()
        self.skiplist.write()
        self.global_replace.write()
        self.user_accepted.write()
        self.cfg.write()
        if self.gedcom is not None:
            self.gedcom.close()
        self.w.root.quit()
        sys.exit()

    def disable_save_button(self, disable: bool):
        if disable:
            # Disable the Save and Map buttons
            self.save_enabled = False
            self.w.save_button.config(state="disabled")
            self.w.map_button.config(state="disabled")
        else:
            # Enable the Save and Map buttons
            self.save_enabled = True
            self.w.save_button.config(state="normal")  # Match - enable  button
            self.w.map_button.config(state="normal")  # Match - enable  button

    def set_status_text(self, txt):
        # status text is readonly
        self.w.status.state(["!readonly"])
        Widge.set_text(self.w.status, txt)
        self.w.status.state(["readonly"])

    def end_of_file_shutdown(self):
        # End of file reached
        Widge.disable_buttons(button_list=self.w.review_buttons)
        Widge.set_text(self.w.status, "Done.  Shutting Down...")
        Widge.set_text(self.w.original_entry, " ")
        path = self.cfg.get("gedcom_path")
        messagebox.showinfo("Info", f"Finished GEDCOM file.\n\nWriting results to\n {path}.new.ged")
        self.logger.info('End of GEDCOM file')
        self.shutdown()

    def periodic_update(self, msg):
        # Display status to user
        if self.err_count % 30 == 0:
            Widge.set_text(self.w.status, msg)
            self.w.status.configure(style="Good.TLabel")
            Widge.set_text(self.w.original_entry, self.place.name)  # Display place
            self.w.root.update_idletasks()  # Let GUI update

    def set_verify_as_preferred(self, set_verify_preferred: bool):
        if set_verify_preferred:
            self.w.verify_button.configure(style="Preferred.TButton")  # Make the Verify button normal style
            self.w.save_button.configure(style="TButton")  # Make the Save button the preferred selection
        else:
            self.w.verify_button.configure(style="TButton")  # Make the Verify button normal style
            self.w.save_button.configure(style="Preferred.TButton")  # Make the Save button the preferred selection


r = GeoFinder()
