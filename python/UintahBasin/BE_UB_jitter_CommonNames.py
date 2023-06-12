# -*- coding: utf-8 -*-
"""
Created on Wed Mar 8 14:29:17 2023

@author: eneemann
Script to "jitter" the coordinates of BoxElder/UintahBasin POIs to ensure that
POIs associated with the same address have different coordinates.
"""

import arcpy
import os
import time
import random

import os
print(os.environ['CONDA_DEFAULT_ENV'])

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))

######################
#  Set up variables  #
######################

# Set up databases
geo_db = r"C:\E911\UtahDPS Schemas\BE_UB_Geovalidation_WGS84.gdb"
staging_db = r"C:\E911\UtahDPS Schemas\BE_UB_Staging.gdb"

arcpy.env.workspace = staging_db
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False

today = time.strftime("%Y%m%d")

# common_names = os.path.join(geo_db, 'CommonNames')
# common_names_update = os.path.join(staging_db, 'CommonName_update_' + today + '_jitter')

common_names = os.path.join(geo_db, 'RoadFeatures')
common_names_update = os.path.join(staging_db, 'RoadFeatures_update_' + today + '_jitter')

print(f"Copying CommonNames to: {common_names_update} ...")
arcpy.management.Copy(common_names, common_names_update)

def jitter(val):
    new_val = val + 0.0000003*random.randint(-9,9)
    return new_val    


field_list = ['SHAPE@', 'SHAPE@X', 'SHAPE@Y']
with arcpy.da.UpdateCursor(common_names_update, field_list) as update_cursor:
    print("Looping through rows in FC ...")
    for row in update_cursor:
        row[1] = jitter(row[1])
        row[2] = jitter(row[2])
        update_cursor.updateRow(row)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
