# This Python script creates a controlled vocabulary from csv input

import os
import csv
from lxml import etree

# Root variables

data_dir = '../artefacts/'
csv_source = 'form-terms.csv'

output_dir = '../../dimev/data/'

def process_str(raw_string):
    term_list = []
    if raw_string != 'DELETE':
        if ';' in raw_string:
            term_list = raw_string.split(';')
        else:
            term_list.append(raw_string)
    return term_list

def process_raw_list(raw_list):
    terms = set()
    for item in raw_list:
        if item['new term'] == '':
            # Add unmodified term
            terms.add(item['term'])
        else:
            # Get modified terms from 'new term'
            term_list = process_str(item['new term'])
            for term in term_list:
                terms.add(term.strip())
    return terms

# Create a list of valid terms
path = data_dir + csv_source
raw_list = []
with open(path, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        raw_list.append(row)
terms = process_raw_list(raw_list)

# Add terms not in the CSV source
new_terms = [
        'prose, according to NIMEV',
        'ballade',
        'virelai'
        ]
for item in new_terms:
    terms.add(item)

terms = sorted(terms, key=str.lower)

# Create XML root and label

root = etree.Element('list')
head = etree.Element('head')
head.text = 'Verse form terms'
root.append(head)

# Serialize the terms as XML elements

for term in terms:
    item_elem = etree.Element('item')
    term_elem = etree.Element('term')
    term_elem.text = term
    item_elem.append(term_elem)
    root.append(item_elem)

# Create an ElementTree and write to file

tree = etree.ElementTree(root)
path = output_dir + 'form-terms.xml'

etree.indent(tree, space="    ", level=0)
tree.write(path, pretty_print=True, xml_declaration=True, encoding='UTF-8')

print('Done')
