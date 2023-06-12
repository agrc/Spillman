# -*- coding: utf-8 -*-
"""
Created on Wed Sep 9 13:21:07 2020
@author: eneemann
Script to add common name information to unit address points

Need to call get_SGID_addpts function first, then comment out the call and run the script
"""

# Addpts query down to units and Null CommonName or LandmarkName

# Addpts neartable with commonnames

# Join tables together: addpts, neartable, commonnames

# Perform logic checks
#   Sort by distance
#   Check levenshtein of Base (appt) and FullAddr (CN)

import arcpy
from arcpy import env
import os
import time
import pandas as pd
import numpy as np
from Levenshtein import StringMatcher as Lv
from matplotlib import pyplot as plt
from tqdm import tqdm

# Initialize the tqdm progress bar tool
tqdm.pandas()

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

weber_db = r"C:\E911\WeberArea\Staging103\WeberSGB.gdb"
staging_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
env.workspace = weber_db
env.overwriteOutput = True

common_names = os.path.join(weber_db, "CommonNames")
weber_addpts = "AddressPoints_SGB_20200909"    # Point to current addpts in staging_db
current_addpts = os.path.join(staging_db, weber_addpts)

today = time.strftime("%Y%m%d")

# Copy current address points into a working FC
working_addpts = os.path.join(staging_db, "zzz_AddPts_CN_working_" + today)
arcpy.CopyFeatures_management(current_addpts, working_addpts)

# Add field to working FC for notes
arcpy.AddField_management(working_addpts, "Notes", "TEXT", "", "", 50)

###############
#  Functions  #
###############
            
            
def check_nearby_CNs(working, CNs, gdb):
    """
    Function performs near table analysis to find 10 closest common names w/i 800m of each address point.
    It then uses pandas dataframes to join address point and common name attributes to near table.
    Calls 'logic_checks' function to compare address point and common name attributes.
    This searches for address point addresses that match near common name addresses.
    Based on appropriate results, Notes field is populated with one of the following:
        - 'good common name'
        - 'possible address typo'
        - 'likely bad common name'
    Results are exported to 'neartable_final.csv', which can later be joined back to the
    address points layer using the 'IN_FID' field to update the 'Notes' field in a FC.
    """
    func_start_time = time.time()
    # look at features that aren't name duplicates
    where_clause = "(UnitType IS NOT NULL OR UnitID IS NOT NULL) AND (CommonName IS NULL OR LandmarkName IS NULL)"
    # Need to make a layer from possible address points feature class here
    arcpy.MakeFeatureLayer_management(working, "working_addpts", where_clause)
    result = arcpy.GetCount_management("working_addpts")
    total = int(result.getOutput(0))
    print("Working layer feature count: {}".format(total))

    # Create table name (in memory) for neartable
    neartable = 'in_memory\\near_table'
    # Perform near table analysis
    print("Generating near table ...")
    arcpy.GenerateNearTable_analysis ("working_addpts", CNs, neartable, '800 Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 10, 'GEODESIC')
    print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(neartable)))
    
    # Convert neartable to pandas dataframe
    neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
    near_df = pd.DataFrame(data = neartable_arr)
    print(near_df.head(5).to_string())
    
    # Convert address points to pandas dataframe
    addpt_fields = ['OID@', 'Base', 'LandmarkName', 'UnitType', 'UnitID', 'Notes']
    addpts_arr = arcpy.da.FeatureClassToNumPyArray(working, addpt_fields)
    addpts_df =pd.DataFrame(data = addpts_arr)
    print(addpts_df.head(5).to_string())
    
    # Convert common names to pandas dataframe
    CN_fields = ['OID@', 'CommonName', 'FullAddr']
    CNs_arr = arcpy.da.FeatureClassToNumPyArray(CNs, CN_fields)
    CNs_df =pd.DataFrame(data = CNs_arr)
    print(CNs_df.head(5).to_string())
    
    # Join address points to near table
    join1_df = near_df.join(addpts_df.set_index('OID@'), on='IN_FID')
    print(join1_df.head(5).to_string())
    path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\CN_neartable_1.csv'
    join1_df.to_csv(path)
    
    # Join CNs to near table
    join2_df = join1_df.join(CNs_df.set_index('OID@'), on='NEAR_FID')
    print(join2_df.head(5).to_string())
    path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\CN_neartable_2.csv'
    join2_df.to_csv(path)
    
    # Apply logic_checks function to rows (axis=1) and output new df as CSV
    near_df_updated = join2_df.progress_apply(logic_checks, axis=1)
    path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\CN_neartable_updated.csv'
    near_df_updated.to_csv(path)
    
    # Separate rows with a good nearby CN into a separate dataframe
    is_goodCN = near_df_updated['goodCN'] == True      # Create indexes
    # Grab rows with good CNs, sort by near rank from near table, remove address point duplicates
    # This preserves the only the record with the nearest good CN to the address point
#    goodCNs_df = near_df_updated[is_goodCN].sort_values('NEAR_RANK').drop_duplicates('IN_FID')
    goodCNs_df = near_df_updated[is_goodCN].sort_values('NEAR_RANK')
    
    # Separate rows with no good nearby CN into a separate dataframe
    not_goodCN = near_df_updated['goodCN'] == False    # Create indexes
    # Grab rows with bad CNs, sort by near rank from near table, remove address point duplicates
    # This preserves the only the record with the nearest bad CN to the address point
#    badCNs_df = near_df_updated[not_goodCN].sort_values('NEAR_RANK').drop_duplicates('IN_FID')
    badCNs_df = near_df_updated[not_goodCN].sort_values('NEAR_RANK')
    
    # Combine good and bad CN dataframes, sort so good CNs are at the top, then remove duplicates of address points
    # If a good CNs are found, nearest one will be used; otherwise nearest bad CN will be used ("near CN not found")
#    filtered_df = goodCNs_df.append(badCNs_df).sort_values('goodCN', ascending=False).drop_duplicates('IN_FID')
    # Sort by multiple columns (goodCN, then goodnum) to ensure 2nd nearest CN with good num will get used
#    filtered_df = goodCNs_df.append(badCNs_df).sort_values(['goodCN', 'goodnum'], ascending=False).drop_duplicates('IN_FID')
    filtered_df = goodCNs_df.append(badCNs_df).sort_values(['IN_FID','goodCN', 'edit_dist', 'NEAR_DIST'],
                                       ascending=[True,False, True, True])
    filtered_df.to_csv(r'C:\E911\WeberArea\Staging103\Addpts_working_folder\CN_neartable_all.csv')
    # Re-sort data frame on address point ID for final data set
    final_df = filtered_df.drop_duplicates('IN_FID')
    path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\CN_neartable_final.csv'
    final_df.to_csv(path)
    
    
    # Create new dataframe that will be used to join to address point feature class with arcpy
    join_df = final_df[['IN_FID', 'Notes', 'CommonName', 'FullAddr', 'edit_dist']]
    # Rename 'Notes' column to 'Notes_near' -- prevents conflict with 'Notes' field already in FC table
    join_df.columns = ['IN_FID', 'Notes_near', 'CommonName', 'FullAddr', 'edit_dist']
    join_path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\CN_neartable_join.csv'
    join_df.to_csv(join_path)
        
    # Convert CSV output into table and join to working address points FC
    env.workspace = gdb
    env.qualifiedFieldNames = False
    if arcpy.Exists("CN_neartable_join"):
        arcpy.Delete_management("CN_neartable_join")
    arcpy.TableToTable_conversion(join_path, gdb, "CN_neartable_join")
    joined_table = arcpy.AddJoin_management(working, "OBJECTID", "CN_neartable_join", "IN_FID")
    if arcpy.Exists(working + "_final"):
        arcpy.Delete_management(working + "_final")
    # Copy joined table to "_final" feature class
    # This is a copy of the address points feature class with new joined fields
    arcpy.CopyFeatures_management(joined_table, working + "_final")
                                                          
    # Update 'Notes' field in working address points with joined table notes
    # ArcPy makes a mess of the field names after the join, so we need to make
    # sure the proper fields are pulled and updated
#    field1 = os.path.basename(working) + "_Notes"
#    field2 = "neartable_join" + "_Notes_near"
#    fields = [field1, field2]
#    for field in fields:
#        print(field)
    fields = ['Notes', 'Notes_near']
    with arcpy.da.UpdateCursor(working + "_final", fields) as cursor:
        print("Looping through rows in {} to update 'Notes' field ...".format(os.path.basename(working) + "_final"))
        for row in cursor:
            # Only update 'Notes' field if joined 'Near_notes' not null
            if row[1] is not None:
                if len(row[1]) > 0:
                    row[0] = row[1]
            cursor.updateRow(row)
                                 
    print("Time elapsed in 'check_nearby_CNs' function: {:.2f}s".format(time.time() - func_start_time))
    
    
def logic_checks(row):
    """
    Function calculates new values for 'Notes' field by comparing address
    point to nearby CNs' name and address range
    """
    goodCN = False
    
    if row['Base'] == row['FullAddr']:
        goodCN = True

    # Update Notes field based on if CN and number are good from near analysis
    if goodCN:
        row['Notes'] = 'good common name'
    else:
        row['Notes'] = 'likely bad common name'
    
    row['goodCN'] = goodCN
    row['edit_dist'] = Lv.distance(row['Base'], row['FullAddr'])
    # Check edit distance for pairs that might have typos, predir, or sufdir errors
    if row['Notes'] == 'likely bad common name' and row['edit_dist'] in (1, 2):
        row['Notes'] = 'possible address typo'
    
    return row
    

##########################
#  Call Functions Below  #
##########################


arcpy.Delete_management('in_memory\\near_table')
check_nearby_CNs(working_addpts, common_names, staging_db)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))


# Plot histogram of Edit Distances
print("Creating edit distance histogram ...")
df = pd.read_csv(r'C:\E911\WeberArea\Staging103\Addpts_working_folder\CN_neartable_final.csv')
plt.figure(figsize=(6,4))
plt.hist(df['edit_dist'], bins = np.arange(0, df['edit_dist'].max(), 1)-0.5, color='red', edgecolor='black')
plt.xticks(np.arange(0, df['edit_dist'].max(), 2))
plt.title('Address/CN Edit Distance Histogram')
plt.xlabel('Edit Distance')
plt.ylabel('Count')
plt.show()

df['edit_dist'].max()

# Plot bar chart of Notes column
print("Creating notes bar chart ...")
plt.figure(figsize=(6,4))
plt.hist(df['Notes'], color='lightblue', edgecolor='black')
# plt.xticks(np.arange(0, df['Notes'].max(), 2))
plt.xticks(rotation='vertical')
plt.title('Address Point Categories')
plt.xlabel('Category')
plt.ylabel('Count')
plt.show()

df.groupby('Notes').count()