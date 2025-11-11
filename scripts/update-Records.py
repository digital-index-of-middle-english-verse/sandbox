from lxml import etree
import csv
import copy
import os
import re

# Top-level variables

source_file = '../../dimev/data/Records.xml'
mec_source = '../../external-resources/MEC/bib_all.xml'
subject_categories_csv = '../artefacts/subject-categories.csv'
subject_crosswalk_csv = '../artefacts/subjects.csv'
namespace = '{http://www.w3.org/XML/1998/namespace}'

# Variables for atomization
#output_dir = '../../dimev/data/records'
#cross_ref_output_file = os.path.join(output_dir, 'cross_references.xml')

def main():
    tree = etree.parse(source_file)
    root = tree.getroot()  # root element <records>

    # Create repertories and populate with IMEV, NIMEV, and Ringler
    root = extract_imev_etc(root)

    # Add ME Compendium as repertory
    root = add_mec_refs(root)

    # Update subjects
    root = update_subjects(root)

    # Move formal terms misplaced in subjects
    root = move_misplaced_form_terms(root)

    print('All transformations complete')
    etree.indent(tree, space="    ", level=0)
    tree.write(source_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print(f'Wrote the revised tree to {source_file}')

def process_mec(mec_source):
    tree = etree.parse(mec_source)
    mec_root = tree.getroot()
    mec_to_dimev_xwalk = []
    for entry in mec_root.findall('ENTRY'):
        mec_id = entry.get('ID')
        xwalk_item = (mec_id, [])
        dimev_refs = entry.findall('INDEXC')
        for ref in dimev_refs:
            xwalk_item[1].append(ref.text)
        if len(xwalk_item[1]) > 0:
            mec_to_dimev_xwalk.append(xwalk_item)
    return mec_to_dimev_xwalk

def add_mec_refs(root):
    print('Creating Middle English Compendium-to-DIMEV crosswalk...')
    mec_to_dimev_xwalk = process_mec(mec_source)
    print('Adding references to Middle English Compendium Bibliography as repertory...')
    for record in root.findall('record'):
        dimev_id = record.get(namespace + 'id')
        if dimev_id is not None:
            dimev_id = re.sub('record-', '', dimev_id)
            for item in mec_to_dimev_xwalk:
                if dimev_id in item[1]:
                    new_repertory = etree.Element('repertory', key='MECompendium')
                    new_repertory.text = item[0]
                    record = add_repertory(record, new_repertory)
    print('Done')
    return root

def update_subjects(root):
    print('Updating subject terms...')
    print('Creating crosswalk from current subject terms to revised subject terms...')
    deleted_subjects, subject_crosswalk = create_subject_crosswalk(subject_crosswalk_csv)
    print('Implementing the crosswalk...')
    for record in root.findall('record'):
        new_subjects = etree.Element('subjects')
        old_subjects_element = record.find('subjects')
        if old_subjects_element is not None:
            subjects_index = record.index(old_subjects_element)
            for child in old_subjects_element:
                if child.text is not None:
                    # concatinate child.text to string, stripping inline formatting elements
                    old_term = etree.tostring(child, encoding='unicode', method='text')
                    # process string
                    old_term = re.sub(r'\n', '', old_term) # strip newlines
                    old_term = re.sub('  +', ' ', old_term) # strip internal runs of space characters
                    old_term = old_term.strip()
                    term_found = False # watch for unmatched terms
                    if old_term in deleted_subjects: # do nothing
                        term_found = True
                    else:
                        for item in subject_crosswalk:
                            if old_term == item[0]:
                                new_subject_list = item[1]
                                for subject_term in new_subject_list:
                                    new_subjects = add_unique_terms(new_subjects, 'subject', subject_term)
                                term_found = True
                                break
                    if term_found == False:
                        print(f'WARNING: subject term "{old_term}" not found in cross-walk')
            record.insert(subjects_index, new_subjects)
            record.remove(old_subjects_element)
    print('Done')
    return root

def move_misplaced_form_terms(root):
    print('Moving formal terms misplaced as subject terms...')
    list_of_formal_terms = get_formal_terms_misplaced_as_subjects(subject_categories_csv)
    for record in root.findall('record'):
        new_subjects = etree.Element('subjects')
        old_subjects_element = record.find('subjects')
        if old_subjects_element is not None:
            subjects_index = record.index(old_subjects_element)
            for child in old_subjects_element:
                if child.text in list_of_formal_terms:
                    record = update_forms(record, child.text)
                else:
                    new_subjects.append(child)
            record.insert(subjects_index, new_subjects)
            record.remove(old_subjects_element)
    print('Done')
    return root

def update_forms(record, form_term):
    formal_terms_to_rewrite_as_singular = ['ballads', 'carols', 'roundels', 'virelais']
    if form_term in formal_terms_to_rewrite_as_singular:
        form_term = re.sub('s$', '', form_term)
    new_forms_element = etree.Element('verseForms')
    old_forms_element = record.find('verseForms')
    if old_forms_element is None:
        index = record.index(record.find('subjects')) + 1
        new_forms_element = add_unique_terms(new_forms_element, 'verseForm', form_term)
        record.insert(index, new_forms_element)
    else:
        index = record.index(old_forms_element)
        for child in old_forms_element:
            if child.text is None:
                continue
            else:
                new_forms_element = add_unique_terms(new_forms_element, 'verseForm', child.text)
        new_forms_element = add_unique_terms(new_forms_element, 'verseForm', form_term)
        record.insert(index, new_forms_element)
        record.remove(old_forms_element)
    return record

def add_unique_terms(parent, tag, term):
    term_list = []
    if len(parent):
        for child in parent:
            term_list.append(child.text)
    if term not in term_list:
        child_element = etree.Element(tag)
        child_element.text = term
        parent.append(child_element)
    return parent

def create_subject_crosswalk(source_file):
    list_of_dict = load_csv_to_list_of_dict(source_file)
    deleted_subjects = set()
    subject_crosswalk = []
    for item in list_of_dict:
        current_subject_term = re.sub('’|‘', '\'', item['subject']) # replace curly apostrophes/single quotes to match current character encoding in Records.xml
        if item['new subjects'] == 'DELETE':
            deleted_subjects.add(current_subject_term)
        else:
            if item['new subjects'] == '':
                crosswalk_tuple = (current_subject_term, [current_subject_term])
            else:
                crosswalk_tuple = (current_subject_term, [])
                subject_string = re.sub('’|‘', '\'', item['new subjects']) # replace any curly apostrophes/single quotes
                subject_list = subject_string.split("; ")
                for new_subject_term in subject_list:
                    crosswalk_tuple[1].append(new_subject_term)
            subject_crosswalk.append(crosswalk_tuple)
    return deleted_subjects, subject_crosswalk

def get_formal_terms_misplaced_as_subjects(source_file):
    formal_terms_misplaced = []
    subject_categories = load_csv_to_list_of_dict(source_file)
    for item in subject_categories:
        if item['category'] == 'form':
            formal_terms_misplaced.append(item['subject'])
    formal_terms_misplaced.sort()
    print(f'Found misplaced formal terms {", ".join(formal_terms_misplaced)}')
    return formal_terms_misplaced

def load_csv_to_list_of_dict(file_path):
    list_of_dict = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            list_of_dict.append(row)
    return list_of_dict

def remove_alpha(record):
    # Remove the <alpha> child element if it exists.
    alpha = record.find('alpha')
    if alpha is not None:
        record.remove(alpha)
    return record

def extract_imev_etc(root):
    print('Extracting NIMEV and IMEV references to child element repertories...')
    for record in root.findall('record'):
        # @imev and @nimev values that map to no repertory
        junk_values = {'', 'n', 'C16', 'C 19', 'delete', 'delete C16', 'delete: C16', 'delete: prose', 'Dubar', 'Dunbar (?)', 'Dunbar', 'not ME', 'Old English', 'post-1500', 'post medieval', 'post-medieval', 'prose', 'Skelton'}
        dimev_id = record.get(namespace + 'id')
        if 'imev' in record.attrib:
            value = record.attrib.pop('imev').strip()
            if value not in junk_values:
                validate_numeric(value, dimev_id)
                if '.' in value: # Decimals are new in the Supplement
                    repertory = etree.Element('repertory', key='Robbins1965b')
                else:
                    repertory = etree.Element('repertory', key='Brown1943')
                repertory.text = value
                record = add_repertory(record, repertory)
        if 'nimev' in record.attrib:
            value = record.attrib.pop('nimev').strip()
            if value not in junk_values:

                # The 'nimev' attribute has been used inconsistently, for reference
                # to three different 'repertories'. Most values of 'nimev' are
                # references 'NIMEV', but some are references to Ringler1992,
                # others are to Ringer1988 (I refer to the xml:ids of items in
                # Bibliography.xml), and others reference both Ringler's volumes.
                # The double references are delimited by a pipe character.

                if '|' in value:
                    reference_list = re.split(r'\|', value)
                    for string in reference_list:
                        if string.strip() not in junk_values:
                            if 'TM' in string: # 'TM' is Ringler1992
                                attr = 'Ringler1992'
                                value = re.sub('TM', '', string).strip()
                            elif 'TP' in string: # 'TP' is Ringler 1988
                                attr = 'Ringler1988'
                                value = re.sub('TP', '', string).strip()
                            else:
                                attr = 'NIMEV' # the corresponding key in Bibliography.XML is all uppercase
                                value = string.strip()
                            validate_numeric(value, dimev_id)
                            repertory = etree.Element('repertory', key=attr)
                            repertory.text = value
                            record = add_repertory(record, repertory)
                else:
                    if 'TM' in value:
                        attr = 'Ringler1992'
                        value = re.sub('TM', '', value).strip()
                    elif 'TP' in value:
                        attr = 'Ringler1988'
                        value = re.sub('TP', '', value).strip()
                    else:
                        attr = 'NIMEV'
                    validate_numeric(value, dimev_id)
                    repertory = etree.Element('repertory', key=attr)
                    repertory.text = value
                    record = add_repertory(record, repertory)
    print('Done')
    return root

def add_repertory(record, new_repertory):
    repertories = record.find('repertories')
    alpha = record.find('alpha')

    # Create the element 'repertories' if it does not exist
    if repertories is None:
        repertories = etree.Element('repertories')
        index = record.index(alpha) + 1
        record.insert(index, repertories)

    # Test whether new_repertory already exists
    found_identical = False
    if len(repertories):
        target_text = new_repertory.text
        target_key = new_repertory.get('key')
        for child in repertories:
            if child.text == target_text and child.get('key') == target_key:
                found_identical = True
                break

    # Add the child element 'new_repertory' if it does not already exist
    if found_identical == False:
        repertories.append(new_repertory)
    return record

def validate_numeric(value, dimev_id):
    value = re.sub('^see ', '', value) # Treat "see" as acceptable non-numeric prefix
    if not re.match(r'\d+(\.\d+)?(/\d+)?$', value): # Refs to NIMEV witnesses use fwd slash as delimiter
        print(f'WARNING: attrib. "imev"/"nimev" in {dimev_id} has unexpected value "{value}"')

def create_output_dir(output_dir):
    if not os.path.exists(output_dir):
        os.makedir(output_dir)

def atomize_records():
    # Iterate over each 'record' element in the original tree
    record_count = 0
    cross_ref_count = 0
    cross_refs = etree.Element('records') # Create a new root for cross-references
    for record in root.findall('record'):
    
        # If the <record> element has no child-element <witnesses>, the <record>
        # element is a cross-reference. These are handled differently from 'full'
        # record elements, per Documentation 2.2.1 and 2.2.3.  NOTE: I'm unsure
        # whether the deepcopy is necessary.
    
        if record.find('witnesses') is None:
            new_record = process_record(copy.deepcopy(record))
            cross_refs.append(new_record)
            cross_ref_count += 1
        else:
            # Retrieve the xml:id attribute.
            xml_id = record.get(namespace + 'id')
            if xml_id is None:
                print("Record without xml:id, skipping.")
                continue
            else:
                # Create a new tree containing a deep copy of the current record.
                # Again, I'm unsure whether the deepcopy is needed.
                new_record = process_record(copy.deepcopy(record))
                new_tree = etree.ElementTree(new_record)
                # Construct a file name using the xml:id attribute.
                formatted_id = format_id(xml_id)
                file_name = os.path.join(output_dir, f"{formatted_id}.xml")
                # Write the new tree to a file.
                new_tree.write(file_name, pretty_print=True, xml_declaration=True, encoding='UTF-8')
            record_count += 1
    
    print(f'Wrote {record_count} full records to {output_dir}')
    
    # Create a new ElementTree for the cross references and write to a file.
    new_tree = etree.ElementTree(cross_refs)
    new_tree.write(cross_ref_output_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print(f"Wrote {cross_ref_count} cross references to {cross_ref_output_file}")

def format_id(xml_id):
    # DIMEV ids are numerals in the range 1-6889, with two optional decimal
    # spaces. To create good unique file names I move the decimal point two
    # places to the right (for integer representation) and pad with leading
    # zeros.
    xml_id = 100 * float(re.sub('record-', '', xml_id))
    xml_id = str(int(xml_id))
    if len(xml_id) < 6:
        difference = 6 - len(xml_id)
        xml_id = '0' * difference + xml_id
    return xml_id

main()
