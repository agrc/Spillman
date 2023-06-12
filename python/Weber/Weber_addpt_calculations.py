# -*- coding: utf-8 -*-
"""
Created on Tue Feb 22 16:02:29 2022 (2/22/2022)

@author: eneemann

EMN: Initial script to calculate address point fields for Weber
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

# stage_db = r"C:\E911\WeberArea\Staging103\WeberSGB.gdb"
# addpts = os.path.join(stage_db, "AddressPoints")
stage_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
addpts = os.path.join(stage_db, "AddressPoints_SGB_20230523")

env.workspace = stage_db


# # Optional selection to narrow down rows the calculations are performed on
arcpy.management.SelectLayerByAttribute(addpts, 'NEW_SELECTION', "Label IS NULL")


unit_list = ['#', 'APT', 'BLDG', 'BSMT', 'CONDO', 'DEPT', 'FL', 'FRNT', 'HANGAR',
             'HNGR', 'LOT', 'MAIN', 'OFC', 'OFFICE', 'REAR', 'RM', 'SIDE', 'SP', 'SPC',
             'STE', 'TOP', 'TRLR', 'UNIT']


###############
#  Functions  #
###############


# def calc_unit_from_fulladd(pts):
#     update_count = 0
#     # Use update cursor to calculate unit type from address field
#     fields = ['FULLADDR', 'UnitType', 'UnitID']
#     where_clause = "FULLADDR IS NOT NULL AND UnitType IS NULL AND UnitID IS NULL"
#     with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
#         print("Looping through rows in FC ...")
#         for row in cursor:
#             if  ' UNIT' in row[0]:
#                 unit = 'UNIT'
#                 unit_id = row[0].rsplit('UNIT', 1)[1]
#                 row[1] = unit
#                 row[2] = unit_id
#                 update_count += 1
#             cursor.updateRow(row)
#     print("Total count of unit calculations is: {}".format(update_count))
    
    
def calc_unit_info_from_fulladd(pts):
    update_count = 0
    # Use update cursor to calculate unit type from address field
    fields = ['FULLADDR', 'UnitType', 'UnitID']
    where_clause = "FULLADDR IS NOT NULL AND UnitType IS NULL AND UnitID IS NULL"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            unit_type = None      # initialize as None
            unit_id = None        # initialize as None
            splitter = None        # initialize as None
            
            # break off and discard the house number
            parts = row[0].split(' ')
            if parts[0].isdigit():
                temp = " ".join(parts[1:])
            else:
                print(f"    Address '{row[0]}' does not have a valid house number")
            
       
            # check parts of remaining address for a unit type separator
            # if found, split string at unit type and keep unit id
            temp_parts = temp.split(' ')
            for i in np.arange(len(temp_parts)):
                if temp_parts[i].upper() in unit_list:
                    splitter = temp_parts[i]
                    unit_id = temp.split(splitter, 1)[1]
                    unit_id = unit_id.strip()
                    break
                else:
                    unit_id = None
        
            # now verify unit_type    
            # check if splitter is '#', if so split again to get real unit type
            # if not, splitter is unit_type

            if splitter:
                if splitter == '#':
                    unit_type = '#'    # re-initialize to '#'
                    temp2 = temp.split(splitter, 1)[0]
                    temp2_parts = temp2.split(' ')
                    for i in np.arange(len(temp2_parts)):
                        if temp2_parts[i].upper() in unit_list:
                            # overwrite with real unit type
                            unit_type = temp2_parts[i]
                            unit_type = unit_type.strip()
                            break
                else:
                    unit_type = splitter.strip()
            else:
                unit_type = None
            
            row[1] = unit_type
            row[2] = unit_id
            update_count += 1
            cursor.updateRow(row)
    print("Total count of unit calculations is: {}".format(update_count))
    

def calc_prefixdir_from_street(pts):
    update_count = 0
    # Use update cursor to calculate prefixdir from street field
    fields = ['STREET', 'PrefixDir']
    where_clause = "STREET IS NOT NULL AND (PrefixDir IS NULL OR PrefixDir = '')"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            pre = row[0].split(' ', 1)[0]
            if len(pre) == 1:
                row[1] = pre
                update_count += 1
            cursor.updateRow(row)
    print("Total count of PrefixDir calculations is: {}".format(update_count))
    
    
def calc_suffixdir_from_street(pts):
    update_count = 0
    # Use update cursor to calculate suffixdir from street field
    fields = ['STREET', 'SuffixDir']
    where_clause = "STREET IS NOT NULL AND (SuffixDir IS NULL OR SuffixDir = '')"
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
    print("Total count of SuffixDir calculations is: {}".format(update_count))
    
    
def calc_streettype_from_street(pts):
    update_count = 0
    # Use update cursor to calculate suffixdir from street field
    fields = ['STREET', 'StreetType']
    where_clause = "STREET IS NOT NULL AND (StreetType IS NULL OR StreetType = '')"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            # print(row[0])
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
    print("Total count of StreetType calculations is: {}".format(update_count))


def calc_streetname_from_street(pts):
    update_count = 0
    # Use update cursor to calculate suffixdir from street field
    #            0           1            2            3             4
    fields = ['STREET', 'PrefixDir', 'SuffixDir', 'StreetType', 'StreetName']
    where_clause = "STREET IS NOT NULL AND (StreetName IS NULL OR StreetName = '')"
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
    print("Total count of StreetName calculations is: {}".format(update_count))


def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'PrefixDir', 'StreetName', 'StreetType', 'SuffixDir', 'UnitType', 'UnitID',
             'Building', 'LandmarkName', 'PtLocation', 'PtType', 'Structure', 'ParcelID', 'AddSource',
             'LoadDate', 'Status', 'Editor', 'ModifyDate', 'Location', 'ACSNAME', 'ACSSUF', 'ACSALIAS',
             'NeedsAttn', 'Label', 'CommonName', 'Base', 'CityCode']
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


def calc_fulladd(pts):
    update_count = 0
    # Calculate "FullAdd" field where applicable
    where_clause = "StreetName IS NOT NULL AND AddNum IS NOT NULL AND FullAdd IS NULL"
    # where_clause = "OBJECTID >= 116122"
    #            0           1            2             3            4            5          6          7
    fields = ['AddNum', 'PrefixDir', 'StreetName', 'SuffixDir', 'StreetType', 'UnitType', 'UnitID', 'FullAdd']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
#    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[1] is None: row[1] = ''
            if row[3] is None: row[3] = ''
            if row[4] is None: row[4] = ''
            if row[5] is None: row[5] = ''
            if row[6] is None:
                row[6] = ''
                full = f'{row[0]} {row[1]} {row[2]} {row[3]} {row[4]}'
            else:
                full = f'{row[0]} {row[1]} {row[2]} {row[3]} {row[4]} {row[5]} # {row[6]}'   
            
            # parts = [row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
            # row[7] = " ".join(parts)
            full = full.strip()
            full = full.replace("  ", " ").replace("  ", " ").replace("  ", " ").replace("  ", " ").replace("  ", " ").replace("# #", "#")
            row[7] = full
            # print(f"New value for {fields[7]} is: {row[7]}")
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[7]} field: {update_count}")


def calc_street(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "StreetName IS NOT NULL AND STREET IS NULL"
    fields = ['PrefixDir', 'StreetName', 'SuffixDir', 'StreetType', 'STREET']
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
    where_clause = "Label IS NULL"
    # where_clause = "OBJECTID >= 116122"
    fields = ['Label', 'AddNum', 'UnitType', 'UnitID']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[3] is not None and row[2] is None:
                row[2] = '#'
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


def calc_common_name(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "CommonName IS NULL AND LandmarkName IS NOT NULL"
    # where_clause = "OBJECTID >= 116122"
    fields = ['CommonName', 'LandmarkName', 'UnitID']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[1] is None:
                row[0] = None
            else:
                # if row[1] is None: row[1] = ''
                if row[2] is None: row[2] = ''
                row[0] = row[1] + ' #' + row[2]
                row[0] = row[0].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")

#            print("New value for {0} is: {1}".format(fields[0], row[0]))         
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")


def calc_join_id(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    fields = ['JoinID', 'OBJECTID']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")


def calc_base(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "Base IS NULL"
    # where_clause = "OBJECTID >= 116122"
    fields = ['Base', 'UnitType', 'FullAdd']
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[1] is None or row[1] in ('', ' '):
                row[0] = row[2]
            else:
                row[0] = row[2].split(row[1], 1)[0].strip()
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")





##########################
#  Call Functions Below  #
##########################
# calc_unit_info_from_fulladd(addpts)
# calc_prefixdir_from_street(addpts)
# calc_suffixdir_from_street(addpts)
# calc_streettype_from_street(addpts)
# calc_streetname_from_street(addpts)
# calc_street(addpts)
calc_fulladd(addpts)
calc_label(addpts)
strip_fields(addpts)
calc_common_name(addpts)
calc_join_id(addpts)
calc_base(addpts)
blanks_to_nulls(addpts)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))