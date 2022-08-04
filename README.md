# GeoFinder 
GeoFinder reads the place names in a GEDCOM genealogy file, validates and corrects them, and adds their latitude and longitude using geo data from the  geoname.org database.  For unrecognized places, it supports wildcard searches and phonetic searches.    

<a name="features"></a>
## Features  
* Designed for correcting place names in large GEDCOM files
* Rich place name database from geonames.org optimized for Genealogy including cemeteries, historic locations, and religious locations.
* Automatic matching wherever possible adds missing information such as missing state/province or county.
* Adds latitude/longitude for recognized place names
* Cleans up spelling and standardizes place names
* Output is to a new GEDCOM file.  The original file is not touched.
* Supports wildcard usage to find places
* Attempts Phonetic search to correct spelling errors
* Highlights locations in the US and Canada where the event date is before European naming of that location
   
[See User Guide Wiki for details](https://github.com/corb555/GeoFinder/wiki/User-Guide)
