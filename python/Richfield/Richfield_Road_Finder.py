# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 16:10:21 2019
@author: eneemann
Script to detect possible new street segments by comparing new data to current data

20 Nov 2019: Created initial version of code (EMN).
"""

import arcpy
from arcpy import env
import os
import time


# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

staging_db = r"C:\E911\RichfieldComCtr\richfield_staging.gdb"
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
current_streets = os.path.join(staging_db, "streets_update_20220523")
sgid_roads = os.path.join(SGID, "SGID.TRANSPORTATION.Roads")
env.workspace = staging_db
env.overwriteOutput = True

# Export roads from SGID into new FC based on desired counties
today = time.strftime("%Y%m%d")
export_roads = os.path.join(staging_db, "Roads_SGID_export_" + today)

# Create a 10m buffer around current streets data to use for selection
roads_buff = os.path.join(staging_db, "temp_roads_buffer")
if arcpy.Exists(roads_buff):
    arcpy.Delete_management(roads_buff)
print("Buffering {} ...".format(current_streets))
arcpy.Buffer_analysis(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# Select and export roads with centroids outside of the current streets buffer
#fips_list = ('49015', '49017', '49023', '49025', '49027', '49031', '49039', '49041', '49055')
fips_list = ('49015', '49017', '49023', '49025', '49027', '49031', '49039') # Exclude Sevier and Wayne
where_SGID = f"COUNTY_L IN {fips_list} OR COUNTY_R IN {fips_list}"      # All Relevant counties for Richfield
print(where_SGID)

## Use these two lines for checking against local data
#sgid_roads = r'C:\E911\RichfieldComCtr\richfield_staging.gdb\WayneCoRds_20211109'
#arcpy.MakeFeatureLayer_management(sgid_roads, "sgid_roads_lyr")


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