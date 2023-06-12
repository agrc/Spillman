# -*- coding: utf-8 -*-
"""
Created on Wed Oct 29 13:00:29 2019

@author: eneemann

EMN: Initial script to calculate address point fields for Millard
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

stage_db = r"C:\E911\MillardCo\Millard_Staging.gdb"
addpts = os.path.join(stage_db, "Millard_AddressPoints_update_20220919")
env.workspace = stage_db

# Add field to working FC for CITYCD and STREET (if necessary)
#arcpy.AddField_management(addpts, "CITYCD", "TEXT", "", "", 3)
# arcpy.AddField_management(addpts, "STREET", "TEXT", "", "", 40)

###############
#  Functions  #
###############


def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['PREDIR', 'STREETTYPE', 'SUFDIR', 'UNIT_TYPE', 'UNIT_ID', 'COMMUNITY', 'LABEL', 'ZIPCODE', 'CITYCD', 'STREET']
    fields = arcpy.ListFields(pts)

    field_list = []
    for field in fields:
        if field.name in flist:
            field_list.append(field.name)
            
    print(flist)
    print(field_list)

    with arcpy.da.UpdateCursor(pts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if row[i] == '' or row[i] == ' ':
                    update_count += 1
                    row[i] = None
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))

# Calculate STREET from component fields"
#def calc_street(pts):
#    update_count = 0
#    # Calculate "Street" field where applicable
#    where_clause = "STREETNAME IS NOT NULL AND STREET IS NULL"
#    fields = ['PREDIR', 'STREETNAME', 'SUFDIR', 'STREETTYPE', 'STREET']
#    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
#        print("Looping through rows in FC ...")
#        for row in cursor:
#            if row[0] is None: row[0] = ''
#            if row[2] is None: row[2] = ''
#            if row[3] is None: row[3] = ''
#            parts = [row[0], row[1], row[2], row[3]]
#            row[4] = " ".join(parts)
#            row[4] = row[4].strip()
#            row[4] = row[4].replace("  ", " ").replace("  ", " ").replace("  ", " ")
##            print("New value for {0} is: {1}".format(fields[4], row[4]))
#            update_count += 1
#            cursor.updateRow(row)
#    print("Total count of updates to {0} field: {1}".format(fields[4], update_count))


# Calculate STREET from FULLADDR field"
def calc_street(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "FULLADDR IS NOT NULL AND STREET IS NULL"
    fields = ['STREET', 'FULLADDR']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1].split(" ", 1)[1].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[0], update_count))
    

def calc_predir(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "PREDIR IS NULL"
    fields = ['FULLADDR', 'PREDIR']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[1] = row[0].split(" ")[1].strip()
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[1], update_count))
    

def calc_sufdir(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "SUFDIR IS NULL"
    fields = ['FULLADDR', 'SUFDIR']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            temp = row[0].rsplit(" ", 1)[1]
            if len(temp) == 1:
                row[1] = temp
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[1], update_count))
    
    
def calc_streettype(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "STREETTYPE IS NULL"
    fields = ['FULLADDR', 'STREETTYPE']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            temp = row[0].rsplit(" ", 1)[1]
            if len(temp) != 1:
                row[1] = temp
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[1], update_count))
    
    
def calc_streetname(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "STREETNAME IS NULL"
    fields = ['PREDIR', 'SUFDIR', 'FULLADDR', 'STREETTYPE']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            fulladd = row[2]
            pre = row[0]
            suf = row[1]
            temp = fulladd.rsplit(pre, 1)[1].split(suf,1)[0].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
            row[3] = temp
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[3], update_count))


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
            print("New value for {0} is: {1}".format(fields[0], row[0]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[0], update_count))

##########################
#  Call Functions Below  #
##########################

calc_street(addpts)
# calc_predir(addpts)
# calc_sufdir(addpts)
# calc_streettype(addpts)
# calc_streetname(addpts)
calc_label(addpts)
blanks_to_nulls(addpts)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))

## sufdir
#def calc(fulladd):
#    temp = fulladd.rsplit(" ", 1)[1]
#    if len(temp) == 1:
#        return temp
#    else:
#        return        
#    
#calc()
#
## streettype
#def calc(fulladd):
#    temp = fulladd.rsplit(" ", 1)[1]
#    if len(temp) == 1:
#        return
#    else:
#        return temp
#    
#calc()
#
## streetname
#def calc(pre, suf, fulladd):
#    temp = fulladd.rsplit(pre, 1)[1].split(suf,1)[0].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
#    if len(temp) == 1:
#        return
#    else:
#        return temp
#    
#calc()