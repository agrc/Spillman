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
# county_gdb = r"\\itwfpcap2\AGRC\agrc\data\county_obtained\Sevier\SevierCo_20230415.gdb" # Sevier County data
# county_gdb = r"\\itwfpcap2\AGRC\agrc\data\county_obtained\Wayne\WayneCo_20220414.gdb" # Wayne County data
# county_gdb = r"\\itwfpcap2\AGRC\agrc\data\county_obtained\Piute\PiuteCo_20230415.gdb" # Piute County data
county_gdb = r"C:\E911\RichfieldComCtr\2 Data From County\Wanda_20230517\WayneCoRds_20230517.gdb" # Wayne County data
current_streets = os.path.join(staging_db, "streets_update_20230515")
# county_data = os.path.join(county_gdb, "SC911AddressRds_041723") # Sevier County data
county_data = os.path.join(county_gdb, "WayneCoRds_20230517") # Wayne County data
# county_data = os.path.join(county_gdb, "Roads") # Piute County data
env.workspace = staging_db
env.overwriteOutput = True

# Export roads from county_gdb into new FC based on desired counties
today = time.strftime("%Y%m%d")
export_roads = os.path.join(staging_db, "Roads_SGID_export_" + today)

# Create a 10m buffer around current streets data to use for selection
roads_buff = os.path.join(staging_db, "temp_roads_buffer")
if arcpy.Exists(roads_buff):
    arcpy.Delete_management(roads_buff)
print("Buffering {} ...".format(current_streets))
arcpy.Buffer_analysis(current_streets, roads_buff, "10 Meters", "FULL", "ROUND", "ALL")

# Use these two lines for checking against local data
county_roads = os.path.join(county_gdb, county_data)
arcpy.MakeFeatureLayer_management(county_roads, "county_roads_lyr")


#arcpy.MakeFeatureLayer_management(county_roads, "county_roads_lyr", where_SGID)
print("County roads layer feature count: {}".format(arcpy.GetCount_management("county_roads_lyr")))
arcpy.SelectLayerByLocation_management("county_roads_lyr", "HAVE_THEIR_CENTER_IN", roads_buff,
                                                     "", "", "INVERT")
outname = os.path.join(staging_db, "county_roads_to_review_" + today)
arcpy.CopyFeatures_management("county_roads_lyr", outname)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))