# This script extracts a small sample of source records from Manuscripts.xml
# and transforms them into individual YAML files with consistent data
# structure. The element `msDesc` is modeled loosely and very selectively on
# the TEI module for manuscript description.

# TODO: Allow for transformed data to be written to `../docs/_sources`

import os
import xmltodict
import re
import yaml
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

src_dir = '../DIMEV_XML/'
file1 = 'Manuscripts.xml'
file2 = 'MSSIndex.xml'
source1 = src_dir + file1
source2 = src_dir + file2
destination = '../docs/_sources/'
test_sample = ['BodDou384', 'CULFf548', 'BLHar541', 'BLHar1304', 'Lam853']
test_ms = 'Chicago36'

target = \
    {
        'source_key': '',
        'source_type': '',
        'msDesc': {
            'msIdentifier': {
                'settlement': '',
                'repository': '',
                'idno': '',
                'altIdentifier': []
            },
            'head': '',
            'additional': {
                'surrogates': [],
                'listBibl': []
            },
        },
        'count': '',
        'note': ''
    }

def read_xml_to_dict(xml_source):
    print(f'Reading `{xml_source}` to string...')
    with open(xml_source) as f:
        xml_string = f.read()
    print('Parsing string as a Python dictionary...')
    xml_dict = xmltodict.parse(xml_string)
    return xml_dict

def get_valid_input(prompt, options):
    while True:
        choice = input(prompt).lower()
        if choice in options:
            return choice
        prompt = "Invalid selection. Try again. "

def get_item(source_id):
    new_record = target
    for idx in range(len(mss)):
        if '@xml:id' in mss[idx]:
            if mss[idx]['@xml:id'] == source_id:
                ms = mss[idx]
                new_record['source_key'] = ms.pop('@xml:id')
                if xml_source == source1 or xml_source == source2:
                    new_record['source_type'] = 'manuscript'
                new_record['msDesc']['msIdentifier']['settlement'] = ms.pop('loc')
                new_record['msDesc']['msIdentifier']['repository'] = ms.pop('repos')
                idno, altIdentifier = split_shelfmark(ms['desc'])
                new_record['msDesc']['msIdentifier']['idno'] = idno
                new_record['msDesc']['msIdentifier']['altIdentifier'] = altIdentifier
                new_record['msDesc']['head'] = ''
                new_record['msDesc']['additional']['surrogates'] = []
                new_record['msDesc']['additional']['listBibl'] = []
                new_record['note'] = ''
                return new_record

def split_shelfmark(dimevDesc):
    if '[' in dimevDesc:
        idno = re.sub(' \[.*$', '', dimevDesc)
        altIdentifier = re.sub('^.*\[', '', dimevDesc)
        altIdentifier = re.sub('\]', '', altIdentifier)
        altIdentifier.split(',')
    else:
        idno = dimevDesc
        altIdentifier = []
    return idno, altIdentifier

def yaml_dump(new_record):
    yml_out = yaml.dump(new_record, sort_keys=False, allow_unicode=True)
    print('---')
    print(yml_out)
    print('---')

# read first source file to dictionary
xml_source = source1
Manuscripts_dict = read_xml_to_dict(xml_source)
mss = Manuscripts_dict['mss']['item'] # strip outer keys

# define job
print(f'''
Select conversion from the options below:
   (1) Convert `{test_ms}` (Default)
   (2) Convert the test sample
   (3) Convert nothing (exit)''')
prompt= 'Selection: '
options = ['1', '2', '3', '']
job = get_valid_input(prompt, options)
print()

# identify item(s) and run conversion(s)
if job == '2': # this isn't working
    for ms in test_sample:
        new_record = get_item(ms)
        yaml_dump(new_record)
elif job != '3':
    new_record = get_item(test_ms)
    yaml_dump(new_record)

print('\nGoodbye')
