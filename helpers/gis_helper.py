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
# General Arcgis Functions
def buildWhereClause(table, field, value):
    """Constructs a SQL WHERE clause to select rows having the specified value
    within a given field and table (or Feature Class)."""

    # Add DBMS-specific field delimiters
    fieldDelimited = arcpy.AddFieldDelimiters(table, field)

    # Determine field type
    fieldType = arcpy.ListFields(table, field)[0].type

    # Add single-quotes for string field values
    if str(fieldType) == 'String':
        value = "'{}'".format(value)

    # Format WHERE clause
    whereClause = "{} = {}".format(fieldDelimited, value)
    return whereClause


def Add_Records_to_Table(input_list, table_path):
    '''
    Add data from a list to a blank ArcGIS Table.

    Required input:
        Python list
        Path to ArcGIS table

    *Note*
    Table should be empty before adding data to it.
    '''
    input_fields = Extract_Field_Name(table_path)
    if "GLOBALID" in input_fields:
        input_fields.remove('GLOBALID')
    with arcpy.da.InsertCursor(table_path, input_fields) as iCursor:
        for id, row in enumerate(input_list):
            row.insert(0,id)
            try:
                row = [x if x else None for x in row] #TODO Look into adding a continue statement for the else statement.
            except:
                print "Ran in to a Problem adding the following row to the table... {}: Likely an issues with text format i.e. unicode encoding problem. Try fixing the items and run the script again.".format(row)
            iCursor.insertRow(row)

#TODO
def Create_Empty_Table(input_field_info, table_name, path):
    '''
    Create an empty table with from a list of input fields. TODO

    Required input:
        List of field information - [Field Name, Field Type, Field Length] *Must be in this order
        Name of table to be created
        Path of workspace where table will be saved to.
    '''

    tmp_table = os.path.join('in_memory', 'table_template')
    arcpy.management.CreateTable(*os.path.split(tmp_table))
    for field in input_field_info:
        arcpy.AddField_management(tmp_table,field[0], field_type=field[1], field_length=field[2])
    # Create the actual output table.
    try:
        arcpy.CreateTable_management(path, table_name, template=tmp_table)
    except:
        print ("Unable to create table since it already exists at '{}'. "
                "Please close out of the ArcMap and/or ArcCatalog session that may be accessing the table, '{}' "
                "and re-run the script").format(path, table_name)
        arcpy.AddWarning(("Unable to create table since it already exists at '{}'. "
                "Please close out of the ArcMap and/or ArcCatalog session that may be accessing the table, '{}' "
                "and re-run the script").format(path, table_name))
        sys.exit()
    arcpy.Delete_management(tmp_table)


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


def csv_to_table(input_csv, input_fc, scratch_gdb):
    '''
    Don't need input FC
    Don't need field selection
    '''
    # Getting Filepath/name of input csv/fc
    csv_path, csv_name = InputCheck(input_csv)
    fc_path, fc_name = InputCheck(input_fc)

    #Extracting CSV stuff
    csv_list = Extract_File_Records(csv_path,"No")
    header = Space2Underscore(csv_list.pop(0))
    #fields = Extract_input_fields_from_csv(header, header)
    field_index = get_column_index(header,header)
    ##arcpy.AddMessage(field_index) ##TEST
    csv_list = extract_list_columns(csv_list, field_index, "No")

    #Creating blank table and appending csv list
    name = "csv2table_temp"
    header_fieldInfo = get_Data_Type_FromGIS(fields, fc_path)
    Create_Empty_Table(header_fieldInfo, name, scratch_gdb)
    Add_Records_to_Table(csv_list, os.path.join(scratch_gdb, name))
    return os.path.join(scratch_gdb, name)

def does_value_exist(fc,field,value):
    '''
    Search for a value within a field in a Feature Class and return True or False based on its existance.
    '''
    sql = buildWhereClause(fc,field,value)
    with arcpy.da.SearchCursor(fc,[field],where_clause=sql) as cur:
        vals = [row[0] for row in cur]
    if len(vals) == 0:
        return False
    else:
        return True


def Extract_Field_Name(fc):
    '''
    Return a list of fields name from a FC.
    '''
    fields = [f.name for f in arcpy.ListFields(fc)]
    return fields


def Extract_Field_Name_NoneGIS(fc):
    '''
    Return a list of fields name from a FC that does not include ArcGIS standard fields.
    '''
    fields = [f.name for f in arcpy.ListFields(fc)]
    for i,f in enumerate(fields):
        if f == 'Shape' or f == 'Shape_Length' or f == 'OBJECTID' or f == 'GLOBALID':
            del fields[i]
    return fields


def Extract_Field_Info(fc):
    '''
    Extract Field name and Type.
    Return list format: [Name, Type]

    *NOTE*
        - Sort of a replication of gthe function called "get_Data_Type"
    '''
    field_info=[]
    for field in arcpy.ListFields(fc):
        if field.name == 'Shape' or field.name == 'Shape_Length' or field.name == 'OBJECTID' or field.name == 'RID':
            pass
        else:
            item=[]
            item.append(field.name)
            item.append(field.type)
            field_info.append(item)
    return field_info


def Extract_Table_Records(fc,fields=''):
    '''
    Extract records from an ArcMap table.  Return value is a list of lists.  User has the option to specify a lists of fields
    for the return list.

    Requried Inputs:
        Path to Feature class

    Opptional:
        User specified list of fields.

    *Note*
    The inner list was originally a tuple.
    '''
    if not fields:
        fields = Extract_Field_Name(fc)
    records=[]
    with arcpy.da.SearchCursor(fc, fields) as cursor:
        for row in cursor:
            records.append(list(row))
    return records


def FieldExist(FC,field):
    '''
    Check if a field exists in a Feature Class or Table
    '''
    fc_check = arcpy.ListFields(FC, field)
    if len(fc_check) == 1:
      return True
    else:
      return False

def FieldExist_List(fc,input_list):
    '''
    Check if a field from a list exists in a Feature Class or Table.
    '''
    for item in input_list:
        if FieldExist(fc,item):
            return item
    return False


def get_Data_Type_FromGIS(input_fields, path):
    '''
    Return a list of pertinent field information for a list of fields from a user specfied Feature Class or Table.
    The return list contains:
        - Field Name
        - Field Type
        - Field Length

    Requried Inputs:
        List of input fields.
        Path to Feature class or Table

    *NOTE*
    The fields in the list must be present in the feature class or table.
    '''
    allFields = arcpy.ListFields(path)
    # List Formt: [Field Name (0), Field Type (1), Field Length (2)]
    field_info = []
    for field in allFields:
        if field.name in input_fields:
            temp = []
            temp.append(field.name)
            temp.append(field.type)
            temp.append(field.length)
            field_info.append(temp)
    return field_info


def get_Data_Type(fields):
    '''
    Return a list of pertinent field information for a list of fields.  This is intended to be used for lists created from some misc. analysis
    with the intention to export to an ArcGIS table.
    The return list contains:
        - Field Name
        - Field Type
        - Field Length

    Requried Inputs:
        List of input fields

    *NOTE*
    The default field datatype is a String with a length of 255 characters.
    '''
    # List Formt: [Field Name (0), Field Type (1), Field Length (2)]
    field_info = []
    for field in fields:
        temp = []
        temp.append(field)
        temp.append("String")
        temp.append('255')
        field_info.append(temp)
    return field_info


def Get_Database_Path(input_path):
    '''
    Get the database path from input file path. If path does not reside in a
    geodatabase, return False.
    '''
    workspace = arcpy.Describe(input_path)
    if workspace.dataType == "Folder":
        arcpy.AddError("Path does not contain a geodatabase")
        return False
    elif workspace.dataType is not "Workspace":
        return Get_Database_Path(workspace.path)
    else:
        return workspace.catalogPath


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


def is_empty(fc):
    '''
    Check to see if a feature class is empty.  Return True if it is.
    '''
    count = str (arcpy.GetCount_management(FC_INPUTPATH))
    if count1 == "0":
        return True
    else:
        return False


def is_workspace_gdb(input_path):
    '''
    Return True if path is a in a GDB workspace.
    '''
    workspace = arcpy.Describe(input_path)
    if workspace.dataType == "Folder":
        return False
    else:
        return True


def load_csv_into_table(loading_table, input_csv, header, Truncate="NO"):
    '''
    Load a .csv document into a table.  User has the option to trancate the loading table before appending
    data from document

    Default Values:
    Truncate = "NO"
    '''
    if Truncate is "YES":
        arcpy.TruncateTable_management(loading_table)
    table_fields = Extract_Field_Info(loading_table)
    create_schema_file(input_csv, table_fields, header)
    arcpy.Append_management(input_csv, loading_table, "NO_TEST", "", "")


def make_attribute_dict(fc, key_field, attr_list=['*']):
    '''
    Create a dictionary from an from a Feature Class or Table.
    The user specifies what field to use for the main outer dictionary.  Values in this field are used to for the dictionary key.  The values for the outer
    dictionary consist of the subsequent fields names as the inner dictionary key and storing the corresponding values.
    are stored in an inner dictionary with the

    *NOTE*
        - If every record is considered unique, Think about using a field that is unique such as an Object ID.
        - If the field the user specifies has duplicate values ie more than 1 record for a given value, the last
            occurance for that key (value) will be stored. Subsequent records for the key will be overwritten.
    '''
    attdict = {}
    fc_field_objects = arcpy.ListFields(fc)
    fc_fields = [field.name for field in fc_field_objects if field.type != 'Geometry']
    if attr_list == ['*']:
        valid_fields = fc_fields
    else:
        valid_fields = [field for field in attr_list if field in fc_fields]
    #Ensure that key_field is always the first field in the field list
    cursor_fields = [key_field] + list(set(valid_fields) - set([key_field]))
    with arcpy.da.SearchCursor(fc, cursor_fields) as cursor:
        for row in cursor:
            attdict[row[0]] = dict(zip(cursor.fields,row))
    return attdict


def unique_values(fc,field):
    '''
    Return a list of unique values from a user spcified field in a feature class or table.
    '''
    with arcpy.da.SearchCursor(fc,[field])as cur:
        return sorted({row[0] for row in cur})


#..............................................................................................................................................
# Parcel Analysis Functions

def get_index(county_field, muni_field, muni_coded_val, header_fields):
    '''
    Get the index values of the of the three parcel specific fields from a header field.
    The return value is a list of integers of index values for the three specified fields.
    '''
    ref_fields = [county_field, muni_field, muni_coded_val]
    #get index value for the fc header fields
    ref_fields = make_dictionary(header_fields,ref_fields)
    index = ref_fields.values()
    return index


def Get_Municipality_Dict():
    '''
    Return a dictionary of counties.  The dictionary values is a dictionary of municipalities which stores the
    municipality code. This dictionary is intended to be used when you need to call a list of municipalities for a given county.
    '''
    #Getting input parameters
    (muni_fc, county_field, muni_field, muni_coded_val) = Static_Inputs()

    # Extract the header fields and records from the municipality fc
    muni_rows_header = Extract_Field_Name(muni_fc)
    muni_rows = Extract_Table_Records(muni_fc)
    (county_field_index, muni_field_index, muni_coded_val_index) = get_index(county_field,muni_field,muni_coded_val,muni_rows_header)
    county_names = Get_County_List()

    #Create dictionary of Counties with a dictionary of municipalities that stores the municipality code as a value.
    county_mun_dict = dict()
    for county_name in county_names:
        if county_name not in county_mun_dict:
            county_mun_dict[str(county_name)] = dict()
        for muni in muni_rows:
            if muni[county_field_index] == county_name:
                if muni[muni_field_index] not in county_mun_dict[county_name]:
                    county_mun_dict[county_name][muni[muni_field_index]] = muni[muni_coded_val_index]

    return county_mun_dict

def Get_Municipality_List():
    '''
    Return a list of municipalities
    '''
    (muni_fc, county_field, muni_field, muni_coded_val) = Static_Inputs()
    #populate a list of unique county names
    municipality_names = unique_values(muni_fc,muni_field)
    return municipality_names


def Get_County_List():
    '''
    Return a list of counties
    '''
    (muni_fc, county_field, muni_field, muni_coded_val) = Static_Inputs()
    #populate a list of unique county names
    county_names = unique_values(muni_fc,county_field)
    return county_names


def validate_row(row):
    """
    This function test's values stored in a adictionary of parcel specific information to ensure they are valid.
    The following keys are analyzed:
    - Filenumber
    - BLOCK
    - LOT
    - MUNID

    If any of the values are invalid, a False statement is returned.
    """
    #test for all cases
    valitidy = 0

    #check for valid file number
    var = row["Filenumber"]
    invalid_chr = re.findall("\D+",var)
    invalid_chr = filter(lambda x: x!=".",invalid_chr) #remove decimal from list
    invalid_chr = filter(lambda x: x!="-",invalid_chr) #remove dash from list
    if invalid_chr: #check to see if list is empty. If so, there are no invalid characters
       valitidy +=1 # continuevalid_file_num = re.findall("\d+\-\d+\-\d+\.\d+",var)

    #check for valid block values
    var = row["BLOCK"]
    invalid_chr = re.findall("\D+",var)
    invalid_chr = filter(lambda x: x!=".",invalid_chr) #remove decimal from list
    if invalid_chr: #check to see if list is empty. If so, there are no invalid characters
       valitidy +=1 # continuevalid_file_num = re.findall("\d+\-\d+\-\d+\.\d+",var)

    #check for valid lot values
    var = row["LOT"]
    invalid_chr = re.findall("\D+",var)
    invalid_chr = filter(lambda x: x!=".",invalid_chr) #remove decimal from list
    if invalid_chr: #check to see if list is empty. If so, there are no invalid characters
       valitidy +=1 # continuevalid_file_num = re.findall("\d+\-\d+\-\d+\.\d+",var)

    #Check for valid mun id
    var = row["MUNID"]
    if var == 0 or not var:
        valitidy +=1

    if valitidy == 0:
        return row
    else:
        return False


def validity_check(input_dict):
    valid_records = []
    invalid_records = []
    for key, row in input_dict.items():
        row = create_pams_pinANDmuncode(row)
        if validate_row(row):
            temp = []
            for item in row.values():
                temp.append(item)
            valid_records.append(temp)
        else:
            temp = []
            for item in row.values():
                temp.append(item)
            invalid_records.append(temp)
    #Create Header List
    header_fields = []
    for key in input_dict[1].keys():
        header_fields.append(key)

    return valid_records,invalid_records,header_fields

def municipality_dict_storage(*values):
    municipality_dict_storage.values = values or municipality_dict_storage.values
    return municipality_dict_storage.values


def create_pams_pinANDmuncode(input_row):
    '''
    Add a PAMS PIN and MUNCODE dictionary item and return dictionary.

    Required:
        - Input must be a dictionary that has the following keys:
            ~ BLOCK
            ~ LOT
            ~ MUNID

    '''
    Municipality_GIS, Municipality_Table = municipality_dict_storage()
    block = input_row["BLOCK"]
    lot = input_row["LOT"]
    munid = str(int(input_row["MUNID"]))
    county,municipality = [val for val in Municipality_Table[munid].values()]
    try:
        mun_code = str(Municipality_GIS[county][municipality])
        input_row["MUNCODE"] = mun_code
        input_row["PAMS_PIN"] = "{}_{}_{}".format(mun_code, block, lot)
    except:
        #print "Skipping - Municipality: {} does not exist..........".format(municipality)
        input_row["MUNCODE"] = "NULL"
        input_row["PAMS_PIN"] = "NULL"
    return input_row


def create_pams_pin(input_row):
    '''
    Add a PAMS PIN  dictionary item and return dictionary.

    Required:
        - Input must be a dictionary that has the following keys:
            ~ BLOCK
            ~ LOT
            ~ MUNID

    '''
    block = input_row["BLOCK"]
    lot = input_row["LOT"]
    munid = str(int(input_row["MUNID"]))
    try:
        input_row["PAMS_PIN"] = "{}_{}_{}".format(munid, block, lot)
    except:
        #print "Skipping - Municipality: {} does not exist..........".format(municipality)
        input_row["PAMS_PIN"] = "NULL"
    return input_row

#..............................................................................................................................................
