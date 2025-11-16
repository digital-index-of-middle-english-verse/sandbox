import os
from lxml import etree

# top-level variables

src_dir = '../../dimev/data/'
source_file = 'Manuscripts.xml'
mssindex_xml = 'MSSIndex.xml'
namespace = '{http://www.w3.org/XML/1998/namespace}'

def main():
    tree = etree.parse(src_dir + source_file)
    root = tree.getroot()

    # Create union of Manuscripts.xml and MSSIndex.xml
    root = unify_files(root)

    print('All transformations complete')
    etree.indent(tree, space="    ", level=0)
    tree.write(src_dir + source_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print(f'Wrote the updated tree to {source_file}')

def unify_files(root):
    print('Reconciling Manuscripts.xml and MSSIndex.xml')
    tree2 = etree.parse(src_dir + mssindex_xml)
    root2 = tree2.getroot()
    count_new = 0
    for location in root2:
        loc_val2 = location.get('key')
        for repository in location:
            repo_val2 = repository.get('key')
            for item2 in repository:
                if item2.get(namespace + 'id') is not None:
                    root, count_new = write_to_root(root, item2, loc_val2, repo_val2, count_new)
    print(f'Wrote {count_new} items to Manuscripts.xml')
    return root

def write_to_root(root, item2, loc2_val, repo2_val, count_new):
    itemID2 = item2.get(namespace + 'id')
    shelfmark2 = item2.find('desc')
    lang2 = item2.find('lang')
    item_id_found = False
    for item in root:
        itemID1 = item.get(namespace + 'id')
        if itemID1 == itemID2:
            # remove current child elements
            for child in item:
                item.remove(child)
            # create new child elements
            loc_el = etree.Element('loc')
            loc_el.text = loc2_val
            repo_el = etree.Element('repos')
            repo_el.text = repo2_val
            # insert new elements
            item.insert(0, loc_el)
            item.insert(1, repo_el)
            item.insert(2, shelfmark2)
            if lang2 is not None:
                item.insert(3, lang2)
            item_id_found = True
            break
    if item_id_found == False:
        loc_el = etree.Element('loc')
        loc_el.text = loc2_val
        item2.insert(0, loc_el)
        repo_el = etree.Element('repos')
        repo_el.text = repo2_val
        item2.insert(1, repo_el)
        count_el = item2.find('count')
        item2.remove(count_el)
        root.append(item2)
        count_new += 1
    return root, count_new

main()
