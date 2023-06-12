# -*- coding: utf-8 -*-
"""
Created on Fri Nov 1 07:37:17 2019

@author: eneemann
Script to "jitter" the coordinates of Weber Area commonplaces to ensure that
commonplaces associated with the same address have different coordinates.
"""

import arcpy
import os
import time
from datetime import datetime
import random

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

######################
#  Set up variables  #
######################

# Set up databases (SGID must be changed based on user's path)
# weber_db = r"C:\E911\WeberArea\Staging103\WeberSGB.gdb"
weber_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"

arcpy.env.workspace = weber_db
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False

today = time.strftime("%Y%m%d")

common_names = os.path.join(weber_db, 'CommonNames_update_20201023')
cn_update = os.path.join(weber_db, 'CommonNames_update_' + today + '_jitter')

print(f"Copying CommonNames to: {cn_update} ...")
arcpy.management.Copy(common_names, cn_update)

def jitter(val):
    new_val = val + 0.0000003*random.randint(-9,9)
    return new_val    


field_list = ['SHAPE@', 'SHAPE@X', 'SHAPE@Y']
with arcpy.da.UpdateCursor(cn_update, field_list) as update_cursor:
    print("Looping through rows in FC ...")
    for row in update_cursor:
#        print(f'Shape: {row[0]}')
#        print(f'X Coord: {row[1]}')
#        print(f'Y Coord: {row[2]}')
        row[1] = jitter(row[1])
        row[2] = jitter(row[2])
        update_cursor.updateRow(row)
#print("Total count of blanks converted to NULLs is: {}".format(update_count))


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
