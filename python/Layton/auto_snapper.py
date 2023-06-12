# -*- coding: utf-8 -*-
"""
Created on Mon Oct 24 16:22:07 2022
@author: eneemann
Script to detect possible snapping errrors in Layton road data (built from SGID)

"""

import arcpy
from arcpy import env
import os
import time
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import h3
from tqdm import tqdm
import math
from arcgis.features import GeoAccessor, GeoSeriesAccessor

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
today = time.strftime("%Y%m%d")
print("The script start time is {}".format(readable_start))

layton_db = r"C:\E911\Layton\Layton_staging.gdb"
staging_db = r"C:\E911\Layton\Layton_staging.gdb"
work_dir = r'C:\E911\Layton\working_data'
env.workspace = staging_db
env.overwriteOutput = True
env.qualifiedFieldNames = False

real_streets = os.path.join(layton_db, "Davis_streets_build_20221021")
temp_streets = os.path.join(staging_db, f"St_snap_working_{today}")
working_streets = os.path.join(staging_db, f"St_snap_working_UTM_{today}")
st_endpoints = os.path.join(staging_db, f"St_snap_endpoints_{today}")

arcpy.CopyFeatures_management(real_streets, temp_streets)

# Add h3 index level 9 for start and end points
arcpy.management.AddField(temp_streets, "start_h3_9", "TEXT", "", "", 30)
arcpy.management.AddField(temp_streets, "end_h3_9", "TEXT", "", "", 30)

count = 0
#             0          1            2
fields = ['SHAPE@', 'start_h3_9', 'end_h3_9']
with arcpy.da.UpdateCursor(temp_streets, fields) as ucursor:
    print("Calculating h3 for start and end points ...")
    for row in ucursor:
        start_lon = row[0].firstPoint.X
        start_lat = row[0].firstPoint.Y
        end_lon = row[0].lastPoint.X
        end_lat = row[0].lastPoint.Y

        row[1] = h3.geo_to_h3(start_lat, start_lon, 9)
        row[2] = h3.geo_to_h3(end_lat, end_lon, 9)
               
        count += 1
        ucursor.updateRow(row)
print(f'Total count of h3 field updates: {count}')

sr = arcpy.SpatialReference(26912)
arcpy.management.Project(temp_streets, working_streets, sr, "WGS_1984_(ITRF00)_To_NAD_1983")
oid_fieldname = arcpy.Describe(working_streets).OIDFieldName
print(f"OID field name:  {oid_fieldname}")


arcpy.management.FeatureVerticesToPoints(working_streets, st_endpoints, "BOTH_ENDS")

# Create table name (in memory) for neartable
neartable = 'in_memory\\near_table'
# Perform near table analysis
print("Generating near table ...")
arcpy.analysis.GenerateNearTable(st_endpoints, st_endpoints, neartable, '4 Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 6, 'PLANAR')
print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(neartable)))

# Convert neartable to pandas dataframe
neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
near_df = pd.DataFrame(data = neartable_arr)
print(near_df.head(5).to_string())

# Convert endpts to pandas dataframe
endpt_fields = [oid_fieldname, 'ORIG_FID', 'STREET']
endpt_arr = arcpy.da.FeatureClassToNumPyArray(st_endpoints, endpt_fields)
endpt_df = pd.DataFrame(data = endpt_arr)
print(endpt_df.head(5).to_string())

# Join end points to near table
join1_df = near_df.join(endpt_df.set_index(oid_fieldname), on='NEAR_FID')
print(join1_df.head(5).to_string())

sorted_df = join1_df.sort_values('NEAR_DIST')
sorted_path = os.path.join(work_dir, 'snapping_test_sorted.csv')
sorted_df.to_csv(sorted_path)

non_zero = sorted_df[sorted_df.NEAR_DIST != 0]
non_zero_path = os.path.join(work_dir, 'snapping_test_nonzero.csv')
non_zero.to_csv(non_zero_path)

no_dups = non_zero.drop_duplicates('ORIG_FID')
no_dups_path = os.path.join(work_dir, 'snapping_test_nodups.csv')
no_dups.to_csv(no_dups_path)


# Convert CSV output into table and join to working streets FC
join_name = f"neartable_join_{today}"
if arcpy.Exists(join_name):
    arcpy.Delete_management(join_name)
arcpy.TableToTable_conversion(no_dups_path, staging_db, join_name)
# joined_table = arcpy.AddJoin_management(working_streets, oid_fieldname, join_name, "IN_FID")
features_with_join = arcpy.AddJoin_management(working_streets, oid_fieldname, join_name, "ORIG_FID")
final_name = f'{temp_streets}_final'
if arcpy.Exists(final_name):
    arcpy.Delete_management(final_name)
# Copy joined table to "_final" feature class
# This is a copy of the streets feature class with new joined fields
arcpy.CopyFeatures_management(features_with_join, final_name)
arcpy.Delete_management('in_memory\\near_table')

#########################
# WORK ON AUTO-SNAPPING #
#########################

def update_geom(shape, case, x, y):
    pts_orig = []
    new_pt = arcpy.Point(x, y)
    # Step through and use first part of the feature
    part = shape.getPart(0)
    # Put the original points into a list
    for pnt in part:
        pts_orig.append((pnt.X, pnt.Y))
    # Rebuild original geometry of the line
    arc_pts = [arcpy.Point(item[0], item[1]) for item in pts_orig]
    array = arcpy.Array(arc_pts)
    
    # Replace the original enpoint with the new point (snapped)
    # Update the end point for cases 1 and 3
    if case in (1, 3):
        array.replace(array.count-1, new_pt)
    # Update the start point for cases 2 and 4
    elif case in (2, 4):
        array.replace(0, new_pt)

    updated_shape = arcpy.Polyline(array, sr)

    return updated_shape



snapped = os.path.join(staging_db, f"St_working_{today}_snapped")
arcpy.CopyFeatures_management(final_name, snapped)

# Get the spatial reference for later use
sr = arcpy.Describe(snapped).spatialReference
print(sr)

# Add field to use for auto-snapping
# arcpy.management.AddField(snapped, 'start_x', 'FLOAT')
# arcpy.management.AddField(snapped, 'start_y', 'FLOAT')
# arcpy.management.AddField(snapped, 'end_x', 'FLOAT')
# arcpy.management.AddField(snapped, 'end_y', 'FLOAT')
arcpy.management.AddField(snapped, 'snap_status', 'TEXT', '', '', 30)

# Calculate new geometries and update fields
# Get list of unique h3s and distances for selection queries
print("Converting working data to spatial dataframe ...")
sdf = pd.DataFrame.spatial.from_featureclass(final_name)
not_zero = sdf[(sdf.NEAR_DIST > 0) & (sdf.NEAR_DIST is not None)]

# Slim down to columns of interest for building selection queries
cols = ['start_h3_9', 'end_h3_9', 'NEAR_DIST']
query_df = not_zero[cols].sort_values('NEAR_DIST')


# Create list from rows with unique combo of h3s and near distances
unique_list = []
for index, row in query_df.iterrows():
    unique_list.append((row[0], row[1], row[2]))
unique_tuple = tuple(unique_list)
new_list = set(unique_tuple)
# print(new_list)

for item in new_list:
    item_number = 0
    multi = 0
    # print(f"Working on snapping for group {item_number} ...")
    query = f"""(start_h3_9 = '{item[0]}' AND NEAR_DIST = {item[2]}) OR (end_h3_9 = '{item[1]}' AND NEAR_DIST = {item[2]})"""
    # print(query)
    #             0          1               2             3           4           5         6        7        8
    fields = ['SHAPE@', 'Shape_Length', 'start_h3_9', 'end_h3_9', 'NEAR_DIST', 'snap_status', 'OID@']
    with arcpy.da.UpdateCursor(snapped, fields, query) as ucursor:
        cnt = 0
        for row in ucursor:
            shape_obj = row[0]
            if shape_obj.partCount > 1: 
                print("Warning: multiple parts! extra parts are automatically trimmed!")
                print("Line has {} parts".format(shape_obj.partCount))
                multi += 1
            # Operate on lines whose length is more than 4m and snap_satus is None
            if row[1] > 4 and row[5] is None:
                # Get start/end coordinates of each feature
                start_x = shape_obj.firstPoint.X
                start_y = shape_obj.firstPoint.Y
                end_x = shape_obj.lastPoint.X
                end_y = shape_obj.lastPoint.Y

                if cnt == 0:
                    # Hold first features start/end coordinates in a variable
                    first_start_x = start_x
                    first_start_y = start_y
                    first_end_x = end_x
                    first_end_y = end_y
                    row[5] = 'static'
                else:
                    # Calculate distances from each endpoint to endpoint of first feature
                    thisend_firstend = math.sqrt((end_x - first_end_x)**2 + (end_y - first_end_y)**2)
                    thisstart_firstend = math.sqrt((start_x - first_end_x)**2 + (start_y - first_end_y)**2)
                    thisend_firststart = math.sqrt((end_x - first_start_x)**2 + (end_y - first_start_y)**2)
                    thisstart_firststart = math.sqrt((start_x - first_start_x)**2 + (start_y - first_start_y)**2)

                    benchmark_dist = min(thisend_firstend, thisstart_firstend, thisend_firststart, thisstart_firststart)
                    # print(f'benchmark_dist for {query} \n \t is: {benchmark_dist}')
                    print(f'benchmark_dist: {benchmark_dist}    near_dist: {row[4]}')

                    # if thisend_firstend == benchmark_dist and benchmark_dist == row[4]:
                    if thisend_firstend == benchmark_dist and abs(benchmark_dist - row[4]) < 0.01:
                        scenario = 1
                        print(f'Case 1: thisend_firstend')
                        new_geom = update_geom(shape_obj, scenario, first_end_x, first_end_y)
                        row[0] = new_geom
                        row[5] = 'snapped end point'
                        cnt += 1
                    # if thisstart_firstend == benchmark_dist and benchmark_dist == row[4]:
                    if thisstart_firstend == benchmark_dist and abs(benchmark_dist - row[4]) < 0.01:
                        scenario = 2
                        print(f'Case 2: thisstart_firstend')
                        new_geom = update_geom(shape_obj, scenario, first_end_x, first_end_y)
                        row[0] = new_geom
                        row[5] = 'snapped start point'
                        cnt += 1
                    # if thisend_firststart == benchmark_dist and benchmark_dist == row[4]:
                    if thisend_firststart == benchmark_dist and abs(benchmark_dist - row[4]) < 0.01:
                        scenario = 3
                        print(f'Case 3: thisend_firststart')
                        new_geom = update_geom(shape_obj, scenario, first_start_x, first_start_y)
                        row[0] = new_geom
                        row[5] = 'snapped end point'
                        cnt += 1
                    # if thisstart_firststart == benchmark_dist and benchmark_dist == row[4]:
                    if thisstart_firststart == benchmark_dist and abs(benchmark_dist - row[4]) < 0.01:
                        scenario = 4
                        print(f'Case 4: thisstart_firststart')
                        new_geom = update_geom(shape_obj, scenario, first_start_x, first_start_y)
                        row[0] = new_geom
                        row[5] = 'snapped start point'
                        cnt += 1

            ucursor.updateRow(row)

    item_number += 1

print(f'Total count of snapping updates: {item_number}')
print(f'Total count of multipart features: {multi}')


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))