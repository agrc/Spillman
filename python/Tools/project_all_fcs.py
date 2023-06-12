import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

# Input variables
in_db = r"C:\E911\TOC\TOC_Geovalidation_WGS84.gdb"
out_db = r"C:\E911\TOC\TOC_Geovalidation_UTM.gdb"
sr = arcpy.SpatialReference(26912)

env.workspace = in_db
fclist = arcpy.ListFeatureClasses()


def project(input_features):
    print(f"Projecting the following datasets to {sr.name} ...")
    print(f"Output database: {out_db}")
    for layer in input_features:
        print(layer)
    arcpy.BatchProject_management(input_features, out_db, sr, "", "WGS_1984_(ITRF00)_To_NAD_1983") 


project(fclist)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
