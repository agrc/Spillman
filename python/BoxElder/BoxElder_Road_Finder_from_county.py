# -*- coding: utf-8 -*-
"""
Created on Thu Mar 31 09:15:21 2022
@author: eneemann
Script to detect possible new street segments by comparing new data to current data

31 Mar 2022: Created from Box Elder version of code that uses SGID data (EMN).
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
staging_db = r"C:\E911\Box Elder CO\BoxElder_Staging.gdb"
# SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
county = r"\\itwfpcap2\AGRC\agrc\data\county_obtained\BoxElder\BoxElder_20220922.gdb"
# current_streets = os.path.join(staging_db, "BoxElder_Streets_update_" + today)
current_streets = os.path.join(staging_db, "Streets_update_20220930")
county_roads = os.path.join(county, "ROADS")
env.workspace = staging_db
env.overwriteOutput = True

# Export roads from county into new FC based on desired counties
export_roads = os.path.join(staging_db, "Roads_SGID_export_" + today)

# Create a 10m buffer around current streets data to use for selection
roads_buff = os.path.join(staging_db, "temp_roads_buffer")
if arcpy.Exists(roads_buff):
    arcpy.Delete_management(roads_buff)
print("Buffering {} ...".format(current_streets))
arcpy.Buffer_analysis(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# Select and export roads with centroids outside of the current streets buffer
#where_SGID = "COUNTY_L IN ('49003') OR COUNTY_R IN ('49003')"      # Box Elder County
if arcpy.Exists("county_roads_lyr"):
    arcpy.Delete_management("county_roads_lyr")
arcpy.MakeFeatureLayer_management(county_roads, "county_roads_lyr")
print("county roads layer feature count: {}".format(arcpy.GetCount_management("county_roads_lyr")))
arcpy.SelectLayerByLocation_management("county_roads_lyr", "HAVE_THEIR_CENTER_IN", roads_buff, "", "", "INVERT")
outname = os.path.join(staging_db, "SGID_roads_to_review_" + today)
arcpy.CopyFeatures_management("county_roads_lyr", outname)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))