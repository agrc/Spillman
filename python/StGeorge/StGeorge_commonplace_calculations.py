# -*- coding: utf-8 -*-
"""
Created on Tue Aug 25 11:00:29 20209

@author: eneemann

EMN: Initial script to calculate commonplace fields for St George
"""

import arcpy
from arcpy import env
import numpy as np
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

stage_db = r"C:\E911\StGeorgeDispatch\StGeorge_Staging.gdb"
# stage_db = r"C:\E911\StGeorgeDispatch\StGeorgeDispatch_WGS84.gdb"
commonplaces = os.path.join(stage_db, "StG_CP_update_20211117")
env.workspace = stage_db


# # Optional selection to narrow down rows the calculations are performed on
# arcpy.management.SelectLayerByAttribute(commonplaces, 'NEW_SELECTION', "StreetName IS NULL")

unit_list = ['#', 'APT', 'BLDG', 'BSMT', 'CONDO', 'DEPT', 'FL', 'FRNT', 'HANGAR',
             'HNGR', 'LOT', 'MAIN', 'OFC', 'OFFICE', 'REAR', 'RM', 'SIDE', 'SP', 'SPC',
             'STE', 'TOP', 'TRLR', 'UNIT']


def calc_all_components_from_street(pts):
    update_count = 0
    five_letter = 0
    # Use update cursor to calculate components from street field
    #            0           1           2           3           4
    fields = ['STREET', 'STREETNAME', 'PREDIR', 'STREETTYPE', 'SUFDIR']
    where_clause = "STREET IS NOT NULL AND STREETNAME IS NULL"
    # where_clause = "STREET IS NOT NULL"
    with arcpy.da.UpdateCursor(pts, fields, where_clause) as cursor:
        print("Looping through rows in FC ...")
        for row in cursor:
            street = row[0]
            pre = None
            suf = None
            stname = None
            sttype = None
            rest = None
            
            # print(street)
            
            # calculate predirection
            st_split = street.split(' ', 1)
            pre_test = st_split[0]
            if len(st_split) > 1:
                rest = street.split(' ', 1)[1]
            if len(pre_test) == 1:
                pre = pre_test.strip()
            
            # calculate sufdir
            if len(street.rsplit(' ', 1)) > 1:
                end = street.rsplit(' ', 1)[1]
            else:
                end = street
            # beg = street.rsplit(' ', 1)[0]
            # print(beg)
            if len(end) == 1 and end in ['N', 'S', 'E', 'W']:
                suf = end.strip()
            elif rest:
                rest_parts = rest.split(' ')
                for i in np.arange(len(rest_parts)):
                    if rest_parts[i].upper() in ['N', 'S', 'E', 'W']:
                        suf = rest_parts[i]
                
            # calculate streettype
            if suf and pre:
                temp = street.split(pre, 1)[1]
                new_end = temp.rsplit(suf, 1)[1].strip()
                if new_end is None:
                    sttype = None
                elif 1 < len(new_end) <= 4 and end.isalpha():
                    if new_end not in unit_list:
                        sttype = new_end.strip()
                elif len(new_end) == 5:
                    print(f'Encountered possible 5 letter streettype: {new_end}')
                    five_letter += 1
            elif not suf:
                if len(street.split()) > 1:
                    new_end = street.rsplit(' ', 1)[1].strip()
                    if 1 < len(new_end) <= 4 and end.isalpha():
                        if new_end not in unit_list:
                            sttype = new_end.strip()
                    elif len(new_end) == 5:
                        print(f'Encountered possible 5 letter streettype: {new_end}')
                        five_letter += 1
                
            
            
            # calculate streetname
            if pre is not None:
                new_temp = street.split(pre, 1)[1]
                if suf is not None:
                    stname = new_temp.rsplit(suf, 1)[0]
                elif sttype is not None:
                    stname = new_temp.rsplit(sttype, 1)[0]
                else:
                    stname = new_temp
            else:
                new_temp = street
                if suf is not None:
                    stname = street.rsplit(suf, 1)[0]
                elif sttype is not None:
                    stname = street.rsplit(sttype, 1)[0]
                else:
                    stname = new_temp
            
            # Calc the new fields
            if stname:
                row[1] = stname.strip()
            else:
                row[1] = None
                
            if pre:
                row[2] = pre.strip()
            else:
                row[2] = None
                
            if sttype:
                row[3] = sttype.strip()
            else:
                row[3] = None
            
            if suf:
                row[4] = suf.strip()
            else:
                row[4] = None
            
            update_count += 1
            cursor.updateRow(row)
    print("Total count of STREETNAME calculations is: {}".format(update_count))
    print("Total count of Five letter street types is: {}".format(five_letter))
    
calc_all_components_from_street(commonplaces)


print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))