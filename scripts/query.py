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
    tree = etree.parse(src_dir + RecordsXML)
    root = tree.getroot()

    ## Export manuscript shelfmarks as csv
    #export_shelfmarks_as_csv(MSroot)

    # Export person names
    retrieve_person_names(root)

    print('Goodbye')

def print_to_csv(data, csv_file):
    with open(write_dir + csv_file, 'w', newline='') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerows(data)
    print(f"Data have been written to '{csv_file}'")


def retrieve_person_names(root):
    print('Retrieving person names from Records.xml...')
    data = []
    column_labels = ['firstname', 'lastname', 'suffix']
    data.append(column_labels)
    target_tags = ['author', 'scribe']
    for elem in root.iter():
        if elem.tag in target_tags:
            # retrieve elements
            firstname = elem.find('first')
            lastname = elem.find('last')
            suffix = elem.find('suffix')
            name_parts = [firstname, lastname, suffix]

            # create a container
            new_name = []

            # retrieve text content
            for part in name_parts:
                if part is not None:
                    text = str(part.text)
                    text = clean_text(text)
                else:
                    text = ''
                new_name.append(text)

            # add to list, if not already present

            if new_name in data:
                continue
            else:
                data.append(new_name)

    count = len(data) - 1
    print(f'Found {count} unique names')

    # print to csv
    csv_file = 'person-names.csv'
    print_to_csv(data, csv_file)

def clean_text(string):
    string = re.sub(r'\n', '', string)
    string = re.sub(' +', ' ', string)
    return string

def export_shelfmarks_as_csv(root):

    # Create container
    data = []
    column_labels = [
            'xml:id', 'location', 'repository', 'shelfmark', 'alt_id', 'facsimile'
            ]
    data.append(column_labels)
    csv_file = 'manuscript-shelfmarks.csv'

    for item in root.findall('item'):
        ms_id = item.get(namespace + 'id')
        location = item.find('loc')
        repository = item.find('repos')
        facs_link = get_facs_link(item)

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
        data_row = [ms_id, location.text, repository.text, shelfmark_txt, alt_id_txt, facs_link]
        data.append(data_row)

    # print to csv
    print_to_csv(data, csv_file)

def get_facs_link(item):
    facs_link = ''
    surrogates = item.find('surrogates')
    if surrogates is not None:
        ref = surrogates.find('ref')
        facs_link = ref.get('target')
    return facs_link

def remove_whitespace(text_str):
    text_str = re.sub(' {2,}', ' ', text_str)
    text_str = re.sub(r'\n', '', text_str)
    return text_str

main()
