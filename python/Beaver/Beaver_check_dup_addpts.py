# -*- coding: utf-8 -*-
"""
Created on Fri Oct 18 10:29:51 2019
@author: eneemann

Script to check for duplicate address points
"""

import arcpy
from arcpy import env
import os
import time
import re
from xxhash import xxh64


# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

beaver_db = r"C:\E911\Beaver Co\0 VESTA Update 20191016\Beaver_VESTA_update_20191016.gdb"
#beaver_db = r'C:\E911\Beaver Co\Beaver_Spillman_WGS84.gdb'
#beaver_db = r'C:\E911\Beaver Co\Beaver_Spillman_UTM.gdb'
#staging_db = r"C:\E911\Beaver Co\Beaver_Staging.gdb"
addpts = os.path.join(beaver_db, 'AddressPoints')
streets = os.path.join(beaver_db, 'Streets')
env.workspace = beaver_db
env.overwriteOutput = True

#workspace = r"C:\E911\Beaver Co\0 VESTA Update 20191016\Beaver_VESTA_update_20191016.gdb"
#table_name = os.path.join(beaver_db, 'AddressPoints')

#print(table_name)

class DuplicateTest():
    '''A class that finds and removes duplicate geometries or attributes or both
    '''
    def __init__(self, workspace, table_name):
        self.report = {'title': 'Duplicate Test', 'feature_class': table_name, 'issues': []}
        self.workspace = workspace
        self.table_name = table_name


    def sweep(self):
        '''A method that finds duplicate records and returns a report dictionary
        '''
        digests = set([])

        truncate_shape_precision = re.compile(r'(\d+\.\d{2})(\d+)')

        with arcpy.EnvManager(workspace=self.workspace):
            description = arcpy.da.Describe(self.table_name)

            skip_fields = ['guid', description['shapeFieldName']]

            if description['hasGlobalID']:
                skip_fields.append(description['globalIDFieldName'])

            if description['hasOID']:
                skip_fields.append(description['OIDFieldName'])

            fields = [field.name for field in description['fields'] if field.name not in skip_fields]

            fields.append('SHAPE@WKT')
            fields.append('OID@')

            shapefield_index = fields.index('SHAPE@WKT')
            oid_index = fields.index('OID@')

            with arcpy.da.SearchCursor(self.table_name, fields) as search_cursor:
                for row in search_cursor:
                    shape_wkt = row[shapefield_index]
                    object_id = row[oid_index]

                    if shape_wkt is None:
                        # self.report['issues'].append(object_id)

                        continue

                    #: trim some digits to help with hash matching
                    generalized_wkt = truncate_shape_precision.sub(r'\1', shape_wkt)

                    hasher = xxh64(f'{row[:-2]} {generalized_wkt}')
                    digest = hasher.hexdigest()

                    if digest in digests:
                        self.report['issues'].append(str(object_id))

                        continue

                    digests.add(digest)

        return self.report


duplicates = DuplicateTest(beaver_db, streets)
report = duplicates.sweep()
print(report)

print(len(report['issues']))

new_list = [ int(item) for item in report['issues']]
print(new_list)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
