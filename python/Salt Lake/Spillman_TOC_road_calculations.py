# -*- coding: utf-8 -*-
"""
Created on Wed Jul 22 13:58:56 2020
@author: eneemann

22 Jul 2020 - script to calculate street fields
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

# work_db = r"C:\E911\TOC\TOC_Staging.gdb"
work_db = r"C:\E911\TOC\TOC_Geovalidation_WGS84.gdb"
env.workspace = work_db
# fc_layer = "TOC_Streets_update_20210125"    # Update to working streets fc
fc_layer = "Streets_Combined"    # Update to working streets fc
streets_fc = os.path.join(work_db, fc_layer)

###############
#  Functions  #
###############


def blanks_to_nulls(streets):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['STREET', 'PREDIR', 'STREETNAME', 'STREETTYPE', 'SUFDIR', 'ALIAS1', 'ALIAS1TYPE', 'ALIAS2', 'ALIAS2TYPE',
              'ALIAS3', 'ALIAS3TYPE', 'ACSALIAS', 'ACSNAME', 'ACSSUF', 'HWYNAME', 'LOCATION', 'ZIPLEFT', 'ZIPRIGHT',
              'CITYCD_L', 'CITYCD_R']
    fields = arcpy.ListFields(streets)

    field_list = []
    for field in fields:
        # print field.name
        if field.name in flist:
            # print("{} appended to field_list".format(field.name))
            field_list.append(field.name)

    with arcpy.da.UpdateCursor(streets, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            # print row
            for i in range(len(field_list)):
                # if (field_list[i].type == "String" and row[i] == '') or\
                #         (field_list[i].type == "String" and row[i] == ' '):
                if row[i] == '' or row[i] == ' ':
                    # print("Updating field: {0} on ObjectID: {1}".format(field_list[i], row[0]))
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
            row[4] = row[4].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
            print("New value for {0} is: {1}".format(fields[4], row[4]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0}: {1}".format(fields[4], update_count))


def calc_prefixdir_from_street(streets):
    update_count = 0
    # Use update cursor to calculate PREDIR from street field
    fields = ['STREET', 'PREDIR']
    where_clause = "STREET IS NOT NULL AND (PREDIR IS NULL OR PREDIR = '')"
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            pre = row[0].split(' ', 1)[0]
            if len(pre) == 1:
                row[1] = pre
                update_count += 1
            cursor.updateRow(row)
    print("Total count of PREDIR calculations is: {}".format(update_count))
    
    
def calc_suffixdir_from_street(streets):
    update_count = 0
    # Use update cursor to calculate SUFDIR from street field
    fields = ['STREET', 'SUFDIR']
    where_clause = "STREET IS NOT NULL AND (SUFDIR IS NULL OR SUFDIR = '')"
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
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
    
    
def calc_streettype_from_street(streets):
    update_count = 0
    # Use update cursor to calculate StreetType from street field
    fields = ['STREET', 'STREETTYPE']
    where_clause = "STREET IS NOT NULL AND (STREETTYPE IS NULL OR STREETTYPE = '')"
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
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


def calc_streetname_from_street(streets):
    update_count = 0
    # Use update cursor to calculate StreetName from street field
    #            0           1            2            3             4
    fields = ['STREET', 'PREDIR', 'SUFDIR', 'STREETTYPE', 'STREETNAME']
    where_clause = "STREET IS NOT NULL AND (STREETNAME IS NULL OR STREETNAME = '')"
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
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
                temp = street
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


def street_blank_to_null(streets):
    update_count = 0
    # Calculate updates on "SALIAS3" to call all highways 'HWY' based on "SALIAS2" field
    where_clause = "STREET IN ('', ' ')"
    fields = ['STREET']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = None
            # print("New value for {0} is: {1}".format(fields[0], row[0]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of STREET updates from blank to null is: {}".format(update_count))


def calc_location(streets):
    # Calculate the "LOCATION" field with ACSALIAS
    update_count = 0
    where_clause = "ACSNAME IS NOT NULL AND ACSSUF IS NOT NULL AND (LOCATION IS NULL OR ACSALIAS IS NULL)"
    fields = ['ACSNAME', 'ACSSUF', 'ACSALIAS', 'LOCATION']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            loc = row[0] + ' ' + row[1]
            loc = loc.strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
            row[2] = loc
            row[3] = loc
            print(f"New value for {fields[2]} and {fields[3]} is: {loc.strip()}")
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of LOCATION field updates in {streets} is: {update_count}")


def strip_fields(streets):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field

    fields = arcpy.ListFields(streets)

    field_list = []
    for field in fields:
        print(field.type)
        if field.type == 'String':
            field_list.append(field.name)
            
    print(field_list)

    with arcpy.da.UpdateCursor(streets, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if isinstance(row[i], str):
                    row[i] = row[i].strip()
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of stripped fields is: {}".format(update_count))


def calc_joinid(streets):
    # Calculate remaining fields
    update_count = 0
    # Calculate "JOINID" field
    fields = ['JOINID', 'OID@']
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")


##########################
#  Call Functions Below  #
##########################
# # Calc STREET from other fields
blanks_to_nulls(streets_fc)
calc_street(streets_fc)
street_blank_to_null(streets_fc)
calc_location(streets_fc)
calc_joinid(streets_fc)
strip_fields(streets_fc)
blanks_to_nulls(streets_fc)

# Calc other fields from STREET
# calc_street(streets_fc)
# calc_prefixdir_from_street(streets_fc)
# calc_suffixdir_from_street(streets_fc)
# calc_streettype_from_street(streets_fc)
# calc_streetname_from_street(streets_fc)
# highway_to_sr_us(streets_fc)
# calc_salias3(streets_fc)
# street_blank_to_null(streets_fc)
# calc_location(streets_fc)
# blanks_to_nulls(streets_fc)
# strip_fields(streets_fc)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))