# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 12:22:08 2019

@author: eneemann
"""

# Import Libraries
import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")
#-----------------------Start Main Code------------------------#

## Prep data for network

# Set up variables
database = r"C:\Users\eneemann\Documents\ArcGIS\Projects\MyFirstProject\UHP_FATPOT_update.gdb"
env.workspace = database

fclist = arcpy.ListFeatureClasses()
fclist.sort()

for fc in fclist:
    print("The spatial reference of {0} is: {1}".format(fc, arcpy.Describe(fc).spatialReference.name))
    
for fc in fclist:
    print(fc)




#-----------------------End Main Code------------------------#
print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))