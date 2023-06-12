import arcpy
from arcpy import env
import time

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script start time is {}".format(readable_start))

database = r"C:\E911\TOC\aaa_empty_geovalidation_schema.gdb"
env.workspace = database
fclist = arcpy.ListFeatureClasses()
fclist.sort()

print(f'Truncating all tables in {database} ...')

for fc in fclist:
    print(f'    Truncating {fc} ...')
    arcpy.management.TruncateTable(fc)

print("Script shutting down ...")
# Stop timer and print end time in UTC
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
