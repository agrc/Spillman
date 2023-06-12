# -*- coding: utf-8 -*-
"""
Created on Wed Mar 20 08:06:23 2019
@author: eneemann

9 Feb 2021: Created initial code from Spillman_TOC_prep_v3_0.py (EMN).  This version
is to be used with the new Geovalidation schema.  Code was changed to update feature
class names, variables, geodatabases, etc.
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

#: Set up variables
geo_db = r"C:\E911\TOC\TOC_Geovalidation_WGS84.gdb"
out_dir = r'C:\E911\TOC\0 Table Build'
env.workspace = geo_db

FCs = ["LawZones", "LawAreas", "FireZones", "FireAreas", "EMSZones", "EMSAreas", "MiscZones"]

###############
#  Functions  #
###############

def prep_zone(fc):
    print(f'Working on {fc} ...')
    #: Add fields for centroid coordinates
    arcpy.management.AddField(fc, 'xcenter', 'DOUBLE')
    arcpy.management.AddField(fc, 'ycenter', 'DOUBLE')
    
    #: Calculate centroid coordinates
    print(f'Calculating centroid coordinates ...')
    arcpy.management.CalculateField(fc, 'xcenter', '!Shape!.centroid.X', "PYTHON3")
    arcpy.management.CalculateField(fc, 'ycenter', '!Shape!.centroid.Y', "PYTHON3")
    # arcpy.management.CalculateGeometryAttributes(fc, geometry_property, {length_unit}, {area_unit}, {coordinate_system}, {coordinate_format})
    
    #: Export to Shapefile
    print(f'Exporting to shapefile ...')
    arcpy.conversion.FeatureClassToFeatureClass(fc, out_dir, f'{fc}_{today}')


# Call Functions
for feature_class in FCs:
    prep_zone(feature_class)
    

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
