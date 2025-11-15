# This script loads two partially redundant data files and checks one against
# the other. It reports manuscript sources included in MSSIndex.xml but not
# Manuscripts.xml.

# TODO: Write the complementary check, for manuscripts sources in
# Manuscripts.xml but not MSSIndex.xml

import os
import xmltodict

src_dir = '../../dimev/data/'
file1 = 'Manuscripts.xml'
file2 = 'MSSIndex.xml'
source1 = src_dir + file1
source2 = src_dir + file2

def read_xml_to_dict(source):
    print(f'Reading source file `{source}` to string...')
    with open(source) as f:
        xml_string = f.read()
    print('Parsing string as a Python dictionary...')
    xml_dict = xmltodict.parse(xml_string)
    return xml_dict

def cross_check(mss, mssIndex):
    errors = 0
    checks = 0
    print(f'Checking keys in {file2}...')
    for idx in range(len(mssIndex)):
        if mssIndex[idx]['@key'] != 'Location Unknown':
            settlement = mssIndex[idx]['repos']
            if type(settlement) == dict: # settlement with one repository
                node = settlement['item']
                checks, errors = get_keys_at_repo(node, checks, errors)
            elif type(settlement) == list: # settlements with multiple repositories
                for idx in range(len(settlement)):
                    node = settlement[idx]['item']
                    checks, errors = get_keys_at_repo(node, checks, errors)
    print(f'Checked {checks} manuscript keys')
    print(f'Checks concluded with {errors} errors')

def get_keys_at_repo(node, checks, errors):
    if type(node) == dict:
        key = node['@xml:id']
        errors = count_keys(key, errors)
        checks += 1
    elif type(node) == list: # repositories with multiple items
        for idx in range(len(node)):
            key = node[idx]['@xml:id']
            errors = count_keys(key, errors)
            checks += 1
    return checks, errors

def count_keys(key, errors):
    count = 0
    for idx in range(len(mss)):
        if mss[idx]['@xml:id'] == key:
            count += 1
    if count == 0:
        print(f'WARNING: key {key} not found!')
        errors += 1
    elif count > 1:
        print(f'WARNING: {file1} has multiple entries for key {key}!')
        errors += 1
    return errors

# read first source file to dictionary
file = source1
Manuscripts_dict = read_xml_to_dict(file)
mss = Manuscripts_dict['mss']['item'] # strip outer keys

# read second source file to dictionary
file = source2
MSSIndex_dict = read_xml_to_dict(file)
mssIndex = MSSIndex_dict['records']['loc'] # strip outer keys

# Check Manuscripts.xml against MSSIndex.xml
print('Verifing `MSSIndex.xml` against `Manuscripts.xml`...')
cross_check(mss, mssIndex)

print('\nWARNING: The verification just run was unidirectional. Further checks to come.')
