# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 08:24:17 2020
@author: eneemann
Exploring the state's ALI data for San Juan county

30 Sep 2020: first version of code (EMN)
"""

import arcpy
from arcpy import env
import os
import time
import pandas as pd
import numpy as np
from Levenshtein import StringMatcher as Lv
from matplotlib import pyplot as plt
import re
import timeit
import csv
from tqdm import tqdm

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

tqdm.pandas()
today = time.strftime("%Y%m%d")

work_dir = r'C:\E911\1 - Utah ALI Data'
city_file = os.path.join(work_dir, 'cities.txt')
quads_file = os.path.join(work_dir, 'addquads.txt')
places_file = os.path.join(work_dir, 'all_places.txt')
holdout_file = os.path.join(work_dir, 'Geocode Results', 'ALI_holdouts_bad_cities.csv')
not_found = os.path.join(work_dir, 'not_found.txt')
uni_file = os.path.join(work_dir, 'ali_unique_addresses.csv')
prob_file = os.path.join(work_dir, 'likey_city-direction_problems.txt')
geocoded_file = os.path.join(work_dir, 'Geocode Results', 'geocoding_results_20201021213257.csv')


    
cities = []
with open(city_file, "r+") as file:
    city_lines = file.readlines()
    for line in city_lines:
        cities.append(line.upper())

cities = [x.replace(' MT', '').strip() for x in cities]

quads = []
with open(quads_file, "r+") as file2:
    all_quads = file2.readlines()
    for item in all_quads:
        quads.append(item.upper().strip())
    
unique_quads = set(quads)

all_cities = list(set(cities + list(unique_quads)))

all_places = []
with open(places_file, "r+") as placefile:
    allplaces = placefile.readlines()
    for item in allplaces:
        all_places.append(item.upper().strip())
        
        
probs = []
with open(prob_file, "r+") as probfile:
    allprobs = probfile.readlines()
    for item in allprobs:
        probs.append(item.upper().strip())
        

# Pad with leading space and remove duplicates
all_places = list(set(all_places))
# all_places = [' ' + x for x in all_places]


geo = ali = pd.read_csv(geocoded_file)
temp = geo.head(10)

fails = geo[geo.score == 0]
# fails.to_csv(os.path.join(work_dir, 'Geocode Results', 'geocoding_fails.csv'))


uni_fails = fails.drop_duplicates(subset=['input_zone'], keep='first')

zone_fails = list(uni_fails['input_zone'])

bad_zones = []
for item in zone_fails:
    if item.strip() not in all_places:
        bad_zones.append(item.strip())
        
        
holdouts = pd.read_csv(holdout_file)   


unfound = []
with open(not_found, "r+") as notfile:
    allnot = notfile.readlines()
    for item in allnot:
        unfound.append(item.upper().strip())

unfound_final = []
for item in unfound:
    if item.strip() not in all_places:
        unfound_final.append(item.strip())

bad_places = r'C:\E911\1 - Utah ALI Data\Geocode Results\bad_places.txt'
with open(bad_places, "w", newline='') as out_file:
    for row in tqdm(unfound_final):
        out_file.write(f'{row}\n')


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))