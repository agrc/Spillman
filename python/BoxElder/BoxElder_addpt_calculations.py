# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 20:29:29 2020

@author: eneemann

EMN: Initial script to calculate address point fields for Box Elder
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

stage_db = r"C:\E911\Box Elder CO\BoxElder_Staging.gdb"
addpts = os.path.join(stage_db, "AddPt_update_20220930")
env.workspace = stage_db

###############
#  Functions  #
###############


def calc_unit_from_fulladd(pts):
    update_count = 0
    # Use update cursor to calculate unit type from address field
    fields = ['FULLADDR', 'UNIT_TYPE', 'UNIT_ID']
    where_clause = "FULLADDR IS NOT NULL AND UNIT_TYPE IS NULL AND UNIT_ID IS NULL"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if  ' UNIT' in row[0]:
                unit = 'UNIT'
                unit_id = row[0].rsplit('UNIT', 1)[1]
                row[1] = unit
                row[2] = unit_id
                update_count += 1
            cursor.updateRow(row)
    print("Total count of unit calculations is: {}".format(update_count))
    

def calc_PREDIR_from_street(pts):
    update_count = 0
    # Use update cursor to calculate PREDIR from street field
    fields = ['STREET', 'PREDIR']
    where_clause = "STREET IS NOT NULL AND (PREDIR IS NULL OR PREDIR = '')"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            pre = row[0].split(' ', 1)[0]
            if len(pre) == 1:
                row[1] = pre
                update_count += 1
            cursor.updateRow(row)
    print("Total count of PREDIR calculations is: {}".format(update_count))
    
    
def calc_SUFDIR_from_street(pts):
    update_count = 0
    # Use update cursor to calculate SUFDIR from street field
    fields = ['STREET', 'SUFDIR']
    where_clause = "STREET IS NOT NULL AND (SUFDIR IS NULL OR SUFDIR = '')"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
#            print(row[0])
#            end = row[0].rsplit(' ', 1)[1]
            temp = row[0].rsplit(' ', 1)
            if len(temp) > 1:
                end = temp[1]
            else:
                end = ''
            
            if len(end) == 1 and end in ['N', 'S', 'E', 'W']:
                row[1] = end
                update_count += 1
                cursor.updateRow(row)
    print("Total count of SUFDIR calculations is: {}".format(update_count))
    
    
def calc_STREETTYPE_from_street(pts):
    update_count = 0
    # Use update cursor to calculate SUFDIR from street field
    fields = ['STREET', 'STREETTYPE']
    where_clause = "STREET IS NOT NULL AND (STREETTYPE IS NULL OR STREETTYPE = '')"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            print(row[0])
#            end = row[0].rsplit(' ', 1)[1]
            temp = row[0].rsplit(' ', 1)
            if len(temp) > 1:
                end = temp[1]
            else:
                end = ''
            if 1 < len(end) <= 4 and end.isalpha():
                if end not in ('MAIN', 'TOP', 'UNIT'):
                    row[1] = end
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of STREETTYPE calculations is: {}".format(update_count))


def calc_STREETNAME_from_street(pts):
    update_count = 0
    # Use update cursor to calculate SUFDIR from street field
    #            0           1            2            3             4
    fields = ['STREET', 'PREDIR', 'SUFDIR', 'STREETTYPE', 'STREETNAME']
    where_clause = "STREET IS NOT NULL AND (STREETNAME IS NULL OR STREETNAME = '')"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            street = row[0]
            pre = row[1]
            suf = row[2]
            sttype = row[3]
            if pre is not None:
                temp = street.split(pre, 1)[1]
                if suf is not None:
                    temp2 = temp.rsplit(suf, 1)[0]
                elif sttype is not None:
                    temp2 = temp.rsplit(sttype, 1)[0]
                else:
                    temp2 = temp
            else:
                if suf is not None:
                    temp2 = street.rsplit(suf, 1)[0]
                elif sttype is not None:
                    temp2 = street.rsplit(sttype, 1)[0]
                else:
                    temp2 = temp
                
            row[4] = temp2.strip()
            update_count += 1
            cursor.updateRow(row)
    print("Total count of STREETNAME calculations is: {}".format(update_count))


def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'PREDIR', 'STREETNAME', 'STREETTYPE', 'SUFDIR', 'UNIT_TYPE', 'UNIT_ID', 'LABEL', 'CITYCD', 'STREET']
    fields = arcpy.ListFields(pts)

    field_list = []
    for field in fields:
        if field.name in flist:
            field_list.append(field)
            
#    field_list = []
#    for field in fields:
#        print(field.type)
#        if field.type == 'String':
#            field_list.append(field.name)
#            
#    print(field_list)

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


def calc_street(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "STREETNAME IS NOT NULL AND STREET IS NULL"
    fields = ['PREDIR', 'STREETNAME', 'SUFDIR', 'STREETTYPE', 'STREET']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
#    with arcpy.da.UpdateCursor(pts, fields) as cursor:
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
    fields = ['LABEL', 'ADDRNUM', 'UNIT_TYPE', 'UNIT_ID']
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


##########################
#  Call Functions Below  #
##########################
# calc_unit_from_fulladd(addpts)
# calc_PREDIR_from_street(addpts)
# calc_SUFDIR_from_street(addpts)
# calc_STREETTYPE_from_street(addpts)
# calc_STREETNAME_from_street(addpts)
calc_street(addpts)
calc_label(addpts)
strip_fields(addpts)
blanks_to_nulls(addpts)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))

