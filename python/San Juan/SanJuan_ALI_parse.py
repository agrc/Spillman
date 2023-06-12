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


# # Turn street types into a single list
# val = [item for item in st_types.values()]
# vals = [x for n in val for x in n]

today = time.strftime("%Y%m%d")

work_dir = r'C:\E911\1 - Utah ALI Data'
city_file = os.path.join(work_dir, 'cities.txt')
quads_file = os.path.join(work_dir, 'addquads.txt')
places_file = os.path.join(work_dir, 'all_places.txt')
ali_better = r'C:\E911\1 - Utah ALI Data\ali_better.txt'
ali_log = r'C:\E911\1 - Utah ALI Data\ali_log.txt'
ali_file = r'C:\E911\1 - Utah ALI Data\archive\UT_512_edited.txt'
ali_out = r'C:\E911\1 - Utah ALI Data\ali_out.csv'
ali_errors = r'C:\E911\1 - Utah ALI Data\ali_errors.csv'

# ali_file = r'C:\E911\1 - Utah ALI Data\archive\sample.txt'
# ali_out = r'C:\E911\1 - Utah ALI Data\ali_out_test.csv'

# col_names = ['FUNCTION CODE', 'TELEPHONE NUMBER', 'HOUSE #', 'PRE DIR', 'STREET NAME', 'STREET SUFFIX', 'BLANK_1',
#             'COUNTY', 'STATE', 'COMMUNITY', 'CLASS OF SERVICE', 'TYPE OF SERVICE', 'BLANK_2', 'PILOT TELEPHONE NUMBER',
#             'EXTRACT DATE',	'NENA ID', 'BLANK_3']

col_names = ['FUNCTION CODE', 'TELEPHONE NUMBER', 'ADDRESS',
            'CITY', 'STATE', 'COMMUNITY']


# Read in city names
# Read raw ALI data and write out to CSV
no_city = 0
all_good = 0
no_ut = 0
wireless = 0
multi = 0
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
all_cities = [' ' + x for x in all_cities]

all_places = []
with open(places_file, "r+") as placefile:
    allplaces = placefile.readlines()
    for item in allplaces:
        all_places.append(item.upper().strip())

# Pad with leading space and remove duplicates
all_places = list(set(all_places))
all_places = [' ' + x + ' ' for x in all_places]


# Read raw ALI data and write out to CSV
with open(ali_file, "r+") as raw_file:
    with open(ali_out, "w", newline='') as out_file:
        with open(ali_errors, "w", newline='') as errors:
            with open(ali_log, "w", newline='') as log_file:
                good = csv.writer(out_file)
                bad = csv.writer(errors)
                good.writerow(col_names)
                bad.writerow(col_names)
                lines = raw_file.readlines()
                for line in tqdm(lines):
                    term = None
                    ut_found = False
                    city_found = False
                    full_string = ' '.join(line.split())

                    full_list = full_string.split()
                    # print(full_list)
                    if 'WIRELESS CALL' in full_string or ' CALLER' in full_string or ' CALLBK#' in full_string or ' VOIP 9' in full_string:
                        # print(f'Wireless call:   {full_string}')
                        log_file.write(f'Wireless call:   {full_string}\n')
                        wireless += 1
                        continue
                    if ' UT' in full_string:
                        before_ut = full_string.rsplit(' UT', 1)[0]
                        after_ut = full_string.rsplit(' UT', 1)[1]
                        good_ut = True
                    else:
                        print(f'UT is not found in    {full_string}')
                        log_file.write(f'UT is not found in    {full_string}\n')
                        no_ut += 1
                        continue
                    final = []
                    final.append(full_list[0][:1])          # Get function code
                    final.append(full_list[0][1:11])        # Get telephone number
                    addnum = full_list[0][11:]              # Get house number
                    
                    # # Get full address as a single field use street types to split
                    # before_parts = before_ut.split()
                    # possible_add = before_parts[1:]
                    # possible_str = ' '.join(possible_add)
                    # for i in np.arange(1, len(possible_add)):
                    #     st_found = False
                    #     if possible_add[i] in vals:
                    #         add_splitter = ' ' + possible_add[i] + ' '
                    #         addr = possible_str.split(add_splitter, 1)[0] + add_splitter
                    #         addr = addr.strip()
                    #         st_found = True
                    #         break
                    # if not st_found:
                    #     print(f'Street type not found in {possible_add}')
                    # final_addr = ' '.join([addnum, addr])
                    # final.append(final_addr)
                    
                    # Get full address as a single field use city name to split
                    before_parts = before_ut.split()
                    possible_add = before_parts[1:]
                    possible_str = ' '.join(possible_add)
                    
                    # Clean up possible_str and add whitespace to the end
                    if ' -' in possible_str:
                        possible_str = possible_str.split(' -', 1)[0]
                    elif '- ' in possible_str:
                        possible_str = possible_str.split('- ', 1)[0]
                    elif '.' in possible_str:
                        possible_str = possible_str.replace('.', '')
                        
                    possible_str += ' '
                    
                    if '15040 S MOUNTAINSIDE' in possible_str:
                        print(possible_str)
                        
                    # if 'HILL AFB' in possible_str:
                    #     print(possible_str)
                    
                    add_splitter = None
                    splitters = []
                    for i in np.arange(len(all_places)):          
                        if all_places[i] in possible_str:
                            splitters.append(all_places[i])
                            city_found = True
                            # break
                        # else:
                        #     addr = possible_str
                    
                    highest = 0
                    high_index = 0
                    if len(splitters) > 1:
                        multi += 1
                        # print(possible_str)
                        # print(f'Multiple splitters found:   {splitters}')
                        for j in np.arange(len(splitters)):
                            term = splitters[j]
                            # result = re.search(fr"\b({term})\b | \b({term})[]", possible_str)
                            # result = re.search((r"\b" + re.escape(term) + r"\b", possible_str))
                            # beg = result.start()
                            beg = possible_str.find(term)
                            # print(f'Item "{splitters[j]}" starts at: {beg}')
                            if beg > highest:
                                highest = beg
                                high_index = j
                            
                            del beg
                        
                        # print(f'The highest value is:  {highest}, at splitters index {high_index}, will use "{splitters[high_index]}"')
                        
                    # if city_found:
                    #     add_splitter = splitters[high_index].strip()
                    #     addr = possible_str.rsplit(add_splitter, 1)[0]
                    #     addr = addr.strip()
                    # else:
                    #     addr = possible_str
                        
                    if not city_found:
                        for i in np.arange(len(all_places)):          
                            if all_places[i] in possible_str:
                                add_splitter = all_places[i].strip()
                                addr = possible_str.rsplit(add_splitter, 1)[0]
                                addr = addr.strip()
                                city_found = True
                                break
                            else:
                                addr = possible_str.strip()
                    else:
                        add_splitter = splitters[high_index].strip()
                        addr = possible_str.rsplit(add_splitter, 1)[0]
                        addr = addr.strip()
                    
                    if not city_found:
                        no_city += 1
                        # print(f'City not found in:   {full_string}')
                        log_file.write(f'City not found in:   {full_string}\n')
                    final_addr = ' '.join([addnum, addr])
                    final.append(final_addr)
                    
                    if ut_found and city_found:
                        all_good += 1
                    
                    # Get 'city'
                    if add_splitter:
                        city = add_splitter
                    else:
                        city = possible_str
                    
                    final.append(city)
                    
                    
                    # final.append(full_list[1])              # Get pre dir
                    # final.append(' '.join([full_list[2], full_list[3], full_list[4]]))         # Get street name
                    # # Get 'county'
                    # final.append(full_list[5])
                    
                    # # Get 'county'
                    # county = possible_str.split(addr)[1].strip()
                    # final.append(county)
                    
                    final.append('UT')              # Get state
                    
                    # # Get community           
                    # after_ut = after_ut.strip()
                    # # print(after_ut)
                    # comm_parts = after_ut.split(' ')
                    # print(f'after_ut is:      {after_ut}')
                    # for i in np.arange(len(comm_parts)):
                    #     # print(comm_parts[1])
                    #     if comm_parts[i].isdigit():
                    #         splitter = comm_parts[i]
                    #         comm = after_ut.split(splitter, 1)[0]
                    #         comm = comm.strip()
                    #         break
                    # final.append(comm)
        
                    
                    # print(final)
                    
                    if city_found:
                        good.writerow(final)
                    else:
                        bad.writerow(final)
                    
                    del add_splitter
                    del before_ut
                    del after_ut
                    del splitters
                    del highest
                    del high_index
                    del term


print(f'Number of lines in ALI file:  {len(lines)}')
print(f'Number of lines with wireless call:  {wireless}')
print(f'Number of lines where UT was not found:  {no_ut}')
print(f'Number of lines where City was not found:  {no_city} \n')
print(f'Number of lines where UT and City were found:  {all_good} \n')
print(f'Number of lines with multiple splitters:  {multi} \n')

# # df = pd.read_csv(ali_file, sep=' ', engine='python', header=None, names=col_names)
# df = pd.read_csv(ali_file, sep=' ', engine='python', header=None, names=col_names, error_bad_lines=False)


# print(df.shape)

# temp = df.head(100)
# temp = temp.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))


# for item in all_cities:
#     if item not in all_places:
#         print(item)