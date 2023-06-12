# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 08:27:21 2020
@author: eneemann
Script to detect possible new street segments by comparing new data to current data

17 Jan 2020: Created initial version of code (EMN).
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
staging_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
weber_db = r"C:\E911\WeberArea\Staging103\WeberSGB.gdb"
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
current_streets = os.path.join(weber_db, "Streets_Map")
citycd = os.path.join(weber_db, "CityCodes")
sgid_roads = os.path.join(SGID, "SGID.TRANSPORTATION.Roads")
env.workspace = staging_db
env.overwriteOutput = True

# Export roads from SGID into new FC based on intersection with city codes layer
# First make layer from relevant counties (Weber and Morgan)
export_roads = os.path.join(staging_db, "Roads_SGID_export_" + today)
where_SGID = "COUNTY_L IN ('49057', '49029') OR COUNTY_R IN ('49057', '49029')"      # Weber and Morgan Counties
arcpy.management.MakeFeatureLayer(sgid_roads, "sgid_roads_lyr", where_SGID)
arcpy.management.CopyFeatures("sgid_roads_lyr", "temp_roads")
print("Selecting SGID roads to export by intersection with city codes ...")
arcpy.management.SelectLayerByLocation("temp_roads", "INTERSECT", citycd)
arcpy.management.CopyFeatures("temp_roads", export_roads)

if arcpy.Exists("temp_roads"):
    arcpy.management.Delete("temp_roads")

# Create a 10m buffer around current streets data to use for selection
roads_buff = os.path.join(staging_db, "temp_roads_buffer")
if arcpy.Exists(roads_buff):
    arcpy.management.Delete(roads_buff)
print("Buffering {} ...".format(current_streets))
arcpy.analysis.Buffer(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# Select and export roads with centroids outside of the current streets buffer
arcpy.management.MakeFeatureLayer(export_roads, "sgid_export_lyr")
print("SGID roads layer feature count: {}".format(arcpy.management.GetCount("sgid_export_lyr")))
arcpy.management.SelectLayerByLocation("sgid_export_lyr", "HAVE_THEIR_CENTER_IN", roads_buff,
                                                     "", "", "INVERT")
outname = os.path.join(staging_db, "SGID_roads_to_review_" + today)
arcpy.management.CopyFeatures("sgid_export_lyr", outname)

arcpy.management.Delete(export_roads)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))