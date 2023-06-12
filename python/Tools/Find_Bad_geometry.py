import arcpy
from arcpy import env
import os
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

database = r"C:\E911\TOC\TOC_Data_UTM.gdb"
#database = r"C:\E911\TOC\TOC_Spillman_WGS_84.gdb"
#database = r"C:\E911\StGeorgeDispatch_TEST\StGeorgeDispatch_UTM.gdb"
env.workspace = database
fclist = arcpy.ListFeatureClasses()

###############
#  Functions  #
###############


def id_bad_geom(fc):
#    update_count = 0
#    flist = ['SHAPE@XY', 'OBJECTID']  # for points
    flist = ['Shape', 'OID@']  # for point, polylines, or polygons
    bad = False
    with arcpy.da.SearchCursor(fc, flist) as cursor:
        print("Looping through rows in {}...".format(arcpy.Describe(fc).name))
        for row in cursor:
            # print row
            if row[0][0] == None or row[0][1] == None:
                bad = True
                
    if bad == True:
        print("     {} has features with bad geometry".format(fc))            
    
def list_bad_geom(fc):
#    update_count = 0
#    flist = ['SHAPE@XY', 'OBJECTID']  # for points
    flist = ['Shape', 'OID@']  # for point, polylines, or polygons
    with arcpy.da.SearchCursor(fc, flist) as cursor:
        print("Looping through rows in {}...".format(arcpy.Describe(fc).name))
        for row in cursor:
            # print row
            if row[0][0] == None or row[0][1] == None:
                print(row)                

##########################
#  Call Functions Below  #
##########################

for fc in fclist:
    list_bad_geom(fc)

#for fc in fclist:
#    id_bad_geom(fc)

#for fc in fclist:
#    desc = arcpy.Describe(fc)
#    print("{} is of shape type: {}".format(fc, desc.shapeType))
    

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
