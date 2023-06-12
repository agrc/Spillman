# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 14:21:02 2021
@author: eneemann

EMN: On 21 Jun 2021, created initial script from StGeorge to copy files to be updated
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

staging_db = r"C:\E911\UintahBasin\UB_Staging.gdb"
wgs84_db = r"C:\E911\UintahBasin\UintahBasin_WGS84.gdb"

# Get list of files to project and copy to staging GDB
# FCs_to_project = ["address_points", "citycodes", "common_places", "fire_zones",
#                   "streets", "MZ_Zones", "municipalities"]

#FCs_dict = {"UintahBasinCityCodes": "UB_CityCodes",
##            "UintahBasinFire": "UB_Fire",
##            "UintahBasinEMS": "UB_EMS",
##            "UintahBasinLaw": "UB_Law",
##            "UintahBasinMZ": "UB_MZ",
#            "UintahBasin_CommonPlaces": "UB_CP",
#            "UintahBasinStreets": "UB_Streets"}

# FCs_dict = {"UintahBasin_CommonPlaces": "UB_CP",
#             "UintahBasinStreets": "UB_Streets"}

FCs_dict = {"UintahBasinCityCodes": "UB_CityCodes",
            "UintahBasinFire": "UB_Fire",
            "UintahBasinEMS": "UB_EMS",
            "UintahBasinLaw": "UB_Law",
            "UintahBasinMZ": "UB_MZ",
            "UintahBasin_CommonPlaces": "UB_CP",
            "UintahBasinStreets": "UB_Streets"}

# FCs_to_project = ["address_points", "citycodes",
#                   "common_places", "ems_zones",
#                   "fire_zones", "law_zones", "streets", "MZ_Zones",
#                   "streets_CAD", "municipalities",
#                   "common_places_Exits", "common_places_Mileposts"]

    
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
