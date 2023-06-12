# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 14:02:44 2019
@author: eneemann

Script to build simple street segment from endpoints

21 Aug 2019: Created initial version of code (EMN).
"""

import arcpy
from arcpy import env
import os
import time
import pandas as pd

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

today = time.strftime("%Y%m%d")

staging_db = r"C:\E911\StGeorgeDispatch\StGeorge_Staging.gdb"
env.workspace = staging_db
env.overwriteOutput = True

# Create new segments FC from previous copy, rename, and truncate table
lines = r"temp_street_segments_20201102"    # points to an empty line feature class
segments = os.path.join(staging_db, lines)

# # Add fields to feature class
# arcpy.AddField_management(segments, "STREET", "TEXT", "", "", 50)
# arcpy.AddField_management(segments, "CITYCD", "TEXT", "", "", 3)
# arcpy.AddField_management(segments, "BEG", "TEXT", "", "", 5)
# arcpy.AddField_management(segments, "END", "TEXT", "", "", 5)
# arcpy.AddField_management(segments, "X_START", "TEXT", "", "", 50)
# arcpy.AddField_management(segments, "Y_START", "TEXT", "", "", 50)
# arcpy.AddField_management(segments, "X_END", "TEXT", "", "", 50)
# arcpy.AddField_management(segments, "Y_END", "TEXT", "", "", 50)

# Import file
excel_file = r"C:\E911\StGeorgeDispatch\Street_data_20201102.xlsx"
df = pd.read_excel(excel_file)

# Populate feature class
# Create list of fields for the insertCursor
fields = ['STREET',
          'CITYCD',
          'BEG',
          'END',
          'X_START',
          'Y_START',
          'X_END',
          'Y_END',
          'SHAPE@']

spatial_reference = arcpy.SpatialReference(4326)

for index, row in df.iterrows():
    array = arcpy.Array([arcpy.Point(float(row['X START']), float(row['Y START'])),
                     arcpy.Point(float(row['X END']), float(row['Y END']))])
    shape = arcpy.Polyline(array, spatial_reference) 
    values = [row['STREET'],
          row['CITYCD'],
          row['BEG'],
          row['END'],
          row['X START'],
          row['Y START'],
          row['X END'],
          row['Y END'],
          shape]
    
    # add line to FC
    print('Adding line to feature class...')
    with arcpy.da.InsertCursor(segments, fields) as iCur:
        print('Inserting line...')
        print(values)
        iCur.insertRow(values)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))