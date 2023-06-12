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

# Drop duplicates to narrow it down to the important end points 
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


snapped = os.path.join(staging_db, f"zzz_Layton_TEST_{today}_near_snapped")
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


# Create dataframe from relevant oids to track start/endpoint snapping staus
snap_df = not_zero[['OBJECTID']].rename(columns={'OBJECTID': 'oid'}).set_index('oid')
snap_df['start'] = ''
snap_df['end'] = ''

# Get list of OIDs for use in selction by location within 4m of each point
snap_area_oids = []
with arcpy.da.SearchCursor(endpts_fc, ['OID@']) as scursor:
    for row in scursor:
        snap_area_oids.append(row[0])


# Create Near Table to get OIDs within 4m of each snap point
n_table = os.path.join(staging_db, f"Snap_near_table_{today}")
print("Generating near table on snap points ...")
arcpy.analysis.GenerateNearTable(endpts_fc, snapped, n_table, f'{snap_radius} Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 6, 'PLANAR')
print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(n_table)))


item_number = 0
multi = 0
deletes = 0
skipped = False
# Iterate over list of OIDs and perform selction by location within 4m of each point
for snap_oid in snap_area_oids:
    near_oids = []
    oid_query = f"""IN_FID = {snap_oid}"""
    near_fields = ['NEAR_FID']
    with arcpy.da.SearchCursor(n_table, near_fields, oid_query) as scursor:
        for row in scursor:
            near_oids.append(row[0])

    snap_query = f"""OBJECTID IN ({','.join([str(o) for o in near_oids])}) AND NEAR_DIST IS NOT NULL"""
    sql_clause = [None, "ORDER BY NEAR_DIST ASC, OBJECTID ASC"]
    #             0          1               2             3           4             5           6          7         8
    fields = ['SHAPE@', 'Shape_Length', 'start_h3_9', 'end_h3_9', 'NEAR_DIST', 'snap_start', 'snap_end', 'OID@', 'snap_status']
    with arcpy.da.UpdateCursor(snapped, fields, snap_query, '', '', sql_clause) as ucursor:
        cnt = 0
        for row in ucursor:
            skipped = False
            shape_obj = row[0]
            if shape_obj.partCount > 1: 
                print("Warning: multiple parts! extra parts are automatically trimmed!")
                print(f"Line has {shape_obj.partCount} parts")
                multi += 1
            # Only operate on lines whose length is more than the snap_radius
            if row[1] < snap_radius:
                skipped = True
                deletes += 1
                print(f'OID: {row[7]} was deleted,      Length: {row[1]}')
            else:
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
                    benchmark_dist = min(d for d in distances if d > 0)

                    if thisend_firstend < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'end']:
                        scenario = 1
                        # print(f'    Case 1: thisend_firstend')
                        new_geom = update_geom(shape_obj, scenario, first_end_x, first_end_y)
                        row[0] = new_geom
                        snap_df.at[this_oid, 'end'] = 'snapped - done'
                        snap_df.at[first_oid, 'end'] = 'static - done'
                        cnt += 1
                    elif thisstart_firstend < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'start']:
                        scenario = 2
                        # print(f'    Case 2: thisstart_firstend')
                        new_geom = update_geom(shape_obj, scenario, first_end_x, first_end_y)
                        row[0] = new_geom
                        snap_df.at[this_oid, 'start'] = 'snapped - done'
                        snap_df.at[first_oid, 'end'] = 'static - done'
                        cnt += 1
                    elif thisend_firststart < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'end']:
                        scenario = 3
                        # print(f'    Case 3: thisend_firststart')
                        new_geom = update_geom(shape_obj, scenario, first_start_x, first_start_y)
                        row[0] = new_geom
                        snap_df.at[this_oid, 'end'] = 'snapped - done'
                        snap_df.at[first_oid, 'start'] = 'static - done'
                        cnt += 1
                    elif thisstart_firststart < 4 and benchmark_dist < 4 and 'done' not in snap_df.at[this_oid, 'start']:
                        scenario = 4
                        # print(f'    Case 4: thisstart_firststart')
                        new_geom = update_geom(shape_obj, scenario, first_start_x, first_start_y)
                        row[0] = new_geom
                        snap_df.at[this_oid, 'start'] = 'snapped - done'
                        snap_df.at[first_oid, 'start'] = 'static - done'
                        cnt += 1
            if skipped:
                ucursor.deleteRow()
            else:
                ucursor.updateRow(row)

    item_number += 1

print(f'Total count of snapping areas: {item_number}')
print(f'Total count of multipart features: {multi}')
print(f'Total count of deleted features: {deletes}')

# Go back through data and update the comment fields (snap_start, snap_end) based on snap_df
snap_count = 0
oid_list = snap_df.index.to_list()
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
        ucursor.updateRow(row)
print(f'Total count of snap field comment updates: {snap_count}')


# OTHER IDEAS #
# SPEED UP
# Calculate lat/lons and h3s in dataframe/lambdas (might need to project to WGS84)
# SORTING
# Current sorting occasionally has a NEAR_DIST null at the top (due to ASC)
#   This results in no snapping because other points aren't within 4m
#   Maybe sort NEAR_DIST DESC


print("Script shutting down ...")
# Stop timer and print end time
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))