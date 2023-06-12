# -*- coding: utf-8 -*-
"""
Created on Mon May 17 12:20:07 2021
@author: eneemann

Script to find addpts where an interstate segment or ramp is nearest street
- These can cause problems in QuickestRoute, where the routing engine sends
  the vehicle on the wrong route or ends it on a ramp/interstate segment
  
Original script took about 65 min to run on 110k points
"""

import arcpy
from arcpy import env
import os
import time
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

weber_db = r"C:\E911\WeberArea\Staging103\WeberSGB.gdb"
staging_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
env.workspace = weber_db
env.overwriteOutput = True

weber_streets = os.path.join(weber_db, "Streets_Map")
weber_addpts = "AddressPoints"    # Point to current addpts in weber_db
current_addpts = os.path.join(weber_db, weber_addpts)

today = time.strftime("%Y%m%d")

# Copy current address points into a working FC
working_addpts = os.path.join(staging_db, "zzz_interstate_AddPts_" + today)
arcpy.CopyFeatures_management(current_addpts, working_addpts)

# Add field to working FC for notes
arcpy.AddField_management(working_addpts, "Interstate", "TEXT", "", "", 50)

###############
#  Functions  #
###############

        
def check_nearby_roads(working, streets, gdb):
    """
    Function performs near table analysis to find the closest road to each address point.
    It then uses pandas dataframes to join address point and street attributes to near table.
    Calls 'logic_checks' function to compare address point and street attributes.
    This searches for address points whose nearest street is an interstate or ramp segment.
    Then, it flags those address points with a comment in the "Interstate" field
    Results are exported to 'interstate_final.csv', which can later be joined back to the
    address points layer using the 'IN_FID' field to update the 'Notes' field in a FC.
    """
    func_start_time = time.time()
    # Need to make a layer from possible address points feature class here
    arcpy.MakeFeatureLayer_management(working, "working_lyr")
    result = arcpy.GetCount_management("working_lyr")
    total = int(result.getOutput(0))
    print("Working layer feature count: {}".format(total))

    # Create table name (in memory) for neartable
    neartable = 'in_memory\\near_table'
    # Perform near table analysis
    print("Generating near table ...")
    arcpy.GenerateNearTable_analysis ("working_lyr", streets, neartable, '400 Meters', 'NO_LOCATION', 'NO_ANGLE', 'CLOSEST')
    print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(neartable)))
    
    # Convert neartable to pandas dataframe
    neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
    near_df =pd.DataFrame(data = neartable_arr)
    print(near_df.head(5).to_string())
    
    # Convert address points to pandas dataframe
    addpt_fields = ['OID@', 'FullAdd', 'Base', 'Interstate']
    addpts_arr = arcpy.da.FeatureClassToNumPyArray(working, addpt_fields)
    addpts_df =pd.DataFrame(data = addpts_arr)
    print(addpts_df.head(5).to_string())
    
    # Convert roads to pandas dataframe
    street_fields = ['OID@', 'HWYNAME', 'STREETTYPE', 'STREET']
    streets_arr = arcpy.da.FeatureClassToNumPyArray(streets, street_fields)
    streets_df =pd.DataFrame(data = streets_arr)
    print(streets_df.head(5).to_string())
    
    # Join address points to near table
    join1_df = near_df.join(addpts_df.set_index('OID@'), on='IN_FID')
    print(join1_df.head(5).to_string())
    path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\interstate_join1.csv'
    join1_df.to_csv(path)
    
    # Join streets to near table
    join2_df = join1_df.join(streets_df.set_index('OID@'), on='NEAR_FID')
    print(join2_df.head(5).to_string())
    path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\interstate_join2.csv'
    join2_df.to_csv(path)
    
    # Apply logic_checks function to rows (axis=1) and output new df as CSV
    near_df_updated = join2_df.apply(logic_checks, axis=1)
    path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\interstate_updated.csv'
    near_df_updated.to_csv(path)
    
    # Create new dataframe that will be used to join to address point feature class with arcpy
    join_df = near_df_updated[['IN_FID', 'Interstate']]
    join_path = r'C:\E911\WeberArea\Staging103\Addpts_working_folder\weber_interstate_join.csv'
    join_df.to_csv(join_path)
        
    # Convert CSV output into table and join to working address points FC
    env.workspace = gdb
    env.qualifiedFieldNames = False
    if arcpy.Exists("interstate_join"):
        arcpy.Delete_management("interstate_join")
    arcpy.TableToTable_conversion(join_path, gdb, "interstate_join")
    joined_table = arcpy.AddJoin_management(working, "OBJECTID", "interstate_join", "IN_FID")
    if arcpy.Exists(working + "_final"):
        arcpy.Delete_management(working + "_final")
    # Copy joined table to "_final" feature class
    # This is a copy of the address points feature class with new joined fields
    arcpy.CopyFeatures_management(joined_table, working + "_final")
                                 
    print("Time elapsed in 'check_nearby_roads' function: {:.2f}s".format(time.time() - func_start_time))
    
    
def logic_checks(row):
    """
    Function calculates a value for 'Interstate' field by checking if the nearby
    road segment is and interstate or ramp segment.
    """

    if row['HWYNAME'] == 'I-15':
        row['Interstate'] = 'I-15'
    elif row['HWYNAME'] == 'I-80':
        row['Interstate'] = 'I-80'
    elif row['HWYNAME'] == 'I-84':
        row['Interstate'] = 'I-84'
    elif row['STREETTYPE'] == 'RAMP':
        row['Interstate'] = 'Ramp'
    
    return row
    

##########################
#  Call Functions Below  #
##########################

arcpy.Delete_management('in_memory\\near_table')
check_nearby_roads(working_addpts, weber_streets, staging_db)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))

