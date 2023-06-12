# -*- coding: utf-8 -*-
"""
Created on Mon Jan 9 08:349:21 2023
@author: eneemann
Script to build Layton/Davis County QuickestRoute network
- adds 'link' streets to regular splits
- splits streets where features cross over each other
- snaps endpoints and deletes small segments (<4m)
- creates network dataset from template
- builds road network

"""

import arcpy
from arcpy import env
import os
import time
import pandas as pd
import h3
from tqdm import tqdm
import math
from arcgis.features import GeoAccessor, GeoSeriesAccessor

# Initialize the tqdm progress bar tool
tqdm.pandas()
pd.options.mode.chained_assignment = None  # default='warn'

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Set up directories and variables
geo_db = r'C:\E911\Layton\DavisGeoValidation.gdb'
staging_db = r'C:\E911\Layton\Davis_staging.gdb'
davis_streets = os.path.join(geo_db, 'DavisStreets')
streets_plus_links = os.path.join(staging_db, f'DavisStreets_w_Links_{today}')
links = os.path.join(geo_db, 'DavisStreets_schema_QR_Links')
split_streets = os.path.join(staging_db, f'split_streets_{today}')

##########################################
# Set up user variables for auto-snapper #
##########################################

snap_radius = 4  # in meters
current_name = 'DavisStreets'
current_streets = streets_plus_links
output_db = staging_db
work_dir = r'C:\E911\Layton\working_data'

# Set up the environment and workspace
env.workspace = staging_db
env.overwriteOutput = True
env.qualifiedFieldNames = False

temp_streets = os.path.join(output_db, f"St_snap_working_{today}")
temp_for_splits = os.path.join(output_db, f"zzz_temp_for_splits_{today}")
working_streets = os.path.join(output_db, f"St_snap_working_UTM_{today}")
st_endpoints = os.path.join(output_db, f"St_snap_endpoints_{today}")
join_name = os.path.join(output_db, f"neartable_join_{today}")
endpts_fc = os.path.join(output_db, f"zzz_endpts_to_snap_{today}")
snapped = os.path.join(output_db, f"{current_name}_{today}_snapped")
snapped_wgs84 = os.path.join(output_db, f"{current_name}_{today}_snapped_WGS84")
n_table = os.path.join(output_db, f"Snap_near_table_{today}")

intermediate_files = [temp_streets, temp_for_splits, working_streets, st_endpoints, join_name, n_table, snapped]

sr_wgs84 = arcpy.SpatialReference(4326)
sr_utm = arcpy.SpatialReference(26912)


###########################################
# Set up user variables for QuickestRoute #
###########################################
Davis_dir = r"C:\E911\Layton"
Davis_db = geo_db
Davis_streets = snapped_wgs84
network_db = os.path.join(Davis_dir,'QuickestRoute_TEST_' + today +  '.gdb')
network_dataset = os.path.join(network_db, 'QuickestRoute')
env.workspace = network_db

def append_links():
    ### Append Links into DavisStreets
    arcpy.management.CopyFeatures(davis_streets, streets_plus_links)
    print(f"Adding {arcpy.management.GetCount(links)[0]} QR Links to DavisStreets ...")
    arcpy.management.Append(links, streets_plus_links, "NO_TEST")


def split_street_features():
    # Select and export links and segments within 4 meters
    print("Selecting links and intersecting streets ...")
    selection = arcpy.management.SelectLayerByLocation(streets_plus_links, "INTERSECT", links, f"{snap_radius} Meters", "NEW_SELECTION")
    arcpy.management.CopyFeatures(selection, temp_for_splits)
    
    # Delete those selected segments from the working roads
    arcpy.management.DeleteFeatures(selection)
    
    ### Run Feature to Line to split at intersections
    print("Splitting streets with Feature to Line ...")
    arcpy.management.FeatureToLine(temp_for_splits, split_streets, None, 'ATTRIBUTES')
    
    # Append splits segments back into the working roads
    print("Appending in split streets ...")
    arcpy.management.Append(split_streets, streets_plus_links, "NO_TEST")

def confirm_wgs84(current):
    # Check sr, project to WGS84 (if needed) or copy to temp_streets
    current_sr = arcpy.Describe(current).spatialReference

    if current_sr.factoryCode == 26912:
        print("Projecting features to working layer (WGS84) ...")
        arcpy.management.Project(current, temp_streets, sr_wgs84, "WGS_1984_(ITRF00)_To_NAD_1983")
    else:
        print("Copying features to working layer ...")
        arcpy.CopyFeatures_management(current, temp_streets)


def calc_endpoint_h3s(temp_st):
    # streets fc must be in wgs84
    # Add h3 index level 9 for start and end points
    arcpy.management.AddField(temp_st, "start_h3_9", "TEXT", "", "", 30)
    arcpy.management.AddField(temp_st, "end_h3_9", "TEXT", "", "", 30)

    h3_time = time.time()
    count = 0
    #             0          1            2
    fields = ['SHAPE@', 'start_h3_9', 'end_h3_9']
    with arcpy.da.UpdateCursor(temp_st, fields) as ucursor:
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
    print("Time elapsed calculating h3 indexes in update cursor: {:.2f}s".format(time.time() - h3_time))


def project_to_utm(temp_st):
    arcpy.management.Project(temp_st, working_streets, sr_utm, "WGS_1984_(ITRF00)_To_NAD_1983")


def create_endpoints(working_st):
    if arcpy.Exists(st_endpoints):
        arcpy.Delete_management(st_endpoints)
    arcpy.management.FeatureVerticesToPoints(working_st, st_endpoints, "BOTH_ENDS")


def calc_endpoint_lon_lat(st_endpts):
    # Project endpoints to WGS84, convert to spatial dataframe, calc lon/lat, convert to table, then join back to feature class (much faster this way)
    calc_time = time.time()
    st_endpts_wgs84 = os.path.join(output_db, f'endpts_wgs84_{today}')
    arcpy.management.Project(st_endpts, st_endpts_wgs84, sr_wgs84, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Convert to spatial dataframe and calc lat/lon fields
    endpts_wgs84_sdf = pd.DataFrame.spatial.from_featureclass(st_endpts_wgs84)
    endpts_wgs84_sdf['lon'] = endpts_wgs84_sdf.SHAPE.progress_apply(lambda p: p.x)
    endpts_wgs84_sdf['lat'] = endpts_wgs84_sdf.SHAPE.progress_apply(lambda p: p.y)

    # Convert SDF to table and join back to FC with JoinField
    # Simplify to dataframe, save as CSV, convert to ArcGIS table, then use JoinField
    keep_cols = ['OBJECTID', 'lon', 'lat']
    endpts_wgs84_df = endpts_wgs84_sdf[keep_cols]
    endpt_path = os.path.join(work_dir, 'temp_endpts.csv')
    endpts_wgs84_df.to_csv(endpt_path)
    endpt_table = os.path.join(output_db, f'endpts_table_{today}')
    arcpy.conversion.TableToTable(endpt_path, output_db, f'endpts_table_{today}')
    arcpy.management.JoinField(st_endpts, "OBJECTID", endpt_table, "OBJECTID", ["lon", "lat"])
    print("Time elapsed calculating lat/lon fields: {:.2f}s".format(time.time() - calc_time))

    # Delete in-memory temp data for lat/lon calculation
    if arcpy.Exists(st_endpts_wgs84):
        arcpy.Delete_management(st_endpts_wgs84)
    if arcpy.Exists(endpt_table):
        arcpy.Delete_management(endpt_table)


def generate_neartable_and_join_to_streets(st_endpts):
    # Create table name (in memory) for neartable
    neartable = 'in_memory\\near_table'
    # Perform near table analysis
    print("Generating near table ...")
    arcpy.analysis.GenerateNearTable(st_endpts, st_endpts, neartable, f'{snap_radius} Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 6, 'PLANAR')
    print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(neartable)))

    # Convert neartable to pandas dataframe for street join
    neartable_arr = arcpy.da.TableToNumPyArray(neartable, '*')
    near_df = pd.DataFrame(data = neartable_arr)
    print(near_df.head(5))

    # Convert endpts to spatial dataframe for endpoint fc
    print("Converting working end points to spatial dataframe ...")
    endpt_sdf = pd.DataFrame.spatial.from_featureclass(st_endpts)

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
    no_dups_fc.spatial.to_featureclass(location=endpts_fc)

    # Convert endpts to pandas dataframe for street join
    endpt_fields = [oid_fieldname, 'ORIG_FID', 'STREET']
    endpt_arr = arcpy.da.FeatureClassToNumPyArray(st_endpts, endpt_fields)
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
    if arcpy.Exists(join_name):
        arcpy.Delete_management(join_name)
    arcpy.TableToTable_conversion(no_dups_path, output_db, f"neartable_join_{today}")
    # Use JoinField instead of AddJoin for a cleaner schema
    arcpy.management.JoinField(working_streets, oid_fieldname, join_name, "ORIG_FID", ["IN_FID", "NEAR_FID", "NEAR_DIST", "NEAR_RANK"])
    arcpy.Delete_management('in_memory\\near_table')


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

    updated_shape = arcpy.Polyline(array, sr_utm)

    return updated_shape


def prep_snapped_fc(working_st):
    if arcpy.Exists(snapped):
        arcpy.Delete_management(snapped)
    arcpy.CopyFeatures_management(working_st, snapped)

    # Add field to use for auto-snapping
    arcpy.management.AddField(snapped, 'snap_start', 'TEXT', '', '', 30)
    arcpy.management.AddField(snapped, 'snap_end', 'TEXT', '', '', 30)
    arcpy.management.AddField(snapped, 'snap_status', 'TEXT', '', '', 30)


def prep_snap_df(snapped_fc):
    # Calculate new geometries and update fields
    # Get list of unique h3s and distances for selection queries
    print("Converting working roads to spatial dataframe ...")
    sdf = pd.DataFrame.spatial.from_featureclass(snapped_fc)
    not_zero = sdf[(sdf.NEAR_DIST > 0) & (sdf.NEAR_DIST is not None)]

    # Create dataframe from relevant oids to track start/endpoint snapping staus
    snapped_df = not_zero[['OBJECTID']].rename(columns={'OBJECTID': 'oid'}).set_index('oid')
    snapped_df['start'] = ''
    snapped_df['end'] = ''

    return snapped_df


def generate_neartable_for_snapping():
    # Create Near Table to get OIDs within 4m of each snap point
    print("Generating near table on snap points ...")
    arcpy.analysis.GenerateNearTable(endpts_fc, snapped, n_table, f'{snap_radius} Meters', 'NO_LOCATION', 'NO_ANGLE', 'ALL', 6, 'PLANAR')
    print("Number of rows in Near Table: {}".format(arcpy.GetCount_management(n_table)))

    # Get list of OIDs for use in selection queries within 4m of each point
    snap_areas = []
    with arcpy.da.SearchCursor(endpts_fc, ['OID@']) as scursor:
        for row in scursor:
            snap_areas.append(row[0])

    return snap_areas


def perform_snapping():
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


def update_comments():
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


def project_snapped():
    print("Projecting snapped features to WGS84 ...")
    arcpy.management.Project(snapped, snapped_wgs84, sr_wgs84, "WGS_1984_(ITRF00)_To_NAD_1983")


def delete_intermediate_files(file_list):
    for item in file_list:
        if arcpy.Exists(item):
            print(f'Deleting {item} ...')
            arcpy.Delete_management(item)


def create_network_db_and_template():
    if arcpy.Exists(network_db):
        arcpy.Delete_management(network_db)
    arcpy.CreateFileGDB_management(Davis_dir, 'QuickestRoute_TEST_' + today +  '.gdb')
    arcpy.CreateFeatureDataset_management(network_db, 'QuickestRoute', Davis_streets)
    
    print('Creating network template ...')
    output_xml_file = r"C:\E911\TOC\Network Dataset Template\NDTemplate.xml"
    
    return output_xml_file


def import_streets():
    print('Importing street data ...')
    net_streets = os.path.join(network_dataset, 'Streets')
    arcpy.CopyFeatures_management(Davis_streets, net_streets)
    
    return net_streets


def calc_network_fields(network_st):
    print('Calculating geometry (distance) ...')
    geom_start_time = time.time()
    arcpy.management.CalculateGeometryAttributes(network_st, [["Distance", "LENGTH_GEODESIC"]], "MILES_US", "", sr_utm)
    print("Time elapsed calculating geometry: {:.2f}s".format(time.time() - geom_start_time))
    
    #: Calculate travel time field
    update_count = 0
    #             0            1         2    
    fields = ['TrvlTime', 'Distance', 'SPEED']
    with arcpy.da.UpdateCursor(network_st, fields) as cursor:
        print("Looping through rows to calculate TrvlTime ...")
        for row in cursor:
            row[0] = (row[1]/row[2])*60
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of TrvlTime updates is {update_count}")
                                          
    #: Calculate "One_Way" field
    update_count_oneway = 0
    #                    0         1  
    fields_oneway = ['ONEWAY', 'One_Way']
    with arcpy.da.UpdateCursor(network_st, fields_oneway) as cursor:
        print("Looping through rows to calculate One_Way field ...")
        for row in cursor:
            if row[0] == '0' or row[0] == None:
                row[1] = 'B'
                update_count_oneway += 1
            elif row[0] == '1':
                row[1] = 'FT'
                update_count_oneway += 1
            elif row[0] == '2':
                row[1] = 'TF'
                update_count_oneway += 1
            cursor.updateRow(row)
    print(f"Total count of One_Way updates is {update_count_oneway}")

    #: Recalculate travel times based on multiplication factors
    #: Interstates to not get an additional multiplication factor applied

    #: First, multiply all "other" streets by 2
    update_count2 = 0
    #              0
    fields2 = ['TrvlTime', 'Multiplier']
    # where_clause2 = "HWYNAME IS NULL AND (STREETTYPE IS NULL OR STREETTYPE <> 'RAMP')"
    # 12/17/2020 Update: simplified to 'HWYNAME IS NULL' and calculated first to improve QR FIXES
    where_clause2 = "HWYNAME IS NULL AND (STREETTYPE IS NULL OR STREETTYPE <> 'RAMP')"
    with arcpy.da.UpdateCursor(network_st, fields2, where_clause2) as cursor:
        print("Looping through rows to multiply TrvlTime on all other roads ...")
        for row in cursor:
            row[0] = row[0]*2
            row[1] = 2
            update_count2 += 1
            cursor.updateRow(row)
    print(f"Total count of TrvlTime updates (x2) is {update_count2}")

    #: Second, multiply state and federal highways by 1.5
    update_count1 = 0
    #              0
    fields1 = ['TrvlTime', 'Multiplier']
    # where_clause1 = "HWYNAME IS NOT NULL AND HWYNAME NOT IN ('I-15', 'I-80', 'I-84') AND STREETTYPE <> 'RAMP'"
    # 3/11/2019 Update: added 'STREETTYPE IS NULL' to where clause to catch highway segments correctly
    # 1/2/2020 Update: added some segments with 'QR FIX' in HWYNAME field to improve routing with 1.5 multiplier
    # where_clause1 = "HWYNAME IS NOT NULL AND HWYNAME NOT LIKE 'I-%' AND (STREETTYPE <> 'RAMP' OR STREETTYPE IS NULL)"
    where_clause1 = """(HWYNAME IS NOT NULL AND HWYNAME NOT LIKE 'I-%') OR STREETTYPE = 'RAMP' OR \
    (HWYNAME IS NOT NULL AND HWYNAME NOT LIKE 'I-%' AND STREETTYPE IS NULL)"""
    with arcpy.da.UpdateCursor(network_st, fields1, where_clause1) as cursor:
        print("Looping through rows to multiply TrvlTime on state and federal highways ...")
        for row in cursor:
            row[0] = row[0]*1.5
            row[1] = 1.5
            update_count1 += 1
            cursor.updateRow(row)
    print(f"Total count of TrvlTime updates (x1.5) is {update_count1}")


    #: Third, populate Multiplier field with 1 for interstates and ramps
    update_count3 = 0
    #              0
    fields3 = ['Multiplier']
    # where_clause3 = "(HWYNAME IS NOT NULL AND HWYNAME LIKE 'I-%') OR STREETTYPE = 'RAMP'"
    where_clause3 = """HWYNAME IS NOT NULL AND HWYNAME LIKE 'I-%'"""
    with arcpy.da.UpdateCursor(network_st, fields3, where_clause3) as cursor:
        print("Looping through rows to assign Multiplier on ramps and interstates ...")
        for row in cursor:
            row[0] = 1
            update_count3 += 1
            cursor.updateRow(row)
    print(f"Total count of ramp and interstate (x1) updates is {update_count3}")


def create_and_build_network():
    #: Create the new network dataset in the output location using the template.
    #: The output location must already contain feature classes with the same
    #: names and schema as the original network
    arcpy.nax.CreateNetworkDatasetFromTemplate(xml_template, network_dataset)
    print("Done creating network, now building it ...")

    #: Build the new network dataset
    arcpy.nax.BuildNetwork(os.path.join(network_dataset, "QuickestRoute_ND"))
    print("Done building the network ...")


##################
# Call Functions #
##################
#: Prep Functions
append_links()
split_street_features()

#: Auto-Snapper Functions
confirm_wgs84(current_streets)
calc_endpoint_h3s(temp_streets)
project_to_utm(temp_streets)
oid_fieldname = arcpy.Describe(working_streets).OIDFieldName
create_endpoints(working_streets)
calc_endpoint_lon_lat(st_endpoints)
generate_neartable_and_join_to_streets(st_endpoints)
prep_snapped_fc(working_streets)
snap_df = prep_snap_df(snapped)
snap_area_oids = generate_neartable_for_snapping()
perform_snapping()
update_comments()
project_snapped()
delete_intermediate_files(intermediate_files)

#: Quickest Route Functions
# Check out Network Analyst license if available. Fail if the Network Analyst license is not available.
if arcpy.CheckExtension("network") == "Available":
    arcpy.CheckOutExtension("network")
else:
    raise arcpy.ExecuteError("Network Analyst Extension license is not available.")

xml_template = create_network_db_and_template()
network_streets = import_streets()
calc_network_fields(network_streets)
create_and_build_network()

arcpy.CheckInExtension("network")



print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))