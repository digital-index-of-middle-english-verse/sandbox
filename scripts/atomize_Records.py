# This script accomplishes the first four items listed in Documentation under
# section 2.2.3 ("Technical direction" for Records.xml)

from lxml import etree
import copy
import os
import re

# Background on the function format_id: DIMEV ids are integers 1-6889, with two
# optional decimal spaces. To create good unique file names I move the decimal
# point two places to the right and pad with leading zeros

def format_id(xml_id):
    # delete the invariant prefix, convert to float, and multiply by 100 for
    # integer representation

    xml_id = 100 * float(re.sub('record-', '', xml_id))
    xml_id = str(int(xml_id))
    # pad with leading zeros
    if len(xml_id) < 6:
        difference = 6 - len(xml_id)
        xml_id = '0' * difference + xml_id
    return xml_id

def process_record(record):
    # Remove the <alpha> child element if it exists. For explanation see the
    # documentation, section 2.2.2.4 and 2.2.3

    alpha = record.find('alpha')
    if alpha is not None:
        record.remove(alpha)

    # Extract NIMEV and IMEV references (currently attributes of <record>) to a
    # new child element <repertories>.

    # Create a dictionary of attribute values to be extracted from each <record>
    rep_attrs = ["nimev", "imev"]

    # Only proceed if any of these attributes exist.
    if any(attr in record.attrib for attr in rep_attrs):
        # Create a new <repertories> element.
        repertories = etree.Element("repertories")
        for attr in rep_attrs:
            if attr in record.attrib:
            # Pop the attribute value from the record.
                value = record.attrib.pop(attr)

                # The 'nimev' attribute has been used inconsistently, to
                # reference three different 'namespaces'/'repertories'. Most
                # 'nimev' values are indeed references to the repertory
                # recorded in Bibliography.xml as xml:id 'NIMEV', but some are
                # really references to Ringler1992 and others are to Ringer1988
                # (I refer to the xml:ids of items in Bibliography.xml).
                # These references must be disambiguated.

                if 'TM' in value: # 'TM' abbreviates 'Tudor Manuscript', an alternate reference to Ringler1992
                    attr = 'Ringler1992'
                    value = re.sub('TM', '', value).strip()
                elif 'TP' in value: # 'TP' abbreviates 'Tudor Manuscript', an alternate reference to Ringler1988
                    attr = 'Ringler1988'
                    value = re.sub('TP', '', value).strip()
                else:
                    attr = 'NIMEV' # the corresponding key in Bibliography.XML is all uppercase

                # Create a new <repertory> element with key set to the attribute name.
                repertory = etree.Element("repertory", key=attr)
                repertory.text = value
                repertories.append(repertory)

        # Insert the new <repertories> element into the <record>, in second position (following <name>)
        record.insert(1, repertories)

    return record

def main():
    # Iterate over each 'record' element in the original tree
    record_count = 0
    cross_ref_count = 0
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
            xml_id = record.get("{http://www.w3.org/XML/1998/namespace}id")
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

# Top-level variables

source_file = '../../dimev/data/Records.xml'
output_dir = '../artefacts/records'
cross_ref_output_file = os.path.join(output_dir, 'cross_references.xml')

tree = etree.parse(source_file)
root = tree.getroot()  # root element <records>
cross_refs = etree.Element("records") # Create a new root for cross-references

# Workflow

# Create the output directory if it does not exist
if not os.path.exists(output_dir):
    os.makedir(output_dir)

main()
