# -*- coding: utf-8 -*-
"""
Created on Mon Mar 6 8:49:21 2023
@author: eneemann
Script to export SGID address points for BoxElder and UintahBasin

6 Mar 2023: Created initial version of code (EMN).
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

# Set up paths and variables
staging_db = r"C:\E911\UtahDPS Schemas\BE_UB_Staging.gdb"
schema_db = r"C:\E911\UtahDPS Schemas\Geovalidation_WGS84.gdb"
geovalidation_db = r"C:\E911\UtahDPS Schemas\BE_UB_Geovalidation_WGS84.gdb"
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
citycodes = os.path.join(geovalidation_db, "CityCodes")
sgid_addpts = os.path.join(SGID, "SGID.LOCATION.AddressPoints")
export_addpts = os.path.join(staging_db, "Addpts_SGID_export_" + today)
wgs84_export_addpts = os.path.join(staging_db, f"Addpts_SGID_export_{today}_WGS84")
addpts_schema = os.path.join(schema_db, "AddressPoints")
working_addpts = os.path.join(staging_db, f"BE_UB_addpts_build_{today}")
env.workspace = staging_db
env.overwriteOutput = True

poly_dict = {
        'CityCode': {'poly_path': citycodes, 'poly_field': "CITYCD"},
        }

def export_from_sgid():
    # Export address points from SGID into new FC based on intersection with citycodes boundary
    # First make layer from relevant counties (BoxElder, Weber, Davis, Tooele, Cache and Summit, Daggett, Wasatch, Duchesne, Uintah, Carbon, Emery, Grand)
    where_SGID = "CountyID IN ('49003', '49057', '49011', '49045', '49005', '49043', '49009', '49051', '49013', '49047', '49007', '49015', '49019') AND AddNumSuffix IS NULL"
    if arcpy.Exists("sgid_addpts_lyr"):
        arcpy.management.Delete("sgid_addpts_lyr")
    arcpy.management.MakeFeatureLayer(sgid_addpts, "sgid_addpts_lyr", where_SGID)
    print("Selecting SGID address points to export by intersection with 10-mile citycode buffer ...")
    arcpy.management.SelectLayerByLocation("sgid_addpts_lyr", "HAVE_THEIR_CENTER_IN", citycodes, "10 Miles")
    arcpy.management.CopyFeatures("sgid_addpts_lyr", export_addpts)


def project_to_wgs84():
    # Project to WGS84
    print(f"Projecting {export_addpts} to WGS84...")
    sr = arcpy.SpatialReference("WGS 1984")
    arcpy.management.Project(export_addpts, wgs84_export_addpts, sr, "WGS_1984_(ITRF00)_To_NAD_1983")



def load_into_schema():
    if arcpy.Exists(working_addpts):
        arcpy.management.Delete(working_addpts)
    arcpy.management.CopyFeatures(addpts_schema, working_addpts)

    # # Create field map for SGID to DPS Geovalidation schema
    # print('Creating field map ...')
    # fms_addpts = arcpy.FieldMappings()
    
    # fm_dict_addpts = {
    #            'FullAdd': 'FullAdd',
    #            'AddNum': 'AddNum',
    #            'POSTDIR': 'PrefixDir',
    #            'PrefixDir': 'StreetName',
    #            'StreetType': 'StreetType',
    #            'SuffixDir': 'SuffixDir',
    #            'LandmarkName': 'LandmarkName',
    #            'Building': 'Building',
    #            'City': 'City',
    #            'ZipCode': 'ZipCode',
    #            'CountyID': 'CountyID',
    #            'State': 'State',
    #            'PtLocation': 'PtLocation',
    #            'PtType': 'PtType',
    #            'Structure': 'Structure',
    #            'ParcelID': 'ParcelID',
    #            'AddSource': 'AddSource',
    #            'LoadDate': 'LoadDate',
    #            'UnitType': 'UnitType',
    #            'UnitID': 'UnitID'
    #            }

    # for key in fm_dict_addpts:
    #     fm_addpts = arcpy.FieldMap()
    #     fm_addpts.addInputField(wgs84_export_addpts, key)
    #     output_addpts = fm_addpts.outputField
    #     output_addpts.name = fm_dict_addpts[key]
    #     fm_addpts.outputField = output_addpts
    #     fms_addpts.addFieldMap(fm_addpts)

    # Append SGID_WGS84 export data into DPS Geovalidation schema
    print('Appending SGID address points into DPS Geovalidation schema ...')
    # arcpy.management.Append(wgs84_export_addpts, working_addpts, "NO_TEST", field_mapping=fms_addpts)
    arcpy.management.Append(wgs84_export_addpts, working_addpts, "NO_TEST")


def remove_special_chars(addpts):
    # Remove '.(), from string fields
    special_chars = ["'", ".", "(", ")", ","]
    update_count = 0
    field_list = [f.name for f in arcpy.ListFields(addpts) if f.type == "String"]
    with arcpy.da.UpdateCursor(addpts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                # Replace any special character with an empty string
                for char in special_chars:
                    if row[i] is not None and char in row[i]:
                        row[i] = row[i].replace(char, "")
                        update_count += 1
            cursor.updateRow(row)
    print(f"Total count of special characters removed: {update_count}")


def calc_fields(addpts):
    # 'Status', 'Editor', 'ModifyDate', 'CityCode', 'JoinID', 'Location', 'ACSNAME', 'ACSSUF', 'NeedsAttn', 'Label', 'ACSALIAS', 'CommonName',
        
    # Calculate remaining fields
    update_count = 0
    # Calculate "JOINID" field
    fields = ['JoinID', 'OID@']
    with arcpy.da.UpdateCursor(addpts, fields) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            row[0] = row[1]
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")

    # Calculate the "Label" field
    update_count = 0
    where_clause = "Label IS NULL"
    fields = ['Label', 'AddNum', 'UnitType', 'UnitID']
    with arcpy.da.UpdateCursor(addpts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[3] is not None and row[2] is None:
                row[2] = '#'
            if row[1] is None: row[0] = ''
            if row[2] is None: row[2] = ''
            if row[3] is None: row[3] = ''
            parts = [row[1], row[2], row[3]]
            row[0] = " ".join(parts).strip()
            row[0] = row[0].replace("  ", " ").replace("  ", " ").replace("  ", " ")
            update_count += 1
            cursor.updateRow(row)
    print("Total count of updates to {0} field: {1}".format(fields[0], update_count))
    
    # Calculate "CommonName" field where applicable
    update_count = 0
    where_clause = "CommonName IS NULL AND LandmarkName IS NOT NULL"
    fields = ['CommonName', 'LandmarkName', 'UnitID']
    with arcpy.da.UpdateCursor(addpts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if row[1] is None:
                row[0] = None
            else:
                # if row[1] is None: row[1] = ''
                if row[2] in (None, '', ' '):
                    row[0] = row[1]
                else:
                    row[0] = row[1] + ' #' + row[2]
                    row[0] = ' '.join(row[0].split()).strip()    
            update_count += 1
            cursor.updateRow(row)
    print(f"Total count of updates to {fields[0]} field: {update_count}")


def assign_city_code(pts, polygonDict):
    #: Assing polygon attributes to poins using near tables to get the nearsest polygon info
    arcpy.env.workspace = os.path.dirname(pts)
    arcpy.env.overwriteOutput = True
    
    for lyr in polygonDict:
        #: Set path to polygon layer
        polyFC = polygonDict[lyr]['poly_path']
        print (polyFC)
        
        #: Generate near table for each polygon layer
        neartable = 'in_memory\\near_table'
        arcpy.analysis.GenerateNearTable(pts, polyFC, neartable, '1 Meters', 'NO_LOCATION', 'NO_ANGLE', 'CLOSEST')
        
        #: Create dictionaries to store data
        pt_poly_link = {}       #: Dictionary to link points and polygons by OIDs 
        poly_OID_field = {}     #: Dictionary to store polygon NEAR_FID as key, polygon field as value
    
        #: Loop through near table, store point IN_FID (key) and polygon NEAR_FID (value) in dictionary (links two features)
        with arcpy.da.SearchCursor(neartable, ['IN_FID', 'NEAR_FID', 'NEAR_DIST']) as nearCur:
            for row in nearCur:
                pt_poly_link[row[0]] = row[1]       # IN_FID will return NEAR_FID
                #: Add all polygon OIDs as key in dictionary
                poly_OID_field.setdefault(row[1])
        
        #: Loop through polygon layer, if NEAR_FID key in poly_OID_field, set value to poly field name
        with arcpy.da.SearchCursor(polyFC, ['OID@', polygonDict[lyr]['poly_field']]) as polyCur:
            for row in polyCur:
                if row[0] in poly_OID_field:
                    poly_OID_field[row[0]] = row[1]
        
        #: Loop through points layer, using only OID and field to be updated
        with arcpy.da.UpdateCursor(pts, ['OID@', lyr]) as uCur:
            for urow in uCur:
                try:
                    #: Search for corresponding polygon OID in polygon dictionay (polyDict)
                    if pt_poly_link[urow[0]] in poly_OID_field:
                        #: If found, set point field equal to polygon field
                        #: IN_FID in pt_poly_link returns NEAR_FID, which is key in poly_OID_field that returns value of polygon field
                        urow[1] =  poly_OID_field[pt_poly_link[urow[0]]]
                except:         #: If error raised, just put a blank in the field
                    urow[1] = ''
                uCur.updateRow(urow)
    
        #: Delete in memory near table
        arcpy.management.Delete(neartable)


def strip_fields(addpts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field

    fields = arcpy.ListFields(addpts)

    field_list = []
    for field in fields:
        print(field.type)
        if field.type == 'String':
            field_list.append(field.name)
            
    print(field_list)

    with arcpy.da.UpdateCursor(addpts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if isinstance(row[i], str):
                    row[i] = row[i].strip()
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of stripped fields is: {}".format(update_count))


def blanks_to_nulls(addpts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    fields = arcpy.ListFields(addpts)

    field_list = []
    for field in fields:
        if field.name != 'OBJECTID':
            field_list.append(field.name)

    with arcpy.da.UpdateCursor(addpts, field_list) as cursor:
        print("Converting blanks to NULLs ...")
        for row in cursor:
            for i in range(len(field_list)):
                if row[i] in ('', ' '):
                    update_count += 1
                    row[i] = None
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))
    
    
def check_duplicates(addpts):
    # Flag duplicates addresses in the feature class (address + citycode)
    
    # Add 'Duplicate' field, if necessary
    fields = arcpy.ListFields(addpts)
    field_names = [field.name for field in fields]
    
    if 'Duplicate' not in field_names:
        arcpy.management.AddField(addpts, "Duplicate", "TEXT", "", "", 10)
    
    # Create counter variables    
    count = 0
    dup_count = 0
    unique_count = 0
    # # Need to make a layer from possible address points feature class here
    # arcpy.management.MakeFeatureLayer(addpts, "working_lyr")

    # Create list of features in the current address points feature class
    current_dict = {}
    duplicate_dict = {}
    fields = ['FullAdd', 'CityCode', 'Duplicate', 'ZipCode']
    with arcpy.da.UpdateCursor(addpts, fields) as cursor:
        print(f"Checking for duplicates in {addpts} ...")
        for row in cursor:
            if row[1] is None:
                citycd = row[3] # ZipCode
            else:
                citycd = row[1] # CityCode
            count += 1
            full_addr = ' '.join([row[0], citycd])
            if count % 10000 == 0:
                print(full_addr)
            if full_addr in current_dict:
                row[2] = 'yes'
                duplicate_dict.setdefault(full_addr)
                dup_count += 1
            else:
                current_dict.setdefault(full_addr)
                row[2] = 'no'
                unique_count += 1
            cursor.updateRow(row)
            
    print(f"Total current address points: {count}")
    print(f"Unique address count: {len(current_dict)}")
    print(f"Duplicate addresses: {len(duplicate_dict)}")
    print(f"Unique address count: {unique_count}")
    print(f"Duplicate address point count: {dup_count}")



# Update/uncomment next line to apply nomenclature to existing feature class
working_addpts = os.path.join(staging_db, "BE_UB_addpts_build_20230305")

export_from_sgid()
project_to_wgs84()
load_into_schema()
remove_special_chars(working_addpts)
calc_fields(working_addpts)
assign_city_code(working_addpts, poly_dict)
strip_fields(working_addpts)
blanks_to_nulls(working_addpts)
check_duplicates(working_addpts)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
