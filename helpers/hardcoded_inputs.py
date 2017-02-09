import os
import csv
import sys
import operator
import re
import arcpy
from os.path import split, join
from string import replace
from collections import defaultdict, OrderedDict
arcpy.env.overwriteOutput = True

#..............................................................................................................................................
# Statis Inputs that stores variables

def Static_Inputs():
    municipality_fc_path = r"\\Dep-gisprodnew\FileGeoDataBases\Dep_GIS_Publication\Government\Government.gdb\Govt_admin_municipal_bnd"
    county_field = "COUNTY"
    municipality_field = "MUN"
    municipality_coded_val = "MUN_CODE"
    return (municipality_fc_path,county_field,municipality_field,municipality_coded_val)
#..............................................................................................................................................

