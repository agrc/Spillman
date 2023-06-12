# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 09:46:21 2019
@author: eneemann
Script to detect possible new street segments by comparing new data to current data

28 Oct 2019: Created initial version of code (EMN).
"""

import arcpy
from arcpy import env
import os
import time


# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

staging_db = r"C:\E911\MillardCo\Millard_Staging.gdb"
# local_db = r"C:\E911\MillardCo\Britt_data_20200908\Millard_20200908.gdb"
current_streets = os.path.join(staging_db, "Millard_Streets_update_20220919")
local_roads = os.path.join(staging_db, "Britt_Millard_Roads_Sep2022")
env.workspace = staging_db
env.overwriteOutput = True

# Export roads from SGID into new FC based on desired counties
today = time.strftime("%Y%m%d")

# Create a 10m buffer around current streets data to use for selection
roads_buff = os.path.join(staging_db, "temp_roads_buffer")
if arcpy.Exists(roads_buff):
    arcpy.Delete_management(roads_buff)
print("Buffering {} ...".format(current_streets))
arcpy.Buffer_analysis(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# Select and export roads with centroids outside of the current streets buffer
arcpy.MakeFeatureLayer_management(local_roads, "local_roads_lyr")
print("local roads layer feature count: {}".format(arcpy.GetCount_management("local_roads_lyr")))
arcpy.SelectLayerByLocation_management("local_roads_lyr", "HAVE_THEIR_CENTER_IN", roads_buff,
                                                     "", "", "INVERT")
outname = os.path.join(staging_db, "local_roads_to_review_" + today)
arcpy.CopyFeatures_management("local_roads_lyr", outname)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))