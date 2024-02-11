# This script walks a transect through item records in Records.xml, from the
# top-level down to witness keys. Unexpected data types and structures are
# reported.  The script then counts documentary witnesses bearing each verse
# item and verse items in each documentary witness.

import os
import xmltodict
import re

source = '../DIMEV_XML/Records.xml'

def read_xml_to_string(source):
    print(f'Reading source file `{source}` to string...')
    with open(source) as f:
        xml_string = f.read()
    print('Preprocessing string...')
    xml_string = re.sub(' {2,}', ' ', xml_string) # remove whitespace
    xml_string = re.sub('\\n', '', xml_string) # remove newlines
    xml_string = re.sub('<lb/>', '\\n    ', xml_string) # replace <lb/> elements with newlines and spaced indent
    xml_string = re.sub('<sup>', 'BEGIN_SUP', xml_string) # replace <sup> tags
    xml_string = re.sub('</sup>', 'END_SUP', xml_string)
    xml_string = re.sub('<i>', 'BEGIN_ITALICS', xml_string)  # replace <i> tags
    xml_string = re.sub('</i>', 'END_ITALICS', xml_string)
    xml_string = re.sub(r'<ref xml:target="([\.0-9]+)" *>[0-9]+</ref>', 'DIMEV_' + r'\1', xml_string)
#    xml_string = re.sub(r'<mss key="([A-Za-z0-9]+)"/>', 'MS_' + r'\1', xml_string) # This substitution disrupts rendering of <ghost>
    return xml_string

def xml_to_dict(xml_string):
    print('Parsing string as a Python dictionary...')
    xml_dict = xmltodict.parse(xml_string)
    items = xml_dict['records']['record'] # strip outer keys
    return items

def create_ms_index(wit_id, dimev_id, ms_index):
    if wit_id in ms_index.keys():
        item_list = ms_index[wit_id]
        item_list.append(dimev_id)
        ms_index[wit_id] = item_list
    else:
        ms_index[wit_id] = [dimev_id]
    return ms_index

# read the source file to string and pre-process
xml_string = read_xml_to_string(source)

# create a dictionary
items = xml_to_dict(xml_string)

# create empty variables and assign data types
ms_index = {}
checks = 0
missing_witnesses = 0
item_not_dict = 0
no_id = 0
witnesses_not_dict = 0
witnesses_without_child = 0
witnesses_without_key = 0
child_is_dict = 0
child_is_list = 0
witness_counts = list()

for idx in range(len(items)):
    item = items[idx]
    if type(item) != dict:
        print("\nWARNING: Unexpected data type. <record> is not a dictionary. Printing...")
        print("\t", item)
        item_not_dict += 1
    else:
        if '@xml:id' not in item:
            no_id += 1
        else:
            dimevID = item['@xml:id']
            if 'witnesses' not in item:
                print(f"\nWARNING: Unexpected data structure. <record> {dimevID} has no element <witnesses>. Printing <record>...")
                print("\t", item)
                missing_witnesses += 1
            else:
                if type(item['witnesses']) != dict:
                    print(f"\nWARNING: Unexpected data type. The element <witnesses> in <record> {dimevID} is not a dictionary. Printing <witnesses>...")
                    print("\t", item['witnesses'])
                    witnesses_not_dict += 1
                else:
                    if 'witness' not in item['witnesses']:
                        print(f"\nWARNING: Unexpected data structure. The element <witnesses> in <record> {dimevID} has no child <witness>. Printing <witnesses>...")
                        print("\t", item['witnesses'])
                        witnesses_without_child += 1
                    else:
                        witnesses = item['witnesses']['witness']
                        if type(witnesses) == dict:
                            wit_id = witnesses['source']['@key']
                            mx_index = create_ms_index(wit_id, dimevID, ms_index)
                            child_is_dict += 1
                            witness_counts.append(1)
                            checks += 1
                        else:
                            if type(witnesses) == list:
                                child_is_list += 1
                                wit_count = len(witnesses)
                                witness_counts.append(wit_count)
                                for idx in range(wit_count):
                                    wit_id = witnesses[idx]['source']['@key']
                                    ms_index = create_ms_index(wit_id, dimevID, ms_index)
                                    checks += 1

print('\nSUMMARY REPORT:\n')
print('Total items: ', len(items))
print('Total items of type non-dictionary: ', item_not_dict)
print('Total items of type dictionary without xml:id: ', no_id)
print('Total items with xml:id but no element <witnesses>: ', missing_witnesses)
print('Total items with element <witnesses> of type other than dictionary: ', witnesses_not_dict)
print('Total items with element <witnesses> of type dictionary but without child-element <witness>: ', witnesses_without_child)
print('Total items with child-element <witness> of type dictionary: ', child_is_dict)
print('Total items with child-element <witness> of type list: ', child_is_list)
partials = item_not_dict + no_id + missing_witnesses + witnesses_not_dict + witnesses_without_child + child_is_dict + child_is_list
print('Do the numbers add up?', len(items) == partials)
print()
print('Total unique item-instances (excluding data errors): ', checks)
print('Total number of source keys found: ', len(ms_index))

count_of_items_by_document = {}
source_keys = list(ms_index.keys())
item_counts = list()
for idx in range(len(ms_index)):
    key = source_keys[idx]
    count = len(ms_index[key])
    count_of_items_by_document[key] = count
    item_counts.append(count)

item_counts.sort()
count_documents_with_n_items = dict()
for idx in range(len(item_counts)):
    if str(item_counts[idx]) in count_documents_with_n_items.keys():
        count_documents_with_n_items[str(item_counts[idx])] += 1
    else:
        count_documents_with_n_items[str(item_counts[idx])] = 1

print("\nDocuments with n recorded dimev items:")
print(count_documents_with_n_items)

witness_counts.sort()
count_items_with_n_witnesses = dict()
for idx in range(len(witness_counts)):
    if str(witness_counts[idx]) in count_items_with_n_witnesses.keys():
        count_items_with_n_witnesses[str(witness_counts[idx])] += 1
    else:
        count_items_with_n_witnesses[str(witness_counts[idx])] = 1


print("\nDIMEV items with n recorded witnesses:")
print(count_items_with_n_witnesses)
