# -*- coding: utf-8 -*-
"""
Created on Mon Apr 15 16:18:26 2019

@author: eneemann

This script is used to combine shapefiles into point and line datasets from
individual zip files received via email.  Points are address points, lines are
road segments to be added, deleted, or modified.
"""

# Import Libraries
import arcpy
from arcpy import env
import os
import time
import numpy as np
import zipfile

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")


#-----------------------Start Main Code------------------------#

## Prep and variables for combining data

# Set up variables, create geodatabase, if necessary
#data_dir = r"C:\E911\RichfieldComCtr\00 Working_data_area\Spillman_update_20210524"
data_dir = r"C:\E911\RichfieldComCtr\2 Data From County\20220525\deletes"
env.workspace = data_dir
new_db_name = "Sevier_data_" + today
#new_db_name = 'Sevier_data_20190415'
new_db = os.path.join(data_dir, new_db_name + ".gdb")
if arcpy.Exists(new_db) == False:
    arcpy.CreateFileGDB_management(data_dir, new_db_name)


#-----------------------Functions------------------------#


def unzip_files(directory):
    os.chdir(directory)
    zip_list = []
    for file in os.listdir(directory):
        if file.endswith(".zip"):
            zip_list.append(file)
    
    print("List of .zip files:")
    for zip in zip_list:
        print(zip)
    
    for zip in zip_list:
        print("Unzipping {} ...".format(zip))
        with zipfile.ZipFile(zip,"r") as zip_ref:
            zip_ref.extractall(directory)


def create_lists():
    # Create feature class list from the data directory
    fclist = arcpy.ListFeatureClasses()
    
    # Loop through FCs and create list of points and lines
    points = []
    lines =[]
    for fc in fclist:
        if arcpy.Describe(fc).shapeType == 'Point':
            points.append(fc)
        elif arcpy.Describe(fc).shapeType == 'Polyline':
            lines.append(fc)
        else: continue
    return points, lines


def combine_addpts(points):
    # Create list of good fields that will be kept in the combined point FC
    point_fields = ["FID", "OBJECTID", "SHAPE", "ADDRES", "CITYCD", "OLD_AD", "GRID", "STREET", "PARCEL", "NUMBER", "AUDIT", "AUDIT911", "OWNER"]
    
    # Copy first point into FC that will be used to combine point files
    first_point = os.path.join(data_dir, arcpy.Describe(points[0]).file)
    print(first_point)
    print(arcpy.Describe(first_point).shapeType)
    combined_points = os.path.join(new_db, "Sevier_addpts_combined")
    if arcpy.Exists(combined_points) == False:
        arcpy.CopyFeatures_management(first_point, combined_points)
    
    # Loop through combined point FC and delete fields that aren't in point_fields list
    # Rename other fields by trimming down to first 6 characters and making upper case
    combined_fields = arcpy.ListFields(combined_points)
    print("Combined_points fields are:")
    for fld in combined_fields:
        print(fld.name)
    for fld in combined_fields:
        if "NUMB" in fld.name.upper()[:6] and "HOUSE" not in fld.name.upper()[:6]:
            arcpy.AlterField_management(combined_points, fld.name, "NUMBER")
        if "PROPERTY_O" in fld.name.upper() or "OWNER" in fld.name.upper()[:5]:
            arcpy.AlterField_management(combined_points, fld.name, "OWNER", "", "", 100)
        if "AUDIT9" in fld.name.upper()[:6]:
            arcpy.AlterField_management(combined_points, fld.name, "AUDIT911")
        if "AUDIT" == fld.name.upper()[:6]:
            arcpy.AlterField_management(combined_points, fld.name, "AUDIT")
        temp_list = [(fld.name.upper()[:6] in x) for x in point_fields]
        if fld.name != "X" and fld.name != "Y" and temp_list.count(True) == 0:
#            print("fld.name is: {}".format(fld.name))
#            print("fld.name on line 76 is: {}".format(fld.name.upper()[:6]))
            arcpy.DeleteField_management(combined_points, fld.name)
        elif fld.name.upper()[:6] not in ('OBJECT', 'SHAPE'):
            arcpy.AlterField_management(combined_points, fld.name, fld.name.upper()[:6])
    
    # Loop through rest of points and append them to the combined point FC
    for i in np.arange(1, len(points)):
        print("Working on: {}".format(points[i]))
        temp_pt = os.path.join(new_db, "temp_point")
        if arcpy.Exists(temp_pt):
            arcpy.Delete_management(temp_pt)
        arcpy.CopyFeatures_management(points[i], temp_pt)
        flds = arcpy.ListFields(temp_pt)
        for fld in flds:
            temp_list2 = [(fld.name.upper()[:6] in x) for x in point_fields]
            if fld.name == "X" or fld.name == "Y" or temp_list2.count(True) >= 1 and fld.name.upper()[:6] not in ('OBJECT', 'SHAPE'):
#                print("fld.name on line 92 is: {}".format(fld.name.upper()[:6]))
                arcpy.AlterField_management(temp_pt, fld.name, fld.name.upper()[:6])
            if "NUMB" in fld.name.upper()[:6] and "HOUSE" not in fld.name.upper()[:6]:
#                print("fld.name on line 95 is: {}".format(fld.name.upper()[:6]))
                arcpy.AlterField_management(temp_pt, fld.name, "NUMBER")
            # if "AUDIT9" in fld.name.upper()[:6]:
            #     print("fld.name on line 98 is: {}".format(fld.name.upper()[:5]))
            #     arcpy.AlterField_management(temp_pt, fld.name, "AUDIT911")
#             if "AUDIT" == fld.name.upper()[:6]:
# #                print("fld.name on line 98 is: {}".format(fld.name.upper()[:5]))
#                 arcpy.AlterField_management(temp_pt, fld.name, "AUDIT")
            if "PROPERTY_O" in fld.name.upper() or "OWNER" in fld.name.upper()[:5]:
#                print("fld.name on line 101 is: {}".format(fld.name.upper()[:10]))
                arcpy.AlterField_management(temp_pt, fld.name, "OWNER")
        arcpy.Append_management(temp_pt, combined_points, "NO_TEST")
        arcpy.Delete_management(temp_pt)


def combine_roads(lines):
    # Create list of good fields that will be kept in the combined point FC
    line_fields = ["FID", "OBJECTID", "OBJECTID_1" "SHAPE", "SHAPE_LENGTH", "PRE_DIR", "S_NAME", "S_TYPE", "STREET", "L_F_ADD", "L_T_ADD",
                   "R_F_ADD", "R_T_ADD", "GRID", "LZIP", "RZIP", "LCITYCD", "RCITYCD", "ALIAS", "SUF_DIR" ]
    
    # Copy first line into FC that will be used to combine line files
    first_line = os.path.join(data_dir, arcpy.Describe(lines[0]).file)
    print(first_line)
    print(arcpy.Describe(first_line).shapeType)
    combined_lines = os.path.join(new_db, "Sevier_roads_combined")
    if arcpy.Exists(combined_lines) == False:
        arcpy.CopyFeatures_management(first_line, combined_lines)
    
    # Loop through combined line FC and delete fields that aren't in line_fields list
    # Rename other fields by trimming down to first 12 characters and making upper case (shouldn't matter for shapefiles)
    combined_fields_orig = arcpy.ListFields(combined_lines)
    if "ALIAS" not in combined_fields_orig:
        arcpy.AddField_management(combined_lines, "ALIAS", "TEXT", "", "", 100)
    print("Original combined_lines fields:")
    for fld in combined_fields_orig: print(fld.name)
    combined_fields = arcpy.ListFields(combined_lines)
    print("Updated combined_lines fields:")
    for fld in combined_fields: print(fld.name)
    
    for fld in combined_fields:
        if "SUR_DIR" in fld.name.upper()[:12]:
            arcpy.AlterField_management(combined_lines, fld.name, "SUF_DIR")
        temp_list = [(fld.name.upper()[:12] in x) for x in line_fields]
        if temp_list.count(True) == 0:
#            print("fld.name is: {}".format(fld.name))
#            print("fld.name on line 137 is: {}, and will be deleted".format(fld.name.upper()[:12]))
            arcpy.DeleteField_management(combined_lines, fld.name)
        elif fld.name.upper()[:8] not in ('OBJECTID', 'SHAPE', 'SHAPE_LE'):
#            print("fld.name on line 140 is: {}, and will be renamed".format(fld.name.upper()[:12]))
            arcpy.AlterField_management(combined_lines, fld.name, fld.name.upper()[:12])
    
    # Loop through rest of lines and append to combined line FC
    for i in np.arange(1, len(lines)):
        print("Working on: {}".format(lines[i]))
        temp_pt = os.path.join(new_db, "temp_line")
        if arcpy.Exists(temp_pt):
            arcpy.Delete_management(temp_pt)
        arcpy.CopyFeatures_management(lines[i], temp_pt)
        flds = arcpy.ListFields(temp_pt)
        for fld in flds:
            temp_list2 = [(fld.name.upper()[:12] in x) for x in line_fields]
            if temp_list2.count(True) >= 1 and fld.name.upper()[:8] not in ('OBJECTID', 'SHAPE', 'SHAPE_LE'):
#                print("fld.name on line 154 is: {}".format(fld.name.upper()[:12]))
                arcpy.AlterField_management(temp_pt, fld.name, fld.name.upper()[:12])
            if "SUR_DIR" in fld.name.upper()[:12]:
#                print("fld.name on line 157 is: {}".format(fld.name.upper()[:12]))
                arcpy.AlterField_management(temp_pt, fld.name, "SUF_DIR")
        arcpy.Append_management(temp_pt, combined_lines, "NO_TEST")
        arcpy.Delete_management(temp_pt)


#-----------------------Call Functions-----------------------#


#unzip_files(data_dir)
point_list, line_list = create_lists()
combine_addpts(point_list)
combine_roads(line_list)


#-----------------------End Main Code------------------------#
print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))


# for fc in point_list:
#     result = arcpy.GetCount_management(fc)
#     print(f'{result[0]} records in {fc}')
    