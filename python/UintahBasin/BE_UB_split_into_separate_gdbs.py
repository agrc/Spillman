# -*- coding: utf-8 -*-
"""
Created on Fri Mar 17 09:28:39 2023
@author: eneemann
Script to split out BoxElder and UintahBasin data into their own geodatabases

17 Mar 2023: Created initial version of code (EMN).
"""

import os
import time
import arcpy
from arcpy import env

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))

today = time.strftime("%Y%m%d")

#: Set up paths and variables
staging_db = r"C:\E911\UtahDPS Schemas\BE_UB_Staging.gdb"
geovalidation_db = r"C:\E911\UtahDPS Schemas\BE_UB_Geovalidation_WGS84.gdb"

UintahBasin_citycodes = os.path.join(staging_db, "UintahBasin_CityCodes")
BoxElder_citycodes = os.path.join(staging_db, "BoxElder_CityCodes")

gdb_dir = r"C:\E911\UtahDPS Schemas"
UB_name = f"UintahBasin_Geo_WGS84_{today}.gdb"
BE_name = f"BoxElder_Geo_WGS84_{today}.gdb"
UintahBasin_gdb = os.path.join(gdb_dir, UB_name)
BoxElder_gdb = os.path.join(gdb_dir, BE_name)

env.workspace = geovalidation_db
env.overwriteOutput = True


def create_gdbs():
    #: Create UintahBasin and BoxElder geodatabases
    if arcpy.Exists(UintahBasin_gdb):
        arcpy.management.Delete(UintahBasin_gdb)
    arcpy.management.CreateFileGDB(gdb_dir, UB_name)
    
    if arcpy.Exists(BoxElder_gdb):
        arcpy.management.Delete(BoxElder_gdb)
    arcpy.management.CreateFileGDB(gdb_dir, BE_name)
    
    
def calc_join_id(lyr, fld):
    update_count = 0
    # Calculate "JOINID" field
    fields = [f'{fld}', 'OID@']
    with arcpy.da.UpdateCursor(lyr, fields) as cursor:
        print(f"Looping through rows in {lyr} to calculate JoinIDs ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")


def select_and_export():
    fc_list = arcpy.ListFeatureClasses()
    print(fc_list)
    
    #: Select and export BoxElder
    for fc in fc_list:
        new_fc = os.path.join(BoxElder_gdb, fc)
        arcpy.management.MakeFeatureLayer(fc, "temp_lyr")
        print(f'Selecting and copying {fc} to {BoxElder_gdb} ...')
        arcpy.management.SelectLayerByLocation("temp_lyr", "INTERSECT", BoxElder_citycodes, "5 Miles")
        arcpy.management.CopyFeatures("temp_lyr", new_fc)
        
        #: Must recalculate JoinID, if it exists in the layer, based on the new OIDs
        field = [field.name for field in arcpy.ListFields(new_fc) if field.name.lower() == 'joinid']
        if len(field) > 0 and field[0].lower() == 'joinid':
            calc_join_id(new_fc, field[0])
        # else:
        #     print(f'no JoinID field in {fc}')
            
        if arcpy.Exists("temp_lyr"):
            arcpy.management.Delete("temp_lyr")
    
    #: Select and export UintahBasin
    for fc in fc_list:
        new_fc = os.path.join(UintahBasin_gdb, fc)
        arcpy.management.MakeFeatureLayer(fc, "temp_lyr")
        print(f'Selecting and copying {fc} to {UintahBasin_gdb} ...')
        arcpy.management.SelectLayerByLocation("temp_lyr", "INTERSECT", UintahBasin_citycodes, "5 Miles")
        arcpy.management.CopyFeatures("temp_lyr", new_fc)

        #: Must recalculate JoinID, if it exists in the layer, based on the new OIDs
        field = [field.name for field in arcpy.ListFields(new_fc) if field.name.lower() == 'joinid']
        if len(field) > 0 and field[0].lower() == 'joinid':
            calc_join_id(new_fc, field[0])
        # else:
        #     print(f'no JoinID field in {fc}')
            
        if arcpy.Exists("temp_lyr"):
            arcpy.management.Delete("temp_lyr")

#: Call functions
create_gdbs()
select_and_export()

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
