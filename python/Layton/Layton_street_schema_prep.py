# -*- coding: utf-8 -*-
"""
Created on Fri Oct 21 08:27:21 2022
@author: eneemann
Script to create streets schema template from Davis County data
    - Remove domains
    - Project to WGS84

21 Oct 2022: Created initial version of code (EMN).
"""

import os
import time
import arcpy
from arcpy import env

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

today = time.strftime("%Y%m%d")
new_db = r"C:\E911\Layton\Davis_new_road_schema.gdb"
davis_db = r"C:\E911\Layton\DavisCoDispatchData_working.gdb"
davis_roads = os.path.join(davis_db, "RoadCenterlines")
davis_no_domains = os.path.join(new_db, "DavisRoads_no_domains")
env.workspace = new_db
env.overwriteOutput = True

# Export roads from SGID into new FC based on intersection with county boundary
arcpy.management.CopyFeatures(davis_roads, davis_no_domains)

# Remove domains
for domain in arcpy.da.ListDomains(new_db):
   arcpy.DeleteDomain_management(new_db, domain.name)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
