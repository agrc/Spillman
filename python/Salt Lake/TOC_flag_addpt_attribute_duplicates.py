# -*- coding: utf-8 -*-
"""
Created on Thu Sep 16 15:20:42 2021
@author: eneemann
Script to flag NG911 errors on fcess Points
"""

import arcpy
import os
import time
from xxhash import xxh64

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

######################
#  Set up variables  #
######################

# Set up databases (SGID must be changed based on user's path)
toc_db = r"C:\E911\TOC\TOC_Geovalidation_WGS84_fixes_20220909.gdb"

arcpy.env.workspace = toc_db
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False

today = time.strftime("%Y%m%d")

fc = os.path.join(toc_db, r'AddressPoints')
fc_working = os.path.join(toc_db, f'AddressPoints_errors_{today}')
fc_final_name = f'AddressPoints_errors_only_{today}'

## Make a copy of the data to work on
arcpy.management.CopyFeatures(fc, fc_working)
arcpy.AddField_management(fc_working, "Error_UGRC", "TEXT", "", "", 100)

print("Time elapsed: {:.2f}s".format(time.time() - start_time)) 


fc_count = int(arcpy.management.GetCount(fc_working)[0])

#: Check for duplicate attributes
digests = set([])

description = arcpy.da.Describe(fc_working)
print(f'Working on Duplicates for: {fc_working}')
# skip_fields = ['Error_UGRC', 'Long', 'Lat', description['shapeFieldName']]
# skip_fields = ['Error_UGRC', 'JoinID']        # for CommonNames
skip_fields = ['Error_UGRC', 'JoinID', 'ParcelID', 'PtType', description['shapeFieldName']]        # for AddressPoints


if description['hasGlobalID']:
    skip_fields.append(description['globalIDFieldName'])

if description['hasOID']:
    skip_fields.append(description['OIDFieldName'])

fields = [field.name for field in description['fields'] if field.name not in skip_fields]

#: Add OID and Error_UGRC at the end, so we can ignore them in the hash
fields.append('OID@')
fields.append('Error_UGRC')
print(fields)

oid_index = fields.index('OID@')
notes_index = fields.index('Error_UGRC')

oids_with_issues = []

duplicate_count = 0
required_count = 0
print("Looping through rows in FC ...")
with arcpy.da.UpdateCursor(fc_working, fields) as update_cursor:
    for row in update_cursor:
        comment = None
        object_id = row[oid_index]
        if object_id % 100000 == 0:
            print(f'working on OBJECTID: {object_id}')

        #: Has all fields except for OID and Error_UGRC, which are the last fields
        hasher = xxh64(str(row[:-2]))
        digest = hasher.hexdigest()

        if digest in digests:
            oids_with_issues.append(object_id)
            comment = 'attribute duplicate'
            duplicate_count += 1

        digests.add(digest)
        
        row[notes_index] = comment
        update_cursor.updateRow(row)

print(f"Total count of attribute duplicates is: {duplicate_count} or {round((duplicate_count/fc_count)*100, 3)}%")

oid_set = set(oids_with_issues)
print('\nSelect statement to view errors in ArcGIS:')
sql = f'OBJECTID IN ({", ".join([str(oid) for oid in oid_set])})'
print(sql)

# # Create copy with only points containing errors
# print('Exporting features with errors in separate feature class ...')
# where_clause = """Error_UGRC IS NOT NULL"""
# arcpy.conversion.FeatureClassToFeatureClass(fc_working, toc_db, fc_final_name, where_clause)

##########################
#  Call Functions Below  #
##########################

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))