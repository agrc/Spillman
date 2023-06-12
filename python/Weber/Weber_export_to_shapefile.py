# -*- coding: utf-8 -*-
"""
Created on Mon Aug 23 15:30:56 2021
@author: eneemann

23 Aug 2021 - extremely simple script to export shapefiles to a folder
    - This was created because the ArcMap/ArcCatalog tools kept freezing on me
"""

import arcpy
from arcpy import env
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

# staging_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
live_db = r"C:\E911\WeberArea\Staging103\WeberSGB.gdb"
env.workspace = live_db
today = time.strftime("%Y%m%d")
# output_folder = r'C:\E911\WeberArea\Staging103\00 Weber_Updates_20230109'
output_folder = rf'C:\E911\WeberArea\Staging103\00 Weber_Updates_{today}'

# input_features = ['CommonNames',
#                   'AddressPoints',
#                   'Streets_Map',
#                   'LawZones',
#                   'LawAreas',
#                   'CityCodes']

input_features = ['CommonNames']

#input_features = ['CommonNames',
#                  'AddressPoints',
#                  'Streets_Map',
#                  'LawAreas',
#                  'LawZones']

# input_features = ['CommonNames',
#                   'POI',
#                   'Streets_Map']

# input_features = ['CommonNames',
#                   'CityCodes',
#                   'LawZones',
#                   'LawAreas']

# input_features = ['CommonNames',
#                   'AddressPoints',
#                   'LawAreas']

# input_features = ['CommonNames',
#                   'AddressPoints']

arcpy.conversion.FeatureClassToShapefile(input_features, output_folder)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
