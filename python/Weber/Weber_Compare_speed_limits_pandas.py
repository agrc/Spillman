# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 13:21:50 2019

@author: eneemann
"""

import arcpy
from arcpy import env
import os
import time
import pandas as pd
import numpy as np
from Levenshtein import StringMatcher as Lv
from matplotlib import pyplot as plt

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

weber_db = r"C:\E911\WeberArea\Staging103\Weber_Speed_Limits.gdb"
env.workspace = weber_db
env.overwriteOutput = True

weber_streets = os.path.join(weber_db, "Streets_Map_20191227")
updates = os.path.join(weber_db, "Streets_Map_updates_20191227_WGS84")

# Convert updates to points to use in near table
updates_pts = os.path.join(weber_db, "Updates_20191227_pts")
arcpy.management.FeatureToPoint(updates, updates_pts, "INSIDE")

# Add field to working FC for notes
arcpy.management.AddField(updates_pts, "Notes", "TEXT", "", "", 50)

###############
#  Functions  #
###############
           
            
def check_nearby_roads(points, streets, gdb):
    """
    Function performs near table analysis to find 5 closest roads w/i 100m of each address point.
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
    print("Generating near table ...")
    arcpy.GenerateNearTable_analysis (points, streets, neartable, '100 Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 5, 'GEODESIC')
    print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(neartable)))
    
    # Convert neartable to pandas dataframe
    neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
    near_df = pd.DataFrame(data = neartable_arr)
    print(near_df.head(5).to_string())
    
    # Convert updates_pts to pandas dataframe
    update_fields = ['OBJECTID_1', 'STREET', 'SPEED', 'L_F_ADD', 'L_T_ADD', 'R_F_ADD', 'R_T_ADD', 'Notes']
    updates_arr = arcpy.da.FeatureClassToNumPyArray(points, update_fields)
    updates_df = pd.DataFrame(data = updates_arr)
    col = {"OBJECTID_1":"OBJECTID_1_up", "STREET":"STREET_up", "SPEED":"SPEED_up", "L_F_ADD":"L_F_ADD_up",
           "L_T_ADD":"L_T_ADD_up", "R_F_ADD":"R_F_ADD_up", "R_T_ADD":"R_T_ADD_up", "Notes":"Notes"}
    updates_df.rename(columns = col, inplace=True)
    print(updates_df.head(5).to_string())
    
    # Convert streets to pandas dataframe
    street_fields = ['OBJECTID_1', 'STREET', 'SPEED', 'L_F_ADD', 'L_T_ADD', 'R_F_ADD', 'R_T_ADD']
    streets_arr = arcpy.da.FeatureClassToNumPyArray(streets, street_fields)
    streets_df = pd.DataFrame(data = streets_arr)
    print(streets_df.head(5).to_string())
    
    # Join updates_pts to near table
    join1_df = near_df.join(updates_df.set_index('OBJECTID_1_up'), on='IN_FID')
    print(join1_df.head(5).to_string())
    path = r'C:\E911\WeberArea\Staging103\Speed_limit_working_folder\weber_neartable_join1.csv'
    join1_df.to_csv(path)
    
    # Join streets to near table
    join2_df = join1_df.join(streets_df.set_index('OBJECTID_1'), on='NEAR_FID')
    print(join2_df.head(5).to_string())
    path = r'C:\E911\WeberArea\Staging103\Speed_limit_working_folder\weber_neartable_join2.csv'
    join2_df.to_csv(path)
    
    # Apply logic_checks function to rows (axis=1) and output new df as CSV
    near_df_updated = join2_df.apply(logic_checks, axis=1)
    path = r'C:\E911\WeberArea\Staging103\Speed_limit_working_folder\weber_neartable_updated.csv'
    near_df_updated.to_csv(path)
      
    # Separate rows with a good nearby street into a separate dataframe
    is_samestreet = near_df_updated['samestreet'] == True      # Create indexes
    # Grab rows with good streets, sort by near rank from near table, remove address point duplicates
    # This preserves the only the record with the nearest good street to the address point
    samestreets_df = near_df_updated[is_samestreet].sort_values('NEAR_RANK')
    
    # Separate rows with no good nearby street into a separate dataframe
    not_samestreet = near_df_updated['samestreet'] == False    # Create indexes
    # Grab rows with bad streets, sort by near rank from near table, remove address point duplicates
    # This preserves the only the record with the nearest bad street to the address point
    badstreets_df = near_df_updated[not_samestreet].sort_values('NEAR_RANK')
    
    # Combine good and bad street dataframes, sort so good streets are at the top
    # If a good streets are found, nearest one will be used; otherwise nearest bad street will be used ("near street not found")
    # Sort by multiple columns (samestreet, then samenum) to ensure 2nd nearest street with good num will get used
    filtered_df = samestreets_df.append(badstreets_df).sort_values(['NEAR_FID', 'samestreet', 'edit_dist', 'NEAR_DIST', 'samenum'],
                                       ascending=[True, False, True, True, False])
    filtered_df.to_csv(r'C:\E911\WeberArea\Staging103\Speed_limit_working_folder\weber_neartable_all.csv')
    # Re-sort data frame on address point ID for final data set
    final_df = filtered_df.drop_duplicates('NEAR_FID')
    path = r'C:\E911\WeberArea\Staging103\Speed_limit_working_folder\weber_neartable_final.csv'
    final_df.to_csv(path)
    
    # Create new dataframe that will be used to join to streets feature class with arcpy
    join_df = final_df[['IN_FID', 'NEAR_FID', 'SPEED_up', 'STREET_up', 'Notes', 'edit_dist']]
    # Rename 'Notes' column to 'Notes_near' -- prevents conflict with 'Notes' field already in FC table
#    join_df.columns = ['NEAR_FID', 'Notes_near', 'edit_dist']
    join_path = r'C:\E911\WeberArea\Staging103\Speed_limit_working_folder\weber_neartable_join.csv'
    join_df.to_csv(join_path)
        
    # Convert CSV output into table and join to working streets FC
    env.workspace = gdb
    env.qualifiedFieldNames = False
    if arcpy.Exists("neartable_join"):
        arcpy.Delete_management("neartable_join")
    arcpy.TableToTable_conversion(join_path, gdb, "neartable_join")
    joined_table = arcpy.AddJoin_management(streets, "OBJECTID_1", "neartable_join", "NEAR_FID")
    if arcpy.Exists(streets + "_final"):
        arcpy.Delete_management(streets + "_final")
    # Copy joined table to "_final" feature class
    # This is a copy of the streets feature class with new joined fields
    arcpy.CopyFeatures_management(joined_table, streets + "_final")
                                                          
    # Update 'Notes' field in working streets with joined table notes
    # ArcPy makes a mess of the field names after the join, so we need to make
    # sure the proper fields are pulled and updated
#    fields = ['Notes', 'Notes_near']
#    with arcpy.da.UpdateCursor(points + "_final", fields) as cursor:
#        print("Looping through rows in {} to update 'Notes' field ...".format(os.path.basename(points) + "_final"))
#        for row in cursor:
#            # Only update 'Notes' field if joined 'Near_notes' not null
#            if row[1] is not None:
#                if len(row[1]) > 0:
#                    row[0] = row[1]
#            cursor.updateRow(row)
                                 
    print("Time elapsed in 'check_nearby_roads' function: {:.2f}s".format(time.time() - func_start_time))
    
    
def logic_checks(row):
    """
    Function calculates values for 'Notes' field by comparing speed limits
    """
    samespeed = False
    if row['SPEED'] == row['SPEED_up']:
        row['Notes'] = 'same speed limit'
        samespeed = True
    else:
        row['Notes'] = 'speed limit changed'
        
    samestreet = False
    samenum = False
    if row['STREET'] == row['STREET_up']:
        samestreet = True
        if (row['L_F_ADD'] == row['L_F_ADD_up']) and (row['R_F_ADD'] == row['R_F_ADD_up']) and (
                row['L_T_ADD'] == row['L_T_ADD_up']) and (row['R_T_ADD'] == row['R_T_ADD_up']):
            samenum = True

    # Check for same address range regardless of street name match or condition
    if (row['L_F_ADD'] == row['L_F_ADD_up']) and (row['R_F_ADD'] == row['R_F_ADD_up']) and (
                row['L_T_ADD'] == row['L_T_ADD_up']) and (row['R_T_ADD'] == row['R_T_ADD_up']):
            samenum = True
        
    row['samestreet'] = samestreet
    row['samenum'] = samenum
    row['samespeed'] = samespeed
    row['edit_dist'] = Lv.distance(row['STREET'], row['STREET_up'])
    
    # Update Notes field based on if street and number are good from near analysis
    if samestreet and samenum and samespeed:
        row['Notes'] = 'all match'
    elif samestreet and samespeed and not samenum:
        row['Notes'] = 'number change'
    elif samestreet and samenum and not samespeed:
        row['Notes'] = 'match - speed limit changed'
    elif samestreet and not samenum and not samespeed:
        row['Notes'] = 'match - speed limit changed, bad number'
    elif not samestreet:
        if samespeed:
            row['Notes'] = 'different street'
        else:
            row['Notes'] = 'different street - speed limit changed'              
        
    return row
 

##########################
#  Call Functions Below  #
##########################

arcpy.Delete_management('in_memory\\near_table')
check_nearby_roads(updates_pts, weber_streets, weber_db)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))


print("Creating edit distance histogram ...")
df = pd.read_csv(r'C:\E911\WeberArea\Staging103\Speed_limit_working_folder\weber_neartable_final.csv')
plt.figure(figsize=(6,4))
plt.hist(df['edit_dist'], bins = np.arange(0, df['edit_dist'].max(), 1)-0.5, color='red', edgecolor='black')
plt.xticks(np.arange(0, df['edit_dist'].max(), 2))
plt.title('Streets/Updates Edit Distance Histogram')
plt.xlabel('Edit Distance')
plt.ylabel('Count')
plt.show()