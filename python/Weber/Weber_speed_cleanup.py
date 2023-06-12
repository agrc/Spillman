# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 11:33:14 2019

@author: eneemann

# Weber speed limit compare clean up
"""

#import arcpy
from arcpy import env
import os
import time
import pandas as pd
import numpy as np

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")
data_dir = r'C:\Users\eneemann\Desktop\Neemann\Spillman\Random Work\Weber Area Speed Limits'
csv_path = os.path.join(data_dir, "Speed_Limits_20191227_Compare_final.csv")
df = pd.read_csv(csv_path)
new_df = df[df['Message'].str.contains('SPEED')]
print(new_df.head().to_string())
print(new_df.shape)

out_file = os.path.join(data_dir, 'Speed_Limits_20191227_Compare_clean.csv')
new_df.to_csv(out_file)








print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))