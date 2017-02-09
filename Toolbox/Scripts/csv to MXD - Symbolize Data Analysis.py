import arcpy
import os
import sys
import csv
import shutil
from os.path import split, join
from datetime import datetime
arcpy.env.overwriteOutput = True

startTime = datetime.now()
print startTime

def Extract_Field_Info(fc):
    '''
    Extract Field name and Type.
    Return list format: [Name, Type]

    *NOTE*
        - Sort of a replication of the function called "get_Data_Type"
    '''
    field_info=dict()
    for field in arcpy.ListFields(fc):
        if field.name == 'Shape' or field.name == 'Shape_Length' or field.name == 'OBJECTID' or field.name == 'RID':
            pass
        else:
##            item=[]
##            item.append(field.name)
##            item.append(field.type)
            field_info[field.name] = field.type
    return field_info


def unique_values(fc,field):
    with arcpy.da.SearchCursor(fc,[field])as cur:
        return sorted({row[0] for row in cur})


def Copy_FC(fc_name, fc_to_copy, output_gdb):
    '''
    Quickly copy a feature class to another location.  This function will check to see if the feature class already exists at said location
    before performing the copy.
    '''
    fc_path = os.path.join(output_gdb,fc_name)
    # Export Table from SDE/Main Database to user specified database
    if arcpy.Exists(fc_path): # Find out if FC already exists.  Delete so it does.  FeatureClassToFeatureClass does not overwrite.
        arcpy.Delete_management(fc_path)
    arcpy.FeatureClassToFeatureClass_conversion(fc_to_copy, output_gdb, fc_name)


def Join_Table_to_FC(fc_path, table_path ,join_field, fields_to_join='', clause=''):
    '''
    Join a table to a fc.  This function will create the necessary layer/table views and peform a permanent join to the input FC
    User can optionally pass in a where clause to filter out specific records from the table as well as a list of specific fields from
    the table that will be joined to the FC.

    Temporary layers views and table views are deleted
    '''
    tmp_layer = "temp_layer_join"
    Create_FL(tmp_layer, fc_path)
    tmp_table = "temp_table_join"
    Create_TV(tmp_table, TABLE_PATH, clause)
    arcpy.JoinField_management(tmp_layer, join_field, tmp_table, join_field, fields_to_join)
    del tmp_table
    del tmp_layer


def CopyPasteLayer(CopyLayer, PastedLayerName,df):
 CopyLayerList = [arcpy.mapping.Layer(str(CopyLayer))]
 for CopyLayer in CopyLayerList:
     CopyLayer.name = str(PastedLayerName)
     return arcpy.mapping.AddLayer(df, CopyLayer, "BOTTOM")
     #CopyLayer.name = str(CopyLayer)


def csv_to_table(input_file, GDB_path):
    name = os.path.splitext(os.path.basename(input_file))[0]
    name = name.replace(" ","_")
    out_path = os.path.join(GDB_path, name)
    if arcpy.Exists(out_path):
        arcpy.Delete_management(out_path)
    arcpy.TableToTable_conversion(input_file, GDB_path, name)
    return out_path


def Create_FL(LayerName, FCPath, expression =''):
    '''
    Create a Feature layer from a feature class. Optionally, an expression clause can be passed in to
    filter out a subset of data.
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


def Create_TV(LayerName, TBLPath, expression =''):
    '''
    Create a table view from a table. Optionally, an expression clause can be passed in to
    filter out a subset of data.
    '''
    if arcpy.Exists(LayerName):
        arcpy.Delete_management(LayerName)
    try:
        if expression:
            return arcpy.MakeTableView_management(TBLPath, LayerName, expression, "", "")
        else:
            return arcpy.MakeTableView_management(TBLPath, LayerName, "", "", "")
    except:
        return arcpy.AddError(arcpy.GetMessages(2))


def InputCheck(Input_Layer):
    '''
    Check if there is a filepath from the input layers. If not, pre-pend the path. Also extract the Layer names.
    return is a list [Layer Path, Layer Name]
    '''
    if arcpy.Exists(Input_Layer):
        InputPath = arcpy.Describe(Input_Layer).catalogPath #join(arcpy.Describe(Input_Layer).catalogPath,arcpy.Describe(Input_Layer).name)
        InputName = arcpy.Describe(Input_Layer).name
    else:
        arcpy.AddError("{} Does not exist".format(Input_Layer))
        sys.exit()
    return InputPath, InputName

def Symbolize_field(fc_name, field, group_lyr_name, lyr_file, mxd, dataframe, bin_size='', class_break_vals=''):
    layer_name = group_lyr_name +" - " + field
    arcpy.AddMessage(".........................Symbolizing the following field: {}".format(field))
    CopyPasteLayer(fc_name, layer_name,dataframe) #Copy FC with joined table and rename based
    move_to_group(group_lyr_name,layer_name, mxd, dataframe) # Move layer inside themed group layer
    Import_Symbology(layer_name, lyr_file, mxd, dataframe)

    # Modify symbology for layers of interest
    lyr = arcpy.mapping.ListLayers(mxd, layer_name, dataframe)[0]
    lyr.definitionQuery = '''{} <> 0 '''.format(field)
    lyr.symbology.reclassify() # update the symbology properties based on the layer's actual data source information and statistics
    if lyr.symbologyType == "GRADUATED_COLORS":
        lyr.symbology.valueField = field
        if bin_size:
            lyr.symbology.numClasses = int(bin_size)
        if class_break_vals:
            lyr.symbology.classBreakValues = class_break_vals
            lyr.symbology.classBreakLabels = Create_Class_Break_Labels(class_break_vals)


def add_layer_TOC(fc_path,df):
    lyr_name = os.path.basename(fc_path)
    lyr = Create_FL(lyr_name, fc_path)
    arcpy.mapping.AddLayer(df,lyr.getOutput(0),"BOTTOM")


def add_table_TOC(table_path, mxd_path):
    addTable = arcpy.MakeTableView_management(table_path)
    mxd = arcpy.mapping.MapDocument(mxd_path)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    arcpy.mapping.AddTableView(df,addTable.getOutput(0),"BOTTOM")


def move_to_group(group_name, lyr_name, mxd_obj, df):
    group_layer = arcpy.mapping.ListLayers(mxd_obj,group_name,df)[0]
    move_layer = arcpy.mapping.ListLayers(mxd_obj,lyr_name,df)[0]
    arcpy.mapping.AddLayerToGroup(df, group_layer, move_layer, "BOTTOM")
    arcpy.mapping.RemoveLayer(df,move_layer)

def Import_Symbology(input_fc, input_source, mxd_obj, df):
    updateLayer = arcpy.mapping.ListLayers(mxd_obj, input_fc, df)[0]
    sourceLayer = arcpy.mapping.Layer(input_source)
    arcpy.mapping.UpdateLayer(df, updateLayer, sourceLayer, True)


def Create_Group_Layer(empty_group_layer_path, group_name,  mxd, dataframe):
    #Import empty group layer and move layer just added to group layer.
    empty_group_layer = arcpy.mapping.Layer(empty_group_layer_path)
    arcpy.mapping.AddLayer(dataframe, empty_group_layer, "BOTTOM")
    empty_group_layer = arcpy.mapping.ListLayers(mxd,'Empty Group Layer', dataframe)[0]
    empty_group_layer.name = group_name


def Remove_Old_Layers(mxd_obj,df,layers):
    if len(layers) != 0:
        for lyr in arcpy.mapping.ListLayers(mxd,'',dataframe):
            if layers[0] in lyr.name:
                arcpy.mapping.RemoveLayer(dataframe,lyr)
                print "removed {}".format(lyr.name)
        layers.remove(layers[0])
        return Remove_Old_Layers(mxd_obj,df,layers)
    else:
        print "All the old layers have been removed"
        arcpy.AddMessage("All the older layers have been removed")

def Space2Underscore(fields):
    '''
    Replace spaces in strings with an underscore.
    This is intended for header fields from that need to be compared against fields in ArcGIS.
    '''
    field_update=[]
    for field in fields:
        if field.find(" ") > 0:
            x=field.replace(' ','_')
            field_update.append(x)
        else:
            field_update.append(field)
    return field_update

def SplashScreen():
    arcpy.AddMessage("\n{}".format("....."*10))
    arcpy.AddMessage("{}Batch Field Symolization".format("     "*2))
    arcpy.AddMessage("{}\n".format("....."*10))

def Validate_Field_Type(field_type, valid_types):
    if field_type in valid_types:
        return True
    else:
        return False

def Create_Class_Break_Labels(class_vals):
    max = len(class_vals)
    class_labels = list()
    for val in range(len(class_vals)):
        if (val+1) < max:
            left = class_vals[val]
            right = class_vals[val+1]
            class_labels.append("{} - {}".format(left, right))
    return class_labels

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
    OUTPUT_MXD_NAME = arcpy.GetParameterAsText(6)
    SCRATCH_GDB = arcpy.GetParameterAsText(7)

##    INPUT_TABLE = r"\\Dep-tisc\homec2\SDOCHERT2\Coding\Python\Parcel_Analysis\Output Data\Parcel_Selection\MunicipalityBreakdown.csv"
##    FIELDS_TO_SYMBOLIZE = "Total_Records;Total_Unique_PI_Numbers;Total_Unique_GIS_PINS"
##    GROUP_FIELD ="Type"
##    CLASS_BIN = 6
##    OUTPUT_MXD_NAME = "Output1"
##    SCRATCH_GDB = r"\\Dep-tisc\homec2\SDOCHERT2\GIS\Geodatabases\Default.gdb"

    if METHOD_CLASSIFICATION == 'Manual':
        CLASS_BIN = ''
    else:
        CLASS_VALUES = ''


    #...........................................................
    # SETTING UP THE DIRECTORY AND DEFAULT FILE NAMES/LOCATIONS
    #...........................................................

    INPUT_PATH = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(os.path.normpath(INPUT_PATH))
    INPUT_DIR = os.path.join(BASE_DIR, "Input Data")
    OUTPUT_DIR = os.path.join(BASE_DIR, "Output Data")
    GIS_DIR = os.path.join(BASE_DIR, "GIS")

    #......................................................................................................
    # Neceessary field names, Lists, Dictionaries, GIS Related Items
    #......................................................................................................

    layer_file_dict = {
        'Equal Interval': "methods\Equal Interval.lyr",
        'Quantile': "methods\Quantile.lyr",
        'Natural Breaks (Jenks)': "methods\Natural Breaks.lyr",
        'Geometrical Interval': "methods\Geometrical Interval.lyr",
        'Manual': "methods\Equal Interval.lyr"
    }

    # GIS Layers
    layer_file = os.path.join(GIS_DIR, layer_file_dict[METHOD_CLASSIFICATION]) #stores symbolgy to be used
    empty_group_path = os.path.join(GIS_DIR, "Empty Group Layer.lyr") #blank group layer
    MUNI_FC = r'\\Dep-gisprodnew\FileGeoDataBases\Dep_GIS_Publication\Government\Government.gdb\Govt_admin_municipal_bnd' #Feature Class that will be symbolized.

    #GIS Fields
    JOIN_FIELD = 'MUN_CODE'

    if CLASS_VALUES:
        CLASS_VALUES =[val.strip() for val in CLASS_VALUES.split(',')]

    #......................................................................................................
    # Adding GIS Layers to document and symbolizing
    #......................................................................................................

    #Setting up the mxd path by copying temp mxd and renameing
    temp_mxd = os.path.abspath(os.path.join(GIS_DIR, "Holder.mxd"))
    mxd_path = os.path.abspath(os.path.join(GIS_DIR, OUTPUT_MXD_NAME + ".mxd"))
    if os.path.exists(mxd_path):
        os.remove(mxd_path)
    shutil.copy(temp_mxd, mxd_path)
    mxd = arcpy.mapping.MapDocument(mxd_path)
    dataframe = arcpy.mapping.ListDataFrames(mxd)[0]

    #Extract Path and Table Name
    #Check if input is Extract contents from csv and create a temporary table
    filename, file_ext = os.path.splitext(INPUT_TABLE)
    if file_ext == ".csv":
        INPUT_TABLE = csv_to_table(INPUT_TABLE,SCRATCH_GDB)
    TABLE_PATH, TABLE_NAME = InputCheck(INPUT_TABLE) #Extract Path and Table Name

    SELECTED_FIELDS = [fields.strip() for fields in SELECTED_FIELDS.split(";")]
    table_field_info = Extract_Field_Info(TABLE_PATH)
    fields_to_symbolize = list() #

    arcpy.AddMessage("Symbolizing the following fields:")
    for item in SELECTED_FIELDS:
        check = Validate_Field_Type(table_field_info[item], ['Double', 'Float', 'Integer'])
        if check:
            arcpy.AddMessage("..... {}".format(item))
            fields_to_symbolize.append(item)
        else:
            arcpy.AddMessage("The field, '{}', is not a valid data type to symbolize. Removing from list".format(item))

    #User Selected a field to break layers into groups. extract unique values and cycle through each field value
    if GROUP_FIELD:
        group_values = unique_values(TABLE_PATH, GROUP_FIELD) #Store all the unqiue attributes for a given field.
        for value in group_values:
            arcpy.AddMessage("Selecting records from the input table containing, '{}', from the field, {}".format(value, GROUP_FIELD))

            # Export Table from SDE/Main Database to user specified database
            FC_NAME = "Muni_Analysis_{}_{}_{}".format(GROUP_FIELD, value,OUTPUT_MXD_NAME)
            FC_PATH = os.path.join(SCRATCH_GDB,FC_NAME)
            arcpy.AddMessage("Copying the municipality feature class and joining selected table records. Feature class named, {}, can be found at the following path: {}".format(FC_NAME, SCRATCH_GDB))
            Copy_FC(FC_NAME, MUNI_FC, SCRATCH_GDB)

            #Create definition query to filter out records in Table and Join to FC
            whereClause = '''{} = '{}' '''.format(GROUP_FIELD,value)
            Join_Table_to_FC(FC_PATH, TABLE_PATH ,JOIN_FIELD, fields_to_symbolize, whereClause)

            #Create Feature Layer
            Create_FL(FC_NAME,FC_PATH)

            #Add Layers to TOC -> Create group layer -> import symbology
            add_layer_TOC(FC_PATH, dataframe) #This Feature Class will be used to make copies and renamed based on the field that will be symbolized.
            Create_Group_Layer(empty_group_path, value, mxd, dataframe)
            Import_Symbology(FC_NAME, layer_file, mxd, dataframe)

            # Symbolize Fields
            for field in fields_to_symbolize:
                Symbolize_field(FC_NAME, field, value, layer_file, mxd, dataframe, CLASS_BIN, CLASS_VALUES)

            layer_to_remove = arcpy.mapping.ListLayers(mxd, FC_NAME, dataframe)[0]
            arcpy.mapping.RemoveLayer(dataframe,layer_to_remove)

    else:
        # Export Table from SDE/Main Database to user specified database
        FC_NAME = "Muni_Analysis_{}".format(OUTPUT_MXD_NAME)
        FC_PATH = os.path.join(SCRATCH_GDB,FC_NAME)
        arcpy.AddMessage("Copying municipality feature class and joining table. Feature class named, {}, can be found at the following path: {}".format(FC_NAME, SCRATCH_GDB))
        Copy_FC(FC_NAME, MUNI_FC, SCRATCH_GDB)
        Join_Table_to_FC(FC_PATH, TABLE_PATH ,JOIN_FIELD, fields_to_symbolize)

        #Create Feature Layer
        Create_FL(FC_NAME,FC_PATH)
        #Add Layers to TOC -> Create group layer -> import symbology
        add_layer_TOC(FC_PATH, dataframe) #This Feature Class will be used to make copies and renamed based on the field that will be symbolized.
        Create_Group_Layer(empty_group_path, "Record Analysis", mxd, dataframe)
        Import_Symbology(FC_NAME, layer_file, mxd, dataframe)

        for field in fields_to_symbolize:
            Symbolize_field(FC_NAME, field, "Record Analysis", layer_file, CLASS_BIN, mxd, dataframe, CLASS_VALUES)

        layer_to_remove = arcpy.mapping.ListLayers(mxd, FC_NAME, dataframe)[0]
        arcpy.mapping.RemoveLayer(dataframe,layer_to_remove)

    mxd.save()
    arcpy.AddMessage("Saving the mxd, '{}', at the following path: {}".format(OUTPUT_MXD_NAME,GIS_DIR))
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
