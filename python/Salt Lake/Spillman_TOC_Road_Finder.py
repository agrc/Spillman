# -*- coding: utf-8 -*-
"""
Created on Thu Jan 09 16:00:21 2020
@author: eneemann
Script to detect possible new street segments by comparing new data to current data

9 Jan 2020: Created initial version of code (EMN).
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
staging_db = r"C:\E911\TOC\TOC_Staging.gdb"
TOC_db = r"C:\E911\TOC\TOC_Spillman_WGS_84.gdb"
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
current_streets = os.path.join(staging_db, "TOC_Streets_updates_20210121")
citycd = os.path.join(TOC_db, "TOC_CITYCD")
sgid_roads = os.path.join(SGID, "SGID.TRANSPORTATION.Roads")
# roads_lyr = os.path.join(staging_db, 'SGID_roads_try2_20200717')
env.workspace = staging_db
env.overwriteOutput = True

# Export roads from SGID into new FC based on intersection with city codes layer
# First make layer from relevant counties (Salt Lake, Utah, Tooele, Davis, Juab, Sanpete, Carbon, Wasatch, Summit, Morgan)
export_roads = os.path.join(staging_db, "Roads_SGID_export_" + today)
where_SGID = "COUNTY_L IN ('49035', '49049', '49011', '49045', '49023', '49039', '49007', '49051', '49043', '49029') OR COUNTY_R IN ('49035', '49049', '49011', '49045', '49023', '49039', '49007', '49051', '49043', '49029')"      # Washington County
arcpy.MakeFeatureLayer_management(sgid_roads, "sgid_roads_lyr", where_SGID)
# arcpy.MakeFeatureLayer_management(roads_lyr, "sgid_roads_lyr")
print("Selecting SGID roads to export by intersection with city codes ...")
arcpy.SelectLayerByLocation_management("sgid_roads_lyr", "INTERSECT", citycd)

arcpy.CopyFeatures_management("sgid_roads_lyr", export_roads)

# # Create a 10m buffer around current streets data to use for selection
# roads_buff = os.path.join(staging_db, "temp_roads_buffer")
# if arcpy.Exists(roads_buff):
#     arcpy.Delete_management(roads_buff)
# print("Buffering {} ...".format(current_streets))
# arcpy.Buffer_analysis(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# # Select and export roads with centroids outside of the current streets buffer
# arcpy.MakeFeatureLayer_management(export_roads, "sgid_export_lyr")
# print("SGID roads layer feature count: {}".format(arcpy.GetCount_management("sgid_export_lyr")))
# arcpy.SelectLayerByLocation_management("sgid_export_lyr", "HAVE_THEIR_CENTER_IN", roads_buff,
#                                                      "", "", "INVERT")
# outname = os.path.join(staging_db, "SGID_roads_to_review_" + today)
# arcpy.CopyFeatures_management("sgid_export_lyr", outname)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))