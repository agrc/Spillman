# -*- coding: utf-8 -*-
"""
Created on Wed May 29 12:19:19 2019
@author: eneemann

EMN: On 29 May 2019, created original script to generate Richfield's Vela shapefiles
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))


wgs84_db = r"C:\E911\RichfieldComCtr\richfield_comctr_WGS84.gdb"
vela_db = r"C:\E911\RichfieldComCtr\VelaData.gdb"
env.workspace = wgs84_db

###############
#  Functions  #
###############

def create_new_vela_gdb(original_vela, vela_delete_files):
    # Creates new GDB by renaming original with today's date
    # Then copy new one (with today's date) with original name
    # This allows original name to be used/edited, but work is done on a new and fresh copy
    today = time.strftime("%Y%m%d")
    # rename original GDB with today's date appended (YYYYMMDD)
    new_name_vela = os.path.splitext(original_vela)[0] + "_" + today + ".gdb"
    print("Renaming vela gdb to: {} ...".format(new_name_vela.split("\\")[-1]))
    arcpy.Rename_management(original_vela, new_name_vela)
    # copy original GDBs to new gdb with original name (no date)
    print("Copying vela gdb to: {} ...".format(original_vela.split("\\")[-1]))
    arcpy.Copy_management(new_name_vela, original_vela)
    # delete files that will be recreated later on
    # reassign workspace to vela GDB
    env.workspace = original_vela
    print("Deleting old files from vela gdb ...")
    for fc in vela_delete_files:
        if arcpy.Exists(fc):
            print("Deleting {} ...".format(fc))
            arcpy.Delete_management(fc)
    env.workspace = wgs84_db


def export_shapefiles_select_fields(fc, folder, field_list):
    print("Output folder is: {}".format(folder))
    print("Exporting {} to shapefile with the following fields:".format(fc))
    for field in field_list:
        print(field)
    env.workspace = vela_db
    infile = os.path.join(vela_db, fc)
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
    env.workspace = vela_db
    infile = os.path.join(vela_db, fc)
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
    
def export_shapefiles_all_fields(input_features, folder):
    # Option 1: Exports ALL FCs to shapefiles in bulk and includes all fields in the output
    env.workspace = vela_db
    arcpy.FeatureClassToShapefile_conversion(input_features, folder)


#######################################
#  Prep variables for function calls  #
#######################################

vela_files_to_delete = ["AddressPoints", "Cities", "CityCodes", "CommonPlacePoints",
                         "EMSZones", "FireZones", "LawZones", "Mileposts", "MZZones",
                         "Streets", "Exits"]

# Create lists to copy needed feature classes to Vela gdb
to_copy_list = ["address_points", "municipalities", "citycodes", "common_places",
                "ems_zones", "fire_zones", "law_zones", "common_places_Exits",
                "common_places_Mileposts", "streets"]

rename_list = ["AddressPoints", "Cities", "CityCodes", "CommonPlacePoints",
               "EMSZones", "FireZones", "LawZones", "Exits",
               "Mileposts", "Streets"]

# Create variables for shapefile exports
today = time.strftime("%Y%m%d")
vela_dir = r"C:\E911\RichfieldComCtr\0 Vela Files"
vela_folder = "Vela_Shapefiles_Richfield_" + today
out_folder_vela = os.path.join(vela_dir, vela_folder)

# Comment out this line if the folder already exists (like if code was already run once today)
if os.path.isdir(out_folder_vela) == False:
    os.mkdir(out_folder_vela)

# Option 1: Exports ALL FCs to shapefiles in bulk and includes all fields in the output
# export_shapefiles_all_fields(FCs_to_export, out_folder)
# Option 2: Individually exports each FC to shapefile, trims output down to specified fields
# -----> See last set of function calls

# Vela Shapefile field lists
street_fields = ["OBJECTID", "CARTOCODE", "FULLNAME", "L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD",
                 "PREDIR", "STREETNAME", "STREETTYPE", "SUFDIR", "ALIAS1", "ALIAS1TYPE",
                 "ALIAS2", "ALIAS2TYPE", "ACSALIAS", "ACSNAME", "ACSSUF", "ZIPLEFT",
                 "ZIPRIGHT", "STREET", "COFIPS", "HWYNAME", "COMM_LEFT", "COMM_RIGHT"]

exit_fields = ["ALIAS", "CITYCD", "ADDRESS"]
milepost_fields = ["ROUTE", "MP", "FULLMPNAME"]

#less = ["Exits", "Mileposts", "Streets"]
more = ["Communities", "Counties", "MZZones"]
# Vela Shapefiles to export with all fields
#vela_to_export = rename_list.extend(more)
vela_to_export = rename_list + more
vela_to_export.remove("Exits")
vela_to_export.remove("Mileposts")
vela_to_export.remove("Streets")

#########################################
#  Call Functions Below & Run Main Code #
#########################################

create_new_vela_gdb(vela_db, vela_files_to_delete)

# Copy needed FCs into vela_db from WGS84_db
for fc, rename in zip(to_copy_list, rename_list):
    print("Copying {0} and renaming to {1} in vela gdb ...".format(fc, rename))
    arcpy.CopyFeatures_management(fc, os.path.join(vela_db, rename))

# Copy MZ_Zones with a query for only UDOT zones
where_clause = "NAME LIKE '%UDOT%'"
arcpy.FeatureClassToFeatureClass_conversion("MZ_Zones", vela_db, "MZZones", where_clause)


# Change workspace to vela_db
env.workspace = vela_db

# Make field corrections for Mileposts FC
arcpy.AlterField_management("Mileposts", 'ALIAS', 'FULLMPNAME')
# Add field to working FC for notes
arcpy.AddField_management("Mileposts", "ROUTE", "TEXT", "", "", 20)
arcpy.AddField_management("Mileposts", "MP", "DOUBLE")
# Calculate Route and MP fields
fields = ['FULLMPNAME', 'ROUTE', 'MP']
with arcpy.da.UpdateCursor("Mileposts", fields) as uCursor:
    print("Looping through rows in FC ...")
    for row in uCursor:
        row[1] = row[0].split(" ", 1)[1]
        row[2] = row[0].split()[0].split("MP")[1]
        if row[2] == ".5":
            row[2] = "0.5"
        uCursor.updateRow(row)

## Vela Shapefiles Export (select fields)
export_shapefiles_select_fields("Streets", out_folder_vela, street_fields)
export_shapefiles_select_fields("Exits", out_folder_vela, exit_fields)
export_shapefiles_select_fields("Mileposts", out_folder_vela, milepost_fields)

# Vela Shapefiles Export (all fields)
export_shapefiles_all_fields(vela_to_export, out_folder_vela)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
