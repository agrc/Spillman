# -*- coding: utf-8 -*-
"""
Created on Mon Mar 6 10:43:29 2023

@author: eneemann

EMN: Initial script to calculate commonplace fields for BoxElde and UintahBasin, built from Weber
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

stage_db = r"C:\E911\UtahDPS Schemas\BE_UB_Staging.gdb"
# commonplaces = os.path.join(stage_db, "CommonNames")
commonplaces = os.path.join(stage_db, "CommonName_update_20230308_jitter")
env.workspace = stage_db


# # Optional selection to narrow down rows the calculations are performed on
# arcpy.management.SelectLayerByAttribute(commonplaces, 'NEW_SELECTION', "StreetName IS NULL")

unit_list = ['#', 'APT', 'BLDG', 'BSMT', 'CONDO', 'DEPT', 'FL', 'FRNT', 'HANGAR',
             'HNGR', 'LOT', 'MAIN', 'OFC', 'OFFICE', 'REAR', 'RM', 'SIDE', 'SP', 'SPC',
             'STE', 'TOP', 'TRLR', 'UNIT']


def calc_all_components_from_street(pts):
    update_count = 0
    five_letter = 0
    # Use update cursor to calculate components from street field
    #            0           1           2           3         4          5
    fields = ['FullAddr', 'ADDR_SN', 'ADDR_PD', 'ADDR_ST', 'ADDR_SD', 'ADDR_HN']
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
    
    
def calc_join_id(pts):
    update_count = 0
    # Calculate "JOINID" field
    fields = ['JoinID', 'OID@']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")
    
    
def check_duplicates(pts):
    # Flag duplicates addresses in the feature class (address + citycode)
    
    # Add 'Duplicate' field, if necessary
    fields = arcpy.ListFields(pts)
    field_names = [field.name for field in fields]
    
    if 'Duplicate' not in field_names:
        arcpy.management.AddField(pts, "Duplicate", "TEXT", "", "", 10)
    
    # Create counter variables    
    count = 0
    dup_count = 0
    unique_count = 0
    # # Need to make a layer from possible address points feature class here
    # arcpy.management.MakeFeatureLayer(pts, "working_lyr")

    # Create list of features in the current address points feature class
    current_dict = {}
    duplicate_dict = {}
    fields = ['CommonName', 'FullAddr', 'CityCode', 'Duplicate', 'Zip']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print(f"Checking for duplicates in {pts} ...")
        for row in cursor:
            if row[2] is None:
                citycd = 'None' # ZipCode
            else:
                citycd = row[2] # CityCode
            count += 1
            full_commonname = ' '.join([row[0], row[1], citycd])
            if count % 10000 == 0:
                print(full_commonname)
            if full_commonname in current_dict:
                row[3] = 'yes'
                duplicate_dict.setdefault(full_commonname)
                dup_count += 1
            else:
                current_dict.setdefault(full_commonname)
                row[3] = 'no'
                unique_count += 1
            cursor.updateRow(row)
            
    print(f"Total current common names: {count}")
    print(f"Unique common name count: {len(current_dict)}")
    print(f"Duplicate common names: {len(duplicate_dict)}")
    print(f"Unique common name count: {unique_count}")
    print(f"Duplicate common name count: {dup_count}")

    
# calc_all_components_from_street(commonplaces)
calc_join_id(commonplaces)
# check_duplicates(commonplaces)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))