import arcpy
import os
import sys
import csv
import shutil
from os.path import split, join
from datetime import datetime
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))
from helpers import general_helper 
from helpers import gis_helper

arcpy.env.overwriteOutput = True

startTime = datetime.now()
print startTime

def SplashScreen():
    arcpy.AddMessage("\n{}".format("....."*10))
    arcpy.AddMessage("{}Batch Field Symolization".format("     "*2))
    arcpy.AddMessage("{}\n".format("....."*10))


try:

    SplashScreen()

    #...........................................................
    # Geo-processing Input Tools
    #...........................................................
    INPUT_TABLE = arcpy.GetParameterAsText(0)
    SELECTED_FIELDS = arcpy.GetParameterAsText(1) #FIELDS_TO_SYMBOLIZE
    GROUP_FIELD = arcpy.GetParameterAsText(2)
    METHOD_CLASSIFICATION = arcpy.GetParameterAsText(3)
    CLASS_BIN = arcpy.GetParameterAsText(4)
    CLASS_VALUES = arcpy.GetParameterAsText(5)
    OUTPUT_MXD_NAME = general_helper.Space2Underscore(arcpy.GetParameterAsText(6)) #Modify output file name for invalid characters.
    SCRATCH_GDB = arcpy.GetParameterAsText(7)

    if METHOD_CLASSIFICATION == 'Manual':
        CLASS_BIN = ''
    else:
        CLASS_VALUES = ''

    #...........................................................
    # SETTING UP THE DIRECTORY AND DEFAULT FILE NAMES/LOCATIONS
    #...........................................................

    INPUT_PATH = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(os.path.normpath(INPUT_PATH))
    SCRIPT_CONTENTS = os.path.join(BASE_DIR, "csv to MXD")
    OUTPUT_DIR = os.path.join(SCRIPT_CONTENTS, "Output Data")
    GIS_DIR = os.path.join(SCRIPT_CONTENTS, "GIS")

    #......................................................................................................
    # Neceessary field names, Lists, Dictionaries, GIS Related Items
    #......................................................................................................

    layer_file_dict = {
        'Equal Interval': r"methods\Equal Interval.lyr",
        'Quantile': r"methods\Quantile.lyr",
        'Natural Breaks (Jenks)': r"methods\Natural Breaks.lyr",
        'Geometrical Interval': r"methods\Geometrical Interval.lyr",
        'Manual': r"methods\Equal Interval.lyr"
    }

    # GIS Layers
    layer_file = os.path.join(GIS_DIR, layer_file_dict[METHOD_CLASSIFICATION]) #stores symbolgy to be used
    empty_group_path = os.path.join(GIS_DIR, "Empty Group Layer.lyr") #blank group layer
    MUNI_FC = os.path.join(GIS_DIR, r"GISdata.gdb\Govt_admin_municipal_bnd")

    #GIS Fields
    JOIN_FIELD = 'MUN_CODE'

    if CLASS_VALUES:
        CLASS_VALUES =[val.strip() for val in CLASS_VALUES.split(',')]

    #......................................................................................................
    # Adding GIS Layers to document and symbolizing
    #......................................................................................................

    #Setting up the mxd path by copying temp mxd and renameing
    temp_mxd = os.path.abspath(os.path.join(GIS_DIR, "Holder.mxd"))
    mxd_path = os.path.abspath(os.path.join(OUTPUT_DIR, OUTPUT_MXD_NAME + ".mxd"))
    if os.path.exists(mxd_path):
        os.remove(mxd_path)
    shutil.copy(temp_mxd, mxd_path)
    mxd = arcpy.mapping.MapDocument(mxd_path)
    dataframe = arcpy.mapping.ListDataFrames(mxd)[0]

    #Extract Path and Table Name
    #Check if input is Extract contents from csv and create a temporary table
    filename, file_ext = os.path.splitext(INPUT_TABLE)
    if file_ext == ".csv":
        INPUT_TABLE = gis_helper.csv_to_table(INPUT_TABLE,SCRATCH_GDB)
    TABLE_PATH, TABLE_NAME = gis_helper.InputCheck(INPUT_TABLE) #Extract Path and Table Name

    SELECTED_FIELDS = [fields.strip() for fields in SELECTED_FIELDS.split(";")]
    table_field_info = gis_helper.Extract_Field_InfoDict(TABLE_PATH)
    fields_to_symbolize = list()

    arcpy.AddMessage("Symbolizing the following fields:")
    for item in SELECTED_FIELDS:
        check = gis_helper.Validate_Field_Type(table_field_info[item], ['Double', 'Float', 'Integer'])
        if check:
            arcpy.AddMessage("..... {}".format(item))
            fields_to_symbolize.append(item)
        else:
            arcpy.AddMessage("The field, '{}', is not a valid data type to symbolize. Removing from list".format(item))

    #User Selected a field to break layers into groups. extract unique values and cycle through each field value
    if GROUP_FIELD:
        group_values = gis_helper.unique_values(TABLE_PATH, GROUP_FIELD) #Store all the unqiue attributes for a given field.
        for value in group_values:
            arcpy.AddMessage("Selecting records from the input table containing, '{}', from the field, {}".format(value, GROUP_FIELD))

            # Export Table from SDE/Main Database to user specified database
            FC_NAME = "Muni_Analysis_{}_{}_{}".format(GROUP_FIELD, value, OUTPUT_MXD_NAME)
            FC_PATH = os.path.join(SCRATCH_GDB, FC_NAME)
            arcpy.AddMessage("Copying the municipality feature class and joining selected table records. Feature class named, {}, can be found at the following path: {}".format(FC_NAME, SCRATCH_GDB))
            gis_helper.Copy_FC(FC_NAME, MUNI_FC, SCRATCH_GDB)

            #Create definition query to filter out records in Table and Join to FC
            whereClause = '''{} = '{}' '''.format(GROUP_FIELD, value)
            gis_helper.Join_Table_to_FC(FC_PATH, TABLE_PATH, JOIN_FIELD, fields_to_symbolize, whereClause)

            #Create Feature Layer
            gis_helper.Create_FL(FC_NAME, FC_PATH)

            #Add Layers to TOC -> Create group layer -> import symbology
            gis_helper.add_layer_TOC(FC_PATH, dataframe) #This Feature Class will be used to make copies and renamed based on the field that will be symbolized.
            gis_helper.Create_Group_Layer(empty_group_path, value, mxd, dataframe)
            gis_helper.Import_Symbology(FC_NAME, layer_file, mxd, dataframe)

            # Symbolize Fields
            for field in fields_to_symbolize:
                gis_helper.Symbolize_field(FC_NAME, field, value, layer_file, mxd, dataframe, CLASS_BIN, CLASS_VALUES)

            layer_to_remove = arcpy.mapping.ListLayers(mxd, FC_NAME, dataframe)[0]
            arcpy.mapping.RemoveLayer(dataframe, layer_to_remove)

    else:
        # Export Table from SDE/Main Database to user specified database
        FC_NAME = "Muni_Analysis_{}".format(OUTPUT_MXD_NAME)
        FC_PATH = os.path.join(SCRATCH_GDB,FC_NAME)
        arcpy.AddMessage("Copying municipality feature class and joining table. Feature class named, {}, can be found at the following path: {}".format(FC_NAME, SCRATCH_GDB))
        gis_helper.Copy_FC(FC_NAME, MUNI_FC, SCRATCH_GDB)
        gis_helper.Join_Table_to_FC(FC_PATH, TABLE_PATH ,JOIN_FIELD, fields_to_symbolize)

        #Create Feature Layer
        gis_helper.Create_FL(FC_NAME,FC_PATH)

        #Add Layers to TOC -> Create group layer -> import symbology
        #This Feature Class will be used to make copies and renamed based on the field that will be symbolized.
        gis_helper.add_layer_TOC(FC_NAME, dataframe)
        gis_helper.Create_Group_Layer(empty_group_path, "Record Analysis", mxd, dataframe)
        gis_helper.Import_Symbology(FC_NAME, layer_file, mxd, dataframe)

        for field in fields_to_symbolize:
            gis_helper.Symbolize_field(FC_NAME, field, "Record Analysis", layer_file, mxd, dataframe, CLASS_BIN, CLASS_VALUES)

        layer_to_remove = arcpy.mapping.ListLayers(mxd, FC_NAME, dataframe)[0]
        arcpy.mapping.RemoveLayer(dataframe,layer_to_remove)

    mxd.save()
    arcpy.AddMessage("Saving the mxd, '{}', at the following path: {}".format(OUTPUT_MXD_NAME, OUTPUT_DIR))
    del mxd
    #os.system("TASKKILL /F /IM ArcMap.exe")

except ValueError:
    import traceback, sys
    tb = sys.exc_info()[2]
    print "line %i" % tb.tb_lineno
    print( "\nFormat error." )
    del mxd
    os.system("TASKKILL /F /IM ArcMap.exe")

print "......................................................................End Runtime: ", datetime.now()-startTime