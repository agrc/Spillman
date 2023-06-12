
# Spillman

- The scripts in this repository are used to stage, clean, and prepare Spillman data for Utah PSAPs
- Each PSAP has its own folder with scripts to process and prep data for that location
- **There are variables in each script will need to be updated to point to local data sources, connection files, etc.**

## Python Environment

- Create new environment (might take an hour or so to build):
  - `conda create --clone arcgispro-py3 --name main_303`
  - `activate main_303`
  - `FOR /F "delims=~" %f in (C:\{path-to}requirements_main_303.txt) DO conda install --yes -c conda-forge --no-pin --dry-run "%f"`
  - `pip install zipfile36`
  - `pip install wget`
  - `pip install xxhash`

## Overview of common scripts

- `{psap_name}_copy_update_needs.py`
  - Script that projects a list of data layers from the WGS84 geodatabase into UTM 12N in the staging geodatabase for working on an update.  This ensures the layers for the update are created from the latest in-use data. Output feature classes are controlled by the list or dictionary in the script and have `_update_{yyyymmdd}` appended on the end of their name.
- `{psap_name}_Road_Finder.py`
  - Script that searches for new roads from SGID.TRANSPORTATION.Roads (or optionally, a county's raw roads layer) that are not in the current Spillman streets layer (`current_streets` variable). A definition query filters the search down to counties relevent for the specific PSAP.  The output feature class (`SGID_roads_to_review_{yyyymmdd}`) only contains roads whose centroid falls outside of a 10m buffer around the existing Spillman roads.
- `{psap_name}_road_calculations.py`
  - Script that calculates specific fields in the Spillman roads layer and converts blanks to NULLs. (ex: STREET, JoinID, alias fields, etc.)
- `{psap_name}_check_for_new_addpts.py`
  - Script that searches for new address points from SGID.LOCATION.AddressPoints (or optionally, a county's raw address points layer)
  - Compares possible new points to current address points
    - Checks for duplicates based on the full address
    - Checks for likely unit/spatial duplicate if new point is within 5m of an existing point
  - Checks up to 10 nearby roads within 800m of a new point
    - To see if the street names match between the road and address point
    - To see if the house number fits within the roads address range
  - Categories each address point into one of the following groups in the `Notes` field:
    - **'good address point'** - new and matches to a street segment
    - **'name duplicate'** - the full address already exists
    - **'likely unit or spatial duplicate'** - w/i 5m of exisiting addpt
    - **'near street found, but address range mismatch'** - the street name matches a road segment, but the address range doesn't
    - **'no near st: possible typo predir or sufdir error'** - nearly-matching street with an edit distance of 1 or 2 was found
    - **'no near st: likely predir or sufdir error'** - nearly-matching street with an edit distance of 1 or 2 was found and the house number correctly falls within the nearby segments address range
    - **'near street not found'** - a matching street wasn't found w/i 800m
    - **'not name duplicate'** - catchall if the full address doesn't already exist, but the point didn't fall into another category
  - Outputs a feature class named `zzz_AddPts_new_working_{yyyymmdd}_final` in the staging geodatabase that contains the results
  - Review the output, clean up the points that can be fixed, flag the address points you want to add (use the Notes_near field), and then append them into your Spillman address points layer
- `{psap_name}_addpts_calculations.py`
  - Script that calculates specific fields in the Spillman address points layer and converts blanks to NULLs (ex: STREET, Label, JoinID, etc.)
- `Spillman_classic_{psap_name}_prep.py`
  - Script to prep data for Spillman Classic. Creates new working copies of geodatabases, calculates `STREET` and alias fields on streets layer, cleans up data.  Creates AddressPoints_CAD layer by removing unit addresses (if necessary). Copies TBZONES table to WGS84 geodatabse, projects data layers to WGS84, appends streets in buffer to `Streets_All` (if necessary).  Sets attributes to NULL that will populated from polygon data using the Spillman Toolbar.
    1. Run the script first to prep the data
    2. Use the Spillman ArcMap tools to populate fields from polygon layers
    3. Comment out the main function calls, uncomment the rows to export the shapefiles that you updated, then run the script again to export the shapefiles
- `{psap_name}_jitter_CommonNames.py`
  - A simple script to add some random variability (jitter) to the shape field for point layers.  It moves points about 1-1.5m so that they aren't stacked on top of each other.  In Spillman Geovalidation, this can be important if several common places with different names are stack on top of each other.  By slightly adjusting the location, each common place can properly be located in the Spillman console.
- `{psap_name}_auto_snapper_near.py`
  - Script that automatically snaps together the endpoints of road segments that are unsnapped, but within a specified distance of each other (4m).  Also deletes short segments that are shorter than the specified distance (4m).  This improves the road data for use in a network dataset and routing applications.
  - Uses spatially-enabble data frames (SEDF) with h3 index and near tables to determine what endpoints should be snapped together.  One endpoint is chosen to remain static and the other nearby endpoints (4m) are moved to snapped to the static one.  No other vertices are adjusted, only the endpoints.
  - A few fields are added to the data and populated to track endpoint information and snapping status.
- `{psap_name}_QuickestRoute_build.py`
  - Weber and Davis-Layton use QuickestRoute, Salt Lake TOC may in the future (code is ready)
  - Builds a routing network dataset from the streets layer for use in Spillman's QuickestRoute extension.  Calculates travel time fields and applies a multiplier to incentivize interstates (travel time x1), then state highways (travel time x1.5), then surface streets (travel time x2)
  - `ONEWAY` field must be populated with the following travel convention:
    - 0 = both directions allowed (converted by script to 'B')
    - 1 = travel with line direction (converted by script to 'FT')
    - 2 = travel against line direction (converted by script to 'TF')
  - Note: the `Layton` version of this script also takes care of the auto-snapping
