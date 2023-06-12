# -*- coding: utf-8 -*-
"""
Created on Thu Dec 16 08:23:48 2021

@author: eneemann

"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

sanjuan_db = r"C:\E911\San Juan\SanJuan_Geovalidation_20210527.gdb"
staging_db = r"C:\E911\San Juan\SanJuan_Staging.gdb"
env.workspace = sanjuan_db
env.overwriteOutput = True

sanjuan_streets = os.path.join(sanjuan_db, "Streets")
sanjuan_addpts = "StG_AddPts_update_20211108"    # Point to current addpts in staging_db
current_addpts = os.path.join(staging_db, sanjuan_addpts)

today = time.strftime("%Y%m%d")
new_addpts = "AddressPoints_SGID_export_" + today


###############
#  Functions  #
###############


def get_SGID_addpts(out_db, new_pts):
    SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
    sgid_pts = os.path.join(SGID, "SGID.LOCATION.AddressPoints")
    if arcpy.Exists(new_pts):
        arcpy.Delete_management(new_pts)
    where_SGID = "CountyID = '49037'"   # San Juan County
    print("Exporting SGID address points to: {}".format(new_pts))
    arcpy.FeatureClassToFeatureClass_conversion (sgid_pts, out_db, new_pts, where_SGID)
  

    

##########################
#  Call Functions Below  #
##########################

get_SGID_addpts(staging_db, new_addpts)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))