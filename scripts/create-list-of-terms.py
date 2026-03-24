# This Python script creates a controlled vocabulary from csv input

import os
import csv
from lxml import etree

# Root variables

data_dir = '../artefacts/'
csv_source = 'subject-categories.csv'

output_dir = '../../dimev/data/'


# Create a list of subject-terms
subjects = []
path = data_dir + csv_source
with open(path, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        subjects.append(row['subject'])

# Create a XML tree

root = etree.Element('list')
head = etree.Element('head')
head.text = 'Subject terms'
root.append(head)

# Serialize the subject terms as list items

for term in subjects:
    item_elem = etree.Element('item')
    term_elem = etree.Element('term')
    term_elem.text = term
    item_elem.append(term_elem)
    root.append(item_elem)

# Create an ElementTree and write to file

tree = etree.ElementTree(root)
path = output_dir + 'subject-terms.xml'

etree.indent(tree, space="    ", level=0)
tree.write(path, pretty_print=True, xml_declaration=True, encoding='UTF-8')

print('Done')
