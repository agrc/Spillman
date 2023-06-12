# -*- coding: utf-8 -*-
"""
Created on Thu May 23 12:26:17 2019
@author: eneemann

EMN: On 23 May 2019, created initial Richfield script from StGeorge script
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

utm_db = r"C:\E911\RichfieldComCtr\richfield_comctr_UTM.gdb"
wgs84_db = r"C:\E911\RichfieldComCtr\richfield_comctr_WGS84.gdb"
env.workspace = utm_db
fc_layer = "streets"
streets_fc_utm = os.path.join(utm_db, fc_layer)
streets_cad_wgs84 = os.path.join(wgs84_db, "streets_CAD")

###############
#  Functions  #
###############

def create_new_gdbs(original_utm, original_wgs84, UTM_delete_files, WGS84_delete_files):
    # Creates new GDBs by renaming originals with today's date
    # Then copies new ones (with today's date) with original name
    # This allows original name to be used/edited, but work is done on a new and fresh copy
    today = time.strftime("%Y%m%d")
    # rename original GDBs with today's date appended (YYYYMMDD)
    new_name_utm = os.path.splitext(original_utm)[0] + "_" + today + ".gdb"
    new_name_wgs84 = os.path.splitext(original_wgs84)[0] + "_" + today + ".gdb"
    print("Renaming UTM gdb to: {} ...".format(new_name_utm.split("\\")[-1]))
    arcpy.Rename_management(original_utm, new_name_utm)
    print("Renaming WGS84 gdb to: {} ...".format(new_name_wgs84.split("\\")[-1]))
    arcpy.Rename_management(original_wgs84, new_name_wgs84)
    # copy original GDBs to new gdb with original name (no date)
    print("Copying UTM gdb to: {} ...".format(original_utm.split("\\")[-1]))
    arcpy.Copy_management(new_name_utm, original_utm)
    print("Copying WGS84 gdb to: {} ...".format(original_wgs84.split("\\")[-1]))
    arcpy.Copy_management(new_name_wgs84, original_wgs84)
    # delete WGS84 and UTM files that will be recreated and reprojected later on
    env.workspace = original_wgs84
    print("Deleting old files from WGS84 gdb ...")
    for fc in WGS84_delete_files:
        if arcpy.Exists(fc):
            print("Deleting {} ...".format(fc))
            arcpy.Delete_management(fc)
    # reassign workspace to utm GDB
    env.workspace = original_utm
    print("Deleting old files from UTM gdb ...")
    for fc in UTM_delete_files:
        if arcpy.Exists(fc):
            print("Deleting {} ...".format(fc))
            arcpy.Delete_management(fc)


def blanks_to_nulls(streets):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'PREDIR', 'STREETNAME', 'STREETTYPE', 'SUFDIR', 'ALIAS1', 'ALIAS1TYPE', 'ALIAS2', 'ALIAS2TYPE',
              'ACSALIAS', 'ACSNAME', 'ACSSUF', 'SALIAS1', 'SALIAS2', 'SALIAS3', 'SALIAS4']
    fields = arcpy.ListFields(streets)

    field_list = []
    for field in fields:
        # print field.name
        if field.name in flist:
            # print("{} appended to field_list".format(field.name))
            field_list.append(field)

    with arcpy.da.UpdateCursor(streets, flist) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            # print row
            for i in range(len(field_list)):
                if row[i] == '' or row[i] == ' ':
                    print("Updating field: {0} on ObjectID: {1}".format(field_list[i].name, row[0]))
                    update_count += 1
                    row[i] = None
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))


def calc_street(streets):
    update_count = 0
    # Calculate "STREET" field where applicable
    where_clause = "STREETNAME IS NOT NULL AND STREET IS NULL"
    fields = ['PREDIR', 'STREETNAME', 'SUFDIR', 'STREETTYPE', 'STREET']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[0] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            if row[3] is None: row[3] = ''
            parts = [row[0], row[1], row[2], row[3]]
            row[4] = " ".join(parts)
            row[4] = row[4].lstrip().rstrip()
            row[4] = row[4].replace("  ", " ").replace("  ", " ").replace("  ", " ")
            print("New value for {0} is: {1}".format(fields[4], row[4]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0}: {1}".format(fields[4], update_count))


def calc_salias1(streets):
    update_count = 0
    # Calculate "SALIAS1" field where applicable
    # where_clause = "ALIAS1 IS NOT NULL"
    # where_clause = "ALIAS1 IS NOT NULL AND SALIAS1 IS NULL AND STREETTYPE <> 'RAMP' AND STREETTYPE <> 'FWY'"
    where_clause = """ALIAS1 IS NOT NULL AND SALIAS1 IS NULL AND STREETTYPE <> 'RAMP' AND STREETTYPE <> 'FWY' OR
    (ALIAS1 IS NOT NULL AND SALIAS1 IS NULL AND STREETTYPE IS NULL)"""
    fields = ['PREDIR', 'ALIAS1', 'ALIAS1TYPE', 'SALIAS1']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[0] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            parts = [row[0], row[1], row[2]]
            row[3] = " ".join(parts)
            row[3] = row[3].lstrip().rstrip()
            row[3] = row[3].replace("  ", " ").replace("  ", " ").replace("  ", " ")
            row[3] = row[3][:30]
            print("New value for {0} is: {1}".format(fields[3], row[3]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0}: {1}".format(fields[3], update_count))


def calc_salias2(streets):
    update_count = 0
    # Calculate "SALIAS2" field where applicable
    # where_clause = "ALIAS2 IS NOT NULL"
    # where_clause = "ALIAS2 IS NOT NULL AND SALIAS2 IS NULL AND STREETTYPE <> 'RAMP' AND STREETTYPE <> 'FWY'"
    where_clause = """(ALIAS2 IS NOT NULL AND SALIAS2 IS NULL AND STREETTYPE <> 'RAMP' AND STREETTYPE <> 'FWY') OR
    (ALIAS2 IS NOT NULL AND SALIAS2 IS NULL AND STREETTYPE IS NULL)"""
    fields = ['PREDIR', 'ALIAS2', 'ALIAS2TYPE', 'SALIAS2']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[0] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            parts = [row[0], row[1], row[2]]
            row[3] = " ".join(parts)
            row[3] = row[3].lstrip().rstrip()
            row[3] = row[3].replace("  ", " ").replace("  ", " ").replace("  ", " ")
            row[3] = row[3][:30]
            print("New value for {0} is: {1}".format(fields[3], row[3]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0}: {1}".format(fields[3], update_count))


def calc_salias4(streets):
    update_count = 0
    # Calculate "SALIAS4" field where applicable
    where_clause = "ACSNAME IS NOT NULL and SALIAS4 IS NULL"
    fields = ['PREDIR', 'ACSNAME', 'ACSSUF', 'SALIAS4']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[0] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            parts = [row[0], row[1], row[2]]
            row[3] = " ".join(parts)
            row[3] = row[3].lstrip().rstrip()
            row[3] = row[3].replace("  ", " ").replace("  ", " ").replace("  ", " ")
            row[3] = row[3][:30]
            print("New value for {0} is: {1}".format(fields[3], row[3]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0}: {1}".format(fields[3], update_count))


def highway_to_sr_us(streets):
    update_count1 = 0
    # Calculate updates on "SALIAS1" and change 'HIGHWAY' to 'SR'
    where_clause1 = "HWYNAME LIKE 'SR%' AND SALIAS1 LIKE '%HIGHWAY%'"
    fields1 = ['SALIAS1']
    with arcpy.da.UpdateCursor(streets, fields1, where_clause1) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "SR")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields1[0], row[0]))
            update_count1 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS1 'HIGHWAY' to 'SR' updates: {}".format(update_count1))

    update_count2 = 0
    # Calculate updates on "SALIAS1" and change 'HIGHWAY' to 'US'
    where_clause2 = "HWYNAME LIKE 'US%' AND SALIAS1 LIKE '%HIGHWAY%'"
    fields2 = ['SALIAS1']
    with arcpy.da.UpdateCursor(streets, fields2, where_clause2) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "US")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields2[0], row[0]))
            update_count2 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS1 'HIGHWAY' to 'US' updates: {}".format(update_count2))

    update_count3 = 0
    # Calculate updates on "SALIAS2" and change 'HIGHWAY' to 'SR'
    where_clause3 = "HWYNAME LIKE 'SR%' AND SALIAS2 LIKE '%HIGHWAY%'"
    fields3 = ['SALIAS2']
    with arcpy.da.UpdateCursor(streets, fields3, where_clause3) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "SR")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields3[0], row[0]))
            update_count3 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS2 'HIGHWAY' to 'SR' updates: {}".format(update_count3))

    update_count4 = 0
    # Calculate updates on "SALIAS2" and change 'HIGHWAY' to 'US'
    where_clause4 = "HWYNAME LIKE 'US%' AND SALIAS2 LIKE '%HIGHWAY%'"
    fields4 = ['SALIAS2']
    with arcpy.da.UpdateCursor(streets, fields4, where_clause4) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "US")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields4[0], row[0]))
            update_count4 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS2 'HIGHWAY' to 'US' updates: {}".format(update_count4))


def calc_salias3(streets):
    update_count1 = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "STREET" field
    where_clause1 = "HWYNAME LIKE 'US%' AND STREET LIKE '%US%'"
    fields1 = ['SALIAS3', 'STREET']
    with arcpy.da.UpdateCursor(streets, fields1, where_clause1) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            row[0] = row[0].replace("US", "HWY")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields1[0], row[0]))
            update_count1 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS3 updates based on {0} is: {1}".format(fields1[1], update_count1))

    update_count2 = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "STREET" field
    where_clause2 = "HWYNAME LIKE 'SR%' AND STREET LIKE '%SR%'"
    fields2 = ['SALIAS3', 'STREET']
    with arcpy.da.UpdateCursor(streets, fields2, where_clause2) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            row[0] = row[0].replace("SR", "HWY")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields2[0], row[0]))
            update_count2 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS3 updates based on {0} is: {1}".format(fields2[1], update_count2))

    update_count3 = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "SALIAS1" field
    where_clause3 = "HWYNAME LIKE 'US%' AND SALIAS1 LIKE '%US%'"
    fields3 = ['SALIAS3', 'SALIAS1']
    with arcpy.da.UpdateCursor(streets, fields3, where_clause3) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            row[0] = row[0].replace("US", "HWY")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields3[0], row[0]))
            update_count3 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS3 updates based on {0} is: {1}".format(fields3[1], update_count3))

    update_count4 = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "SALIAS1" field
    where_clause4 = "HWYNAME LIKE 'SR%' AND SALIAS1 LIKE '%SR%'"
    fields4 = ['SALIAS3', 'SALIAS1']
    with arcpy.da.UpdateCursor(streets, fields4, where_clause4) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            row[0] = row[0].replace("SR", "HWY")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields4[0], row[0]))
            update_count4 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS3 updates based on {0} is: {1}".format(fields4[1], update_count4))

    update_count5 = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "SALIAS2" field
    where_clause5 = "HWYNAME LIKE 'US%' AND SALIAS2 LIKE '%US%'"
    fields5 = ['SALIAS3', 'SALIAS2']
    with arcpy.da.UpdateCursor(streets, fields5, where_clause5) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            row[0] = row[0].replace("US", "HWY")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields5[0], row[0]))
            update_count5 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS3 updates based on {0} is: {1}".format(fields5[1], update_count5))

    update_count6 = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "SALIAS2" field
    where_clause6 = "HWYNAME LIKE 'SR%' AND SALIAS2 LIKE '%SR%'"
    fields6 = ['SALIAS3', 'SALIAS2']
    with arcpy.da.UpdateCursor(streets, fields6, where_clause6) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            row[0] = row[0].replace("SR", "HWY")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields6[0], row[0]))
            update_count6 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS3 updates based on {0} is: {1}".format(fields6[1], update_count6))


def street_blank_to_null(streets):
    update_count = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "SALIAS2" field
    where_clause = "STREET LIKE ''"
    fields = ['STREET']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = None
            print("New value for {0} is: {1}".format(fields[0], row[0]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of STREET updates from blank to null is: {}".format(update_count))


def calc_location(streets):
    # Calculate the "LOCATION" field with SALIAS4
    update_count = 0
    where_clause = "SALIAS4 IS NOT NULL AND LOCATION IS NULL"
    fields = ['LOCATION', 'SALIAS4']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            print("New value for {0} is: {1}".format(fields[0], row[0]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of LOCATION field updates in {0} is: {1}".format(streets, update_count))


def create_streets_CAD(streets):
    where_clause = "STREET IS NOT NULL AND (L_F_ADD > 0 OR R_F_ADD > 0)"
    # Need to make layer from feature class here
    arcpy.MakeFeatureLayer_management(streets, "streets_lyr", where_clause)
    # Select where streets are not NULL and have valid address ranges
    sel = arcpy.SelectLayerByAttribute_management("streets_lyr", "NEW_SELECTION", where_clause)
    # Export selected streets to 'streets_CAD' feature class
    outname = os.path.join(utm_db, "streets_CAD")
    print("Exporting {} ...".format(outname))
    arcpy.CopyFeatures_management(sel, outname)
    arcpy.Delete_management("streets_lyr")
    


# NEED FUNCTION TO CREATE ADDRESS POINTS CAD
def create_address_pts_CAD(addpts):
    where_clause = "ADDRESS NOT LIKE '% UNIT%' AND ADDRESS NOT LIKE '% TRLR%' AND ADDRESS NOT LIKE '% APT%' AND" \
                   " ADDRESS NOT LIKE '% STE%' AND ADDRESS NOT LIKE '% SPC%' AND ADDRESS NOT LIKE '% BSMT%' AND" \
                   " ADDRESS NOT LIKE '% LOT%' AND ADDRESS NOT LIKE '% #%' AND ADDRESS NOT LIKE '% BLDG%' AND" \
                   " ADDRESS NOT LIKE '% HNGR%' AND ADDRESS NOT LIKE '% OFC%' AND ADDRESS NOT LIKE '% SP %' AND" \
                   " ADDRESS NOT LIKE '% SP %' AND ADDRESS NOT LIKE '% HANGAR%' AND ADDRESS NOT LIKE '% COURT%' AND" \
                   " ADDRESS NOT LIKE '% POOL%' AND ADDRESS NOT LIKE '% CONFERENCE%' AND ADDRESS NOT LIKE '% HEALTH%' AND ADDRESS NOT LIKE '% BAR'"
    # Need to make layer from feature class here
    arcpy.MakeFeatureLayer_management(addpts, "addpts_lyr", where_clause)
    # Select where streets are not NULL and have valid address ranges
    sel = arcpy.SelectLayerByAttribute_management("addpts_lyr", "NEW_SELECTION", where_clause)
    # Export selected addpts to 'address_points_CAD' feature class
    addpts_CAD = os.path.join(utm_db, "address_points_CAD")
    print("Exporting {} ...".format(addpts_CAD))
    arcpy.CopyFeatures_management(sel, addpts_CAD)

    # Project "address_points_CAD" into WGS84
    print("Project UTM data into WGS84 ...")
    addpts_CAD_wgs84 = os.path.join(wgs84_db, "address_points_CAD")
    sr = arcpy.SpatialReference("WGS 1984")
    arcpy.Project_management(addpts_CAD, addpts_CAD_wgs84, sr, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Calculate XY values for points without them (WGS84 coords)
    print("Calculating XY values in WGS84 ...")
    arcpy.AddXY_management(addpts_CAD_wgs84)

    # Rename fields to just "X" and "Y"
    print("Renaming X and Y fields ...")
    arcpy.AlterField_management(addpts_CAD_wgs84, 'POINT_X', 'X')
    arcpy.AlterField_management(addpts_CAD_wgs84, 'POINT_Y', 'Y')


def copy_tbzones(tbzones_table):
    print("Copying tbzones table from UTM to WGS84 geodatabase ...")
    in_rows = tbzones_table
    arcpy.TableToTable_conversion(in_rows, wgs84_db, "tbzones")


def project_to_wgs84(input_features):
    print("Projecting the following datasets to WGS84 ...")
    for layer in input_features:
        print(layer)
    env.workspace = utm_db
    sr = arcpy.SpatialReference("WGS 1984")
    arcpy.BatchProject_management(input_features, wgs84_db, sr, "", "WGS_1984_(ITRF00)_To_NAD_1983")


def spillman_polygon_prep(streets):
    # Null out the appropriate data on streets layer
    update_count = 0
    # where_clause = ""
    fields = ['LCITYCD', 'RCITYCD', 'LZ_LEFT', 'LZ_RIGHT', 'LA_LEFT', 'LA_RIGHT', 'FZ_LEFT', 'FZ_RIGHT',
              'FA_LEFT', 'FA_RIGHT', 'EZ_LEFT', 'EZ_RIGHT', 'EA_LEFT', 'EA_RIGHT', 'MZ_LEFT', 'MZ_RIGHT', 'LS_ZONE']
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for index, field in enumerate(fields):
                row[index] = None
                update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to null is: {}".format(update_count))


def export_shapefiles_all_fields(input_features, folder):
    # Option 1: Exports ALL FCs to shapefiles in bulk and includes all fields in the output
    env.workspace = wgs84_db
    arcpy.FeatureClassToShapefile_conversion(input_features, folder)


def export_shapefiles_select_fields(fc, folder, field_list):
    print("Output folder is: {}".format(folder))
    print("Exporting {} to shapefile with the following fields:".format(fc))
    for field in field_list:
        print(field)
    env.workspace = wgs84_db
    infile = os.path.join(wgs84_db, fc)
    d = {}                              # create dictionary to hold FieldMap objects
    fms = arcpy.FieldMappings()         # create FieldMappings objects
    for index, field in enumerate(field_list):
        d["fm{}".format(index)] = arcpy.FieldMap()                              # create FieldMap object in dictionary
        d["fm{}".format(index)].addInputField(infile, field)                    # add input field
        # add output field
        d["fname{}".format(index)] = d["fm{}".format(index)].outputField
        d["fname{}".format(index)].name = field
        d["fm{}".format(index)].outputField = d["fname{}".format(index)]
        fms.addFieldMap(d["fm{}".format(index)])                                # add FieldMap to FieldMappings object
    arcpy.FeatureClassToFeatureClass_conversion(fc, folder, fc, field_mapping=fms)


def export_shapefiles_select_fields_rename(fc, folder, field_list, outname):
    print("Output folder is: {}".format(folder))
    print("Exporting {} to shapefile with the following fields:".format(fc))
    for field in field_list:
        print(field)
    env.workspace = wgs84_db
    infile = os.path.join(wgs84_db, fc)
    d = {}                              # create dictionary to hold FieldMap objects
    fms = arcpy.FieldMappings()         # create FieldMappings objects
    for index, field in enumerate(field_list):
        d["fm{}".format(index)] = arcpy.FieldMap()                              # create FieldMap object in dictionary
        d["fm{}".format(index)].addInputField(infile, field)                    # add input field
        # add output field
        d["fname{}".format(index)] = d["fm{}".format(index)].outputField
        d["fname{}".format(index)].name = field
        d["fm{}".format(index)].outputField = d["fname{}".format(index)]
        fms.addFieldMap(d["fm{}".format(index)])                                # add FieldMap to FieldMappings object
    arcpy.FeatureClassToFeatureClass_conversion(fc, folder, outname, field_mapping=fms)


def populate_LS_ZONE(streets, zones_fc):
    if arcpy.Exists("streets_lyr"):
        print("Deleting {} ...".format("streets_lyr"))
        arcpy.Delete_management("streets_lyr")
    env.workspace = wgs84_db
    # Need to create streets layer for select by location operation
    where_clause1 = "HWYNAME IS NOT NULL"
    arcpy.MakeFeatureLayer_management(streets, "streets_lyr", where_clause1)
    
    # Loop through features in LS_zones to get a list
    zone_list = []
    with arcpy.da.SearchCursor(zones_fc, "UHPLS") as sCursor:
        print("Looping through rows in LS_Zones ...")
        for row in sCursor:
            zone_list.append(row[0])
            print(row[0])
    print(zone_list)
    
    if arcpy.Exists("zone_lyr"):
        print("Deleting {} ...".format("zone_lyr"))
        arcpy.Delete_management("zone_lyr")
    # Loop through zone_list for each zone value
    for zone in zone_list:
        update_count = 0
        # Create layer for zone value
        where_temp = f"UHPLS = '{zone}'"
        print(where_temp)
        arcpy.MakeFeatureLayer_management(zones_fc, "zone_lyr", where_temp)
        # Select street segments that intersect zone
        arcpy.SelectLayerByLocation_management("streets_lyr", "HAVE_THEIR_CENTER_IN", "zone_lyr",
                                               "", "NEW_SELECTION")
        # Update LS_ZONE field to zone value
        with arcpy.da.UpdateCursor("streets_lyr", "LS_ZONE") as uCursor:
            print(f"Calculating LS_ZONE to {zone} ...")
            for row in uCursor:
                row[0] = zone
                update_count += 1
                uCursor.updateRow(row)
            print(f"Number of updates to {zone} is: {update_count}")
        # Delete temporary zone layer
        arcpy.Delete_management("zone_lyr")


#######################################
#  Prep variables for function calls  #
#######################################

WGS84_files_to_delete = ["address_points", "address_points_CAD",
                         "citycodes", "common_places",
                         "ems_zones", "fire_zones", "law_zones", "MZ_Zones",
                         "streets", "streets_CAD", "tbzones", "common_places_Exits",
                         "common_places_Mileposts", "municipalities"]
UTM_files_to_delete = ["address_points_CAD", "streets_CAD"]

# Create variables for address points
address_pts = os.path.join(utm_db, "address_points")

# Create variable for tbzones
tbzones = os.path.join(utm_db, "tbzones")

# Create variables for projecting
FCs_to_project = ["address_points", "citycodes",
                  "common_places", "ems_zones",
                  "fire_zones", "law_zones", "streets", "MZ_Zones",
                  "streets_CAD", "municipalities",
                  "common_places_Exits", "common_places_Mileposts"]

# Create variables for populating LS zones
ls_zones = os.path.join(wgs84_db, "UHP_LS_Zones")

######################################################################################################################
#  There are two options for exporting shapefiles.  Choose desired option and comment out the other before running:  #
#  Option 1: Exports ALL FCs to shapefiles in bulk and includes all fields in the output                             #
#  Option 2: Individually exports each FC to shapefile, trims output down to specified fields                        #
######################################################################################################################

# Create variables for shapefiles
FCs_to_export = FCs_to_project
today = time.strftime("%Y%m%d")
spill_dir = r"C:\E911\RichfieldComCtr\0 Shapefiles"
spillman_folder = "Spillman_Shapefiles_Richfield_" + today
out_folder_spillman = os.path.join(spill_dir, spillman_folder)
vela_dir = r"C:\E911\RichfieldComCtr\0 Vela Files"
vela_folder = "Vela_Shapefiles_Richfield_" + today
out_folder_vela = os.path.join(vela_dir, vela_folder)

# Comment out this line if the folder already exists (like if code was already run once today)
if os.path.isdir(out_folder_spillman) == False:
    os.mkdir(out_folder_spillman)
if os.path.isdir(out_folder_vela) == False:
    os.mkdir(out_folder_vela)

# Option 1: Exports ALL FCs to shapefiles in bulk and includes all fields in the output
# export_shapefiles_all_fields(FCs_to_export, out_folder)
# Option 2: Individually exports each FC to shapefile, trims output down to specified fields
# -----> See last set of function calls

# Spillman Shapefile field lists
addpt_fields = ["ADDRESS", "LABEL"]
citycd_fields = ["NAME", "CITYCD", "Shape_Length", "Shape_Area"]
commplc_fields = ["ALIAS", "ADDRESS"]
exit_fields = ["ALIAS"]
milepost_fields = ["ALIAS"]
ezone_fields = ["NAME", "EMSZONE", "EMS_AREA", "Shape_Length", "Shape_Area"]
fzone_fields = ["GRIDNAME", "FIREZONE", "FIREAREA", "Shape_Length", "Shape_Area"]
lzone_fields = ["AGENCY_NAME", "L_ZONE", "L_AREA", "Shape_Length", "Shape_Area"]
muni_fields = ["NAME", "Shape_Length", "Shape_Area"]
mzone_fields = ["NAME", "MZ_ID", "Shape_Length", "Shape_Area"]
street_fields = ["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD", "ZIPLEFT", "ZIPRIGHT", "STREET", "LCITYCD", "RCITYCD"]



# Spillman shapefile outnames
exits_out = "exits"
mileposts_out = "mileposts"

# Vela Shapefile field lists
vela_addpt_fields = ["ADDRESS", "PrefixDir", "StreetName", "StreetType", "SuffixDir", "UnitID", "STREET", "X",
                     "Y"] #, "ZipCode", "State", "COMM"]
vela_citycd_fields = ["NAME", "CITYCD"]
vela_commplc_fields = ["ALIAS", "CITYCD", "STREET", "BEGNUMB", "ENDNUMB", "ADDRESS"]
vela_milepost_fields = ["ROUTE", "MP", "FULLMPNAME"]
vela_law_fields = ["L_ZONE", "L_AREA", "AGENCY_NAME"]
vela_muni_fields = ["NAME"]
vela_mz_fields = ["NAME", "MZ_ID"]
vela_street_fields = ["CARTOCODE", "L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD", "PREDIR", "STREETNAME", "STREETTYPE",
                      "SUFDIR", "ALIAS1", "ALIAS1TYPE", "ALIAS2", "ALIAS2TYPE", "ACSALIAS", "ACSNAME", "ACSSUF",
                      "ZIPLEFT", "ZIPRIGHT", "STREET", "COMM_LEFT", "COMM_RIGHT", "Shape_Length"]

# Vela Shapefile outnames
vela_addpt_out = "AddressPoints"
vela_citycd_out = "CityCodes"
vela_commplc_out = "CommonPlacePoints"
vela_milepost_out = "Mileposts"
vela_law_out = "LawZones"
vela_muni_out = "Cities"
vela_mz_out = "MZZones"
vela_street_out = "Streets"


# Additional Vela Shapefiles to export
vela_to_export = ["ems_zones", "fire_zones", "law_zones"]

##########################
#  Call Functions Below  #
##########################

# create_new_gdbs(utm_db, wgs84_db, UTM_files_to_delete, WGS84_files_to_delete)
# blanks_to_nulls(streets_fc_utm)
# calc_street(streets_fc_utm)
# calc_salias1(streets_fc_utm)
# calc_salias2(streets_fc_utm)
# calc_salias4(streets_fc_utm)
# highway_to_sr_us(streets_fc_utm)
# calc_salias3(streets_fc_utm)
# street_blank_to_null(streets_fc_utm)
# calc_location(streets_fc_utm)
# create_streets_CAD(streets_fc_utm)
# create_address_pts_CAD(address_pts)
# copy_tbzones(tbzones)
# project_to_wgs84(FCs_to_project)
# spillman_polygon_prep(streets_cad_wgs84)


#################################################################
# Run code to here, then pause to use Spillman tools in ArcMap. #
# When complete, run code below to calc LS & export shapefiles  #
#################################################################

# Assign LS_Zones to streets_CAD (wgs84) segments
# populate_LS_ZONE(streets_cad_wgs84, ls_zones)

# Spillman Shapefiles Export
export_shapefiles_select_fields("address_points", out_folder_spillman, addpt_fields)
export_shapefiles_select_fields("citycodes", out_folder_spillman, citycd_fields)
export_shapefiles_select_fields("common_places", out_folder_spillman, commplc_fields)
#export_shapefiles_select_fields_rename("common_places_Exits", out_folder_spillman, exit_fields, exits_out)
#export_shapefiles_select_fields_rename("common_places_Mileposts", out_folder_spillman, milepost_fields, mileposts_out)
#export_shapefiles_select_fields("ems_zones", out_folder_spillman, ezone_fields)
#export_shapefiles_select_fields("fire_zones", out_folder_spillman, fzone_fields)
export_shapefiles_select_fields("law_zones", out_folder_spillman, lzone_fields)
export_shapefiles_select_fields("municipalities", out_folder_spillman, muni_fields)
export_shapefiles_select_fields("MZ_Zones", out_folder_spillman, mzone_fields)
export_shapefiles_select_fields("streets", out_folder_spillman, street_fields)


#export_shapefiles_all_fields(vela_to_export, out_folder_vela)
#env.workspace = out_folder_vela
#arcpy.Rename_management("COMMUNITY.shp", "Communities.shp")
#arcpy.Rename_management("law_zones.shp", "LawZones.shp")

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
