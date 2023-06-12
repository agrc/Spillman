# -*- coding: utf-8 -*-
"""
Created on Wed Nov 16 08:27:29 2023

@author: eneemann

EMN: Initial script to calculate address point fields for Davis
"""

import arcpy
from arcpy import env
import os
import time
import numpy as np

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))

stage_db = r"C:\E911\Layton\Davis_staging.gdb"
# addpts = os.path.join(stage_db, "DavisAddressPoints")
addpts = os.path.join(stage_db, "Addpts_update_20230302")
env.workspace = stage_db



# Use to create a selection to run functions on
# if arcpy.Exists("addpts_lyr"):
#     print("Deleting {} ...".format("addpts_lyr"))
#     arcpy.management.Delete("addpts_lyr")
# where_clause = "(STREET IS NOT NULL AND StreetName is NULL) OR (STREET IS NOT NULL AND StreetName = '') OR (STREET IS NOT NULL AND StreetName = ' ')"
# # Need to make layer from feature class
# arcpy.management.MakeFeatureLayer(addpts, "addpts_lyr", where_clause)

# result = arcpy.management.GetCount("addpts_lyr")
# total = int(result.getOutput(0))
# print(f"addpts_lyr layer feature count: {total}")

casing_replacements = {
    'Nb ': 'NB ',
    'Sb ': 'SB ',
    'Eb ': 'EB ',
    'Wb ': 'WB ',
    'Sr ': 'SR ',
    'Us ': 'US ',
    'Th ': 'th ',
    'Highway': 'Hwy'
    }

endswith_replacements = {
    'Nb': 'NB',
    'Sb': 'SB',
    'Eb': 'EB',
    'Wb': 'WB',
    'Th': 'th',
    }

###############
#  Functions  #
###############


def calc_unit_from_fulladd(pts):
    update_count = 0
    # Use update cursor to calculate unit type from address field
    fields = ['Address', 'UnitType', 'Unit']
    where_clause = "Address IS NOT NULL AND UnitType IS NULL AND Unit IS NULL"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if  ' Unit' in row[0]:
                unittype = 'Unit'
                unit_id = row[0].rsplit('Unit', 1)[1]
                row[1] = unittype
                row[2] = unit_id
                update_count += 1
            cursor.updateRow(row)
    print("Total count of unit calculations is: {}".format(update_count))
    

def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'Address', 'HouseNum', 'PreDir', 'StreetName', 'StreetType', 'SufDir',
             'UnitType', 'Building', 'Unit', 'CITY', 'STATE', 'ZIP', 'CityCode', 'JoinID', 'LocationTy', 'CommonName',
             'Notes', 'Exception', 'UnitTypeLong', 'LandUse', 'ParcelID', 'Annotation', 'AliasStree', 'AliasStr_1'
             'AliasSufDi', 'AliasFullN']
    fields = arcpy.ListFields(pts)

    field_list = []
    print(f'Initial fields: {field_list}')
    for field in fields:
        if field.name in flist:
            field_list.append(field.name)
            
    print(f'Updated fields: {field_list}')
            
#    field_list = []
#    for field in fields:
#        print(field.type)
#        if field.type == 'String':
#            field_list.append(field.name)
#            
#    print(field_list)

    with arcpy.da.UpdateCursor(pts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if row[i] == '' or row[i] == ' ':
#                    print("Updating field: {0} on ObjectID: {1}".format(field_list[i].name, row[0]))
                    update_count += 1
                    row[i] = None
                elif isinstance(row[i], str):
                    row[i] = row[i].strip()
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))


def strip_fields(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field

    fields = arcpy.ListFields(pts)

    field_list = []
    for field in fields:
        if field.type == 'String':
            field_list.append(field.name)
            
    print(field_list)
    
    skip_title = ['STATE', 'CityCode']

    with arcpy.da.UpdateCursor(pts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if isinstance(row[i], str):
                    if field_list[i] in skip_title:
                        row[i] = row[i].strip().upper()
                    else:
                        row[i] = row[i].strip().title()
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of stripped fields is: {}".format(update_count))


def remove_internal_spaces(pts):
    update_count = 0
    # Remove extra spaces within strings
    fields = ['Address', 'CITY', 'StreetName', 'AliasStree', 'AliasFullN', 'LocationTy', 'CommonName', 'CommonName2',
              'CommonName3', 'CommonName4',  'CommonName5', 'LandUse', 'Orig_Addr', ]
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Removing internal spaces on strings ...")
        for row in cursor:
            for i in np.arange(len(fields)):
                if row[i] is not None:
                    row[i] = ' '.join(row[i].split()).strip()
                    update_count += 1
                    cursor.updateRow(row)
    print(f"Total count of updates: {update_count}")


def calc_joinid(pts):
    # Calculate "JoinID" field
    update_count = 0
    fields = ['JoinID', 'OID@']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Calculating JoinIDs ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")


def apply_casing(pts):
    # Apply title casing to street name components
    # Exceptions: NB, SB, EB, WB
    case_count = 0
    
    mixed = ['Address', 'CITY', 'PreDir', 'StreetName', 'StreetType', 'SufDir', 'AliasStree', 'AliasStr_1', 'AliasSufDi',
              'AliasFullN', 'UnitType', 'Building', 'Unit','LocationTy', 'Notes', 'Orig_Addr']
    upper = ['CityCode', 'CommonName', 'CommonName2', 'CommonName3', 'CommonName4',  'CommonName5', 'Exception', 'ParcelID']
    fields = mixed + upper
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Looping through rows to apply casing rules ...")
        for row in cursor:
            for i in np.arange(len(fields)):
                if row[i] is not None and fields[i] in mixed:
                    row[i] = row[i].title()
                    for key in casing_replacements:
                        if key in row[i]:
                            row[i] = row[i].replace(key, casing_replacements[key])
                            case_count += 1
                    for key in endswith_replacements:
                        if row[i].endswith(key):
                            row[i] = row[i].replace(key, endswith_replacements[key])
                            case_count += 1
                elif row[i] is not None and fields[i] in upper:
                    row[i] = row[i].upper()
            cursor.updateRow(row)
    print(f"Total of upper case preservations: {case_count}")



##########################
#  Call Functions Below  #
##########################
# calc_unit_from_fulladd(addpts)
blanks_to_nulls(addpts)
strip_fields(addpts)
remove_internal_spaces(addpts)
calc_joinid(addpts)
apply_casing(addpts)

# Use below to call on a selection
# #calc_unit_from_fulladd("addpts_lyr")
# blanks_to_nulls("addpts_lyr")
# strip_fields("addpts_lyr")

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))