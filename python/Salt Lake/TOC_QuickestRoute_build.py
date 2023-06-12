# -*- coding: utf-8 -*-
"""
Created on Wed Nov 30 15:58:21 2022
@author: eneemann
Script to build Salt Lake Comm Center Dispatch's QuickestRoute network
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

# Check out Network Analyst license if available. Fail if the Network Analyst license is not available.
if arcpy.CheckExtension("network") == "Available":
    arcpy.CheckOutExtension("network")
else:
    raise arcpy.ExecuteError("Network Analyst Extension license is not available.")

## Prep data for network

# Set up variables
TOC_dir = r"C:\E911\TOC"
TOC_db = r"C:\E911\TOC\TOC_Geovalidation_WGS84.gdb"
TOC_streets = os.path.join(TOC_db, "Streets_Combined_network")
network_db = os.path.join(TOC_dir,'QuickestRoute_TEST_' + today +  '.gdb')
network_dataset = os.path.join(network_db, 'QuickestRoute')
env.workspace = network_db

# Create new geodatabase for the network and dataset within it
if arcpy.Exists(network_db):
    arcpy.Delete_management(network_db)
arcpy.CreateFileGDB_management(TOC_dir, 'QuickestRoute_TEST_' + today +  '.gdb')
arcpy.CreateFeatureDataset_management(network_db, 'QuickestRoute', TOC_streets)

# Create XML Template from current dataset
print('Creating network template ...')
# original_network = r"C:\E911\TOC\QuickestRoute.gdb\QuickestRoute\QuickestRoute_ND"
output_xml_file = r"C:\E911\TOC\Network Dataset Template\NDTemplate.xml"
# if arcpy.Exists(output_xml_file):
#     arcpy.Delete_management(output_xml_file)
# arcpy.nax.CreateTemplateFromNetworkDataset(original_network, output_xml_file)

# Import current "Streets_Map" data
print('Importing street data ...')
network_streets = os.path.join(network_dataset, 'Streets')
arcpy.CopyFeatures_management(TOC_streets, network_streets)

# Calculated necessary travel time fields
print('Calculating geometry (distance) ...')
sr_utm12N = arcpy.SpatialReference("NAD 1983 UTM Zone 12N")
geom_start_time = time.time()
arcpy.management.CalculateGeometryAttributes(network_streets, [["Distance", "LENGTH_GEODESIC"]], "MILES_US", "", sr_utm12N)
print("Time elapsed calculating geometry: {:.2f}s".format(time.time() - geom_start_time))

# Calculate travel time field
update_count = 0
#             0            1         2    
fields = ['TrvlTime', 'Distance', 'SPEED']
with arcpy.da.UpdateCursor(network_streets, fields) as cursor:
    print("Looping through rows to calculate TrvlTime ...")
    for row in cursor:
        row[0] = (row[1]/row[2])*60
        update_count += 1
        cursor.updateRow(row)
print("Total count of TrvlTime updates is {}".format(update_count))

# Calculate "One_Way" field
update_count_oneway = 0
#                    0         1  
fields_oneway = ['ONEWAY', 'One_Way']
with arcpy.da.UpdateCursor(network_streets, fields_oneway) as cursor:
    print("Looping through rows to calculate One_Way field ...")
    for row in cursor:
        if row[0] == '0' or row[0] == None:
#        if row[0] == '0':      
            row[1] = 'B'
            update_count_oneway += 1
        elif row[0] == '1':
            row[1] = 'FT'
            update_count_oneway += 1
        elif row[0] == '2':
            row[1] = 'TF'
            update_count_oneway += 1
        cursor.updateRow(row)
print("Total count of One_Way updates is {}".format(update_count_oneway))

# Recalculate travel times based on multiplication factors
# Interstates to not get an additional multiplication factor applied

# First, multiply all "other" streets by 2
update_count2 = 0
#              0
fields2 = ['TrvlTime', 'Multiplier']
# where_clause2 = "HWYNAME IS NULL AND (STREETTYPE IS NULL OR STREETTYPE <> 'RAMP')"
# 12/17/2020 Update: simplified to 'HWYNAME IS NULL' and calculated first to improve QR FIXES
where_clause2 = "HWYNAME IS NULL AND (STREETTYPE IS NULL OR STREETTYPE <> 'RAMP')"
with arcpy.da.UpdateCursor(network_streets, fields2, where_clause2) as cursor:
    print("Looping through rows to multiply TrvlTime on all other roads ...")
    for row in cursor:
        row[0] = row[0]*2
        row[1] = 2
        update_count2 += 1
        cursor.updateRow(row)
print("Total count of TrvlTime updates (x2) is {}".format(update_count2))

# Second, multiply state and federal highways by 1.5
update_count1 = 0
#              0
fields1 = ['TrvlTime', 'Multiplier']
# where_clause1 = "HWYNAME IS NOT NULL AND HWYNAME NOT IN ('I-15', 'I-80', 'I-84') AND STREETTYPE <> 'RAMP'"
# 3/11/2019 Update: added 'STREETTYPE IS NULL' to where clause to catch highway segments correctly
# 1/2/2020 Update: added some segments with 'QR FIX' in HWYNAME field to improve routing with 1.5 multiplier
where_clause1 = "HWYNAME IS NOT NULL AND HWYNAME NOT LIKE 'I-%' AND (STREETTYPE <> 'RAMP' OR STREETTYPE IS NULL)"
with arcpy.da.UpdateCursor(network_streets, fields1, where_clause1) as cursor:
    print("Looping through rows to multiply TrvlTime on state and federal highways ...")
    for row in cursor:
        row[0] = row[0]*1.5
        row[1] = 1.5
        update_count1 += 1
        cursor.updateRow(row)
print("Total count of TrvlTime updates (x1.5) is {}".format(update_count1))


# Third, populate Multiplier field with 1 for interstates and ramps
update_count3 = 0
#              0
fields3 = ['Multiplier']
where_clause3 = "(HWYNAME IS NOT NULL AND HWYNAME LIKE 'I-%') OR STREETTYPE = 'RAMP'"
with arcpy.da.UpdateCursor(network_streets, fields3, where_clause3) as cursor:
    print("Looping through rows to assign Multiplier on ramps and interstates ...")
    for row in cursor:
        row[0] = 1
        update_count3 += 1
        cursor.updateRow(row)
print("Total count of ramp and interstate (x1) updates is {}".format(update_count3))

## Create network dataset   
# Use previously created XML template
xml_template = output_xml_file

# Create the new network dataset in the output location using the template.
# The output location must already contain feature classes with the same
# names and schema as the original network
arcpy.nax.CreateNetworkDatasetFromTemplate(xml_template, network_dataset)
print("Done creating network, now building it ...")

# Build the new network dataset
arcpy.nax.BuildNetwork(os.path.join(network_dataset, "QuickestRoute_ND"))
print("Done building the network ...")

arcpy.CheckInExtension("network")

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))