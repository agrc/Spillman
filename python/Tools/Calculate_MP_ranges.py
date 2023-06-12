# -*- coding: utf-8 -*-
"""
Created on Tue Jul 30 09:46:44 2019

@author: eneemann
Script to calculate milepost-based address ranges from DOT_F_MILE and DOT_T_MILE
- roads layer must be in UTRANS/SGID schema
- segments must all be pointing in direction of increasing mileposts
- then load data into desired schema after new ranges have been calculated

31 Jul 2019: Created initial version of code (EMN).
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
streets = os.path.join(db, "SGID_I8084_only_TEST_WGS84")
# outname = os.path.join(db, "SGID_I8084_only_TEST_" + today)
env.workspace = db
env.overwriteOutput = True
multiplier = 100

# Get list of fields in the feature class
flist = arcpy.ListFields(streets)
field_list = []
for field in flist:
    field_list.append(field.name)

print("Fields in feature class:")
print(field_list)

# If necessary, add fields used to calculate new ranges to feature class
if 'FMPADR' not in field_list:
    arcpy.management.AddField(streets, "FMPADR", "LONG")
if 'TMPADR' not in field_list:
    arcpy.management.AddField(streets, "TMPADR", "LONG")

# Calculate FMPADR and TMPADR fields by multiplying T/F MILE fields
# Select streets where FROM milepost is less than TO milepost (pointed in correct direction)
update_count = 0
where_clause = "DOT_F_MILE < DOT_T_MILE"
#             0          1           2          3
fields = ['FMPADR', 'DOT_F_MILE', 'TMPADR', 'DOT_T_MILE']
with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
    print("Calculating TMPADR and FMPADR on correct segments ...")
    for row in cursor:
        row[0] = row[1]*multiplier
        row[2] = row[3]*multiplier
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is: {update_count}")

# Select streets where FROM milepost is greater than TO milepost (originally pointed in wrong direction)
update_count = 0
where_clause = "DOT_F_MILE > DOT_T_MILE"
#             0          1           2          3
fields = ['FMPADR', 'DOT_F_MILE', 'TMPADR', 'DOT_T_MILE']
with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
    print("Calculating TMPADR and FMPADR on reversed segments ...")
    for row in cursor:
        row[0] = row[3]*multiplier
        row[2] = row[1]*multiplier
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is: {update_count}")

# Calculate new address ranges
# Select addresses that are even: [FROM] add 1 to left side, leave right side alone
update_count = 0
where_clause = "MOD(FMPADR,2) = 0"
#              0             1           2
fields = ['FROMADDR_L', 'FROMADDR_R', 'FMPADR']
with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
    print("Calculating FROMADDR_L and FROMADDR_R on even FROM addresses ...")
    for row in cursor:
        row[0] = row[2] + 1
        row[1] = row[2]
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is: {update_count}")

# Select addresses that are odd: [FROM] leave left side alone, add 1 to right side
update_count = 0
where_clause = "MOD(FMPADR,2) = 1"
#              0             1           2
fields = ['FROMADDR_L', 'FROMADDR_R', 'FMPADR']
with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
    print("Calculating FROMADDR_L and FROMADDR_R on odd FROM addresses ...")
    for row in cursor:
        row[0] = row[2]
        row[1] = row[2] + 1
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is: {update_count}")

# Select addresses that are even: [TO] subtract 1 from left side, subtract 2 from right side
update_count = 0
where_clause = "MOD(TMPADR,2) = 0"
#             0           1          2
fields = ['TOADDR_L', 'TOADDR_R', 'TMPADR']
with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
    print("Calculating TOADDR_L and TOADDR_R on even TO addresses ...")
    for row in cursor:
        row[0] = row[2] - 1
        row[1] = row[2] - 2
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is: {update_count}")

# Select addresses that are odd: subtract 2 from left side, subtract 1 from right side
update_count = 0
where_clause = "MOD(TMPADR,2) = 1"
#             0           1          2
fields = ['TOADDR_L', 'TOADDR_R', 'TMPADR']
with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
    print("Calculating TOADDR_L and TOADDR_R on odd TO addresses ...")
    for row in cursor:
        row[0] = row[2] - 2
        row[1] = row[2] - 1
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is: {update_count}")

# Select where address is zero: [FROM] change zeros to 1 or 2 based on which side of road they're on
update_count = 0
where_clause = "FROMADDR_L = 0 OR FROMADDR_R = 0"
#              0             1    
fields = ['FROMADDR_L', 'FROMADDR_R']
with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
    print("Calculating TOADDR_L and TOADDR_R on odd TO addresses ...")
    for row in cursor:
        row[0] = 1
        row[1] = 2
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is: {update_count}")


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))