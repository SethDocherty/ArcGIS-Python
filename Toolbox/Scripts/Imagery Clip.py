#-------------------------------------------------------------------------
# Name:        Image Clip
# Purpose:     Clip images based on the invidual extents of features in a
#              feature class
#
# Author:      Seth Docherty
#
# Created:     01/17/2017
# Copyright:   (c) sdochert2 2017
# Licence:     <your licence>
#
# Current Issues:   Clip tool is not honoring clipping extent when the ouput
#                   raster is not stored in a geodatabase.
#-------------------------------------------------------------------------

import arcpy
import os
import sys
import csv
import re
from os.path import split, join
from datetime import datetime
arcpy.env.overwriteOutput = True

startTime = datetime.now()
print startTime


def unique_values(fc, field):
    with arcpy.da.SearchCursor(fc, [field])as cur:
        return sorted({row[0] for row in cur})


def InputCheck(Input_Layer):
    '''
    Check if there is a filepath from the input layers. If not, pre-pend the path. 
    Also extract the FC names.
    '''
    if arcpy.Exists(Input_Layer):
        # join(arcpy.Describe(Input_Layer).catalogPath,arcpy.Describe(Input_Layer).name)
        InputPath = arcpy.Describe(Input_Layer).catalogPath
        InputName = arcpy.Describe(Input_Layer).name
    else:
        arcpy.AddError("{} Does not exist".format(Input_Layer))
        sys.exit()
    return InputPath, InputName


def Create_FL(LayerName, FCPath, expression=''):
    '''
    Create a Feature layer from a feature class. Optionally, an expression clause can be passed in
    to filter out a subset of data.
    '''
    if arcpy.Exists(LayerName):
        arcpy.Delete_management(LayerName)
    try:
        if expression:
            return arcpy.MakeFeatureLayer_management(FCPath, LayerName, expression, "")
        else:
            return arcpy.MakeFeatureLayer_management(FCPath, LayerName, "", "")
    except:
        return arcpy.AddError(arcpy.GetMessages(2))


def is_workspace_gdb(input_path):
    '''
    Return True if path is a in a GDB workspace.
    '''
    workspace = arcpy.Describe(input_path)
    if workspace.dataType == "Folder":
        return False
    else:
        return True

def Return_File_Type(input_key):
    file_type_dict = {
        'Esri BIL - .bil': '.bil',
        'Esri BIP - .bip': '.bip',
        'BMP - .bmp': '.bmp',
        'Esri BSQ - .bsq': '.bsq',
        'ENVI DAT - .dat': '.dat',
        'GIF - .gif': '.gif',
        'ERDAS IMAGINE - .img': '.img',
        'JPEG - .jpg': '.jpg',
        'JPEG 2000 - .jp2': '.jp2',
        'PNG - .png': '.png',
        'TIFF - .tif': '.tif',
        '': False
        }
    return file_type_dict[input_key]


#.........................................................................
# User Input data
#.........................................................................

Image_Workspace = arcpy.GetParameterAsText(0)
Clipping_Features = arcpy.GetParameterAsText(1)
Clipping_Feature_Field = arcpy.GetParameterAsText(2)
Final_Output_GDB = arcpy.GetParameterAsText(3)
Output_File_Type = Return_File_Type(arcpy.GetParameterAsText(4))

arcpy.AddMessage("File type: {}".format(Output_File_Type))

#...........................................................
# SETTING UP THE DIRECTORY AND DEFAULT FILE NAMES/LOCATIONS
#...........................................................

INPUT_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.normpath(INPUT_PATH))
SCRIPT_CONTENTS = os.path.join(BASE_DIR, "Imagery Clip")
LOG_DIR = os.path.join(SCRIPT_CONTENTS, "Logs")

# Extract Path and Table Name
Clip_Feat_Path, Clip_Feat_Name = InputCheck(Clipping_Features)

#.........................................................................
# Neceessary field names, Lists, Dictionaries, GIS Related Items
#.........................................................................

# Clipping Features
Feature_Names = unique_values(Clip_Feat_Path, Clipping_Feature_Field)
if " " in Feature_Names:
    Feature_Names.remove(' ')

# Extract names of images in user specified workspace
# Create dictionary of image names as keys and image file paths as values
image_dict = {}
valid_ext = ['jpg', 'tif', 'png']
if is_workspace_gdb(Image_Workspace):
    gdb_walk = arcpy.da.Walk(Image_Workspace, datatype="RasterDataset")
    for dirpath, dirnames, filenames in gdb_walk:
        for filename in filenames:
            image_dict[filename] = os.path.join(dirpath, filename)
else:
    walk = os.walk(Image_Workspace)
    for dirpath, dirnames, filenames in walk:
        for filename in filenames:
            try:
                name, ext = filename.split('.')
            except:
                continue
            if name not in image_dict and ext in valid_ext:
                image_dict[name] = os.path.join(
                    dirpath, filename)

Missing_Maps = []  # Store a list of images that are missing
Unclipped_Maps = []  # Store a list of images that were not clipped

#.........................................................................
# Main Program
#.........................................................................

arcpy.AddMessage("a total of {} images will be processed".format(len(Feature_Names)))
arcpy.env.cellSize = 1

for feature in Feature_Names:
    arcpy.AddMessage("Working on Image {} ({} out of {})............................................................................. Time: {}".format(
        feature, Feature_Names.index(feature) + 1, len(Feature_Names), datetime.now() - startTime))
    if feature not in image_dict:
        arcpy.AddMessage(
            "There is no image for the following feature: {}".format(feature))
        Missing_Maps.append(feature)
        continue

    # Create layer with Select by attribute
    layer_name_regex = re.compile(r'\s|-|\.')
    layer_name = layer_name_regex.sub("_", feature)
    if layer_name[:1].isdigit():
        layer_name = "Image_" + layer_name

    # Create temporary feature layer and extract extent of feature.
    tmp_layer = "layer_" + layer_name
    clause = ''' {} = '{}' '''.format(Clipping_Feature_Field, feature)
    Create_FL(tmp_layer, Clip_Feat_Path, clause)
    # rows = arcpy.SearchCursor(tmp_layer)
    shapeName = arcpy.Describe(tmp_layer).shapeFieldName
    for row in arcpy.SearchCursor(tmp_layer):
        feat = row.getValue(shapeName)
        extent = feat.extent
        envelope = '{} {} {} {}'.format(extent.XMin, extent.YMin, extent.XMax, extent.YMax)
        arcpy.AddMessage("Extent from other Method Layer: {}".format(envelope))

    # Setting up parameters to clip image
    input_raster_path = image_dict[feature]
    if Output_File_Type is False: #Account for when files are saved to a FGDB
        output_raster_path = os.path.join(Final_Output_GDB, layer_name)
    else:
        output_raster_path = os.path.join(Final_Output_GDB, layer_name + Output_File_Type)
    if arcpy.Exists(output_raster_path):
        arcpy.AddMessage("Raster already exists, Skipping")
        continue

    # Clip image based on selected feature
    try:
        arcpy.AddMessage("Processing Image at {}".format(input_raster_path))
        arcpy.Clip_management(input_raster_path, envelope, output_raster_path,
                              tmp_layer, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
    except:
        arcpy.AddError(arcpy.GetMessages(2))
        arcpy.AddMessage("Image could not be clipped due to an error")
        Unclipped_Maps.append(feature)

    # Remove Temporary Layers
    arcpy.Delete_management(tmp_layer)

#.........................................................................
# Ouputting error lsits to .csv files
#.........................................................................

# Ouput list of missing maps that are not in the process folder to .csv
Output_Path = os.path.join(LOG_DIR, "Missing Maps.csv")
with open(Output_Path, 'wb') as ofile:
    writer = csv.writer(ofile, dialect='excel', delimiter=',')
    header = 'Map ID'
    writer.writerow([header])
    for item in Missing_Maps:
        writer.writerow([item])
ofile.close()

# Ouput list of maps that could not be clipped to .csv
Output_Path = os.path.join(LOG_DIR, "Geoprocessing Errors.csv")
with open(Output_Path, 'wb') as ofile:
    writer = csv.writer(ofile, dialect='excel', delimiter=',')
    header = 'Map ID'
    writer.writerow([header])
    for item in Unclipped_Maps:
        writer.writerow([item])
ofile.close()

arcpy.AddMessage(
"......................................................................End Runtime: {}".format(datetime.now() - startTime))