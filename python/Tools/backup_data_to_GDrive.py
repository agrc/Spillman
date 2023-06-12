# -*- coding: utf-8 -*-
"""
Created on Thu Jun 24 16:32:14 2021
Script to backup 911 data to G Drive
@author: eneemann
"""

import os
import time
import shutil
from os.path import basename

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

today = time.strftime("%Y%m%d")

project = 'davis'

# Create dictionary to hold project info with utm, wgs84 geodatbases and G Drive destination folder
spillman_dict = {"beaver": {"utm": r"C:\E911\Beaver Co\Beaver_Spillman_UTM.gdb",
                            "wgs84": r"C:\E911\Beaver Co\Beaver_Spillman_WGS84.gdb",
                            "destination": "Beaver Co"},
            "boxelder": {"utm": r"C:\E911\Box Elder CO\BoxElder_Spillman_UTM.gdb",
                         "wgs84": r"C:\E911\Box Elder CO\BoxElder_Spillman_WGS84.gdb",
                         "destination": "Box Elder CO"},
            "millard": {"utm": r"C:\E911\MillardCo\MillardCo_UTM.gdb",
                        "wgs84": r"C:\E911\MillardCo\MIllard_Co_WGS84.gdb",
                        "destination": "MillardCo"},
            "richfield": {"utm": r"C:\E911\RichfieldComCtr\richfield_comctr_UTM.gdb",
                          "wgs84": r"C:\E911\RichfieldComCtr\richfield_comctr_WGS84.gdb",
                          "destination": "RichfieldComCtr"},
            "stgeorge": {"utm": r"C:\E911\StGeorgeDispatch\StGeorgeDispatch_UTM_good.gdb",
                         "wgs84": r"C:\E911\StGeorgeDispatch\StGeorgeDispatch_WGS84.gdb",
                         "destination": "StGeorgeDispatch"},
            "toc": {"utm": r"C:\E911\TOC\TOC_Data_UTM.gdb",
                    "wgs84": r"C:\E911\TOC\TOC_Spillman_WGS_84.gdb",
                    "destination": "TOC"},
            "uintahbasin": {"utm": r"C:\E911\UintahBasin\UintahBasin_UTM.gdb",
                            "wgs84": r"C:\E911\UintahBasin\UintahBasin_WGS84.gdb",
                            "destination": "UintahBasin"},
            #: Weber has no UTM, will use that key for QuickestRoute
            "weber": {"utm": r"C:\E911\WeberArea\Staging103\QuickestRoute.gdb",
                      "wgs84": r"C:\E911\WeberArea\Staging103\WeberSGB.gdb",
                      "destination": "WeberArea"},
            #: Davis has no UTM, will use that key for QuickestRoute
            "davis": {"utm": r"C:\E911\Layton\QuickestRoute.gdb",
                      "wgs84": r"C:\E911\Layton\DavisGeoValidation.gdb",
                      "destination": "DavisLayton"}
            }
                      
                      

# Build destination directory information from dictionary
backup_dir = r'M:\Shared drives\AGRC Projects\911\SpillmanBackup'
sub_dir = spillman_dict[f'{project}']['destination']
target_dir = os.path.join(backup_dir, sub_dir)

# Created zipped file in C:\Temp and then move it
temp = r'C:\Temp'
UTM = spillman_dict[f'{project}']['utm']
WGS84 = spillman_dict[f'{project}']['wgs84']

today_dir = os.path.join(temp, f'{project}_asof_{today}')
if not os.path.isdir(today_dir):
    os.mkdir(today_dir)

print(f'Zipping {UTM} ...')
zipped_utm = os.path.join(today_dir, basename(UTM))
shutil.make_archive(zipped_utm, 'zip', UTM)

print(f'Zipping {WGS84} ...')
zipped_wgs84 = os.path.join(today_dir, basename(WGS84))
shutil.make_archive(zipped_wgs84, 'zip', WGS84)
        
print(f'Moving {today_dir} to: \n\t {target_dir} ...')
shutil.move(today_dir, target_dir)
        

print('Script shutting down ...')

# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print('The script end time is {}'.format(readable_end))
print('Time elapsed: {:.2f}s'.format(time.time() - start_time))