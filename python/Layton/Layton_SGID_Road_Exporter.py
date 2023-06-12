# -*- coding: utf-8 -*-
"""
Created on Thu Oct 20 16:27:21 2022
@author: eneemann
Script to export SGID roads and ETL into Davis county schema
- exports roads from SGID w/i 7 mile buffer of Davis county
- projects data to WGS84
- preps data and loads into Davis Spillman schema
- calculates fields
- cleans fields and converts blanks to NULLs
- applies Davis Spillman nomenclature using a dictionary
- applies Davis Spillman casing rules (with help of a dictionary)

20 Oct 2022: Created initial version of code (EMN).
"""

import os
import time
import numpy as np
import arcpy
from arcpy import env

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))

today = time.strftime("%Y%m%d")

# Set up paths and variables
staging_db = r"C:\E911\Layton\Davis_staging.gdb"
schema_db = r"C:\E911\Layton\Davis_new_road_schema.gdb"
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
county = os.path.join(staging_db, "aaa_Davis_County_UTM")
sgid_roads = os.path.join(SGID, "SGID.TRANSPORTATION.Roads")
export_roads = os.path.join(staging_db, "Roads_SGID_export_" + today)
wgs84_export_roads = os.path.join(staging_db, f"Roads_SGID_export_{today}_WGS84")
streets_schema = os.path.join(schema_db, "Streets_TOC_schema_edited_for_davis")
working_roads = os.path.join(staging_db, f"Davis_streets_build_{today}")
env.workspace = staging_db
env.overwriteOutput = True

name_change_dict = {
    'I-15 NB': 'NB 15',
    'I-15 SB': 'SB 15',
    'I-84 WB': 'WB 84',
    'I-84 EB': 'EB 84',
    'I-80 WB': 'WB 80',
    'I-80 EB': 'EB 80',
    'I-215 NB': 'NB 215',
    'I-215 SB': 'SB 215',
    'I-215 WB': 'WB 215',
    'I-215 EB': 'EB 215',
    'I-215W NB': 'NB 215W',
    'I-215W SB': 'SB 215W',
    'I-215N EB': 'EB 215N',
    'I-215N WB': 'WB 215N',
    'HWY 89 NB': 'NB 89',
    'HWY 89 SB': 'SB 89',
    'US 89 NB': 'NB 89',
    'US 89 SB': 'SB 89',
    'US 89 X': 'HWY 89 X',
    'US 89 RAMP': 'HWY 89 RAMP',
    'LEGACY NB PKWY': 'NB LEGACY',
    'LEGACY SB PKWY': 'SB LEGACY',
    'LEGACY NB X': 'NB LEGACY X',
    'LEGACY SB X': 'SB LEGACY X',
    'LEGACY NB RAMP': 'NB LEGACY RAMP',
    'LEGACY SB RAMP': 'SB LEGACY RAMP',
    'BANGERTER SB': 'SB BANGERTER',
    'BANGERTER NB': 'NB BANGERTER',
    'LEGACY NB': 'NB LEGACY',
    'LEGACY SB': 'SB LEGACY',
    'HIGHWAY' : 'HWY',
    }

casing_replacements = {
    'Nb ': 'NB ',
    'Sb ': 'SB ',
    'Eb ': 'EB ',
    'Wb ': 'WB ',
    'Sr ': 'SR ',
    'Us ': 'US ',
    'Th ': 'th ',
    }

endswith_replacements = {
    'Nb': 'NB',
    'Sb': 'SB',
    'Eb': 'EB',
    'Wb': 'WB',
    'Th': 'th',
    }


def export_from_sgid():
    # Export roads from SGID into new FC based on intersection with county boundary
    # First make layer from relevant counties (Davis, Weber, SL, Morgan, Tooele)
    where_SGID = "COUNTY_L IN ('49011', '49057', '49035', '49029', '49045') OR COUNTY_R IN ('49011', '49057', '49035', '49029', '49045')"
    if arcpy.Exists("sgid_roads_lyr"):
        arcpy.management.Delete("sgid_roads_lyr")
    arcpy.management.MakeFeatureLayer(sgid_roads, "sgid_roads_lyr", where_SGID)
    print("Selecting SGID roads to export by intersection with 7-mile county buffer ...")
    arcpy.management.SelectLayerByLocation("sgid_roads_lyr", "HAVE_THEIR_CENTER_IN", county, "7 Miles")
    arcpy.management.CopyFeatures("sgid_roads_lyr", export_roads)


def project_to_wgs84():
    # Project to WGS84
    print(f"Projecting {export_roads} to WGS84...")
    sr = arcpy.SpatialReference("WGS 1984")
    arcpy.management.Project(export_roads, wgs84_export_roads, sr, "WGS_1984_(ITRF00)_To_NAD_1983")


def prep_fields(streets):
    # Calculate intermediate fields on wgs84 exported data
    arcpy.management.AddField(streets, "STREET", "TEXT", "", "", 50)

    count = 0
    #             0         1          2        3         4             5
    fields = ['PREDIR', 'FULLNAME', 'STREET']
    with arcpy.da.UpdateCursor(streets, fields) as ucursor:
        print("Calculating STREET field ...")
        for row in ucursor:
            if row[0] is None: row[0] = ''
            if row[1] is None: row[1] = ''
            parts = [row[0], row[1]]
            row[2] = " ".join(parts)
            row[2] = row[2].strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
            row[2] = row[2][:60]
                  
            count += 1
            ucursor.updateRow(row)
    print(f'Total count of STREET field updates: {count}')


def load_into_schema():
    arcpy.management.CopyFeatures(streets_schema, working_roads)

    # Create field map for SGID to Davis schema
    print('Creating field map ...')
    fms_rds = arcpy.FieldMappings()
    
    fm_dict_rds = {'CARTOCODE': 'CARTOCODE',
               'PREDIR': 'PREDIR',
               'NAME': 'STREETNAME',
               'POSTTYPE': 'STREETTYPE',
               'POSTDIR': 'SUFDIR',
               'A1_NAME': 'ALIAS1',
               'A1_POSTTYPE': 'ALIAS1TYPE',
               'A2_NAME': 'ALIAS2',
               'A2_POSTTYPE': 'ALIAS2TYPE',
               'AN_NAME': 'ACSNAME',
               'AN_POSTDIR': 'ACSSUF',
               'ZIPCODE_L': 'ZIPLEFT',
               'ZIPCODE_R': 'ZIPRIGHT',
               'ONEWAY': 'ONEWAY',
               'SPEED_LMT': 'SPEED',
               'DOT_HWYNAM': 'HWYNAME',
               'STREET': 'STREET',
               'FROMADDR_L': 'L_F_ADD',
               'TOADDR_L': 'L_T_ADD',
               'FROMADDR_R': 'R_F_ADD',
               'TOADDR_R': 'R_T_ADD',
               'VERT_LEVEL': 'VERT_LEVEL',
               'STATUS': 'STATUS',
               'UPDATED': 'UPDATED',
               'ADDRSYS_L': 'ADDRSYS_L',
               'ADDRSYS_R': 'ADDRSYS_R'
               }

    for key in fm_dict_rds:
        fm_rds = arcpy.FieldMap()
        fm_rds.addInputField(wgs84_export_roads, key)
        output_rds = fm_rds.outputField
        output_rds.name = fm_dict_rds[key]
        fm_rds.outputField = output_rds
        fms_rds.addFieldMap(fm_rds)

    # Append SGID_WGS84 export data into Davis schema
    print('Appending SGID roads into Davis schema ...')
    query = """STATUS <> 'Planned' AND CARTOCODE NOT IN ('99', '15')"""
    arcpy.management.Append(wgs84_export_roads, working_roads, "NO_TEST", field_mapping=fms_rds, expression=query)


def calc_fields(streets):
    # Calculate remaining fields
    update_count = 0
    # Calculate "JOINID" field
    fields = ['JOINID', 'OID@']
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")

    # Calculate the "LOCATION" and "ACSALIAS" fields
    update_count = 0
    # where_clause = "ACSNAME IS NOT NULL AND ACSSUF IS NOT NULL AND (LOCATION IS NULL AND ACSALIAS IS NULL)"
    #             0          1         2           3          4   
    fields = ['ACSNAME', 'ACSSUF', 'ACSALIAS', 'LOCATION', 'PREDIR']
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[0] not in ('', ' ', None) and row[1] not in ('', ' ', None) and (row[3] in ('', ' ', None) or row[2]  in ('', ' ', None)):
                loc = f"{row[4]} {row[0]} {row[1]}"
                loc = loc.strip().replace("  ", " ").replace("  ", " ").replace("  ", " ")
                row[2] = loc
                row[3] = loc
                # print(f"New value for {fields[2]} and {fields[3]} is: {loc}")
                update_count += 1
                cursor.updateRow(row)
    print(f"Total count of LOCATION field updates in {streets} is: {update_count}")

    # Calculated necessary travel time fields
    print('Calculating geometry (distance) ...')
    sr_utm12N = arcpy.SpatialReference("NAD 1983 UTM Zone 12N")
    geom_start_time = time.time()
    arcpy.management.CalculateGeometryAttributes(streets, [["Distance", "LENGTH_GEODESIC"]], "MILES_US", "", sr_utm12N)
    print("Time elapsed calculating geometry: {:.2f}s".format(time.time() - geom_start_time))

    # Calculate travel time field
    update_count = 0
    #             0            1         2    
    fields = ['TrvlTime', 'Distance', 'SPEED']
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows to calculate TrvlTime ...")
        for row in cursor:
            if row[2] == 0:
                row[2] = 25
            row[0] = (row[1]/row[2])*60
            update_count += 1
            cursor.updateRow(row)
    print("Total count of TrvlTime updates is {}".format(update_count))

    # Calculate "One_Way" field
    update_count_oneway = 0
    #                    0         1  
    fields_oneway = ['ONEWAY', 'One_Way']
    with arcpy.da.UpdateCursor(streets, fields_oneway) as cursor:
        print("Looping through rows to calculate One_Way field ...")
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
    print("Total count of One_Way updates is {}".format(update_count_oneway))


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


def blanks_to_nulls(streets):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    fields = arcpy.ListFields(streets)

    field_list = []
    for field in fields:
        if field.name != 'OBJECTID':
            field_list.append(field.name)

    with arcpy.da.UpdateCursor(streets, field_list) as cursor:
        print("Converting blanks to NULLs ...")
        for row in cursor:
            for i in range(len(field_list)):
                if row[i] in ('', ' '):
                    update_count += 1
                    row[i] = None
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))


def apply_nomenclature(streets):
    # First remove PREDIRs from interstate segments
    predir_count = 0
    fields = ['STREET', 'PREDIR']
    with arcpy.da.UpdateCursor(streets, fields, "(STREETNAME LIKE '%I-1%' OR STREETNAME LIKE '%I-8%' OR STREETNAME LIKE '%I-2%') AND PREDIR IS NOT NULL") as cursor:
        print("Looping through rows make remove PREDIRs from interstates ...")
        for row in cursor:
            row[0] = row[0].split(row[1], 1)[1].strip()
            row[1] = None
            predir_count += 1
            cursor.updateRow(row)
    print(f"Total count of Interstate PREDIR removals is: {predir_count}")

    # Second remove 'FWY' from STREET and STREETTYPE and NULL out PREDIR field (interstates), then convert 'HIGHWAY' to 'HWY'
    fwy_count = 0
    hwy_count = 0
    #             0        1           2             3             4            5        6           7
    fields = ['STREET', 'PREDIR', 'STREETTYPE', 'ALIAS1TYPE', 'ALIAS2TYPE', 'ALIAS1', 'ALIAS2', 'STREETNAME']
    with arcpy.da.UpdateCursor(streets, fields, "STREET is not NULL") as cursor:
        print("Looping through rows make FWY/HWY updates ...")
        for row in cursor:
            if 'FWY' in row[0]:
                row[0] = row[0].replace('FWY', '').replace('  ', ' ').replace('  ', ' ').strip()
                fwy_count += 1
                row[1] = None
                row[2] = None
                row[3] = None
                row[4] = None
            if row[0] is not None and 'HIGHWAY' in row[0]:
                row[0] = row[0].replace('HIGHWAY', 'HWY').replace('  ', ' ').replace('  ', ' ').strip()
                hwy_count += 1
            if row[5] is not None and 'HIGHWAY' in row[5]:
                row[5] = row[5].replace('HIGHWAY', 'HWY').replace('  ', ' ').replace('  ', ' ').strip()
                hwy_count += 1
            if row[6] is not None and 'HIGHWAY' in row[6]:
                row[6] = row[6].replace('HIGHWAY', 'HWY').replace('  ', ' ').replace('  ', ' ').strip()
                hwy_count += 1
            if row[7] is not None and 'HIGHWAY' in row[7]:
                row[7] = row[7].replace('HIGHWAY', 'HWY').replace('  ', ' ').replace('  ', ' ').strip()
                hwy_count += 1
            cursor.updateRow(row)
    print(f"Total count of 'FWY' removals is: {fwy_count}")
    print(f"Total count of 'HIGHWAY' to 'HWY' changes: {hwy_count}")
    
    # Then replace strings based on name_change_dict
    name_query = """STREET LIKE '%FWY%' OR STREET LIKE '%LEGACY%PKWY%' OR STREET LIKE '% NB%' OR STREET LIKE '% SB%' OR STREET LIKE '%I%8%' OR STREET LIKE '%I%15%' OR STREET LIKE '%89%'"""
    # name_query = """STREETNAME LIKE '80 %' OR STREETNAME LIKE '15 %' OR STREETNAME LIKE '84 %' OR STREETNAME LIKE '215%'"""
    name_count = 0
    #             0          1           2          3
    fields = ['STREET', 'STREETNAME', 'ALIAS1', 'ALIAS2']
    with arcpy.da.UpdateCursor(streets, fields, name_query) as cursor:
        print("Looping through rows to make nomenclature changes ...")
        for row in cursor:
            for key in name_change_dict:
                if key in row[0]:
                    row[0] = row[0].replace(key, name_change_dict[key]).replace('  ', ' ').replace('  ', ' ').strip()
                    name_count += 1
                if row[1] is not None and key in row[1]:
                    row[1] = row[1].replace(key, name_change_dict[key]).replace('  ', ' ').replace('  ', ' ').strip()
                if row[2] is not None and key in row[2]:
                    row[2] = row[2].replace(key, name_change_dict[key]).replace('  ', ' ').replace('  ', ' ').strip()
                if row[3] is not None and key in row[3]:
                    row[3] = row[3].replace(key, name_change_dict[key]).replace('  ', ' ').replace('  ', ' ').strip()
            cursor.updateRow(row)
    print(f"Total count of nomenclature changes: {name_count}")
    
    # Clean up dashes in HWYNAME
    dash_query = """HWYNAME LIKE '%US-%' OR HWYNAME LIKE '%SR-%'"""
    dash_count = 0
    fields = ['HWYNAME']
    with arcpy.da.UpdateCursor(streets, fields, dash_query) as cursor:
        print("Looping through rows to make nomenclature changes ...")
        for row in cursor:
            if 'US-' in row[0]:
                row[0] = row[0].replace('US-', 'US ').replace('  ', ' ').replace('  ', ' ').strip()
                dash_count += 1
            if 'SR-' in row[0]:
                row[0] = row[0].replace('SR-', 'SR ').replace('  ', ' ').replace('  ', ' ').strip()
                dash_count += 1
            cursor.updateRow(row)
    print(f"Total count of HWYNAME dash changes: {dash_count}")


def apply_casing(streets):
    # Apply title casing to street name components
    # Exceptions: NB, SB, EB, WB
    case_count = 0
    fields = ['STREETNAME', 'STREETTYPE', 'STREET', 'ALIAS1', 'ALIAS1TYPE', 'ALIAS2', 'ALIAS2TYPE', 'ALIAS3', 'ALIAS3TYPE',]
    with arcpy.da.UpdateCursor(streets, fields) as cursor:
        print("Looping through rows to apply casing rules ...")
        for row in cursor:
            for i in np.arange(len(fields)):
                if row[i] is not None:
                    row[i] = row[i].title()
                    for key in casing_replacements:
                        if key in row[i]:
                            row[i] = row[i].replace(key, casing_replacements[key])
                            case_count += 1
                    for key in endswith_replacements:
                        if row[i].endswith(key):
                            row[i] = row[i].replace(key, endswith_replacements[key])
                            case_count += 1
            cursor.updateRow(row)
    print(f"Total of upper case preservations: {case_count}")



# Update/uncomment next line to apply nomenclature to existing feature class
# working_roads = os.path.join(r"C:\E911\Layton\DavisGeoValidation.gdb", "DavisStreets")
# working_roads = os.path.join(staging_db, 'Streets_update_20230302')

export_from_sgid()
project_to_wgs84()
prep_fields(wgs84_export_roads)
load_into_schema()
calc_fields(working_roads)
strip_fields(working_roads)
blanks_to_nulls(working_roads)
apply_nomenclature(working_roads)
apply_casing(working_roads)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))

