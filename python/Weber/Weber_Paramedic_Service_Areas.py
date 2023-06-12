# -*- coding: utf-8 -*-
"""
Created on Thu Aug 20 15:07:21 2020
@author: eneemann
Script to build Paramedic Service Areas for Weber Area Dispatch
"""

import arcpy
from arcpy import env
from arcgis.gis import GIS
from pathlib import Path
import getpass
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

# Set variables, get AGOL username and password
portal_url = arcpy.GetActivePortalURL()
print(portal_url)

user = getpass.getpass(prompt='    Enter arcgis.com username:\n')
pw = getpass.getpass(prompt='    Enter arcgis.com password:\n')
arcpy.SignInToPortal(portal_url, user, pw)

# gis = GIS(portal_url, username='Erik.Neemann@UtahAGRC')
gis = GIS(portal_url, user, pw)
print("Successfully logged in as: " + gis.properties.user.username)
del pw


# Check out Network Analyst license if available. Fail if the Network Analyst license is not available.
if arcpy.CheckExtension("network") == "Available":
    arcpy.CheckOutExtension("network")
else:
    raise arcpy.ExecuteError("Network Analyst Extension license is not available.")

## Prep data for network

# Set up variables and environment settings
weber_staging = r"C:\E911\WeberArea\Staging103"
output_dir = weber_staging
staging_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
network_db = os.path.join(weber_staging,'QuickestRoute.gdb')
network_dataset = os.path.join(network_db, 'QuickestRoute')
# Current "Streets" data
network_streets = os.path.join(network_dataset, 'Streets')
working_db = os.path.join(weber_staging,'Paramedic_Service_Areas_' + today +  '.gdb')
env.workspace = working_db
env.overwriteOutput = True

# Create new geodatabase for the service areas
if arcpy.Exists(working_db):
    arcpy.Delete_management(working_db)
arcpy.CreateFileGDB_management(weber_staging, 'Paramedic_Service_Areas_' + today +  '.gdb')

# Set environment settings
output_dir = weber_staging

# Set local variables
input_gdb = staging_db
network_data_source = os.path.join(network_dataset, "QuickestRoute_ND")
layer_name = "ParamedicServiceAreas"
travel_mode = "Driving Time"
facilities = os.path.join(staging_db, "Paramedic_Weber_Morgan_20200820_WGS84")

# Create a new service area layer. We wish to generate the service area
# polygons as rings, so that we can easily visualize the coverage for any
# given location. We also want overlapping polygons so we can determine the
# number of stations that cover a given location. We will specify these
# options while creating the new service area layer.

print("Creating the analysis layer ...")
result_object = arcpy.na.MakeServiceAreaAnalysisLayer(network_data_source, layer_name, 
                                                      "Default", "FROM_FACILITIES", [90],
                                                      output_type = "POLYGONS",
                                                      polygon_detail = "HIGH",
                                                      geometry_at_overlaps = "SPLIT",
                                                      geometry_at_cutoffs = "DISKS",
                                                      polygon_trim_distance = "100 Meters")


#Get the layer object from the result object. The service layer can now be
#referenced using the layer object.
layer_object = result_object.getOutput(0)

#Get the names of all the sublayers within the service area layer.
sublayer_names = arcpy.na.GetNAClassNames(layer_object)
#Stores the layer names that we will use later
facilities_layer_name = sublayer_names["Facilities"]
poly_name = sublayer_names["SAPolygons"]

# Load the stations as facilities using default field mappings and default search tolerance
print("Adding Station locations ...")
arcpy.na.AddLocations(layer_object, facilities_layer_name, facilities, "", "5000 Meters")


# Solve the service area layer
print("Solving the Service Areas ...")
arcpy.na.Solve(layer_object)

arcpy.CheckInExtension("network")



# #Save the solved service area layer as a layer file on disk
# layer_object.saveACopy(output_layer_file)
print("Exporting Service Areas to Feature Class ...")
arcpy.conversion.FeatureClassToFeatureClass(r"ParamedicServiceAreas\Polygons", working_db, f"ParamedicServiceArea_Polygons_{today}")
arcpy.conversion.FeatureClassToFeatureClass(r"ParamedicServiceAreas\Polygons", staging_db, "ParamedicServiceArea_Polygons_LIVE")
live_sa = os.path.join(staging_db, "ParamedicServiceArea_Polygons_LIVE")


# Overwrite web layer with new service area data
def define_service(project_path, map_name, layer_name, fc_path_str, item_name, temp_dir_path):

    #: Reference a Pro project so that we can get a map and share it
    print('Getting Pro project and map info ...')
    proj = arcpy.mp.ArcGISProject(str(project_path))

    #: Select the right map from the project
    for m in proj.listMaps():
        if m.name == map_name:
            agol_map = m
    del m
    
    print('Getting layer to update ...')
    layer_list = agol_map.listLayers()
    for l in layer_list:
        if l.name == layer_name:
            layer = l
            
    print(layer)

    #: Save the project so that the changes stick.
    proj.save()

    #: Create paths for the service definition draft and service definition files
    draft_path = Path(temp_dir_path, f'{item_name}.sddraft')
    service_definition_path = Path(temp_dir_path, f'{item_name}.sd')

    #: Delete draft and definition if existing
    for file_path in (draft_path, service_definition_path):
        if file_path.exists():  #: This check can be replaced in 3.8 with missing_ok=True
            print(f'Delete existing {file_path}...')
            file_path.unlink()

    #: Create the service definition draft and stage it to create a service definition file
    print('Draft and stage service definition ...')
    sharing_draft = agol_map.getWebLayerSharingDraft('HOSTING_SERVER', 'FEATURE', item_name, [layer])
    sharing_draft.exportToSDDraft(str(draft_path))
    arcpy.server.StageService(str(draft_path), str(service_definition_path))

    #: Return the path to the service definition file
    return service_definition_path


def overwrite(org, service_definition_path, item_id, sd_id):
    # item = org.content.get(item_id)
    sd_item = org.content.get(sd_id)
    print('Updating service definition ...')
    sd_item.update(data=str(service_definition_path))
    print('Publishing service definition ...')
    sd_item.publish(overwrite=True)
    
    
#: id of the hosted feature service's AGOL item
item_id = '1d010982b7a24fd989dc210c47060d3c'
#: id of the service definition AGOL item for the feature service.
sd_id = 'ba44e22841634e2c92c1e3afb54259d3'

fc_path_str = r'C:\E911\WeberArea\Staging103\Weber_Staging.gdb\ParamedicServiceArea_Polygons_LIVE'
item_name = 'Paramedic Service Areas'
layer_name = 'ParamedicServiceArea_Polygons_LIVE'
map_name = 'Weber_Paramedic_Service_Areas'
temp_dir_path = Path(r'C:\E911\WeberArea\Staging103\0 Paramedic Service Areas Folder')  #: Place to store the .sd and .sddraft files
project_path = Path(r'C:\E911\WeberArea\Staging103\WeberArea.aprx')


# Push changes to AGOL
print(f'Staging {fc_path_str} ...')
service_definition_path = define_service(project_path, map_name, layer_name, fc_path_str, item_name, temp_dir_path)
overwrite(gis, service_definition_path, item_id, sd_id)



print("Script completed successfully")


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))