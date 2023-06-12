# -*- coding: utf-8 -*-
"""
Created on Tue Jun 2 08:51:17 2020
@author: eneemann
Script to compare address points to road centerlines for quality control.
* 

2 June 2020: first version of code (EMN)
"""

import arcpy
import os
import sys
import time
import pandas as pd
import numpy as np
from Levenshtein import StringMatcher as Lv
from matplotlib import pyplot as plt
from tqdm import tqdm
import logging

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
today = time.strftime("%Y%m%d")

# Initialize the tqdm progress bar tool
tqdm.pandas()

###################
# Input variables #
###################

# Provide name for dataset and working directory where output geodatabase will be located
data_name = 'Wayne_local'
root_dir = r'C:\E911\RichfieldComCtr\Addpts_working_folder'
#root_dir = r'C:\Temp'

# Create new directory to store data and set up log
work_dir = os.path.join(root_dir, f'{data_name}_{today}')
if os.path.isdir(work_dir) == False:
    os.mkdir(work_dir)

# Set up logging
handlers = [logging.FileHandler(os.path.join(work_dir, f"{data_name}_{today}.log")), logging.StreamHandler()]
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers = handlers)
logger = logging.getLogger()
# log = open(os.path.join(work_dir, f"{data_name}_{today}.log"), "a")

logger.info(f"The script start time is {readable_start}")

# Street and address point layers with full paths:
addpts = r'C:\E911\RichfieldComCtr\2 Data From County\Wanda_20230517\WayneCoPts_20230517.gdb\WayneCoPts_20230517'  # Point to current addpts layer
#addpts = r'C:\E911\RichfieldComCtr\richfield_staging.gdb\address_points_update_20211118'  # Point to current addpts layer
streets = r'C:\E911\RichfieldComCtr\richfield_staging.gdb\streets_update_20230515'  # Point to current roads layer
# addpts = r'C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde\SGID.LOCATION.AddressPoints'  # Point to current addpts layer
# streets = r'C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde\SGID.TRANSPORTATION.Roads'  # Point to current roads layer
#addpts = r'C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\agrc@opensgid@opensgid.agrc.utah.gov.sde\opensgid.location.address_points'  # Point to current addpts layer
#streets = r'C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\agrc@opensgid@opensgid.agrc.utah.gov.sde\opensgid.transportation.roads'  # Point to current roads layer

# Input address point fields
addpt_fields = {"addnum": "HouseNumbe",
                "predir": "Pre",
                "name": "Name",
                "sufdir": "Dir",
                "type": "Type"}

# Input street fields
street_fields = {"predir": "PREDIR",
            "name": "STREETNAME",
            "sufdir": "SUFDIR",
            "type": "STREETTYPE",
            "l_f_add": "L_F_ADD",
            "l_t_add": "L_T_ADD",
            "r_f_add": "R_F_ADD",
            "r_t_add": "R_T_ADD"}

# Set flags
# Input full address field here in order to use it, otherwise components will be used
#fulladd_field = False
fulladd_field = 'ADDRESS'   # Example of using a full address field

# Set flag if data is coming from SGID
# Use 'internal' for internal SGID, use 'opensgid' for Open SGID
from_sgid = False
# from_sgid = 'internal'     # use for internal
#from_sgid = 'opensgid'     # use for Open SGID

# Provide the county to check (name in Title case), see county_fips dictionary
county = 'Wayne'


#############
# Constants #
#############

unit_list = ['#', 'APT', 'BLDG', 'BSMT', 'CONDO', 'DEPT', 'FL', 'FRNT', 'HANGAR',
             'HNGR', 'LOT', 'OFC', 'OFFICE', 'REAR', 'RM', 'SIDE', 'SP', 'SPC',
             'STE', 'TRLR', 'UNIT']

sgid_addpt_fields = {"addnum": "AddNum",
                "predir": "PrefixDir",
                "name": "StreetName",
                "sufdir": "SuffixDir",
                "type": "StreetType"}

sgid_street_fields = {"predir": "PREDIR",
            "name": "NAME",
            "sufdir": "POSTDIR",
            "type": "POSTTYPE",
            "l_f_add": "FROMADDR_L",
            "l_t_add": "TOADDR_L",
            "r_f_add": "FROMADDR_R",
            "r_t_add": "TOADDR_R"}

county_fips = {"Beaver": "49001",
        "Box Elder": "49003",
        "Cache": "49005",
        "Carbon": "49007",
        "Daggett": "49009",
        "Davis": "49011",
        "Duchesne": "49013",
        "Emery": "49015",
        "Garfield": "49017",
        "Grand": "49019",
        "Iron": "49021",
        "Juab": "49023",
        "Kane": "49025",
        "Millard": "49027",
        "Morgan": "49029",
        "Piute": "49031",
        "Rich": "49033",
        "Salt Lake": "49035",
        "San Juan": "49037",
        "Sanpete": "49039",
        "Sevier": "49041",
        "Summit": "49043",
        "Tooele": "49045",
        "Uintah": "49047",
        "Utah": "49049",
        "Wasatch": "49051",
        "Washington": "49053",
        "Wayne": "49055",
        "Weber": "49057"}

###############
#  Functions  #
###############


def copy_addpts(pts, gdb):
    # Copy current address points into a working FC and add fields
    working = os.path.join(gdb, "AddPts_working_" + today)
    if arcpy.Exists(working):
        arcpy.management.Delete(working)
    arcpy.management.CopyFeatures(pts, working)
    
    arcpy.management.AddField(working, "Notes", "TEXT", "", "", 50)
    arcpy.management.AddField(working, "full_street", "TEXT", "", "", 50)
    
    return working
    
    
def copy_streets(rds, gdb):
    # Copy current roads into a working FC and add 'FULL_STREET' field
    working = os.path.join(gdb, "Streets_working_" + today)
    if arcpy.Exists(working):
        arcpy.Delete_management(working)
    arcpy.management.CopyFeatures(rds, working)

    arcpy.management.AddField(working, "FULL_STREET", "TEXT", "", "", 50)
    
    return working


def filter_sgid_data(pts, rds, gdb, fips):
    """
    Get addpts and roads from SGID (filtered down to specific fips code) and add
    necessary fields to perform checks later in script
    """
    # Set parameters based on whether internal or opensgid is used
    query = {'countyid': 'CountyID',
             'county_l': 'COUNTY_L',
             'county_r': 'COUNTY_R'}
    
    if from_sgid == 'opensgid':
        query = {k: v.lower() for k, v in query.items()}
    elif from_sgid == 'internal':
        pass
    else:
        logger.info(f"SGID type of '{from_sgid}' is invalid. Exiting program ...")
        sys.exit()
        
    # Copy current address points into a working FC and add fields
    where_SGID_pts = f"{query['countyid']} = '{fips}'"      # All Relevant counties for Richfield
    logger.info(where_SGID_pts)
    arcpy.management.MakeFeatureLayer(pts, "sgid_addpts_lyr", where_SGID_pts)
    logger.info("SGID address points layer feature count: {}".format(arcpy.GetCount_management("sgid_addpts_lyr")))
    working_pts = os.path.join(gdb, "AddPts_working_" + today)
    arcpy.management.CopyFeatures("sgid_addpts_lyr", working_pts)
    arcpy.Delete_management("sgid_addpts_lyr")
    
    arcpy.management.AddField(working_pts, "Notes", "TEXT", "", "", 50)
    arcpy.management.AddField(working_pts, "full_street", "TEXT", "", "", 50)
      
    # Copy current roads into a working FC and add 'FULL_STREET' field
    where_SGID_rds = f"{query['county_l']} = '{fips}' OR {query['county_r']} = '{fips}'"      # All Relevant counties for Richfield
    logger.info(where_SGID_rds)
    arcpy.management.MakeFeatureLayer(rds, "sgid_roads_lyr", where_SGID_rds)
    logger.info("SGID roads layer feature count: {}".format(arcpy.GetCount_management("sgid_roads_lyr")))
    working_rds = os.path.join(gdb, "Streets_working_" + today)
    arcpy.management.CopyFeatures("sgid_roads_lyr", working_rds)
    arcpy.Delete_management("sgid_roads_lyr")
    
    arcpy.management.AddField(working_rds, "FULL_STREET", "TEXT", "", "", 50)
    
    return working_pts, working_rds


def calc_street_addpts_fulladd(working, full_add):
    update_count = 0
    
    fields = [full_add, 'full_street']
    with arcpy.da.UpdateCursor(working, fields) as cursor:
        logger.info("Looping through rows in addpts FC ...")
        for row in cursor:
            # break off and discard the house number
            parts = row[0].split(' ')
            if parts[0].isdigit():
                temp = " ".join(parts[1:])
            else:
                logger.info(f"    Address '{row[0]}' does not have a valid house number")
            
            final = temp

            # check parts of remaining address for a unit type separator
            # if found split at unit type and discard everything after
            temp_parts = temp.split(' ')
            for i in np.arange(len(temp_parts)):
                if temp_parts[i].upper() in unit_list:
                    splitter = temp_parts[i]
                    final = temp.split(splitter, 1)[0]
                    break

            row[1] = final.strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
            update_count += 1
            cursor.updateRow(row)  

def calc_street_addpts(working, add_flds):
    
    update_count = 0
    
    flist = arcpy.ListFields(working)
    fnames = [f.name for f in flist]
    # logger.info(fnames)

    if 'STREET' in fnames:
        # Calculate 'full_street' field where applicable
        fields = ['STREET', 'full_street']
        with arcpy.da.UpdateCursor(working, fields) as cursor:
            logger.info("Looping through rows in addpts FC ...")
            for row in cursor:
                if row[0] is None: row[0] = ''
                row[1] = row[0].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
                update_count += 1
                cursor.updateRow(row)    
    else:    
        # Calculate 'full_street' field where applicable
        fields = [add_flds['predir'], add_flds['name'], add_flds['sufdir'], add_flds['type'], 'full_street']
        with arcpy.da.UpdateCursor(working, fields) as cursor:
            logger.info("Looping through rows in addpts FC ...")
            for row in cursor:
                if row[0] is None: row[0] = ''
                if row[1] is None: row[1] = ''
                if row[2] is None: row[2] = ''
                if row[3] is None: row[3] = ''
                parts = [row[0], row[1], row[2], row[3]]
                row[4] = " ".join(parts)
                row[4] = row[4].strip()
                row[4] = row[4].replace("  ", " ").replace("  ", " ").replace("  ", " ")
    #            logger.info(f"New value for {fields[4]} is: {row[4]}")
                update_count += 1
                cursor.updateRow(row)
            
    logger.info(f"Total count of updates: {update_count}")
    
    
def calc_street_roads(working, st_flds):
    
    update_count = 0
    
    flist = arcpy.ListFields(working)
    fnames = [f.name for f in flist]
    # logger.info(fnames)

    if 'STREET' in fnames:
        # Calculate 'full_street' field where applicable
        fields = ['STREET', 'FULL_STREET']
        with arcpy.da.UpdateCursor(working, fields) as cursor:
            logger.info("Looping through rows in roads FC ...")
            for row in cursor:
                if row[0] is None: row[0] = ''
                row[1] = row[0].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
                update_count += 1
                cursor.updateRow(row)
    else:
        # Calculate 'FULL_STREET' field where applicable
        fields = [st_flds['predir'], st_flds['name'], st_flds['sufdir'], st_flds['type'], 'FULL_STREET']
        with arcpy.da.UpdateCursor(working, fields) as cursor:
            logger.info("Looping through rows in roads FC ...")
            for row in cursor:
                if row[0] is None: row[0] = ''
                if row[1] is None: row[1] = ''
                if row[2] is None: row[2] = ''
                if row[3] is None: row[3] = ''
                parts = [row[0], row[1], row[2], row[3]]
                row[4] = " ".join(parts)
                row[4] = row[4].strip()
                row[4] = row[4].replace("  ", " ").replace("  ", " ").replace("  ", " ")
    #            logger.info(f"New value for {fields[4]} is: {row[4]}")
                update_count += 1
                cursor.updateRow(row)
    logger.info(f"Total count of updates: {update_count}")
            
            
def check_nearby_roads(pts, add_flds, streets, st_flds, gdb):
    """
    Function performs near table analysis to find 10 closest roads w/i 800m of each address point.
    It then uses pandas dataframes to join address point and street attributes to near table.
    Calls 'logic_checks' function to compare address point and street attributes.
    This searches for address point street names that match near street segment names.
    Then, the house number is checked to ensure if falls w/i address range of nearby street segment.
    Based on appropriate results, Notes field is populated with one of the following:
        - 'good address point'
        - 'near street found, but address range mismatch'
        - 'near street not found'
    Results are exported to 'neartable_final.csv', which can later be joined back to the
    address points layer using the 'IN_FID' field to update the 'Notes' field in a FC.
    """
    func_start_time = time.time()

    # Create table name (in memory) for neartable
    neartable = 'in_memory\\near_table'
    # Perform near table analysis
    logger.info("Generating near table ...")
    near_start_time = time.time()
    arcpy.GenerateNearTable_analysis (pts, streets, neartable, '800 Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 10, 'GEODESIC')
    logger.info("Time elapsed generating near table: {:.2f}s".format(time.time() - near_start_time))
    logger.info(f"Number of rows in near table: {arcpy.GetCount_management(neartable)}")
    
    # Convert neartable to pandas dataframe
    neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
    near_df = pd.DataFrame(data = neartable_arr)
    logger.info(near_df.head(5).to_string())
    
    # Convert address points to pandas dataframe
    keep_addpt_fields = ['OBJECTID', add_flds['addnum'], 'full_street', 'Notes']
    addpts_arr = arcpy.da.FeatureClassToNumPyArray(pts, keep_addpt_fields)
    addpts_df = pd.DataFrame(data = addpts_arr)
    logger.info(addpts_df.head(5).to_string())
    
    # Convert roads to pandas dataframe
    keep_street_fields = ['OBJECTID', st_flds['l_f_add'], st_flds['l_t_add'],
                          st_flds['r_f_add'], st_flds['r_t_add'], 'FULL_STREET']
    streets_arr = arcpy.da.FeatureClassToNumPyArray(streets, keep_street_fields)
    streets_df = pd.DataFrame(data = streets_arr)
    logger.info(streets_df.head(5).to_string())
    
    # Join address points to near table
    join1_df = near_df.join(addpts_df.set_index('OBJECTID'), on='IN_FID')
    logger.info(join1_df.head(5).to_string())
    join1_path = os.path.join(work_dir, data_name + f'_neartable_{today}_join1.csv')
    # join1_df.to_csv(join1_path)
    
    # Join streets to near table
    join2_df = join1_df.join(streets_df.set_index('OBJECTID'), on='NEAR_FID')
    logger.info(join2_df.head(5).to_string())
    join2_path = os.path.join(work_dir, data_name + f'_neartable_{today}_join2.csv')
    # join2_df.to_csv(join2_path)
    
    # Apply logic_checks function to rows (axis=1) and output new df as CSV
    logger.info("Starting logic checks ...")
    logic_start_time = time.time()
    near_df_updated = join2_df.progress_apply(logic_checks, axis=1, args=(add_flds, st_flds))
    logger.info("Time elapsed in 'logic checks': {:.2f}s".format(time.time() - logic_start_time))
    path = os.path.join(work_dir, data_name + f'_neartable_{today}_updated.csv')
    near_df_updated.to_csv(path)
    
    # Separate rows with a good nearby street into a separate dataframe
    is_goodstreet = near_df_updated['goodstreet'] == True      # Create indexes
    # Grab rows with good streets, sort by near rank from near table, remove address point duplicates
    # This preserves the only the record with the nearest good street to the address point
#    goodstreets_df = near_df_updated[is_goodstreet].sort_values('NEAR_RANK').drop_duplicates('IN_FID')
    goodstreets_df = near_df_updated[is_goodstreet].sort_values('NEAR_RANK')
    
    # Separate rows with no good nearby street into a separate dataframe
    not_goodstreet = near_df_updated['goodstreet'] == False    # Create indexes
    # Grab rows with bad streets, sort by near rank from near table, remove address point duplicates
    # This preserves the only the record with the nearest bad street to the address point
#    badstreets_df = near_df_updated[not_goodstreet].sort_values('NEAR_RANK').drop_duplicates('IN_FID')
    badstreets_df = near_df_updated[not_goodstreet].sort_values('NEAR_RANK')
    
    # Combine good and bad street dataframes, sort so good streets are at the top, then remove duplicates of address points
    # If a good streets are found, nearest one will be used; otherwise nearest bad street will be used ("near street not found")
#    filtered_df = goodstreets_df.append(badstreets_df).sort_values('goodstreet', ascending=False).drop_duplicates('IN_FID')
    # Sort by multiple columns (goodstreet, then goodnum) to ensure 2nd nearest street with good num will get used
#    filtered_df = goodstreets_df.append(badstreets_df).sort_values(['goodstreet', 'goodnum'], ascending=False).drop_duplicates('IN_FID')
    filtered_df = goodstreets_df.append(badstreets_df).sort_values(['IN_FID','goodstreet','goodnum', 'edit_dist', 'NEAR_DIST'],
                                       ascending=[True, False, False, True, True])
    all_path = os.path.join(work_dir, data_name + f'_neartable_{today}_all.csv')
    filtered_df.to_csv(all_path)
    # Re-sort data frame on address point ID for final data set
    final_df = filtered_df.drop_duplicates('IN_FID')
    final_path = os.path.join(work_dir, data_name + f'_neartable_{today}_final.csv')
    final_df.to_csv(final_path)
    
    # Create new dataframe that will be used to join to address point feature class with arcpy
    join_df = final_df[['IN_FID', 'Notes', 'edit_dist', 'NEAR_DIST', 'NEAR_RANK']]
    # Rename 'Notes' column to 'Notes_near' -- prevents conflict with 'Notes' field already in FC table
    join_df.columns = ['IN_FID', 'Notes_near', 'edit_dist', 'NEAR_DIST', 'NEAR_RANK']
    join_path = os.path.join(work_dir, data_name + f'_neartable_{today}_join.csv')
    join_df.to_csv(join_path)
        
    # Convert CSV output into table and join to working address points FC
    arcpy.env.workspace = gdb
    arcpy.env.qualifiedFieldNames = False
    if arcpy.Exists("neartable_join"):
        arcpy.Delete_management("neartable_join")
    arcpy.TableToTable_conversion(join_path, gdb, "neartable_join")
    joined_table = arcpy.AddJoin_management(pts, "OBJECTID", "neartable_join", "IN_FID")
    if arcpy.Exists(pts + "_final"):
        arcpy.Delete_management(pts + "_final")
    # Copy joined table to "_final" feature class
    # This is a copy of the address points feature class with new joined fields
    arcpy.CopyFeatures_management(joined_table, pts + "_final")
                                                          
    # Update 'Notes' field in working address points with joined table notes
    # ArcPy makes a mess of the field names after the join, so we need to make
    # sure the proper fields are pulled and updated
    fields = ['Notes', 'Notes_near']
    with arcpy.da.UpdateCursor(pts + "_final", fields) as cursor:
        logger.info(f"Looping through rows in {os.path.basename(pts) + '_final'} to update 'Notes' field ...")
        for row in cursor:
            # Only update 'Notes' field if joined 'Near_notes' not null
            if row[1] is not None:
                if len(row[1]) > 0:
                    row[0] = row[1]
            cursor.updateRow(row)
    
    # Delete temporary data                             
    # arcpy.Delete_management("temp_pts")
    arcpy.Delete_management('in_memory\\near_table')
    os.remove(join_path)    
    
    logger.info("Time elapsed in 'check_nearby_roads' function: {:.2f}s".format(time.time() - func_start_time))
    
    
def logic_checks(row, a_flds, s_flds):
    """
    Function calculates new values for 'Notes' field by comparing address
    point to nearby roads' full street name and address range
    """
    goodstreet = False
    goodnum = False
    add_num = ''.join(i for i in row[a_flds['addnum']] if i.isdigit())
    
    if add_num.isdigit():
        if row['full_street'] == row['FULL_STREET']:
            goodstreet = True
            if (int(add_num.split()[0]) >= row[s_flds['l_f_add']] and int(add_num.split()[0]) <= row[s_flds['l_t_add']]) or (
                    int(add_num.split()[0]) >= row[s_flds['r_f_add']] and int(add_num.split()[0]) <= row[s_flds['r_t_add']]):
                goodnum = True
        # Update Notes field based on if street and number are good from near analysis
        if goodstreet and goodnum:
            row['Notes'] = 'good address point'
        elif goodstreet and not goodnum:
            row['Notes'] = 'near street found, but address range mismatch'
        elif not goodstreet:
            row['Notes'] = 'near street not found'
        row['goodstreet'] = goodstreet
        row['goodnum'] = goodnum
        row['edit_dist'] = Lv.distance(row['full_street'], row['FULL_STREET'])
        # Check edit distance for roads that might have typos, predir, or sufdir errors
        if row['Notes'] == 'near street not found' and row['edit_dist'] in (1, 2):
            row['Notes'] = 'no near st: possible typo, predir, or sufdir error'
        # Check for likely predir/sufdir errors: road nearly matches, range is good
        # Replace needed in logic to catch potential range in address number (e.g., '188-194')
        if row['Notes'] == 'no near st: possible typo, predir or sufdir error':
            if (int(add_num.replace('-', ' ').split()[0]) >= row[s_flds['l_f_add']] and int(add_num.replace('-', ' ').split()[0]) <= row[s_flds['l_t_add']]) or (
                    int(add_num.replace('-', ' ').split()[0]) >= row[s_flds['r_f_add']] and int(add_num.replace('-', ' ').split()[0]) <= row[s_flds['r_t_add']]):
                goodnum = True
                row['Notes'] = 'no near st: likely predir or sufdir error'
                row['goodnum'] = goodnum
        # Check for a good house number regardless of street name match or condition
        if (int(add_num.replace('-', ' ').split()[0]) >= row[s_flds['l_f_add']] and int(add_num.replace('-', ' ').split()[0]) <= row[s_flds['l_t_add']]) or (
                int(add_num.replace('-', ' ').split()[0]) >= row[s_flds['r_f_add']] and int(add_num.replace('-', ' ').split()[0]) <= row[s_flds['r_t_add']]):
            goodnum = True
            row['goodnum'] = goodnum
    
    return row

# Function to fix nulls in street address range fields
def fix_nulls(streets, st_flds):
    # Loop through and convert nulls to 0s
    update_count = 0
    fields = [st_flds['l_f_add'], st_flds['l_t_add'], st_flds['r_f_add'], st_flds['r_t_add']]
    with arcpy.da.UpdateCursor(streets, fields) as update_cursor:
        logger.info("Converting NULLs to 0s ...")
        for row in update_cursor:
            for i in np.arange(len(fields)):
                if row[i] == None or row[i] in ('', ' '):
                    row[i] = 0
                    update_count += 1
            update_cursor.updateRow(row)
    logger.info(f"Total count of NULLs to 0: {update_count}")

#####################
# Start Main Script #
#####################
  
fips = county_fips[county]

# Set up variables for later in the script 
if fulladd_field:
    address_parts = False
    logger.info('Using full address field ...')
else:
    address_parts = True
    logger.info('Using address field components ...')

logger.info(f'Using address component fields: {address_parts}')

# Create new working geodatabase and set environment variables
gdb_name = f'{data_name}_gdb_{today}.gdb'
if arcpy.Exists(os.path.join(work_dir, gdb_name)):
    arcpy.management.Delete(os.path.join(work_dir, gdb_name))
arcpy.management.CreateFileGDB(work_dir, gdb_name)
working_db = os.path.join(work_dir, gdb_name)

arcpy.env.workspace = working_db
arcpy.env.overwriteOutput = True


##########################
#  Call Functions Below  #
##########################


if from_sgid:
    addpt_fields, street_fields = sgid_addpt_fields, sgid_street_fields
    working_addpts, working_roads = filter_sgid_data(addpts, streets, working_db, fips)
    if from_sgid == 'opensgid':
        addpt_fields = {k: v.lower() for k, v in addpt_fields.items()}
        street_fields = {k: v.lower() for k, v in street_fields.items()}
        logger.info(addpt_fields)
        logger.info(street_fields)
else:
    working_addpts = copy_addpts(addpts, working_db)
    working_roads = copy_streets(streets, working_db)


if address_parts:
    calc_street_addpts(working_addpts, addpt_fields)
else:
    calc_street_addpts_fulladd(working_addpts, fulladd_field)
        
calc_street_roads(working_roads, street_fields)
fix_nulls(working_roads, street_fields)
check_nearby_roads(working_addpts, addpt_fields, working_roads, street_fields, working_db)


############################
#  Generate Plots & Stats  #
############################
logger.info("Generating a few plots and stats ...")

# Plot histogram of Edit Distances
logger.info("Creating edit distance histogram ...")
df = pd.read_csv(os.path.join(work_dir, data_name + f'_neartable_{today}_final.csv'))
plt.figure(figsize=(6,4))
plt.hist(df['edit_dist'], bins = np.arange(0, df['edit_dist'].max(), 1)-0.5, color='red', edgecolor='black')
plt.xticks(np.arange(0, df['edit_dist'].max(), 2))
plt.title('Address/Street Edit Distance Histogram')
plt.xlabel('Edit Distance')
plt.ylabel('Count')
plt.savefig(os.path.join(work_dir, 'addpt_edit_distances.png'))

df['edit_dist'].max()

# Plot bar chart of Notes column
logger.info("Creating notes bar chart ...")
plt.figure(figsize=(6,8), constrained_layout=True)
plt.hist(df['Notes'], color='lightblue', edgecolor='black')
# plt.xticks(np.arange(0, df['Notes'].max(), 2))
plt.xticks(rotation='vertical')
plt.title('Address Point Categories')
plt.xlabel('Category')
plt.ylabel('Count')
plt.savefig(os.path.join(work_dir, 'addpt_categories.png'))

logger.info('\n')
logger.info('Stats by total count:')
logger.info(df.groupby('Notes').count()['edit_dist'])
logger.info('\n')

# Print out percentages for each result in 'Notes'
total_pts = df.shape[0]
logger.info('Stats by percentage:')
logger.info(df.groupby('Notes').count()['edit_dist'].apply(lambda x: 100 * x / float(total_pts)))

logger.info('\n' + "Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
logger.info(f"The script end time is {readable_end}")
logger.info("Time elapsed: {:.2f}s".format(time.time() - start_time))