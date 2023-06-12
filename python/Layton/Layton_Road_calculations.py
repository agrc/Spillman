# -*- coding: utf-8 -*-
"""
Created on Fri Jun 4 11:37:56 2021
@author: eneemann

4 Jun 2021 - script to calculate street fields for Davis_combined (built from Weber)
"""

import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

staging_db = r"C:\E911\Layton\DavisGeoValidation_updates.gdb"
env.workspace = staging_db
fc_layer = "DavisStreets_combined_from_SGID_20210604"    # Update to working streets fc
streets_fc = os.path.join(staging_db, fc_layer)


###############
#  Functions  #
###############


def calc_distances(streets):
    # Calculated necessary distance fields
    print('Calculating geometry (distance) ...')
    sr_utm12N = arcpy.SpatialReference("NAD 1983 UTM Zone 12N")
    geom_start_time = time.time()
    arcpy.management.CalculateGeometryAttributes(streets, [["LengthMiles", "LENGTH_GEODESIC"]], "MILES_US", "", sr_utm12N)
    arcpy.management.CalculateGeometryAttributes(streets, [["LengthFt", "LENGTH_GEODESIC"]], "FEET_US", "", sr_utm12N)
    
    print("Time elapsed calculating geometry: {:.2f}s".format(time.time() - geom_start_time))


def calc_minutes(streets):
    # Calculate travel time field
    update_count = 0
    #             0            1         2    
    fields = ['Minutes', 'LengthMiles', 'Speed']
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows to calculate TrvlTime ...")
        for row in cursor:
            if row[2] == 0:
                speed = 25
            else:
                speed = row[2]
            row[0] = (row[1]/speed)*60
            row[2] = speed
            update_count += 1
            cursor.updateRow(row)
    print("Total count of Minutes updates is {}".format(update_count))


def calc_oneway(streets):
    # Calculate "Oneway" field
    update_count_oneway = 0
    #                    0         1  
    fields_oneway = ['OneWay_code', 'Oneway']
    with arcpy.da.UpdateCursor(streets, fields_oneway) as cursor:
        print("Looping through rows to calculate Oneway field ...")
        for row in cursor:
            if row[0] == '0' or row[0] == None:
    #        if row[0] == '0':      
                row[1] = 'B'
                update_count_oneway += 1
            elif row[0] == '1':
                row[1] = 'FT'
                update_count_oneway += 1
            elif row[0] == '2':
                row[1] = 'TF'
                update_count_oneway += 1
            cursor.updateRow(row)
    print("Total count of Oneway updates is {}".format(update_count_oneway))


def blanks_to_nulls(streets):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'PreDir', 'StreetName', 'StreetType', 'SufDir', 'LocationText', 'Notes', 'AltName',
             'CommonNameShortStName', 'CommonNameStAbbr', 'CommonName4', 'CommonName5', 'CommonName6', 'CommonName7',
             'CommonName8', 'CommonName9', 'OneWay_code', 'OneWay', 'VERT_LEVEL', 'Speed', 'LengthFt', 'LengthMiles',
             'Minutes', 'StreetClassification']
    fields = arcpy.ListFields(streets)

    field_list = []
    for field in fields:
        # print field.name
        if field.name in flist:
            # print("{} appended to field_list".format(field.name))
            field_list.append(field)

    with arcpy.da.UpdateCursor(streets, flist) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            # print row
            for i in range(len(field_list)):
                # if (field_list[i].type == "String" and row[i] == '') or\
                #         (field_list[i].type == "String" and row[i] == ' '):
                if row[i] == '' or row[i] == ' ':
                    print("Updating field: {0} on ObjectID: {1}".format(field_list[i].name, row[0]))
                    update_count += 1
                    row[i] = None
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))


def calc_street(streets):
    update_count = 0
    # Calculate "STREET" field where applicable
    where_clause = "StreetName IS NOT NULL AND STREET IS NULL"
    fields = ['PreDir', 'StreetName', 'SufDir', 'StreetType', 'STREET']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[0] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            if row[3] is None: row[3] = ''
            parts = [row[0], row[1], row[2], row[3]]
            row[4] = " ".join(parts)
            row[4] = row[4].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
            print("New value for {0} is: {1}".format(fields[4], row[4]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0}: {1}".format(fields[4], update_count))


def highway_to_sr_us(streets):
    update_count1 = 0
    # Calculate updates on "SALIAS1" and change 'HIGHWAY' to 'SR'
    where_clause1 = "HWYNAME LIKE 'SR%' AND SALIAS1 LIKE '%HIGHWAY%'"
    fields1 = ['SALIAS1']
    with arcpy.da.UpdateCursor(streets, fields1, where_clause1) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "SR")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields1[0], row[0]))
            update_count1 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS1 'HIGHWAY' to 'SR' updates: {}".format(update_count1))

    update_count2 = 0
    # Calculate updates on "SALIAS1" and change 'HIGHWAY' to 'US'
    where_clause2 = "HWYNAME LIKE 'US%' AND SALIAS1 LIKE '%HIGHWAY%'"
    fields2 = ['SALIAS1']
    with arcpy.da.UpdateCursor(streets, fields2, where_clause2) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "US")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields2[0], row[0]))
            update_count2 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS1 'HIGHWAY' to 'US' updates: {}".format(update_count2))

    update_count3 = 0
    # Calculate updates on "SALIAS2" and change 'HIGHWAY' to 'SR'
    where_clause3 = "HWYNAME LIKE 'SR%' AND SALIAS2 LIKE '%HIGHWAY%'"
    fields3 = ['SALIAS2']
    with arcpy.da.UpdateCursor(streets, fields3, where_clause3) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "SR")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields3[0], row[0]))
            update_count3 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS2 'HIGHWAY' to 'SR' updates: {}".format(update_count3))

    update_count4 = 0
    # Calculate updates on "SALIAS2" and change 'HIGHWAY' to 'US'
    where_clause4 = "HWYNAME LIKE 'US%' AND SALIAS2 LIKE '%HIGHWAY%'"
    fields4 = ['SALIAS2']
    with arcpy.da.UpdateCursor(streets, fields4, where_clause4) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[0].replace("HIGHWAY", "US")
            row[0] = row[0][:30]
            print("New value for {0} is: {1}".format(fields4[0], row[0]))
            update_count4 += 1
            cursor.updateRow(row)
    print("Total count of SALIAS2 'HIGHWAY' to 'US' updates: {}".format(update_count4))


def street_blank_to_null(streets):
    update_count = 0
    # Calculate updates on STREET to remove blanks
    where_clause = "STREET LIKE ''"
    fields = ['STREET']
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = None
            print("New value for {0} is: {1}".format(fields[0], row[0]))
            update_count += 1
            cursor.updateRow(row)
    print("Total count of STREET updates from blank to null is: {}".format(update_count))


def calc_location(streets):
    # Calculate the "LOCATION" field with ACSALIAS
    update_count = 0
    where_clause = "LocationText IS NULL AND ALIAS IS NOT NULL"
    fields = ['ALIAS', 'LocationText',]
    with arcpy.da.UpdateCursor(streets, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[1] = row[0]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of LocationText field updates in {streets} is: {update_count}")


def strip_fields(streets):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field

    fields = arcpy.ListFields(streets)

    field_list = []
    for field in fields:
        print(field.type)
        if field.type == 'String':
            field_list.append(field.name)
            
    print(field_list)

    with arcpy.da.UpdateCursor(streets, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if isinstance(row[i], str):
                    row[i] = row[i].strip()
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of stripped fields is: {}".format(update_count))

##########################
#  Call Functions Below  #
##########################
# # Calc STREET from other fields
#calc_distances(streets_fc)
calc_minutes(streets_fc)
calc_oneway(streets_fc)
blanks_to_nulls(streets_fc)
calc_street(streets_fc)
street_blank_to_null(streets_fc)
calc_location(streets_fc)
strip_fields(streets_fc)


# highway_to_sr_us(streets_fc)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))