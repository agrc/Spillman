# -*- coding: utf-8 -*-
"""
Created on Thu Aug 25 15:44:29 2022

@author: eneemann

EMN: Initial script to calculate address point fields for Salt Lake TOC
"""

import arcpy
from arcpy import env
import numpy as np
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

stage_db = r"C:\E911\TOC\TOC_Geovalidation_WGS84.gdb"
addpts = os.path.join(stage_db, "AddressPoints")
env.workspace = stage_db


# # Optional selection to narrow down rows the calculations are performed on
arcpy.management.SelectLayerByAttribute(addpts, 'NEW_SELECTION', "LABEL IS NULL")


unit_list = ['#', 'APT', 'BLDG', 'BSMT', 'CONDO', 'DEPT', 'FL', 'FRNT', 'HANGAR',
             'HNGR', 'LOT', 'MAIN', 'OFC', 'OFFICE', 'REAR', 'RM', 'SIDE', 'SP', 'SPC',
             'STE', 'TOP', 'TRLR', 'UNIT']


###############
#  Functions  #
###############


def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'FullAdd', 'AddNum', 'AddNumSuffix', 'PrefixDir', 'StreetName', 'StreetType', 'SuffixDir', 'LandmarkName', 'Building', 'UnitType',
             'UnitID', 'City', 'ZipCode', 'CountyID', 'State', 'PtLocation', 'PtType', 'Structure', 'ParcelID', 'AddSource', 'LoadDate', 'Status',
             'Editor', 'ModifyDate', 'CityCode', 'JoinID', 'Location', 'ACSNAME', 'ACSSUF', 'NeedsAttn', 'Label', 'ACSALIAS', 'CommonName']
    fields = arcpy.ListFields(pts)

    field_list = []
    for field in fields:
        print(field.name)
        if field.name in flist:
            field_list.append(field)
            
#    field_list = []
#    for field in fields:
#        print(field.type)
#        if field.type == 'String':
#            field_list.append(field.name)
#            
    # print('    missing fields :')    
    # for field in field_list2:
    #     print(field.name)
    print(flist)

    with arcpy.da.UpdateCursor(pts, flist) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(flist)):
                if row[i] == '' or row[i] == ' ':
#                    print("Updating field: {0} on ObjectID: {1}".format(field_list[i].name, row[0]))
                    update_count += 1
                    row[i] = None
                elif isinstance(row[i], str):
                    row[i] = row[i].strip()
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))
    

def calc_label(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "Label IS NULL"
    fields = ['Label', 'AddNum', 'UnitType', 'UnitID']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[1] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            if row[3] is None: row[3] = ''
            parts = [row[1], row[2], row[3]]
            row[0] = " ".join(parts)
            row[0] = row[0].strip()
            row[0] = row[0].replace("  ", " ").replace("  ", " ").replace("  ", " ")
#            print("New value for {0} is: {1}".format(fields[0], row[0]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[0], update_count))


def strip_fields(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field

    fields = arcpy.ListFields(pts)

    field_list = []
    for field in fields:
        print(field.type)
        if field.type == 'String':
            field_list.append(field.name)
            
    print(field_list)

    with arcpy.da.UpdateCursor(pts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if isinstance(row[i], str):
                    row[i] = row[i].strip()
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of stripped fields is: {}".format(update_count))


def calc_joinid(pts):
    update_count = 0
    # Calculate "JoinID" field
    fields = ['JoinID', 'OID@']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")


##########################
#  Call Functions Below  #
##########################
calc_label(addpts)
blanks_to_nulls(addpts)
strip_fields(addpts)
calc_joinid(addpts)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))