# -*- coding: utf-8 -*-
"""
Created on Sun Apr 21 20:31:02 2021
@author: eneemann

EMN: On 44 Apr 2021, created initial script from St George to copy files to be updated
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

staging_db = r"C:\E911\Beaver Co\Beaver_Staging.gdb"
wgs84_db = r"C:\E911\Beaver Co\Beaver_Spillman_WGS84.gdb"

# Get list of files to project and copy to staging GDB
# FCs_to_project = ["address_points", "citycodes", "common_places", "fire_zones",
#                   "streets", "MZ_Zones", "municipalities"]

FCs_dict = {"CityCodes": "CityCodes",
           "Streets": "Streets",
           "Fire_zone": "Fire_zone",
           "Ems_zone": "Ems_zone",
           "Law_zone": "Law_zone",
           "Law_area": "Law_area",
           "CommonPlaces": "CommonPlaces",
           "AddressPoints": "AddressPoints"}

# FCs_dict = {"Streets": "Streets",
#             "CommonPlaces": "CommonPlaces",
#             "AddressPoints": "AddressPoints"}

#FCs_dict = {"CityCodes": "CityCodes",
#            "Fire_zone": "Fire_zone",
#            "Ems_zone": "Ems_zone",
#            "Law_zone": "Law_zone",
#            "Law_area": "Law_area"}

    
def project_to_UTM(input_features):
    today = time.strftime("%Y%m%d")
    env.workspace = wgs84_db
    sr = arcpy.SpatialReference(26912)
    print("Copy and projecting the following datasets to UTM for updates ...")
    for layer in input_features:
        print(layer)
        outname = f'{input_features[layer]}_update_{today}'
        full_out = os.path.join(staging_db, outname)
        arcpy.management.Project(layer, full_out, sr, "WGS_1984_(ITRF00)_To_NAD_1983")


project_to_UTM(FCs_dict)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
