# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 16:10:21 2019
@author: eneemann
Script to detect possible new street segments by comparing new data to current data

22 Jul 2019: Created initial version of code (EMN).
"""

import arcpy
from arcpy import env
import os
import time


# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

today = time.strftime("%Y%m%d")
staging_db = r"C:\E911\StGeorgeDispatch\StGeorge_Staging.gdb"
county_db = r"\\itwfpcap2\AGRC\agrc\data\county_obtained\Washington\Washington20230517.gdb"
# current_streets = os.path.join(staging_db, "StG_Streets_update_" + today)
current_streets = os.path.join(staging_db, "StG_Streets_update_20230524")
county_roads = os.path.join(county_db, "WashCo_RoadCenterlines")
# county_roads = os.path.join(staging_db, "Stg_county_roads_to_review_20230517")
env.workspace = staging_db
env.overwriteOutput = True

# Create a 10m buffer around current streets data to use for selection
roads_buff = os.path.join(staging_db, "temp_roads_buffer")
if arcpy.Exists(roads_buff):
    arcpy.Delete_management(roads_buff)
print("Buffering {} ...".format(current_streets))
arcpy.Buffer_analysis(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# Select and export roads with centroids outside of the current streets buffer
#where_county = "COUNTY_L IN ('49053') OR COUNTY_R IN ('49053')"      # Washington County
if arcpy.Exists("county_roads_lyr"):
    arcpy.Delete_management("county_roads_lyr")
arcpy.MakeFeatureLayer_management(county_roads, "county_roads_lyr")
print("county roads layer feature count: {}".format(arcpy.GetCount_management("county_roads_lyr")))
arcpy.SelectLayerByLocation_management("county_roads_lyr", "HAVE_THEIR_CENTER_IN", roads_buff, "", "", "INVERT")
outname = os.path.join(staging_db, "county_roads_to_review_" + today)
arcpy.CopyFeatures_management("county_roads_lyr", outname)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))