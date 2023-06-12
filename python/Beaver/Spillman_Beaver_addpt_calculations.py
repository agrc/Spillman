# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 08:27:29 2019

@author: eneemann

EMN: Initial script to calculate address point fields for Beaver
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

stage_db = r"C:\E911\Beaver Co\Beaver_Staging.gdb"
addpts = os.path.join(stage_db, "AddressPoints_update_20221013")
env.workspace = stage_db

###############
#  Functions  #
###############


def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'StreetType', 'UnitType', 'UnitID', 'LABEL', 'SuffixDir', 'CITYCD']
    fields = arcpy.ListFields(pts)

    field_list = []
    for field in fields:
        if field.name in flist:
            field_list.append(field)

    with arcpy.da.UpdateCursor(pts, flist) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(flist)):
                if row[i] == '' or row[i] == ' ':
                    print("Updating field: {0} on ObjectID: {1}".format(field_list[i].name, row[0]))
                    update_count += 1
                    row[i] = None
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))


def calc_street(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "StreetName IS NOT NULL AND STREET IS NULL"
    fields = ['PrefixDir', 'StreetName', 'SuffixDir', 'StreetType', 'STREET']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[0] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            if row[3] is None: row[3] = ''
            parts = [row[0], row[1], row[2], row[3]]
            row[4] = " ".join(parts)
            row[4] = row[4].strip()
            row[4] = row[4].replace("  ", " ").replace("  ", " ").replace("  ", " ")
            print("New value for {0} is: {1}".format(fields[4], row[4]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[4], update_count))
    

def calc_label(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "LABEL IS NULL"
    fields = ['LABEL', 'AddNum', 'UnitType', 'UnitID']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[1] is None: row[1] = ''
            if row[2] is None: row[2] = ''
            if row[3] is None: row[3] = ''
            parts = [row[1], row[2], row[3]]
            row[0] = " ".join(parts)
            row[0] = row[0].strip()
            row[0] = row[0].replace("  ", " ").replace("  ", " ").replace("  ", " ")
            print("New value for {0} is: {1}".format(fields[0], row[0]))
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
    
    
##########################
#  Call Functions Below  #
##########################

calc_street(addpts)
calc_label(addpts)
strip_fields(addpts)
blanks_to_nulls(addpts)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))