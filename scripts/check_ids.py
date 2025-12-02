import glob
import xml.etree.ElementTree as ET

id_registry = set()
checks = 0
namespace = '{http://www.w3.org/XML/1998/namespace}'

# Find all XML files in the directory
data_dir = '../../dimev/data/'
xml_files = glob.glob(data_dir + '*.xml')

for file in xml_files:
    tree = ET.parse(file)
    root = tree.getroot()

    for elem in root.iter():
        if namespace + 'id' in elem.attrib:  # Check if element has xml:id
            checks += 1
            xml_id = elem.attrib[namespace + 'id']
            if xml_id in id_registry:
                print(f"Duplicate xml:id found: {xml_id} in file {file}")
            else:
                id_registry.add(xml_id)

print(f"Check complete with {checks} checks.")
