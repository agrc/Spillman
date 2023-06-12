# -*- coding: utf-8 -*-
"""
Created on Wed Mar 20 07:46:12 2019

@author: eneemann

EMN: As of 18 Jan 2019, this code should be ready for operational use.
EMN: On 20 Mar 2019, converted to Python 3.
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

utm_db = r"C:\E911\MillardCo\MillardCo_UTM.gdb"
wgs84_db = r"C:\E911\MillardCo\MIllard_Co_WGS84.gdb"
# utm_db = r"C:\Users\eneemann\Desktop\Neemann\Spillman\TestData\MillardCo\TEST_MillardCo_UTM.gdb"
# wgs84_db = r"C:\Users\eneemann\Desktop\Neemann\Spillman\TestData\MillardCo\TEST_MIllard_Co_WGS84.gdb"
# env.workspace = r"C:\Users\eneemann\Desktop\Neemann\Spillman\MillardCo"
env.workspace = utm_db
env.overwriteOutput = True
fc_layer = "Streets"
streets_fc_utm = os.path.join(utm_db, fc_layer)
streets_cad_wgs84 = os.path.join(wgs84_db, "Streets_CAD")

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
            # print("{} appended to field_list".format(field.name)
            field_list.append(field)

    with arcpy.da.UpdateCursor(streets, flist) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            # print row
            for i in range(len(field_list)):
                # if (field_list[i].type == "String" and row[i] == '') or\
                #         (field_list[i].type == "String" and row[i] == ' '):
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
    # where_clause = "ALIAS2 IS NOT NULL AND SALIAS1 IS NULL AND STREETTYPE <> 'RAMP' AND STREETTYPE <> 'FWY'"
    where_clause = """ALIAS2 IS NOT NULL AND SALIAS2 IS NULL AND STREETTYPE <> 'RAMP' AND STREETTYPE <> 'FWY' OR
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
    # NOTE: it appears redundant to use the same where_clause twice
    arcpy.MakeFeatureLayer_management(streets, "streets_lyr", where_clause)
    # Select where streets are not NULL and have valid address ranges
    sel = arcpy.SelectLayerByAttribute_management("streets_lyr", "NEW_SELECTION", where_clause)
    # Export selected streets to 'Streets_CAD' feature class
    outname = os.path.join(utm_db, "Streets_CAD")
    print("Exporting {} ...".format(outname))
    arcpy.CopyFeatures_management(sel, outname)


# NEED FUNCTION TO CREATE ADDRESS POINTS CAD
def create_address_pts_CAD(addpts):
    where_clause = "FULLADDR NOT LIKE '% UNIT%' AND FULLADDR NOT LIKE '% TRLR%' AND FULLADDR NOT LIKE '% APT%' AND" \
                   " FULLADDR NOT LIKE '% STE%' AND FULLADDR NOT LIKE '% SPC%' AND FULLADDR NOT LIKE '% BSMT%' AND" \
                   " FULLADDR NOT LIKE '% LOT%' AND FULLADDR NOT LIKE '% #%' AND FULLADDR NOT LIKE '% BLDG%' AND" \
                   " FULLADDR NOT LIKE '% HNGR%' AND FULLADDR NOT LIKE '% OFC%'"
    # Need to make layer from feature class here
    arcpy.MakeFeatureLayer_management(addpts, "addpts_lyr", where_clause)
    # Select where streets are not NULL and have valid address ranges
    sel = arcpy.SelectLayerByAttribute_management("addpts_lyr", "NEW_SELECTION", where_clause)
    # Export selected streets to 'AddressPoints_CAD' feature class
    addpts_CAD = os.path.join(utm_db, "StGeorge_Dispatch_AddressPoints_CAD")
    print("Exporting {} ...".format(addpts_CAD))
    arcpy.CopyFeatures_management(sel, addpts_CAD)


def combine_address_pts(addpts, add_CAD, add_mm, add_all):
    # Create address_pts_CAD
    where_clause = "FULLADDR NOT LIKE '% UNIT%' AND FULLADDR NOT LIKE '% TRLR%' AND FULLADDR NOT LIKE '% APT%' AND" \
                   " FULLADDR NOT LIKE '% STE%' AND FULLADDR NOT LIKE '% SPC%' AND FULLADDR NOT LIKE '% BSMT%' AND" \
                   " FULLADDR NOT LIKE '% LOT%' AND FULLADDR NOT LIKE '% #%' AND FULLADDR NOT LIKE '% BLDG%' AND" \
                   " FULLADDR NOT LIKE '% HNGR%' AND FULLADDR NOT LIKE '% OFC%'"
    # Need to make layer from feature class here
    arcpy.MakeFeatureLayer_management(addpts, "addpts_lyr", where_clause)
    sel = arcpy.SelectLayerByAttribute_management("addpts_lyr", "NEW_SELECTION", where_clause)
    # Export selected streets to 'AddressPoints_CAD' feature class
    # addpts_CAD = os.path.join(utm_db, "AddressPoints_CAD")
    print("Exporting {} ...".format(add_CAD))
    arcpy.CopyFeatures_management(sel, add_CAD)
        
    # Get address points into a single FC
    print("Combining address point data into {} ...".format(add_all))
    arcpy.CopyFeatures_management(add_CAD, add_all)
    arcpy.MakeFeatureLayer_management(add_mm, "add_mm_lyr")
    
    # Field Map milemarkers into addpts_CAD schema
    fms = arcpy.FieldMappings()
    
    # NAME to DsplayName
    fm_name = arcpy.FieldMap()
    fm_name.addInputField("add_mm_lyr", "ADDRESS")
    output = fm_name.outputField
    output.name = "FULLADDR"
    fm_name.outputField = output
    fms.addFieldMap(fm_name)
    
    # NAME to Agency_ID
    fm_agency = arcpy.FieldMap()
    fm_agency.addInputField("add_mm_lyr", "NUMB")
    output = fm_agency.outputField
    output.name = "ADDRNUM"
    fm_agency.outputField = output
    fms.addFieldMap(fm_agency)
    
    # Complete the append with field mapping
    arcpy.management.Append("add_mm_lyr", add_all, "NO_TEST", field_mapping=fms)

    # Project "AddressPoints_CAD_All" into WGS84
    print("Project UTM data into WGS84 ...")
    add_all_wgs84 = os.path.join(wgs84_db, "AddressPoints_CAD_All")
    sr = arcpy.SpatialReference("WGS 1984")
    arcpy.Project_management(add_all, add_all_wgs84, sr, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Calculate XY values for points without them (WGS84 coords)
    print("Calculating XY values in WGS84 ...")
    arcpy.AddXY_management(add_all_wgs84)
    
    # Rename fields to just "X" and "Y"
    print("Renaming X and Y fields ...")
    arcpy.AlterField_management(add_all_wgs84, 'POINT_X', 'X')
    arcpy.AlterField_management(add_all_wgs84, 'POINT_Y', 'Y')


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
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "SALIAS2" field
    # where_clause = ""
    fields = ['LCITYCD', 'RCITYCD', 'LZ_LEFT', 'LZ_RIGHT', 'LA_LEFT', 'LA_RIGHT', 'FZ_LEFT', 'FZ_RIGHT',
              'FA_LEFT', 'FA_RIGHT', 'EZ_LEFT', 'EZ_RIGHT', 'EA_LEFT', 'EA_RIGHT']
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for index, field in enumerate(fields):
                row[index] = None
                update_count += 1
            cursor.updateRow(row)
    print("Total count of updates from to null is: {}".format(update_count))


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


#######################################
#  Prep variables for function calls  #
#######################################

WGS84_files_to_delete = ["AddressPoints", "AddressPoints_CAD_All", "Boundary_County", "CityCodes", "CommonPlaces",
                         "CommonPlaces_MP", "EMSAreas", "EMSZones", "FireAreas", "FireZones", "LawAreas", "LawZones",
                         "Streets", "Streets_CAD", "tbzones"]
UTM_files_to_delete = ["AddressPoints_CAD", "AddressPoints_CAD_All", "Streets_CAD"]

# Create variables for address points
address_pts = os.path.join(utm_db, "AddressPoints")
address_pts_CAD = os.path.join(utm_db, "AddressPoints_CAD")
address_pts_MM = os.path.join(utm_db, "AddressPoints_CAD_Milemarkers")
address_pts_all = os.path.join(utm_db, "AddressPoints_CAD_All")

# Create variable for tbzones
tbzones = os.path.join(utm_db, "tbzones")

# Create variables for projecting
FCs_to_project = ["AddressPoints", "Boundary_County", "CityCodes", "CommonPlaces", "CommonPlaces_MP",
                  "EMSAreas", "EMSZones", "FireAreas", "FireZones", "LawAreas", "LawZones", "Streets", "Streets_CAD"]

######################################################################################################################
#  There are two options for exporting shapefiles.  Choose desired option and comment out the other before running:  #
#  Option 1: Exports ALL FCs to shapefiles in bulk and includes all fields in the output                             #
#  Option 2: Individually exports each FC to shapefile, trims output down to specified fields                        #
######################################################################################################################

# Create variables for shapefiles
FCs_to_export = FCs_to_project
today = time.strftime("%Y%m%d")
spill_dir = r"C:\E911\MillardCo\0 Shapefiles"
spillman_folder = "Spillman_Shapefiles_Millard_" + today
out_folder_spillman = os.path.join(spill_dir, spillman_folder)
vela_dir = r"C:\E911\MillardCo\0 Vela Files"
vela_folder = "Vela_Shapefiles_Millard_" + today
out_folder_vela = os.path.join(vela_dir, vela_folder)


# Comment out this line if the folder already exists (like if code was already run once today)
if os.path.isdir(out_folder_spillman) == False:
    os.mkdir(out_folder_spillman)
if os.path.isdir(out_folder_vela) == False:
    os.mkdir(out_folder_vela)

# Option 1: Exports ALL FCs to shapefiles in bulk and includes all fields in the output
# export_shapefiles_all_fields(FCs_to_export, out_folder_spillman)
# Option 2: Individually exports each FC to shapefile, trims output down to specified fields
# -----> See last set of function calls

addpt_fields = ["FULLADDR", "LABEL"]
commplc_fields = ["ALIAS", "ADDRESS"]
milepost_fields = ["ALIAS", "XCOORD", "YCOORD"]
street_fields = ["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD", "ZIPLEFT", "ZIPRIGHT", "STREET", "LCITYCD", "RCITYCD"]
earea_fields = ["DESCRIPTION", "ABBR", "Shape_Length", "Shape_Area"]
ezone_fields = ["DESCRIPTION", "ABBR", "Shape_Length", "Shape_Area"]
farea_fields = ["DESCRIPTION", "ABBR", "Shape_Length", "Shape_Area"]
fzone_fields = ["DESCRIPTION", "ABBR", "Shape_Length", "Shape_Area"]
larea_fields = ["desc", "abbr", "Shape_Length", "Shape_Area"]
lzone_fields = ["DESCRIPTION", "ABBR", "Shape_Length", "Shape_Area"]
citycd_fields = ["NAME", "CITYCD", "Shape_Length", "Shape_Area"]
# other_fields = ["NAME", "CITYCD", "Length", "Area"]

##########################
#  Call Functions Below  #
##########################

create_new_gdbs(utm_db, wgs84_db, UTM_files_to_delete, WGS84_files_to_delete)
blanks_to_nulls(streets_fc_utm)
calc_street(streets_fc_utm)
calc_salias1(streets_fc_utm)
calc_salias2(streets_fc_utm)
calc_salias4(streets_fc_utm)
highway_to_sr_us(streets_fc_utm)
calc_salias3(streets_fc_utm)
street_blank_to_null(streets_fc_utm)
calc_location(streets_fc_utm)
create_streets_CAD(streets_fc_utm)
combine_address_pts(address_pts, address_pts_CAD, address_pts_MM, address_pts_all)
copy_tbzones(tbzones)
project_to_wgs84(FCs_to_project)
spillman_polygon_prep(streets_cad_wgs84)

################################################################
# Run code to here, then pause to use Spillman tools in ArcMap #
################################################################
#env.workspace = wgs84_db
export_shapefiles_select_fields("AddressPoints", out_folder_spillman, addpt_fields)
# export_shapefiles_select_fields("CommonPlaces", out_folder_spillman, commplc_fields)
#export_shapefiles_select_fields("Mileposts", out_folder_spillman, milepost_fields)
export_shapefiles_select_fields("Streets", out_folder_spillman, street_fields)
#export_shapefiles_select_fields("EMSAreas", out_folder_spillman, earea_fields)
#export_shapefiles_select_fields("EMSZones", out_folder_spillman, ezone_fields)
#export_shapefiles_select_fields("FireAreas", out_folder_spillman, farea_fields)
#export_shapefiles_select_fields("FireZones", out_folder_spillman, fzone_fields)
export_shapefiles_select_fields("LawAreas", out_folder_spillman, larea_fields)
#export_shapefiles_select_fields("LawZones", out_folder_spillman, lzone_fields)
export_shapefiles_select_fields("CityCodes", out_folder_spillman, citycd_fields)
# export_shapefiles_select_fields("_other_", out_folder_spillman, other_fields)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))

