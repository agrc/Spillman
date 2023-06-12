# -*- coding: utf-8 -*-
"""
Created on Wed May 24 14:00:07 2023
@author: eneemann
Script to detect address points duplicates by building a full address from components,
unit, and zip code, then comparing it to existing addresses.

"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

staging_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
env.workspace = staging_db
env.overwriteOutput = True


# Point to current addpts in staging_db
current_addpts = os.path.join(staging_db, "AddressPoints_SGB_20230523")

today = time.strftime("%Y%m%d")
new_addpts = os.path.join(staging_db, "zzz_AddPts_new_TEST_working_20230523_final")


###############
#  Functions  #
###############

def build_existing_addr_dict(pts):
    #: Create dictionary of existing addresses
    #: Address is concatenation of address component fields, unitid, and zip code
    existing_dict = {}
        
    print(f"Building address list from {pts} ...")
    #            0           1             2            3             4          5         6            7
    fields = ['AddNum', 'PrefixDir', 'StreetName', 'StreetType', 'SuffixDir', 'UnitID', 'ZipCode', 'ADDR_UNIT']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        for row in cursor:
            row = [x if x is not None else '' for x in row]
            addr_unit = ' '.join([row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
            addr_unit_clean = ' '.join(addr_unit.split()).strip()
            row[7] = addr_unit_clean
            existing_dict.setdefault(addr_unit_clean)
            
            cursor.updateRow(row)
            
    return existing_dict
    

def check_new_addpt_duplicates(pts, exists):
    count = 0
    dup_count = 0
    unique_count = 0

    # Flag potential new points if a duplicate from existing Weber address points
    duplicate_dict = {}
    ok_dict = {}
    #            0           1             2            3             4          5         6            7              8
    fields = ['AddNum', 'PrefixDir', 'StreetName', 'StreetType', 'SuffixDir', 'UnitID', 'ZipCode', 'ADDR_UNIT', 'Duplicate_Flag']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print(f"Checking for duplicates in {pts} ...")
        for row in cursor:
            count += 1
            row = [x if x is not None else '' for x in row]
            addr_unit = ' '.join([row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
            addr_unit_clean = ' '.join(addr_unit.split()).strip()
            row[7] = addr_unit_clean
            
            if count % 10000 == 0:
                print(addr_unit_clean)
                
            if addr_unit_clean in exists:
                row[8] = 'duplicate'
                duplicate_dict.setdefault(addr_unit_clean)
                dup_count += 1
            else:
                ok_dict.setdefault(addr_unit_clean)
                row[8] = 'ok'
                unique_count += 1
            cursor.updateRow(row)
            
    print(f"Total current address points: {count}")
    print(f"Existing address count: {len(exists)}")
    print(f"Duplicate addresses: {len(duplicate_dict)}")
    print(f"Unique address count: {unique_count}")
    print(f"Duplicate address point count: {dup_count}")


####################
#  Call Functions  #
####################

# Add fields for ADDR_UNIT calculation in current address points
current_fields = arcpy.ListFields(current_addpts)
current_field_names = [f.name for f in current_fields]
if 'ADDR_UNIT' not in current_field_names:
    print('Adding ADDR_UNIT field to {current_addpts} ...')
    arcpy.AddField_management(current_addpts, "ADDR_UNIT", "TEXT", "", "", 100)

# Add fields for ADDR_UNIT calculation and duplicate address check in new address points
new_fields = arcpy.ListFields(new_addpts)
new_field_names = [f.name for f in new_fields]
if 'ADDR_UNIT' not in new_field_names:
    print('Adding ADDR_UNIT field to {new_addpts} ...')
    arcpy.AddField_management(new_addpts, "ADDR_UNIT", "TEXT", "", "", 100)
if 'Duplicate_Flag' not in new_field_names:
    print('Adding Duplicate_Flag field to {new_addpts} ...')
    arcpy.AddField_management(new_addpts, "Duplicate_Flag", "TEXT", "", "", 10)



existing = build_existing_addr_dict(current_addpts)
check_new_addpt_duplicates(new_addpts, existing)



print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))


# test = ['7', None, '5', None]
# print(test)
# new = [x if x is not None else '' for x in test]
# print(new)

