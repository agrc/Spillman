# -*- coding: utf-8 -*-
"""
Created on Sat Apr 24 13:26:21 2020
@author: eneemann
Script to detect possible new street segments by comparing new data to current data

25 Apr 2020: Created initial version of code (EMN) from St George version.
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
staging_db = r"C:\E911\Beaver Co\Beaver_Staging.gdb"
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
# current_streets = os.path.join(staging_db, "StG_Streets_update_" + today)
current_streets = os.path.join(staging_db, 'Streets_update_20221013')
sgid_roads = os.path.join(SGID, "SGID.TRANSPORTATION.Roads")
env.workspace = staging_db
env.overwriteOutput = True

# Export roads from SGID into new FC based on desired counties
export_roads = os.path.join(staging_db, "Roads_SGID_export_" + today)

# Create a 10m buffer around current streets data to use for selection
roads_buff = os.path.join(staging_db, "temp_roads_buffer")
if arcpy.Exists(roads_buff):
    arcpy.Delete_management(roads_buff)
print("Buffering {} ...".format(current_streets))
arcpy.Buffer_analysis(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# Select and export roads with centroids outside of the current streets buffer
if arcpy.Exists("sgid_roads_lyr"):
    arcpy.Delete_management("sgid_roads_lyr")
where_SGID = "COUNTY_L IN ('49001') OR COUNTY_R IN ('49001')"      # Beaver County
arcpy.MakeFeatureLayer_management(sgid_roads, "sgid_roads_lyr", where_SGID)
print("SGID roads layer feature count: {}".format(arcpy.GetCount_management("sgid_roads_lyr")))
arcpy.SelectLayerByLocation_management("sgid_roads_lyr", "HAVE_THEIR_CENTER_IN", roads_buff,
                                                     "", "", "INVERT")
outname = os.path.join(staging_db, "SGID_roads_to_review_" + today)
arcpy.CopyFeatures_management("sgid_roads_lyr", outname)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))