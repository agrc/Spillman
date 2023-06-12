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
ali_csv = os.path.join(work_dir, 'ali_out.csv')
city_file = os.path.join(work_dir, 'cities.txt')
quads_file = os.path.join(work_dir, 'addquads.txt')
places_file = os.path.join(work_dir, 'all_places.txt')
bad_file = os.path.join(work_dir, 'bad_cities.txt')
not_found = os.path.join(work_dir, 'not_found.txt')
uni_file = os.path.join(work_dir, 'ali_unique_addresses.csv')
prob_file = os.path.join(work_dir, 'likey_city-direction_problems.txt')

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
all_places = [' ' + x for x in all_places]


col_names = ['FUNCTION CODE', 'TELEPHONE NUMBER', 'ADDRESS',
            'CITY', 'STATE', 'COMMUNITY']

# # ali = pd.read_csv(ali_file, sep=' ', engine='python', header=None, names=col_names)
ali = pd.read_csv(ali_csv)


print(ali.shape)

unique = ali.drop_duplicates(subset=['ADDRESS', 'CITY'], keep='first')
print(unique.shape)
unique.to_csv(os.path.join(work_dir, 'ali_unique_addresses.csv'))


sj_cities = ['ANETH', 'BLANDING', 'BLUFF', 'DEER CANYON', 'EASTLAND', 'FRY CANYON', 'HALLS CROSSING',
             'LA SAL', 'LA SAL JCT', 'LA SAL JUNCTION', 'MEXICAN HAT', 'MONTEZUMA CREEK', 'MONTICELLO', 'OLJATO',
             'SUMMIT POINT', 'UCOLO', 'WHITE MESA']

sj = unique[unique.CITY.isin(sj_cities)]
sj.to_csv(os.path.join(work_dir, 'ali_SanJuan_addresses.csv'))



temp = unique.head(100)
# temp = temp.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
unique_cities = ali.drop_duplicates('CITY', keep='first')
city_list = list(unique_cities.CITY)


with open(bad_file, "w", newline='') as bad:
    for item in city_list:
        if item in all_cities:
            continue
        else:
            # print(f'Not in all_cities list:    {item}')
            bad.write(f'Not in all_cities list:    {item}\n')
            

uni = pd.read_csv(os.path.join(work_dir, 'ali_unique_addresses.csv'))

dirs = ['NORTH', 'SOUTH', 'EAST', 'WEST']

def count_dirs(row):
    dir_count = 0
    for d in dirs:
        if d in row['ADDRESS']:
            temp_ct = row['ADDRESS'].count(d)
            dir_count += temp_ct
            
    row['DIR_COUNT'] = dir_count
    
    return row
            

uni = uni.progress_apply(count_dirs, axis=1)

uni.to_csv(os.path.join(work_dir, 'unique_address_dirs.csv'))



# NEXT PORTION USED TO FIX DIRECTION ERRORS in unique table with dir_counts
work_df = pd.read_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_3.csv'))

def fix_dirs(row):
    updates = 0
    highest = 0
    high_index = 0
    if row['DIR_COUNT'] == 2:
        addr = row['ADDRESS']
        city = row['CITY']
        
        add_splitter = None
        splitters = []
        for i in np.arange(len(dirs)):          
            if dirs[i] in addr:
                splitters.append(dirs[i])
                dir_found = True     #Flag to process since dir is found in addr
                
        if len(splitters) > 1:
            # print(possible_str)
            # print(f'Multiple splitters found:   {splitters}')
            for j in np.arange(len(splitters)):
                term = splitters[j]
                # result = re.search(fr"\b({term})\b | \b({term})[]", possible_str)
                # result = re.search((r"\b" + re.escape(term) + r"\b", possible_str))
                # beg = result.start()
                beg = addr.find(term)
                # print(f'Item "{splitters[j]}" starts at: {beg}')
                if beg > highest:
                    highest = beg
                    high_index = j
                
                del beg
        
        # Flag not to process if direction already found in city
        fix_dir = True
        for d in dirs:
            if d in city:
                fix_dir = False
        
        # Flag to process if city in list of likely problem cities
        fix_city = False
        for p in probs:
            if city in p:
                fix_city = True
                
        if dir_found and fix_dir and fix_city:
            print(f'Working on:    {addr}')
            add_splitter = splitters[high_index].strip()
            final_addr = addr.rsplit(add_splitter, 1)[0]
            final_addr = final_addr.strip()
            row['ADDRESS'] = final_addr
            row['CITY'] = add_splitter + ' ' + city
            updates += 1

    return row

fixed = work_df.progress_apply(fix_dirs, axis = 1)
fixed.to_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_2.csv'))


# NEXT PORTION USED TO FIX ERRORS WITH an address ending in NORTH AND CITY of SALT LAKE
work_df = pd.read_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_2.csv'))

def fix_nsl(row):
    addr = row['ADDRESS']
    city = row['CITY']
    if city == 'SALT LAKE' and addr.endswith('NORTH'):
        final_addr = addr.rsplit('NORTH', 1)[0]
        final_addr = final_addr.strip()
        row['ADDRESS'] = final_addr
        final_city = 'NORTH SALT LAKE'
        row['CITY'] = final_city
        
        print(f'Changing {addr}, {city}   to    {final_addr}, {final_city}')
        
    return row
        
fixed = work_df.progress_apply(fix_nsl, axis = 1)
fixed.to_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_3.csv'))

# NEXT PORTION USED TO FIX ERRORS WITH ' UT' REMAINING IN THE ADDRESS and 'CENTRAL' as the city
work_df = pd.read_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_3.csv'))

def fix_central(row):
    addr_orig = row['ADDRESS']
    city_orig = row['CITY']
    term = None
    ut_found = False
    city_found = False
    
    if ' UT' in addr_orig and city_orig == 'CENTRAL':
        before_ut = addr_orig.rsplit(' UT', 1)[0]
        after_ut = addr_orig.rsplit(' UT', 1)[1]
        good_ut = True
    
           
        # Get full address as a single field use city name to split
        before_parts = before_ut.split()
        possible_add = before_parts[1:]
        addnum = before_parts[0]
        possible_str = ' '.join(possible_add)
        
        # Clean up possible_str and add whitespace to the end
        if ' -' in possible_str:
            possible_str = possible_str.split(' -', 1)[0]
        elif '- ' in possible_str:
            possible_str = possible_str.split('- ', 1)[0]
        elif '.' in possible_str:
            possible_str = possible_str.replace('.', '')
            
        possible_str += ' '
            
        add_splitter = None
        splitters = []
        for i in np.arange(len(all_places)):          
            if all_places[i] in possible_str:
                splitters.append(all_places[i])
                city_found = True
        
        highest = 0
        high_index = 0
        if len(splitters) > 1:
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
            print(f'City not found in:   {addr_orig}\n')
        final_addr = ' '.join([addnum, addr])
        
        
        # Get 'city'
        if add_splitter:
            final_city = add_splitter
        else:
            final_city = possible_str
             
        # if city_found:
        #     good.writerow(final)
        # else:
        #     bad.writerow(final)
        
        row['ADDRESS'] = final_addr
        row['CITY'] = final_city
        
        del add_splitter
        del before_ut
        del after_ut
        del splitters
        del highest
        del high_index
        del term
    
        print(f'Changing {addr_orig}, {city_orig}   to    {final_addr}, {final_city}')
    
    return row
        
fixed = work_df.progress_apply(fix_central, axis = 1)

def len_calc(row):
    row['CITY_LENGTH'] = len(str(row['CITY']).strip())
    
    return row

fixed = fixed.progress_apply(len_calc, axis = 1)
fixed.sort_values('CITY_LENGTH', inplace=True, ascending=False)
fixed.to_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_4.csv'))


# Examine address length
fixed = pd.read_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_5.csv'))
def len_addr(row):
    row['ADDR_LENGTH'] = len(str(row['ADDRESS']).strip())
    
    return row

fixed = fixed.progress_apply(len_addr, axis = 1)
fixed.sort_values('ADDR_LENGTH', inplace=True, ascending=False)

fixed = fixed.drop_duplicates(subset=['ADDRESS', 'CITY'], keep='first')
fixed.to_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_6.csv'))

# NEXT PORTION USED TO FIX ERRORS WITH ' UT' REMAINING IN THE ADDRESS if it follows a place name
work_df = pd.read_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_7.csv'))

def fix_ut(row):
    addr_orig = row['ADDRESS']
    city_orig = row['CITY']
    term = None
    ut_found = False
    city_found = False
    city_ut_found = False
    
    if ' UT' in addr_orig:
        splitters1 = []
        # Check address string for '{Placename} UT'
        for i in np.arange(len(all_places)):
            test = all_places[i] + ' UT'
            if test in addr_orig:
                splitters1.append(all_places[i])
                city_ut_found = True
        
        # Only edit addresses with '{Placename} UT'
        if city_ut_found:
            before_ut = addr_orig.rsplit(' UT', 1)[0]
            after_ut = addr_orig.rsplit(' UT', 1)[1]
            good_ut = True
        
               
            # Get full address as a single field use city name to split
            before_parts = before_ut.split()
            possible_add = before_parts[1:]
            addnum = before_parts[0]
            possible_str = ' '.join(possible_add)
            
            # Clean up possible_str and add whitespace to the end
            if ' -' in possible_str:
                possible_str = possible_str.split(' -', 1)[0]
            elif '- ' in possible_str:
                possible_str = possible_str.split('- ', 1)[0]
            elif '.' in possible_str:
                possible_str = possible_str.replace('.', '')
                
            possible_str += ' '
                
            add_splitter = None
            splitters = []
            for i in np.arange(len(all_places)):          
                if all_places[i] in possible_str:
                    splitters.append(all_places[i])
                    city_found = True
            
            highest = 0
            high_index = 0
            if len(splitters) > 1:
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
                print(f'City not found in:   {addr_orig}\n')
            final_addr = ' '.join([addnum, addr])
            
            
            # Get 'city'
            if add_splitter:
                final_city = add_splitter
            else:
                final_city = possible_str
                 
            # if city_found:
            #     good.writerow(final)
            # else:
            #     bad.writerow(final)
            
            row['ADDRESS'] = final_addr
            row['CITY'] = final_city
            
            del add_splitter
            del before_ut
            del after_ut
            del splitters
            del highest
            del high_index
            del term
        
            print(f'Changing {addr_orig}, {city_orig}   to    {final_addr}, {final_city}')
    
    return row
        
fixed = work_df.progress_apply(fix_ut, axis = 1)




fixed = fixed.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
fixed = fixed.progress_apply(len_addr, axis = 1)
fixed.sort_values('ADDR_LENGTH', inplace=True, ascending=False)
fixed.to_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_8.csv'))


# NEXT PORTION USED TO FIX ERRORS WITH an address ending in NORTH/SOUTH AND CITY of Logan or Ogden
work_df = pd.read_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_8.csv'))

def fix_oglog(row):
    addr = row['ADDRESS']
    city = row['CITY']
    towns = ['OGDEN', 'LOGAN']
    if city in towns and addr.endswith('NORTH'):
        final_addr = addr.rsplit('NORTH', 1)[0]
        final_addr = final_addr.strip()
        row['ADDRESS'] = final_addr
        final_city = 'NORTH ' + city
        row['CITY'] = final_city.strip()
        
        print(f'Changing {addr}, {city}   to    {final_addr}, {final_city}')
        
    if city == 'OGDEN' and addr.endswith('SOUTH'):
        final_addr = addr.rsplit('SOUTH', 1)[0]
        final_addr = final_addr.strip()
        row['ADDRESS'] = final_addr
        final_city = 'SOUTH ' + city
        row['CITY'] = final_city.strip()
        
        print(f'Changing {addr}, {city}   to    {final_addr}, {final_city}')
        
    return row
        
fixed = work_df.progress_apply(fix_oglog, axis = 1)

fixed = fixed.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
fixed = fixed.progress_apply(len_addr, axis = 1)
fixed.sort_values('ADDR_LENGTH', inplace=True, ascending=False)
fixed.to_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_9.csv'))

# NEXT PORTION USED TO FIX ERRORS with North Logan city that should be Logan w/ addr ending in NORTH
work_df = pd.read_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_9_updates.csv'))

def fix_northlogan(row):
    addr = row['ADDRESS']
    city = row['CITY']
    
    end = addr.split()[-1]
    if end.isdigit():
        row['ends_in_digit'] = True
    else:
        row['ends_in_digit'] = False



    if city == 'NORTH LOGAN' and row['ends_in_digit'] == True:
        final_addr = addr + ' NORTH'
        final_addr = final_addr.strip()
        row['ADDRESS'] = final_addr
        
        final_city = 'LOGAN'
        row['CITY'] = final_city.strip()
        
        print(f'Changing {addr}, {city}   to    {final_addr}, {final_city}')
        
    return row
        
fixed = work_df.progress_apply(fix_northlogan, axis = 1)

fixed = fixed.applymap(lambda x: x.strip() if type(x) == str else x)
fixed = fixed.progress_apply(len_addr, axis = 1)
fixed.sort_values('ADDR_LENGTH', inplace=True, ascending=False)
fixed.to_csv(os.path.join(work_dir, 'unique_address_dir_fixes_TEST_10.csv'))


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))

