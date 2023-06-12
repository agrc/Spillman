# -*- coding: utf-8 -*-
"""
Created on Mon Mar 5 08:39:07 2019
@author: eneemann
Script to detect possible address points by comparing new data to current data

Need to call get_SGID_addpts function first, then comment out the call and run the script
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
today = time.strftime("%Y%m%d")
print("The script start time is {}".format(readable_start))

weber_db = r"C:\E911\WeberArea\Staging103\WeberSGB.gdb"
staging_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
env.workspace = staging_db
env.overwriteOutput = True
env.qualifiedFieldNames = False

real_streets = os.path.join(weber_db, "Streets_Map")
# real_streets = os.path.join(staging_db, "zzz_new_subdiv_st_20200810")
temp_streets = os.path.join(staging_db, f"St_Map_working_{today}")
working_streets = os.path.join(staging_db, f"St_Map_working_UTM_{today}")
st_endpoints = os.path.join(staging_db, f"St_Map_endpoints_{today}")

arcpy.CopyFeatures_management(real_streets, temp_streets)

sr = arcpy.SpatialReference(26912)
arcpy.Project_management(temp_streets, working_streets, sr, "WGS_1984_(ITRF00)_To_NAD_1983")
oid_fieldname = arcpy.Describe(working_streets).OIDFieldName
print(f"OID field name:  {oid_fieldname}")



# # Add field to working FC for notes
# arcpy.AddField_management(working_addpts, "Notes", "TEXT", "", "", 50)
# arcpy.AddField_management(working_addpts, "Street", "TEXT", "", "", 50)


arcpy.management.FeatureVerticesToPoints(working_streets, st_endpoints, "BOTH_ENDS")


# Create table name (in memory) for neartable
neartable = 'in_memory\\near_table'
# Perform near table analysis
print("Generating near table ...")
arcpy.analysis.GenerateNearTable(st_endpoints, st_endpoints, neartable, '4 Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 6, 'PLANAR')
print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(neartable)))

# Convert neartable to pandas dataframe
neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
near_df = pd.DataFrame(data = neartable_arr)
print(near_df.head(5).to_string())

# Convert endpts to pandas dataframe
endpt_fields = [oid_fieldname, 'ORIG_FID', 'STREET']
endpt_arr = arcpy.da.FeatureClassToNumPyArray(st_endpoints, endpt_fields)
endpt_df = pd.DataFrame(data = endpt_arr)
print(endpt_df.head(5).to_string())

# Join end points to near table
join1_df = near_df.join(endpt_df.set_index(oid_fieldname), on='NEAR_FID')
print(join1_df.head(5).to_string())
# path = r'C:\E911\WeberArea\Staging103\snapping_join1.csv'
# join1_df.to_csv(path)


sorted_df = join1_df.sort_values('NEAR_DIST')
sorted_path = r'C:\E911\WeberArea\Staging103\snapping_test_sorted.csv'
sorted_df.to_csv(sorted_path)

non_zero = sorted_df[sorted_df.NEAR_DIST != 0]
non_zero_path = r'C:\E911\WeberArea\Staging103\snapping_test_nonzero.csv'
non_zero.to_csv(non_zero_path)

no_dups = non_zero.drop_duplicates('ORIG_FID')
no_dups_path = r'C:\E911\WeberArea\Staging103\snapping_test_nodups.csv'
no_dups.to_csv(no_dups_path)

# Convert CSV output into table and join to working address points FC
if arcpy.Exists("neartable_join"):
    arcpy.Delete_management("neartable_join")
arcpy.TableToTable_conversion(no_dups_path, staging_db, "neartable_join")
# joined_table = arcpy.AddJoin_management(working_streets, oid_fieldname, "neartable_join", "IN_FID")
joined_table = arcpy.AddJoin_management(temp_streets, oid_fieldname, "neartable_join", "ORIG_FID")
if arcpy.Exists(f'{temp_streets}_final'):
    arcpy.Delete_management(f'{temp_streets}_final')
# Copy joined table to "_final" feature class
# This is a copy of the streets feature class with new joined fields
arcpy.CopyFeatures_management(joined_table, f'{temp_streets}_final')


arcpy.Delete_management('in_memory\\near_table')


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))


# print("Creating edit distance histogram ...")
# df = pd.read_csv(r'C:\E911\WeberArea\Staging103\snapping_test_nodups.csv')
# plt.figure(figsize=(6,4))
# plt.hist(df['edit_dist'], bins = np.arange(0, df['edit_dist'].max(), 1)-0.5, color='red', edgecolor='black')
# plt.xticks(np.arange(0, df['edit_dist'].max(), 2))
# plt.title('Address/Street Edit Distance Histogram')
# plt.xlabel('Edit Distance')
# plt.ylabel('Count')
# plt.show()
