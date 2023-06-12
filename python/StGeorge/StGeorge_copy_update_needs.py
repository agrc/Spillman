# -*- coding: utf-8 -*-
"""
Created on Fri Feb 19 16:42:02 2021
@author: eneemann

EMN: On 19 Feb 2021, created initial script from Salt Lake TOC to copy files to be updated

Need to copy over the latest 'StGeorge_Dispatch_Streets' into the staging database
to use for updates (don't have a WGS84 FC to reproject)

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

staging_db = r"C:\E911\StGeorgeDispatch\StGeorge_Staging.gdb"
wgs84_db = r"C:\E911\StGeorgeDispatch\StGeorgeDispatch_WGS84.gdb"

# Get list of files to project and copy to staging GDB
# FCs_to_project = ["address_points", "citycodes", "common_places", "fire_zones",
#                   "streets", "MZ_Zones", "municipalities"]

FCs_dict = {"StGeorge_Dispatch_CITYCD": "StG_CITYCD",
            "StGeorge_Dispatch_Fire_Zones": "StG_Fire_Zones",
            "StGeorge_Dispatch_EMS_Zones": "StG_EMS_Zones",
            "StGeorge_Dispatch_Law_Zones": "StG_Law_Zones",
            "StGeorge_Dispatch_Common_Place_Points": "StG_CP",
            "StGeorge_Dispatch_AddressPoints": "StG_AddPts",
            "StGeorge_Dispatch_POI": "StG_POI"}

# FCs_to_project = ["address_points", "citycodes",
#                   "common_places", "ems_zones",
#                   "fire_zones", "law_zones", "streets", "MZ_Zones",
#                   "streets_CAD", "municipalities",
#                   "common_places_Exits", "common_places_Mileposts"]

    
def project_to_UTM(input_features):
    env.workspace = wgs84_db
    sr = arcpy.SpatialReference(26912)
    print("Copy and projecting the following datasets to UTM for updates ...")
    for layer in input_features:
        print(layer)
        outname = f'{input_features[layer]}_update_{today}'
        full_out = os.path.join(staging_db, outname)
        arcpy.management.Project(layer, full_out, sr, "WGS_1984_(ITRF00)_To_NAD_1983")


project_to_UTM(FCs_dict)


#: Copy the latest UTM Streets data into the staging database
out_streets = f'StG_Streets_update_{today}' 
arcpy.conversion.FeatureClassToFeatureClass(r'C:\E911\StGeorgeDispatch\StGeorgeDispatch_UTM_good.gdb\StGeorge_Dispatch_Streets', staging_db, out_streets)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
