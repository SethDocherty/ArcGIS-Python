import os
import csv
import sys
import operator
import re
# import arcpy
from os.path import split, join
from string import replace
from collections import defaultdict, OrderedDict


#..............................................................................................................................................
# General Functions

def check_for_letters(input):
    '''
    Check if value contains any letters. Return value contains only alphanumeric characters
    '''
    valids = []
    for character in input:
        if character.isalpha():
            valids.append(character)
    return ''.join(valids)


def check_for_numbers(input):
    '''
    Check if value contains numbers. Return value contains only alphanumeric characters
    '''
    valids = []
    for character in input:
        if character.isdigit():
            valids.append(character)
    return ''.join(valids)


def Extract_File_Records(filename, tuple_list=''):
    '''
    Load a .csv file and that is convereted into a list of tuples
    '''
    fp = open(filename, 'Ur')
    data_list = []
    for line in fp:#reader:
        if not tuple_list:
            data_list.append(tuple(line.strip().split(',')))
        else:
            data_list.append(line.strip().split(','))
    fp.close()
    return data_list


def Extract_input_fields_from_csv(selection_fields, header):
    '''
    TODO
    '''
    input_fields = list()
    field_selection = selection_fields.split(";")
    for field in field_selection:
        if field in header:
            input_fields.append(field)
    if not input_fields:
        # arcpy.AddError("None of the user selected fields to update are in the csv document")
        sys.exit()
    return input_fields


def extract_list_columns(input_list,index_list, tuple_list=''):
    '''
    TODO
    '''
    my_items = operator.itemgetter(*index_list)
    new_list = [my_items(x) for x in input_list]
    if not tuple_list:
        return new_list
    else:
        new_list = [list(item) for item in new_list]
        return new_list


def get_column_index(row_header,fields):
    '''
    Return a dictionary of field names as keys and the mapped column index for the field as the dictionary value.
    '''
    index_list = list()
    for field in fields:
        try:
            index_list.append(row_header.index(field))
        except ValueError:
            # arcpy.AddMessage(("{} does not exist in the header field list. Please make sure field is spelled correctly and in the header row.\n "
            #                 "Exiting script.  Please correct errors and try again.").format(field))
            print ("{} does not exist in the header field list. Please make sure field is spelled correctly and in the header row.\n "
                            "Exiting script.  Please correct errors and try again.").format(field)
            sys.exit()
    return index_list


def header_check(fields_to_check, fields_to_check_against):
    '''
    Check to see if all field names in the list "fields to check" are in the list "fields to check against".
    If any fields are missing, exit the program.
    '''
    missing_header=[]
    for header in fields_to_check:
        if header not in fields_to_check_against:
            missing_header.append(header)
    if len(missing_header) != 0:
        print "The following fields are missing from the input file: ", missing_header
        sys.exit()
    else:
        pass


def keyword_check(string,keylist):
    '''
    Check if a string is present in a key list
    Return True if value is present in list otherwise return False
    '''
    check = set(keylist).intersection(string.split())
    if len(check) == 0:
        return False
    else:
        return True


def list_compare(in_list, comp_list):
    '''
    Check if a list is present in a list of lists. If not, add the item to the list of lists.

    Return value is a list
    '''
    #trigger = False
    #for list in comp_list:
    #    if in_list != list:
    #        trigger = True
    #if trigger == True:
    #    return comp_list.append(in_list)
    #else:
    #    return comp_list
    if in_list not in comp_list:
        return comp_list.append(in_list)
    else:
        return comp_list

#..............................................................................................................................................

#..............................................................................................................................................
# Dictionary Specific Functions

def make_dictionary(row_header,fields):
    '''
    Return a dictionary of field names as keys and the mapped column index for the field as the dictionary value.
    '''
    dic = dict()
    for col_title in fields:
        try:
            dic[ col_title ] = row_header.index(col_title)
        except ValueError:
            pass
    return dic


def count_occurrences(count_field,input_dict):
    """
    Count occurances of value from a dictionary.  Count field represents the dictionary key to look at.
    The return is a dictionary of unique values and how many times they show up.
    The dictionary key = unique value | dictionary value = number of times key occurs.
    """
    count = dict()
    for row in input_dict.keys():
        var = input_dict[row][count_field]
        if var not in count:
            count[var] = 1
        else:
            count[var] = count[var]+1
    #sort dictionary by count: largest -> Smallest
    count = OrderedDict(sorted(count.items(), key = lambda x: x[1], reverse=True))
    return count


def Get_Header_Index(header):
    '''
    Extract the index number for each item in a list.  The input must be a list.
    The return value is a dictionary: key = Header String | value = Header string index
    '''
    header_dict = dict()
    for item in range(len(header)):
        header_dict[header[item]] = item
    return dic


def get_list_nonalphanumeric(field_to_check,input_dict):
    '''
    Check for any non-alphanumeric characters
    '''
    final_list = []
    for row in input_dict.keys():
        var = str(input_dict[row][field_to_check])
        non_numeric = re.findall('\W',var)
        if not non_numeric:
            continue
        for item in non_numeric:
            if item not in final_list and item:
                final_list.append(item)
    return final_list


def get_list_invalid_decimal(field_to_check,input_dict):
    '''
    Find decimal values without non-alphanumeric characters
    '''
    final_list = []
    for row in input_dict.keys():
        var = str(input_dict[row][field_to_check])
        nonNumeric = re.findall('\D+',var)
        nonNumeric = filter(lambda x: x!=".",nonNumeric) #remove decimal from list present
##        decimal_vals = re.findall("\d+\.\d+",var)
        if nonNumeric:
##            for item in nonNumeric:
##                if item not in final_list and item:
##                    final_list.append(item)
            if var not in final_list:
                final_list.append(var)
    return final_list


def get_list_valid_decimal(field_to_check,input_dict):
    '''
    Find decimal values without non-alphanumeric characters
    '''
    final_list = []
    for row in input_dict.keys():
        var = str(input_dict[row][field_to_check])
        nonNumeric = re.findall('\D+',var)
        nonNumeric = filter(lambda x: x!=".",nonNumeric) #remove decimal from list present
        if field_to_check == "Filenumber":
            nonNumeric = filter(lambda x: x!="-",nonNumeric)
        decimal_vals = re.findall("\d+\.\d+",var)
        if decimal_vals and nonNumeric:
            if var not in final_list:
                final_list.append(var)
    return final_list


def make_csv_dict(filepath, key_field='',input_fields=['']):
    '''
    make_csv_dict(filepath, key_field='',input_fields=['']

    Create a dictionary from csv file. User can pick a field to be the main dictionary key and which
    fields to include in the dictionary. Default dictionary key is an integer starting with 0 and default
    fields are all the fields in the csv file.  This function will not account for multiple values
    assigned to a dictionary key.
    '''
    csv_dict = dict()
    inf = csv.DictReader(open(filepath))
    if input_fields:
        valid_fields = input_fields
    else:
        valid_fields = inf.fieldnames
    inf = csv.DictReader(open(filepath))
    if key_field:
        for row in inf:
            dictkey = row[key_field]
            csv_dict[dictkey] = {key:row[key] for key in valid_fields}
    else:
        i = 0
        for row in inf:
            csv_dict[i] = {key:row[key] for key in valid_fields}
            i+=1
    return csv_dict

def WordCount(dictionary):
    '''
    Get a count of words within a string that occur in a dictionary key.  The key is split based on a space and each invidivual word
    in the string is accounted for.

    Required:
        Input dictionary must be in the following format: { String : occurance of that string }
        the value stored to each key must contain an integer for the occurance of that specific string combo.
    '''
    Wordcnt = dict()
    for string, occurance in dictionary.items():
        str_split = string.split()
        for str in str_split:
            if str not in Wordcnt:
                Wordcnt[str] = dict()
                Wordcnt[str] = occurance
            else:
                temp = Wordcnt[str]
                temp += occurance
                Wordcnt[str] = temp
    return Wordcnt
    
#..............................................................................................................................................

# Misc Functions

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

#..............................................................................................................................................


#..............................................................................................................................................
# Export to csv Functions

def export_to_csv_dict(input_dict, header, output_name, output_dir_path):
    '''
    Export a single level dictionary to a .csv

    Required:
        - Input Dictionary
        - Header fields for csv
        - Name of File
        - Output filepath

    *NOTE*
        This function was created to export a single level dictionary to csv. A dictionary that has multiple inner dictionaries will
        store the key and value to a single line.
    '''
    Output_Path = os.path.join(output_dir_path,output_name + ".csv")
    writer = csv.writer(open(Output_Path, 'wb'))
    if type(header) is not type([]):
        writer.writerow([header])
    else:
        writer.writerow(header)
    for key, value in input_dict.items():
       writer.writerow([key, value])


def export_to_csv_list(input_list, header, output_name,output_dir_path):
    '''
    Export a single level list to a .csv

    Required:
        - Input list
        - Header fields for csv
        - Name of File
        - Output filepath

    *NOTE*
        This function was created to export a single level list to csv. A list that has multiple nested lists will
        the nested lists to a single line.
    '''
    Output_Path = os.path.join(output_dir_path,output_name + ".csv")
    writer = csv.writer(open(Output_Path, 'wb'))
    if type(header) is not type([]):
        writer.writerow([header])
    else:
        writer.writerow(header)
    for row in input_list:
        if type(row) is type([]):
            writer.writerow(row)
        else:
            row = [row]
            writer.writerow(row)


def create_schema_file(file_path, gis_field_info, csv_fields):
    '''
    Create schema file based on the field type from a GIS layer.
    Specify the path to where the file will be saved.
    The input GIS paramater must be a list in the following format [Name, Type].
    The input csv fields are based on the input csv file.  Spaces need to be replaced
    with an underscore for proper matching.
    '''
    name=[]
    type=[]
    for a,b in gis_field_info:
        name.append(a)
        if b == 'String':
            type.append('Text')
        elif b == "SmallInteger":
            type.append('Short')
        elif b == "Integer":
            type.append('Long')
        else:
            type.append(b)
    name = schema_header_check(name, csv_fields)
    gis_field_info=zip(name,type)

    directory = os.path.dirname(os.path.normpath(file_path))
    print ("Creating schema.ini file in {}".format(directory))
    # arcpy.AddMessage(("Creating schema.ini file in {}".format(directory)))
    schema = directory + "\schema.ini"

    # Set new schema.ini
    schema_file = open(schema,"w")
    schema_file.write("[" + os.path.basename(os.path.normpath(file_path)) + "]\n")
    #schema_file.write("Format=Delimited(,) .csv"
    schema_file.write("MaxScanRows=0\n")
    x=1
    for name,type in gis_field_info:
        if name.find(" ") > 0:
            schema_file.write("Col{}=".format(x)+'"{}"'.format(name) + " {}\n".format(type))
        else:
            schema_file.write(r"Col{}="'{}'" {}\n".format(x,name,type))
        x += 1

    schema_file.close()


def schema_header_check(fc_header, csv_header):
    revised_name=[]
    for fc_name in fc_header:
        for file_name in csv_header:
            if file_name == fc_name:
                revised_name.append(fc_name)
            else:
                file_name2 = file_name.replace(' ','_')
                if file_name2 == fc_name:
                    revised_name.append(file_name)
    return revised_name

#..............................................................................................................................................