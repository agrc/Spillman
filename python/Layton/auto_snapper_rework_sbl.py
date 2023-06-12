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

# Initialize the tqdm progress bar tool
tqdm.pandas()

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
today = time.strftime("%Y%m%d")
print("The script start time is {}".format(readable_start))

# Create variables
layton_db = r"C:\E911\Layton\Layton_staging.gdb"
staging_db = r"C:\E911\Layton\Layton_staging.gdb"
work_dir = r'C:\E911\Layton\working_data'
env.workspace = staging_db
env.overwriteOutput = True
env.qualifiedFieldNames = False

real_streets = os.path.join(layton_db, "Davis_streets_build_20221021")
# real_streets = os.path.join(layton_db, "zzz_Layton_snap_TEST")
temp_streets = os.path.join(staging_db, f"St_snap_working_{today}")
working_streets = os.path.join(staging_db, f"St_snap_working_UTM_{today}")
st_endpoints = os.path.join(staging_db, f"St_snap_endpoints_{today}")

# Set snapping radius in meters
snap_radius = 4

print("Copying features to working layer ...")
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

# working_streets = temp_streets
sr = arcpy.SpatialReference(26912)
arcpy.management.Project(temp_streets, working_streets, sr, "WGS_1984_(ITRF00)_To_NAD_1983")
# arcpy.CopyFeatures_management(temp_streets, working_streets)
oid_fieldname = arcpy.Describe(working_streets).OIDFieldName
print(f"OID field name:  {oid_fieldname}")

if arcpy.Exists(st_endpoints):
    arcpy.Delete_management(st_endpoints)
arcpy.management.FeatureVerticesToPoints(working_streets, st_endpoints, "BOTH_ENDS")

calc_time = time.time()
#: Add fields for lon/lat values
arcpy.management.AddField(st_endpoints, 'lon', 'FLOAT', field_scale="6", field_alias="Longitude")
arcpy.management.AddField(st_endpoints, 'lat', 'FLOAT', field_scale="6", field_alias="Latitude")

#: Calculate lon/lat values for all points (in WGS84 coords)
lat_calc = f'arcpy.PointGeometry(!Shape!.centroid, !Shape!.spatialReference).projectAs(arcpy.SpatialReference(4326)).centroid.Y'
lon_calc = f'arcpy.PointGeometry(!Shape!.centroid, !Shape!.spatialReference).projectAs(arcpy.SpatialReference(4326)).centroid.X'

arcpy.CalculateField_management(st_endpoints, 'lat', lat_calc, "PYTHON3")
arcpy.CalculateField_management(st_endpoints, 'lon', lon_calc, "PYTHON3")
print("Time elapsed calculating fields: {:.2f}s".format(time.time() - calc_time))

# Create table name (in memory) for neartable
neartable = 'in_memory\\near_table'
# Perform near table analysis
print("Generating near table ...")
arcpy.analysis.GenerateNearTable(st_endpoints, st_endpoints, neartable, f'{snap_radius} Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 6, 'PLANAR')
print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(neartable)))

# Convert neartable to pandas dataframe for street join
neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
near_df = pd.DataFrame(data = neartable_arr)
print(near_df.head(5))

# Convert endpts to spatial dataframe for endpoint fc
print("Converting working end points to spatial dataframe ...")
endpt_sdf = pd.DataFrame.spatial.from_featureclass(st_endpoints)

# Join end points to near table for endpoint fc
endpt_near_df = near_df.join(endpt_sdf.set_index(oid_fieldname), on='NEAR_FID')
print(endpt_near_df.head(5))

endpt_near_df.sort_values('NEAR_DIST', inplace=True)

non_zero_fc = endpt_near_df[endpt_near_df.NEAR_DIST != 0]
non_zero_fc_path = os.path.join(work_dir, 'snapping_test_nonzero.csv')
non_zero_fc.to_csv(non_zero_fc_path)

#: Calculate h3 on points in a lamdba function
print("Calculating h3 index as a lambda function ...")
h3_lambda = time.time()
non_zero_fc['point_h3'] = non_zero_fc.progress_apply(lambda p: h3.geo_to_h3(p['lat'], p['lon'], 12), axis = 1)
print("\n    Time elapsed in h3 as a lambda function: {:.2f}s".format(time.time() - h3_lambda))

# Drop duplicates to narrow down the end points 
# no_dups_fc = non_zero_fc.drop_duplicates('NEAR_DIST')
# no_dups_fc = non_zero_fc.drop_duplicates('ORIG_FID')
# Trying again to get unique combos of NEAR_DIST and h3 hashes (keep getting NULL object)
# no_dups_fc = non_zero_fc.drop_duplicates(subset=['NEAR_DIST', 'start_h3_9'])
# print(no_dups_fc.head(5))
# no_dups_fc = no_dups_fc.drop_duplicates(subset=['NEAR_DIST', 'end_h3_9'], inplace=True)
# print(no_dups_fc.head(5))
no_dups_fc = non_zero_fc.drop_duplicates(subset=['NEAR_DIST', 'point_h3'])
no_dups_fc_path = os.path.join(work_dir, 'snapping_test_nodups_fc.csv')
no_dups_fc.to_csv(no_dups_fc_path)

# Convert endpts with joined near_table info to point feature class
endpts_fc = os.path.join(staging_db, f"zzz_endpts_to_snap_{today}")
no_dups_fc.spatial.to_featureclass(location=endpts_fc)


# Convert endpts to pandas dataframe for street join
endpt_fields = [oid_fieldname, 'ORIG_FID', 'STREET']
endpt_arr = arcpy.da.FeatureClassToNumPyArray(st_endpoints, endpt_fields)
endpt_df = pd.DataFrame(data = endpt_arr)
print(endpt_df.head(5).to_string())

# Join end points to near table for street join
join1_df = near_df.join(endpt_df.set_index(oid_fieldname), on='NEAR_FID')
join1_df.sort_values('NEAR_DIST', inplace=True)
print(join1_df.head(5).to_string())
non_zero = join1_df[join1_df.NEAR_DIST != 0]

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
final_name = f'St_snap_working_{today}_final'
if arcpy.Exists(final_name):
    arcpy.Delete_management(final_name)
# Copy joined table to "_final" feature class
# This is a copy of the streets feature class with new joined fields
arcpy.CopyFeatures_management(features_with_join, final_name)
arcpy.Delete_management('in_memory\\near_table')

# Apply snapping logic to selections 


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


# snapped = os.path.join(staging_db, f"St_working_{today}_snapped")
snapped = os.path.join(staging_db, f"zzz_Layton_TEST_{today}_snapped")
if arcpy.Exists(snapped):
    arcpy.Delete_management(snapped)
arcpy.CopyFeatures_management(final_name, snapped)

# Get the spatial reference for later use
sr = arcpy.Describe(snapped).spatialReference
# print(sr)

# Add field to use for auto-snapping
# arcpy.management.AddField(snapped, 'snap_status', 'TEXT', '', '', 30)
arcpy.management.AddField(snapped, 'snap_start', 'TEXT', '', '', 30)
arcpy.management.AddField(snapped, 'snap_end', 'TEXT', '', '', 30)
arcpy.management.AddField(snapped, 'snap_status', 'TEXT', '', '', 30)

# Calculate new geometries and update fields
# Get list of unique h3s and distances for selection queries
print("Converting working roads to spatial dataframe ...")
sdf = pd.DataFrame.spatial.from_featureclass(snapped)
not_zero = sdf[(sdf.NEAR_DIST > 0) & (sdf.NEAR_DIST is not None)]

# Slim down to columns of interest for building selection queries
# cols = ['start_h3_9', 'end_h3_9', 'NEAR_DIST']
# query_df = not_zero[cols].sort_values('NEAR_DIST')


# Create list from rows with unique combo of h3s and near distances
# unique_list = []
# for index, row in query_df.iterrows():
#     unique_list.append((row[0], row[1], row[2]))
# unique_tuple = tuple(unique_list)
# new_list = set(unique_tuple)
# for i in new_list:
#     print(i)

# Create dataframe from relevant oids to track start/endpoint snapping staus
snap_df = not_zero[['OBJECTID']].rename(columns={'OBJECTID': 'oid'}).set_index('oid')
snap_df['start'] = ''
snap_df['end'] = ''

# Get list of OIDs for use in selction by location within 4m of each point
snap_area_oids = []
with arcpy.da.SearchCursor(endpts_fc, ['OID@']) as scursor:
    for row in scursor:
        snap_area_oids.append(row[0])


item_number = 0
multi = 0
skipped = False
# Iterate over list of OIDs and perform selction by location within 4m of each point
for snap_oid in snap_area_oids:
    # Create layer
    oid_query = f"""OBJECTID = {snap_oid}"""
    # print(f'Snap point OID query: {oid_query}')
    arcpy.management.MakeFeatureLayer(endpts_fc, "snap_point_lyr", oid_query)

    # Create selection from location
    snapped_selection = arcpy.management.SelectLayerByLocation(snapped, "INTERSECT", "snap_point_lyr", "4 Meters", "NEW_SELECTION")

    # low = float(f'{item[2]}') - .01
    # high = float(f'{item[2]}') + .01
    # print(f"Working on snapping for group {item_number} ...")
    # query = f"""(start_h3_9 = '{item[0]}' AND NEAR_DIST = {item[2]}) OR (end_h3_9 = '{item[1]}' AND NEAR_DIST = {item[2]})"""
    # query = f"""(start_h3_9 IN ('{item[0]}', '{item[1]}') OR end_h3_9 IN ('{item[0]}', '{item[1]}')) AND (NEAR_DIST = {item[2]})""" # qnew
    # query = f"""(start_h3_9 IN ('{item[0]}', '{item[1]}') OR end_h3_9 IN ('{item[0]}', '{item[1]}')) AND (NEAR_DIST IS NOT NULL)""" # qnull
    # query = f"""(start_h3_9 IN ('{item[0]}', '{item[1]}') OR end_h3_9 IN ('{item[0]}', '{item[1]}')) AND (NEAR_DIST BETWEEN {low} and {high})""" # betw
    # query = f"""(start_h3_9 IN ('{item[0]}', '{item[1]}') OR end_h3_9 IN ('{item[0]}', '{item[1]}')) AND (NEAR_DIST < {high})""" # high
    # query = f"""(start_h3_9 IN ('{item[0]}', '{item[1]}') OR end_h3_9 IN ('{item[0]}', '{item[1]}')) AND (NEAR_DIST < 4)""" # _q4
    sql_clause = [None, "ORDER BY NEAR_DIST ASC, OBJECTID ASC"]
    # sql_clause = [None, "ORDER BY snap_start DESC, snap_end DESC"]
    # print(query)
    #             0          1               2             3           4             5           6          7         8
    fields = ['SHAPE@', 'Shape_Length', 'start_h3_9', 'end_h3_9', 'NEAR_DIST', 'snap_start', 'snap_end', 'OID@', 'snap_status']
    # with arcpy.da.UpdateCursor(snapped, fields, query, sort_fields='snap_start D; snap_end D') as ucursor:
    # with arcpy.da.UpdateCursor(snapped_selection, fields, query) as ucursor:
    with arcpy.da.UpdateCursor(snapped_selection, fields, '', '', '', sql_clause) as ucursor:
        cnt = 0
        for row in ucursor:
            shape_obj = row[0]
            if shape_obj.partCount > 1: 
                print("Warning: multiple parts! extra parts are automatically trimmed!")
                print(f"Line has {shape_obj.partCount} parts")
                multi += 1
            # Operate on lines whose length is more than 4m and snap_satus is None
            # if row[1] > snap_radius and row[5] is None:
            if row[1] < snap_radius:
                skipped = True
                print(f'OID: {row[7]} was skipped,      Length: {row[1]}')
            else:
                # Get start/end coordinates of each feature
                start_x = shape_obj.firstPoint.X
                start_y = shape_obj.firstPoint.Y
                end_x = shape_obj.lastPoint.X
                end_y = shape_obj.lastPoint.Y
                
                if cnt == 0:
                    # if not skipped:
                    # Hold first features start/end coordinates in a variable
                    first_start_x = start_x
                    first_start_y = start_y
                    first_end_x = end_x
                    first_end_y = end_y
                    # row[5] = 'static start'
                    # row[6] = 'static end'

                    # first_start_x = shape_obj.firstPoint.X
                    # first_start_y = shape_obj.firstPoint.Y
                    # first_end_x = shape_obj.lastPoint.X
                    # first_end_y = shape_obj.lastPoint.Y
                    first_oid = row[7]
                    cnt += 1
                else:
                    start_x = shape_obj.firstPoint.X
                    start_y = shape_obj.firstPoint.Y
                    end_x = shape_obj.lastPoint.X
                    end_y = shape_obj.lastPoint.Y
                    this_oid = row[7]

                    # Calculate distances from each endpoint to endpoint of first feature
                    thisend_firstend = math.sqrt((end_x - first_end_x)**2 + (end_y - first_end_y)**2)
                    thisstart_firstend = math.sqrt((start_x - first_end_x)**2 + (start_y - first_end_y)**2)
                    thisend_firststart = math.sqrt((end_x - first_start_x)**2 + (end_y - first_start_y)**2)
                    thisstart_firststart = math.sqrt((start_x - first_start_x)**2 + (start_y - first_start_y)**2)
                    
                    distances = [thisend_firstend, thisstart_firstend, thisend_firststart, thisstart_firststart]
                    # print(distances)
                    # benchmark_dist = min(thisend_firstend, thisstart_firstend, thisend_firststart, thisstart_firststart)
                    benchmark_dist = min(d for d in distances if d > 0)
                    # print(f'benchmark_dist for {query} \n \t is: {benchmark_dist}')
                    # print(f'Count is:  {cnt}    Comparing First OID: {first_oid}     to This OID: {this_oid}')
                    print(f'benchmark_dist: {benchmark_dist}    NEAR_DIST: {row[4]}')

                    # if thisend_firstend == benchmark_dist and benchmark_dist == row[4]:
                    # if thisend_firstend == benchmark_dist and abs(benchmark_dist - row[4]) < 0.005 and ('done' not in snap_df.at[this_oid, 'end']):
                    # if 0 < thisend_firstend < 4  and 'done' not in snap_df.at[this_oid, 'end']:
                    # if thisend_firstend == benchmark_dist and benchmark_dist == row[4] and 'done' not in snap_df.at[this_oid, 'end']:
                    if thisend_firstend < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'end']:
                        scenario = 1
                        print(f'    Case 1: thisend_firstend')
                        new_geom = update_geom(shape_obj, scenario, first_end_x, first_end_y)
                        row[0] = new_geom
                        # row[6] = 'snapped - done'
                        snap_df.at[this_oid, 'end'] = 'snapped - done'
                        snap_df.at[first_oid, 'end'] = 'static - done'
                        cnt += 1
                    # if thisstart_firstend == benchmark_dist and benchmark_dist == row[4]:
                    # if thisstart_firstend == benchmark_dist and abs(benchmark_dist - row[4]) < 0.005 and ('done' not in snap_df.at[this_oid, 'start']):
                    # elif 0 < thisstart_firstend < 4 and 'done' not in snap_df.at[this_oid, 'start']:
                    # if thisstart_firstend == benchmark_dist and benchmark_dist == row[4] and 'done' not in snap_df.at[this_oid, 'start']:
                    elif thisstart_firstend < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'start']:
                        scenario = 2
                        print(f'    Case 2: thisstart_firstend')
                        new_geom = update_geom(shape_obj, scenario, first_end_x, first_end_y)
                        row[0] = new_geom
                        # row[5] = 'snapped - done'
                        snap_df.at[this_oid, 'start'] = 'snapped - done'
                        snap_df.at[first_oid, 'end'] = 'static - done'
                        cnt += 1
                    # if thisend_firststart == benchmark_dist and benchmark_dist == row[4]:
                    # if thisend_firststart == benchmark_dist and abs(benchmark_dist - row[4]) < 0.005 and ('done' not in snap_df.at[this_oid, 'end']):
                    # elif 0 < thisend_firststart < 4 and 'done' not in snap_df.at[this_oid, 'end']:
                    # if thisend_firststart == benchmark_dist and benchmark_dist == row[4] and 'done' not in snap_df.at[this_oid, 'end']:
                    elif thisend_firststart < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'end']:
                        scenario = 3
                        print(f'    Case 3: thisend_firststart')
                        new_geom = update_geom(shape_obj, scenario, first_start_x, first_start_y)
                        row[0] = new_geom
                        # row[6] = 'snapped - done'
                        snap_df.at[this_oid, 'end'] = 'snapped - done'
                        snap_df.at[first_oid, 'start'] = 'static - done'
                        cnt += 1
                    # if thisstart_firststart == benchmark_dist and benchmark_dist == row[4]:
                    # if thisstart_firststart == benchmark_dist and abs(benchmark_dist - row[4]) < 0.005 and ('done' not in snap_df.at[this_oid, 'start']):
                    # elif 0 < thisstart_firststart < 4 and 'done' not in snap_df.at[this_oid, 'start']:
                    # if thisstart_firststart == benchmark_dist and benchmark_dist == row[4] and 'done' not in snap_df.at[this_oid, 'start']:
                    elif thisstart_firststart < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'start']:
                        scenario = 4
                        print(f'    Case 4: thisstart_firststart')
                        new_geom = update_geom(shape_obj, scenario, first_start_x, first_start_y)
                        row[0] = new_geom
                        # row[5] = 'snapped - done'
                        snap_df.at[this_oid, 'start'] = 'snapped - done'
                        snap_df.at[first_oid, 'start'] = 'static - done'
                        cnt += 1
            
            ucursor.updateRow(row)
            # print(snap_df.to_string())

    item_number += 1

print(f'Total count of snapping updates: {item_number}')
print(f'Total count of multipart features: {multi}')


# Go back through data and update the comment fields (snap_start, snap_end) based on snap_df
snap_count = 0
oid_list = snap_df.index.to_list()
# print(f'oid_list for updates to fc: {oid_list}')
#                 0          1            2            3
fewer_fields = ['OID@', 'snap_start', 'snap_end', 'snap_status']
oid_query = f'OBJECTID IN ({",".join([str(oid) for oid in oid_list])})'
with arcpy.da.UpdateCursor(snapped, fewer_fields, oid_query) as ucursor:
    print("Calculating snap comments for start and end points ...")
    for row in ucursor:
        if row[0] in oid_list:
            row[1] = snap_df.at[row[0], 'start']
            row[2] = snap_df.at[row[0], 'end']
            if 'done' in row[1] and 'done' in row[2]:
                row[3] = 'finished'
            snap_count += 1
        # print(f' OID: {row[0]}    snap_start: {row[1]}    snap_end: {row[2]}')
        ucursor.updateRow(row)
print(f'Total count of snap field comment updates: {snap_count}')



# OTHER IDEAS #
# If iterating to run snapper multiple times:
# - Delete all of the extra fields that were added
# - Delete the temporary files
# - Have naming scheme for multiple output files
# Possibly track start/end points that must remain static in separate data frame or dictionary (OID, snap_start, snap_end)
# Add static oid comment updates in between new_list iterations
# Change queries to unique h3 and near_dist combo, then use new format:
# (start_h3_9 = '89269698cb3ffff' OR end_h3_9 = '89269698cb3ffff') AND (NEAR_DIST = 0.010000500693571748)
# find the start/endpoints and put them in a list, then do a select by location for each list to get nearby segments to snap

# SPEED UP
# Calculate lat/lons and h3s in dataframe/lambdas (might need to project to WGS84)
# Use near table on final snap points to get list of road OIDs within 4m ({snap_oid: [oid, oid, oid, oid]})
#   Then iterate over dictionary to create selection query for snapping operation (instead of select by location on layer)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))

# print(snap_df.to_string())