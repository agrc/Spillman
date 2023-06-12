# -*- coding: utf-8 -*-
"""
Created on Wed May 15 07:16:57 2019
@author: eneemann
Script to identify complexes that need a base address point
"""

import arcpy
from arcpy import env
import os
import time
import pandas as pd
import numpy as np
from Levenshtein import StringMatcher as Lv
from matplotlib import pyplot as plt

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

# Place a copy of the address point layer in the working database
working_db = r"C:\E911\WeberArea\Staging103\Weber_Staging.gdb"
env.workspace = working_db
env.overwriteOutput = True
today = time.strftime("%Y%m%d")

working_addpts = "AddressPoints_Spillman_export_20190515"
addpts = os.path.join(working_db, working_addpts)

# Create empty list to store base addresses, new base addpts, and dict to store all addresses
baseAddList = []
new_baseAdds = []
allAddsDict = {}

fields = ['FullAdd', 'UnitType', 'UnitID']
# Build dictionary with full addresses
with arcpy.da.SearchCursor(addpts, fields) as sCursor:
    print("Looping through rows in FC ...")
    for row in sCursor:
        allAddsDict.setdefault(row[0])
            
    sCursor.reset()
    for row in sCursor:
        # Find addresses with unitType and unitID, add them to base address list
        if row[1] is not None and row[2] is not None:
            splitStr = row[1] + " " + row[2]
            baseAdd = row[0].split(splitStr)[0].strip()
            baseAddList.append(baseAdd)
            # Find base addresses not in dictionary of all addresses, add to new base addpts list
            if baseAdd not in allAddsDict:
                new_baseAdds.append(baseAdd)

# Create dataframe of base addresses
baseAdds_df = pd.DataFrame(data = baseAddList)
baseAdds_df.columns = ['BaseAdd']
baseAdds_df.drop_duplicates(subset='BaseAdd', keep='first', inplace=True)

# Create dataframe of base addresses no in dictionary of all addresses
new_baseAdds_df = pd.DataFrame(data = new_baseAdds)
new_baseAdds_df.columns = ['BaseAdd']
new_baseAdds_df.drop_duplicates(subset='BaseAdd', keep='first', inplace=True)

# Create dataframe of all addresses
temp_list = list(allAddsDict.keys())
allAdds_df = pd.DataFrame(data = temp_list)
allAdds_df.columns = ['FullAdd']

path = r'C:\E911\WeberArea\Staging103\temp_base_Addpts.csv'
#path = 'in_memory\\temp_base_Addpts.csv'
new_baseAdds_df.to_csv(path)
    
# Convert CSV output into arcpy table
env.qualifiedFieldNames = False
arcpy_table = "new_BaseAddpts_" + today
if arcpy.Exists(arcpy_table):
    arcpy.Delete_management(arcpy_table)
arcpy.TableToTable_conversion(path, working_db, arcpy_table)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
