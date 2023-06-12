# -*- coding: utf-8 -*-
"""
Created on Tue Jul 30 15:34:27 2019
@author: eneemann

30 Ju1 2019: Simple script to convert blank fields to nulls (EMN)
- Inputs to function include feature class and list of fields
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

db = r"C:\E911\UintahBasin\UB_Staging.gdb"
fc_name = "UBStreets_updates_20191209"
env.workspace = db
fc_layer = os.path.join(db, fc_name)
fields = ['OBJECTID', 'FULLNAME', 'PREDIR', 'STREETNAME', 'STREETTYPE', 'SUFDIR', 'ALIAS1', 'ALIAS1TYPE', 'ALIAS2', 'ALIAS2TYPE',
              'ACSALIAS', 'ACSNAME', 'ACSSUF', 'SALIAS1', 'SALIAS2', 'SALIAS3', 'SALIAS4', 'HWYNAME', 'DOT_RTNAME', 'DOT_RTPART', 'ACCURACY', 'ACCESS',
              'NOTES', 'SOURCE', 'COUNIQUE', 'SURFTYPE', 'LOCALFUNC', 'MAINTJURIS', 'USAGENOTES', 'FED_RDID', 'DOT_FUNC', 'DOT_COFUND']

###############
#  Functions  #
###############

def blanks_to_nulls(fc, flist):
    print(flist)
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    
    fields = arcpy.ListFields(fc)

    field_list = []
    for field in fields:
        if field.name in flist:
            field_list.append(field.name)
    print(field_list)

    with arcpy.da.UpdateCursor(fc, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if row[i] == '' or row[i] == ' ':
                    print("Updating field: {0} on ObjectID: {1}".format(field_list[i], row[0]))
                    update_count += 1
                    row[i] = None
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))
       

##########################
#  Call Functions Below  #
##########################

blanks_to_nulls(fc_layer, fields)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
