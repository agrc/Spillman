# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 10:44:29 2023

@author: eneemann

EMN: Initial script to replace addpts in Davis with the counties data
- archives existing address points in Davis_staging.gdb
- projects Davis county submitted points to WGS84
- removes current pts from Spillman data and adds new ones
    - NOTE: existing points in Layton city are untouched
- cleans up fields, calculates fields, fixes street types
- checks for duplicates and flags them in the 'Annotation' field

"""

import arcpy
import os
import time
import json

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Set up variables
geo_db = r"C:\E911\Layton\DavisGeoValidation.gdb"
county_db = r"\\itwfpcap2\AGRC\agrc\data\county_obtained\Davis\DavisCounty_20230520.gdb"
stage_db = r"C:\E911\Layton\Davis_staging.gdb"

geo_addpts = os.path.join(geo_db, "DavisAddressPoints")
county_addpts = os.path.join(county_db, "DavisAddress")
working_addpts = os.path.join(stage_db, f"Addpt_Davis_update_WGS84_{today}")
archived_addpts = os.path.join(stage_db, f"DavisAddressPoints_{today}")

city_codes = os.path.join(geo_db, "DavisDispatchServiceArea")
davis_county = os.path.join(stage_db, "aaa_Davis_County_WGS84")

# Create dictionary for polygon assignements
poly_dict = {
        'CityCode': {'poly_path': city_codes, 'poly_field': "CITYCODE"},
        }

# Load invalid street types dictionary - NOTE: the valid type is not list in the values, only the key
json_path = os.path.join(r'C:\Users\eneemann\Desktop\Python Code\Spillman\Layton', 'invalid_street_types.json')
with open(json_path, 'r') as file:
    INVALID_STREET_TYPES = json.loads(file.read())
   
    
###############
#  Functions  #
###############

def archive_current_pts():
    arcpy.management.CopyFeatures(geo_addpts, archived_addpts)


def project_to_wgs84():
    # Select points in Davis County
    davis_selection = arcpy.management.SelectLayerByLocation(county_addpts, "INTERSECT", davis_county)
    # Project to WGS84
    print(f"Projecting {arcpy.management.GetCount(davis_selection)[0]} DavisCo addpts to WGS84...")
    sr = arcpy.SpatialReference(4326)
    arcpy.management.Project(county_addpts, working_addpts, sr)


def remove_current_davis_addpts():
    # Select and delete exisiting address points
    print("Selecting non-Layton DavisCo addpts ...")
    selection = arcpy.management.SelectLayerByLocation(geo_addpts, "INTERSECT", davis_county)
    print(f"Selected  {arcpy.management.GetCount(selection)[0]} addpts in DavisCo")
    
    # Remove points in Layton, Hill AFB, or outside Davis County from the selection (Keep them in data)
    print("Removing Layton addpts from selection ...")
    where = """CityCode IN ('LAY', 'HIL', 'ODC')"""
    non_layton_selection = arcpy.management.SelectLayerByAttribute(selection, "REMOVE_FROM_SELECTION", where)
    print(f"Selected  {arcpy.management.GetCount(non_layton_selection)[0]} addpts after removing Layton pts")
    
    # Delete those selected addpts from the geovalidation addpts
    print("Deleting non-Layton DavisCo addpts ...")
    arcpy.management.DeleteFeatures(non_layton_selection)
    
    # Clear selection
    arcpy.management.SelectLayerByAttribute(geo_addpts, "CLEAR_SELECTION")

def load_new_addpts():
    # Create field map for DavisCo addpts into Geovalidation addpts
    print('Creating field map ...')
    fms_addpts = arcpy.FieldMappings()
    
    fm_dict_addpts = {'FullAddres': 'Address',
               'MunicipalN': 'CITY',
               'State': 'STATE',
               'Zipcode': 'ZIP',
               'AddressNum': 'HouseNum',
               'RoadPrefix': 'PreDir',
               'RoadName': 'StreetName',
               'RoadNameTy': 'StreetType',
               'RoadPostDi': 'SufDir',
               # 'CityCode' : 'CityCode',
               # None : 'AliasStree',
               # None : 'AliasStr_1',
               # None : 'AliasSufDi',
               # None : 'AliasFullN',
               'UnitType': 'UnitType',
               # None : 'Building',
               'UnitNumber': 'Unit',
               # None : 'CityCode',
               # None : 'JoinID',
               # None : 'LocationTy',
               # None : 'CommonName',
               'AddressPoi': 'Notes',
               # None : 'CommonName2',
               # None : 'CommonName3',
               # None : 'CommonName4',
               'PrimaryAdd': 'Exception',
               # None : 'LandUse',
               # None : 'ParcelID',
               }

    for key in fm_dict_addpts:
        fm_addpts = arcpy.FieldMap()
        fm_addpts.addInputField(working_addpts, key)
        output_addpts = fm_addpts.outputField
        output_addpts.name = fm_dict_addpts[key]
        fm_addpts.outputField = output_addpts
        fms_addpts.addFieldMap(fm_addpts)

    # Get dictionary of existing Layton addresses    
    layton_list = [' '.join([row[0], row[1]]) for row in arcpy.da.SearchCursor(geo_addpts, ['Address', 'CityCode'])]
    layton_dict = dict.fromkeys(layton_list, 0)

    # Add fields for city code calculation and duplicate address check
    fc_fields = arcpy.ListFields(working_addpts)
    field_names = [f.name for f in fc_fields]
    if 'CityCode' not in field_names:
        print('Adding CityCode field to Davis WGS84 points ...')
        arcpy.AddField_management(working_addpts, "CityCode", "TEXT", "", "", 3)
    if 'Duplicate_Flag' not in field_names:
        print('Adding Duplicate_Flag field to Davis WGS84 points ...')
        arcpy.AddField_management(working_addpts, "Duplicate_Flag", "TEXT", "", "", 10)
        
    # Assign citycodes from polygons on Davis points
    assign_city_code(working_addpts, poly_dict)  # same dictionary for same fields/paths
    
    # Calculate Duplicate_Flag field
    dup_count = 0
    unique_count = 0
    # # Need to make a layer from possible address points feature class here
    # arcpy.management.MakeFeatureLayer(pts, "working_lyr")

    # Create list of features in the current Davis address points feature class
    curr_dict = {}
    fields = ['FullAddres', 'CityCode', 'Duplicate_Flag']
    with arcpy.da.UpdateCursor(working_addpts, fields) as cursor:
        print(f"Checking for duplicates in {working_addpts} ...")
        for row in cursor:
            full_addr = ' '.join([row[0].split(',', 1)[0].strip(), row[1]])
            # if count % 10000 == 0:
            #     print(full_addr)
            if full_addr in curr_dict or full_addr in layton_dict:
                row[2] = 'yes'
                dup_count += 1
            else:
                curr_dict.setdefault(full_addr)
                row[2] = 'no'
                unique_count += 1
            cursor.updateRow(row)
            
    print(f"Davis unique addresses points: {unique_count}")
    print(f"Davis duplicate addresses points: {dup_count}")
    
    # Select points that aren't within 10m of existing points
    arcpy.management.MakeFeatureLayer(working_addpts, "addpt_lyr")
    arcpy.management.SelectLayerByLocation("addpt_lyr", "INTERSECT", geo_addpts, "10 Meters", "NEW_SELECTION", "INVERT")
    print(f"Initial Davis addpts selection to add:   {arcpy.management.GetCount('addpt_lyr')[0]}")
    
    # Remove duplicates from the selection
    print("Removing duplicates from selection ...")
    where_duplicate = "Duplicate_Flag = 'yes'"
    final_selection = arcpy.management.SelectLayerByAttribute("addpt_lyr", "REMOVE_FROM_SELECTION", where_duplicate)
    print(f"Final Davis addpts selection to add:   {arcpy.management.GetCount(final_selection)[0]}")

    # Append DavisCo WGS84 addpts data into Geovalidation schema
    print(f"Appending {arcpy.management.GetCount(final_selection)[0]} DavisCo WGS84 addpts into Geovalidation schema ...")
    arcpy.management.Append(final_selection, geo_addpts, "NO_TEST", field_mapping=fms_addpts)


def calc_unit_from_fulladd(pts):
    update_count = 0
    # Use update cursor to calculate unit type from address field
    fields = ['Address', 'UnitType', 'Unit']
    where_clause = "Address IS NOT NULL AND UnitType IS NULL AND Unit IS NULL"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            if  ' Unit' in row[0]:
                unittype = 'Unit'
                unit_id = row[0].rsplit('Unit', 1)[1]
                row[1] = unittype
                row[2] = unit_id
                update_count += 1
            cursor.updateRow(row)
    print("Total count of unit calculations is: {}".format(update_count))
    
    
def clean_full_address(pts):
    update_count = 0  
    fields = ['Address']

    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Cleaning Address field ...")
        for row in cursor:
            if ',' in row[0]:
                row[0] = row[0].split(',', 1)[0].strip()
                update_count += 1 
                cursor.updateRow(row)
    print(f"Total count of cleaned addresses is: {update_count}")
    
    
def fix_street_types(pts):
    type_count = 0
    total_count = 0
    bad_types_found = []
    #             0           1             2              3            4             5              6              7
    fields = ['Address', 'StreetType', 'AliasStr_1', 'AliasFullN', 'LocationTy', 'CommonName', 'CommonName2', 'CommonName3']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Fixing street types ...")
        for row in cursor:
            if row[1] is None:
                continue
            else:
                for key, values in INVALID_STREET_TYPES.items():
                    if row[1].title().strip() in values:
                        bad_types_found.append(row[1])
                        # row[1] = key
                        type_count += 1
                        for v in values:
                            if v == row[1]:
                                row[1] = key
                                # replace only once from the right if invalid type found in other fields
                                if row[0] is not None and v in row[0]:
                                    row[0] = key.join(row[0].rsplit(v, 1))
                                    total_count += 1
                                if row[2] is not None and v in row[2]:
                                    row[2] = key.join(row[2].rsplit(v, 1))
                                    total_count += 1
                                if row[3] is not None and v in row[3]:
                                    row[3] = key.join(row[3].rsplit(v, 1))
                                    total_count += 1
                                if row[4] is not None and v in row[4]:
                                    row[4] = key.join(row[4].rsplit(v, 1))
                                    total_count += 1
                                if row[5] is not None and v in row[5]:
                                    row[5] = key.join(row[5].rsplit(v, 1))
                                    total_count += 1
                                if row[6] is not None and v in row[6]:
                                    row[6] = key.join(row[6].rsplit(v, 1))
                                    total_count += 1
                                if row[7] is not None and v in row[7]:
                                    row[7] = key.join(row[7].rsplit(v, 1))
                                    total_count += 1

            cursor.updateRow(row)
    print(f"Total count of fixed street types is: {type_count}")
    print(f"Total count of street type text replacements: {total_count}")
    print("Bad StreetTypes found:")
    # for bad in bad_types_found:
    #     print(f"    {bad}")
    
def calc_joinid(pts):
    fields = ['JoinID', 'OID@']

    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print("Calculating JoinIDs ...")
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)
            
            
def assign_city_code(pts, polygonDict):
    #: Assign polygon attributes to poins using near tables to get the nearsest polygon info
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
            
    

def blanks_to_nulls(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field
    flist = ['OBJECTID', 'Address', 'HouseNum', 'PreDir', 'StreetName', 'StreetType', 'SufDir',
             'UnitType', 'Building', 'Unit', 'CITY', 'STATE', 'ZIP', 'CityCode', 'JoinID', 'LocationTy', 'CommonName',
             'Notes', 'Exception', 'UnitTypeLong', 'LandUse', 'ParcelID', 'Annotation', 'AliasStree', 'AliasStr_1'
             'AliasSufDi', 'AliasFullN']
    fields = arcpy.ListFields(pts)

    field_list = []
    print(f'Initial fields: {field_list}')
    for field in fields:
        print(field.name)
        if field.name in flist:
            field_list.append(field.name)
            
    print(f'Updated fields: {field_list}')
            
#    field_list = []
#    for field in fields:
#        print(field.type)
#        if field.type == 'String':
#            field_list.append(field.name)
#            
#    print(field_list)

    with arcpy.da.UpdateCursor(pts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if row[i] in ('', ' '):
#                    print("Updating field: {0} on ObjectID: {1}".format(field_list[i].name, row[0]))
                    update_count += 1
                    row[i] = None
                elif isinstance(row[i], str):
                    row[i] = row[i].strip()
            cursor.updateRow(row)
    print("Total count of blanks converted to NULLs is: {}".format(update_count))


def strip_fields(pts):
    update_count = 0
    # Use update cursor to convert blanks to null (None) for each field

    fields = arcpy.ListFields(pts)

    field_list = []
    for field in fields:
        print(field.type)
        if field.type == 'String':
            field_list.append(field.name)
            
    print(field_list)
    
    skip_title = ['STATE', 'CityCode']

    with arcpy.da.UpdateCursor(pts, field_list) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            for i in range(len(field_list)):
                if isinstance(row[i], str):
                    if field_list[i] in skip_title:
                        row[i] = row[i].strip().upper()
                    else:
                        row[i] = row[i].replace("'", "").strip().title()
                    update_count += 1
            cursor.updateRow(row)
    print("Total count of stripped fields is: {}".format(update_count))


def check_duplicates(pts):
    count = 0
    dup_count = 0
    unique_count = 0
    # # Need to make a layer from possible address points feature class here
    # arcpy.management.MakeFeatureLayer(pts, "working_lyr")

    # Create list of features in the current Davis address points feature class
    current_dict = {}
    duplicate_dict = {}
    fields = ['Address', 'CityCode', 'Annotation']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print(f"Checking for duplicates in {pts} ...")
        for row in cursor:
            count += 1
            full_addr = ' '.join([row[0], row[1]])
            if count % 10000 == 0:
                print(full_addr)
            if full_addr in current_dict:
                row[2] = 'address duplicate'
                duplicate_dict.setdefault(full_addr)
                dup_count += 1
            else:
                current_dict.setdefault(full_addr)
                row[2] = 'not duplicate'
                unique_count += 1
            cursor.updateRow(row)
            
    print(f"Total current address points: {count}")
    print(f"Unique address count: {len(current_dict)}")
    print(f"Duplicate addresses: {len(duplicate_dict)}")
    print(f"Unique address count: {unique_count}")
    print(f"Duplicate address point count: {dup_count}")

    # where_final = "Annotation <> 'address duplicate'"
    # final_selection = arcpy.SelectLayerByAttribute_management("working_lyr", "NEW_SELECTION", where_final)
    # print("Number of features in new_selection after checking duplicates is: {}"
    #       .format(arcpy.GetCount_management(final_selection)))


def check_davis_duplicates(pts):
    count = 0
    dup_count = 0
    unique_count = 0

    # Create list of features in the current Davis address points feature class
    current_dict = {}
    duplicate_dict = {}
    fields = ['FullAddres', 'Duplicate_Flag']
    with arcpy.da.UpdateCursor(pts, fields) as cursor:
        print(f"Checking for duplicates in {pts} ...")
        for row in cursor:
            count += 1
            full_addr = row[0]
            if count % 10000 == 0:
                print(full_addr)
            if full_addr in current_dict:
                row[1] = 'duplicate'
                duplicate_dict.setdefault(full_addr)
                dup_count += 1
            else:
                current_dict.setdefault(full_addr)
                row[1] = 'ok'
                unique_count += 1
            cursor.updateRow(row)
            
    print(f"Total current address points: {count}")
    print(f"Unique address count: {len(current_dict)}")
    print(f"Duplicate addresses: {len(duplicate_dict)}")
    print(f"Unique address count: {unique_count}")
    print(f"Duplicate address point count: {dup_count}")


##########################
#  Call Functions Below  #
##########################
archive_current_pts()
project_to_wgs84()
remove_current_davis_addpts()
load_new_addpts()
clean_full_address(geo_addpts)
fix_street_types(geo_addpts)
calc_joinid(geo_addpts)
assign_city_code(geo_addpts, poly_dict)
blanks_to_nulls(geo_addpts)
strip_fields(geo_addpts)
check_duplicates(geo_addpts)

# Use below to call on a selection
# #calc_unit_from_fulladd("addpts_lyr")
# blanks_to_nulls("addpts_lyr")
# strip_fields("addpts_lyr")


# Check duplicates on Davis address points
# davis_addr = r'C:\E911\Layton\Davis_staging.gdb\DavisAddress_20230124'
# check_davis_duplicates(davis_addr)



print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
