# -*- coding: utf-8 -*-
"""
Created on Thu Nov 212 15:30:29 2020

@author: eneemann

EMN: Initial script to calculate commonplace fields for Weber, built from St George
"""

import arcpy
from arcpy import env
import numpy as np
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))

stage_db = r"C:\E911\Layton\Davis_staging.gdb"
commonplaces = os.path.join(stage_db, "PointsOfInterest_update_20230420")
env.workspace = stage_db

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


# # Optional selection to narrow down rows the calculations are performed on
# arcpy.management.SelectLayerByAttribute(commonplaces, 'NEW_SELECTION', "StreetName IS NULL")


def calc_street(pts):
    update_count = 0
    # Calculate "Street" field where applicable
    where_clause = "StreetName IS NOT NULL AND STREET IS NULL"
    # where_clause = "StreetName IS NOT NULL"
    #            0           1           2           3           4
    fields = ['PreDir', 'StreetName', 'SufDir', 'StreetType', 'street']
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
            print(f"New value for {fields[4]} is: {row[4]}")
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[4]} field: {update_count}")
    


unit_list = ['#', 'APT', 'BLDG', 'BSMT', 'CONDO', 'DEPT', 'FL', 'FRNT', 'HANGAR',
             'HNGR', 'LOT', 'MAIN', 'OFC', 'OFFICE', 'REAR', 'RM', 'SIDE', 'SP', 'SPC',
             'STE', 'TOP', 'TRLR', 'UNIT']


def calc_all_components_from_street(pts):
    update_count = 0
    five_letter = 0
    # Use update cursor to calculate components from street field
    #               0            1           2           3           4          5
    fields = ['FullAddres', 'StreetName', 'PreDir', 'StreetType', 'SufDir', 'HouseNum']
    # where_clause = "STREET IS NOT NULL AND STREETNAME IS NULL"
    where_clause = "ADDR_SN IS NULL AND FullAddr IS NOT NULL"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            street, numb = None, None
            street = row[0].split(' ', 1)[1].strip()
            numb = row[0].split(' ', 1)[0].strip()
            pre = None
            suf = None
            stname = None
            sttype = None
            rest = None
            
            # print(street)
            
            # calculate predirection
            st_split = street.split(' ', 1)
            pre_test = st_split[0]
            if len(st_split) > 1:
                rest = street.split(' ', 1)[1]
            if len(pre_test) == 1:
                pre = pre_test.strip()
            
            # calculate sufdir
            if len(street.rsplit(' ', 1)) > 1:
                end = street.rsplit(' ', 1)[1]
            else:
                end = street
            # beg = street.rsplit(' ', 1)[0]
            # print(beg)
            if len(end) == 1 and end in ['N', 'S', 'E', 'W']:
                suf = end.strip()
            elif rest:
                rest_parts = rest.split(' ')
                for i in np.arange(len(rest_parts)):
                    if rest_parts[i].upper() in ['N', 'S', 'E', 'W']:
                        suf = rest_parts[i]
                
            # calculate streettype
            if suf and pre:
                temp = street.split(pre, 1)[1]
                new_end = temp.rsplit(suf, 1)[1].strip()
                if new_end is None:
                    sttype = None
                elif 1 < len(new_end) <= 4 and end.isalpha():
                    if new_end not in unit_list:
                        sttype = new_end.strip()
                elif len(new_end) == 5:
                    print(f'Encountered possible 5 letter streettype: {new_end}')
                    five_letter += 1
            elif not suf:
                if len(street.split()) > 1:
                    new_end = street.rsplit(' ', 1)[1].strip()
                    if 1 < len(new_end) <= 4 and end.isalpha():
                        if new_end not in unit_list:
                            sttype = new_end.strip()
                    elif len(new_end) == 5:
                        print(f'Encountered possible 5 letter streettype: {new_end}')
                        five_letter += 1
                
            
            
            # calculate streetname
            if pre is not None:
                new_temp = street.split(pre, 1)[1]
                if suf is not None:
                    stname = new_temp.rsplit(suf, 1)[0]
                elif sttype is not None:
                    stname = new_temp.rsplit(sttype, 1)[0]
                else:
                    stname = new_temp
            else:
                new_temp = street
                if suf is not None:
                    stname = street.rsplit(suf, 1)[0]
                elif sttype is not None:
                    stname = street.rsplit(sttype, 1)[0]
                else:
                    stname = new_temp
            
            # Calc the new fields
            if stname:
                row[1] = stname.strip()
            else:
                row[1] = None
                
            if pre:
                row[2] = pre.strip()
            else:
                row[2] = None
                
            if sttype:
                row[3] = sttype.strip()
            else:
                row[3] = None
            
            if suf:
                row[4] = suf.strip()
            else:
                row[4] = None
                
            if numb:
                row[5] = numb.strip()
            else:
                row[5] = None
            
            update_count += 1
            cursor.updateRow(row)
    print("Total count of STREETNAME calculations is: {}".format(update_count))
    print("Total count of Five letter street types is: {}".format(five_letter))


def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['HouseNum', 'FullAddres', 'PreDir', 'StreetName', 'StreetType', 'SufDir', 'UnitType',
             'Unit', 'CityCode', 'Zip', 'LocationTy', 'CommonName', 'IsIntersec', 'JoinID', 'ALIAS_1',
             'ALIAS_2', 'ALIAS_3', 'ALIAS4', 'ALIAS5', 'ALIAS6', 'ALIAS7', 'ALIAS8', 'ALIAS9', 'ALIAS10']
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
                if row[i] in ('', ' ', 'None', None):
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
        print(field.type)
        if field.type == 'String':
            field_list.append(field.name)
            
    print(field_list)

    with arcpy.da.UpdateCursor(pts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if isinstance(row[i], str):
                    row[i] = row[i].strip().upper()
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of stripped fields is: {}".format(update_count))
    
    
def remove_internal_spaces(pts):
    update_count = 0
    # Remove extra spaces within strings
    fields = ['FullAddres', 'StreetName', 'street', 'LocationTy', 'CommonName', 'ALIAS_1', 'ALIAS_2', 'ALIAS_3',  'ALIAS4', 'ALIAS5', 'ALIAS6', 'ALIAS7' ]
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


def apply_casing(pts):
    # Apply title casing to street name components
    # Exceptions: NB, SB, EB, WB
    case_count = 0
    
    mixed = ['FullAddres', 'PreDir', 'StreetName', 'StreetType', 'street', 'UnitType', 'Unit', 'LocationTy']
    upper = ['CommonName', 'ALIAS_1', 'ALIAS_2', 'ALIAS_3',  'ALIAS4', 'ALIAS5', 'ALIAS6', 'ALIAS7', 'CityCode']
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



# calc_street(commonplaces)
# calc_all_components_from_street(commonplaces)
blanks_to_nulls(commonplaces)
strip_fields(commonplaces)
remove_internal_spaces(commonplaces)
calc_joinid(commonplaces)
apply_casing(commonplaces)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))