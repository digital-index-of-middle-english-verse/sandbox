from lxml import etree
import copy
import os
import re

# Top-level variables

source_file = '../../dimev/data/Records.xml'
mec_source = '../../external-resources/MEC/bib_all.xml'
namespace = '{http://www.w3.org/XML/1998/namespace}'

# Variables for atomization
#output_dir = '../../dimev/data/records'
#cross_ref_output_file = os.path.join(output_dir, 'cross_references.xml')

def main():
    tree = etree.parse(source_file)
    root = tree.getroot()  # root element <records>
    mec_to_dimev_xwalk = process_mec(mec_source)
    for record in root.findall('record'):
        record = extract_imev_etc(record)
        record = add_mec_refs(record, mec_to_dimev_xwalk)
    etree.indent(tree, space="    ", level=0)
    tree.write(source_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print('Done')

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

def add_mec_refs(record, mec_to_dimev_xwalk):
    dimev_id = record.get(namespace + 'id')
    if dimev_id is not None:
        dimev_id = re.sub('record-', '', dimev_id)
        for item in mec_to_dimev_xwalk:
            if dimev_id in item[1]:
                new_repertory = etree.Element('repertory', key='MECompendium')
                new_repertory.text = item[0]
                if record.find('repertories') is None:
                    record.insert(2, new_repertory)
                else:
                    repertories = record.find('repertories')
                    repertories.append(new_repertory)
    return record

def remove_alpha(record):
    # Remove the <alpha> child element if it exists.
    alpha = record.find('alpha')
    if alpha is not None:
        record.remove(alpha)
    return record

def extract_imev_etc(record):
    # Extract NIMEV and IMEV references to child element <repertories>, which is created if it does not exist.
    new_repertories = etree.Element('repertories')
    junk_values = {'', 'n', 'C16', 'C 19', 'delete', 'delete C16', 'delete: C16', 'delete: prose', 'Dubar', 'Dunbar (?)', 'Dunbar', 'not ME', 'Old English', 'post-1500', 'post medieval', 'post-medieval', 'prose', 'Skelton'} # @imev and @nimev values that map to no repertory
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
            new_repertories.append(repertory)
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
                        new_repertories.append(repertory)
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
                new_repertories.append(repertory)
        if len(new_repertories): # test for children
            if record.find('repertories') is None:
                record.insert(2, new_repertories)
            else:
                repertories = record.find('repertories')
                repertories.extend(new_repertories)
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
