# -*- coding: utf-8 -*-
"""
Created on Mon Apr 1 13:31:12 2019

@author: eneemann

- Adds necessary field to Beaver PSAP streets
EMN: On 1 Apr 2019, created script from Millard_prep_v3_0.
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

utm_db = r"C:\E911\Beaver Co\Beaver_Spillman_UTM.gdb"
env.workspace = utm_db
fc_layer = "Streets"
streets_fc_utm = os.path.join(utm_db, fc_layer)

# Add Spillman fields to feature class
arcpy.AddField_management(streets_fc_utm, "LZ_LEFT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "LZ_RIGHT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "LA_LEFT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "LA_RIGHT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "FZ_LEFT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "FZ_RIGHT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "EZ_LEFT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "EZ_RIGHT", "TEXT", "", "", 5)
arcpy.AddField_management(streets_fc_utm, "LOCATION", "TEXT", "", "", 20)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))










