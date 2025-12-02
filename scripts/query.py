import os
from lxml import etree
import csv
import re

# top-level variables

src_dir = '../../dimev/data/'
write_dir = '../artefacts/'
ManuscriptsXML = 'Manuscripts.xml'
RecordsXML = 'Records.xml'
namespace = '{http://www.w3.org/XML/1998/namespace}'

def main():
    MStree = etree.parse(src_dir + ManuscriptsXML)
    MSroot = MStree.getroot()

    # Export manuscript shelfmarks as csv
    export_shelfmarks_as_csv(MSroot)

    print('Goodbye')

def export_shelfmarks_as_csv(root):

    # Create container
    data = []
    column_labels = [
            'xml:id', 'location', 'repository', 'shelfmark', 'alt_id'
            ]
    data.append(column_labels)
    csv_file = 'manuscript-shelfmarks.csv'

    for item in root.findall('item'):
        ms_id = item.get(namespace + 'id')
        location = item.find('loc')
        repository = item.find('repos')

        desc = item.find('desc')
        desc_txt = etree.tostring(desc, encoding='unicode', method='text').strip()
        desc_txt = remove_whitespace(desc_txt)

        alt_id_prefixes = ['olim', '(SC']
        complex_value = False
        for prefix in alt_id_prefixes:
            if prefix in desc_txt:
                desc_parts = desc_txt.split(prefix, maxsplit=1)
                shelfmark_txt = desc_parts[0].strip('([ ')
                alt_id_txt = prefix.strip('( ') + ' ' + desc_parts[1].strip(')] ')
                complex_value = True
                break
        if complex_value == False:
            shelfmark_txt = desc_txt
            alt_id_txt = ''
        data_row = [ms_id, location.text, repository.text, shelfmark_txt, alt_id_txt]
        data.append(data_row)

    with open(write_dir + csv_file, 'w', newline='') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerows(data)
    print(f"Manuscript shelfmarks have been written to '{csv_file}'")

def remove_whitespace(text_str):
    text_str = re.sub(' {2,}', ' ', text_str)
    text_str = re.sub(r'\n', '', text_str)
    return text_str

main()
